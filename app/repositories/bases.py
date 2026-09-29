"""Bases imutáveis, arquivos originais e projeções para consulta SQL."""

from contextlib import nullcontext
from pathlib import Path
from dataclasses import fields
import json
import numpy as np
import pandas as pd
from sqlalchemy import select
from app.db import schema as s
from app.db.session import get_engine
from app.db.codec import pack, unpack, sha256, json_dumps, dataclass_values
from app.repositories.common import now, audit


def store_source(conn, path, content, commit, kind="original"):
    digest = sha256(content)
    if (
        conn.execute(
            select(s.source_files.c.sha256).where(s.source_files.c.sha256 == digest)
        ).scalar()
        is None
    ):
        conn.execute(
            s.source_files.insert().values(sha256=digest, size=len(content), content=content)
        )
    ident = sha256(json_dumps([path, digest, commit]).encode())
    if conn.execute(select(s.archives.c.id).where(s.archives.c.id == ident)).scalar() is None:
        conn.execute(
            s.archives.insert().values(
                id=ident, path=path, source_sha256=digest, source_commit=commit, kind=kind
            )
        )
    return digest


def _batch(conn, table, rows, size=5000):
    for offset in range(0, len(rows), size):
        conn.execute(table.insert(), rows[offset : offset + size])


def store_base(
    base,
    dataset,
    source_contents,
    etl_hash,
    commit,
    *,
    engine=None,
    activate=False,
    connection=None,
):
    engine = engine or get_engine()
    payload = pack({"base": dataclass_values(base), "dataset": dataclass_values(dataset)})
    snapshot_hash = sha256(payload)
    identity = {
        "base_id": base.base_id,
        "snapshot": snapshot_hash,
        "etl": etl_hash,
        "sources": {p: sha256(v) for p, v in sorted(source_contents.items())},
    }
    version = sha256(json_dumps(identity).encode())
    # Transaction includes originals, snapshot, projections and alias. Failure leaves no partial version.
    with nullcontext(connection) if connection is not None else engine.begin() as conn:
        existing = conn.execute(
            select(s.base_versions.c.version_id).where(s.base_versions.c.version_id == version)
        ).scalar()
        if not existing:
            for path, content in source_contents.items():
                store_source(conn, path, content, commit)
            conn.execute(
                s.base_versions.insert().values(
                    version_id=version,
                    base_id=base.base_id,
                    year=dataset.ano,
                    created_at=now(),
                    manifest=json_dumps(base.manifesto),
                    snapshot=payload,
                    snapshot_sha256=snapshot_hash,
                    etl_sha256=etl_hash,
                    source_commit=commit,
                )
            )
            _batch(
                conn,
                s.base_sources,
                [
                    {"version_id": version, "path": p, "source_sha256": sha256(v)}
                    for p, v in source_contents.items()
                ],
            )
            _batch(
                conn,
                s.entities,
                [
                    {
                        "version_id": version,
                        "ibge": int(row.ibge),
                        "position": i,
                        "uf": row.uf,
                        "name": row.nome,
                        "network": row.tipo_rede,
                    }
                    for i, row in enumerate(base.entes.itertuples())
                ],
            )
            _batch(
                conn,
                s.categories,
                [
                    {
                        "version_id": version,
                        "code": row.etapa,
                        "position": i,
                        "name": row.nome,
                        "weight_vaaf": float(row.peso_vaaf),
                        "weight_vaat": float(row.peso_vaat),
                    }
                    for i, row in enumerate(base.pesos.itertuples())
                ],
            )
            # Sparse projection: omitted cells are exactly zero. Full matrix incl. dtypes/index is in snapshot.
            values = base.matriculas[base.etapas].to_numpy()
            if not np.isfinite(values).all():
                raise ValueError(
                    "Matrículas não finitas: importação interrompida sem alterar a base anterior."
                )
            ii, jj = np.nonzero(values)
            ids = base.matriculas.ibge.to_numpy()
            _batch(
                conn,
                s.enrollments,
                [
                    {
                        "version_id": version,
                        "ibge": int(ids[i]),
                        "category": base.etapas[j],
                        "value": float(values[i, j]),
                    }
                    for i, j in zip(ii, jj)
                ],
            )
            from app.api.legacy import sanitize_for_json

            _batch(
                conn,
                s.financial_inputs,
                [
                    {
                        "version_id": version,
                        "ibge": int(row["ibge"]),
                        "values_json": json_dumps(sanitize_for_json(row)),
                    }
                    for row in base.complementar.to_dict("records")
                ],
            )
            audit(conn, "base.import", version, {"base_id": base.base_id, "source_commit": commit})
        current = conn.execute(
            select(s.base_aliases.c.version_id).where(s.base_aliases.c.base_id == base.base_id)
        ).scalar()
        if current is None:
            conn.execute(s.base_aliases.insert().values(base_id=base.base_id, version_id=version))
        elif activate and current != version:
            conn.execute(
                s.base_aliases.update()
                .where(s.base_aliases.c.base_id == base.base_id)
                .values(version_id=version)
            )
            audit(conn, "base.activate", version, {"previous_version": current})
    return version


def load_bundle(base_id=None, *, year=None, version=None, engine=None):
    engine = engine or get_engine()
    with engine.connect() as conn:
        if version:
            query = select(s.base_versions).where(s.base_versions.c.version_id == version)
        else:
            query = select(s.base_versions).join(
                s.base_aliases, s.base_aliases.c.version_id == s.base_versions.c.version_id
            )
            query = (
                query.where(s.base_aliases.c.base_id == base_id)
                if base_id
                else query.where(s.base_versions.c.year == year)
            )
        rows = conn.execute(query).mappings().all()
    if len(rows) != 1:
        raise ValueError(
            f"Base não importada ou ambígua: {base_id or year or version}. Execute import-data."
        )
    row = rows[0]
    bundle = unpack(row["snapshot"], row["snapshot_sha256"])
    return bundle, row["version_id"]


def load_base(base_id=None, *, version=None, engine=None):
    from app.services.bases import Base

    bundle, version = load_bundle(base_id, version=version, engine=engine)
    base = Base(**bundle["base"])
    # Outside legacy dataclass/API metadata to keep its historical response contract intact.
    base.version_id = version
    return base


def load_dataset(year, *, engine=None):
    from app.ingestion.fundeb_dataset import FundebDataset

    bundle, version = load_bundle(year=year, engine=engine)
    ds = FundebDataset(**bundle["dataset"])
    ds.version_id = version
    return ds


def catalog(engine=None):
    engine = engine or get_engine()
    with engine.connect() as conn:
        rows = (
            conn.execute(
                select(s.base_versions.c.manifest)
                .join(s.base_aliases, s.base_aliases.c.version_id == s.base_versions.c.version_id)
                .order_by(s.base_versions.c.year.desc())
            )
            .scalars()
            .all()
        )
    if not rows:
        raise ValueError("Nenhuma base ativa no banco. Execute import-data.")
    bases = [json.loads(row) for row in rows]
    return {"versao_catalogo": 2, "base_padrao": bases[0]["base_id"], "bases": bases}


# Development compatibility: file-backed routes also link each new scenario to an immutable base.
_FILE_VERSIONS = {}
from threading import RLock

_FILE_LOCK = RLock()


def ensure_file_base(base):
    from app.core.config import ROOT
    from app.ingestion.fundeb_dataset import carregar_dataset

    if getattr(base, "version_id", None):
        return base.version_id
    engine = get_engine()
    source_paths = [a["caminho"] for a in base.manifesto["arquivos"]]
    if base.ano_exercicio == 2024:
        source_paths += ["data/cenario_atual_agregada.rda", "data/cenario_ufs_atual.rda"]
    else:
        source_paths += [f"data/{base.ano_exercicio}/dataset.pkl"]
    sources = {p: (ROOT / p).read_bytes() for p in source_paths}
    etl = sha256(
        b"".join(
            (ROOT / p).read_bytes()
            for p in [
                "app/ingestion/fundeb_dataset.py",
                "app/services/bases.py",
                "app/domain/calculo/motor.py",
            ]
        )
    )
    key = (engine, base.base_id, etl, tuple((p, sha256(b)) for p, b in sources.items()))
    with _FILE_LOCK:
        if key not in _FILE_VERSIONS:
            dataset = carregar_dataset(base.ano_exercicio)
            _FILE_VERSIONS[key] = store_base(
                base, dataset, sources, etl, "working-tree", engine=engine
            )
        base.version_id = _FILE_VERSIONS[key]
        return base.version_id
