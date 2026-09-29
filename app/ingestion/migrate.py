"""Importações verificadas e idempotentes. Nunca substituem usuários ou resultados."""

from contextlib import nullcontext
from dataclasses import fields
from pathlib import Path
import json
import sqlite3
import pandas as pd
from sqlalchemy import select
from app.core.config import ROOT
from app.db import schema as s
from app.db.session import get_engine
from app.db.codec import sha256, json_dumps
from app.repositories.bases import store_base, store_source
from app.repositories.common import audit


def assert_dataset_equal(left, right):
    for f in fields(left):
        a, b = getattr(left, f.name), getattr(right, f.name)
        if isinstance(a, pd.DataFrame):
            pd.testing.assert_frame_equal(a, b, check_exact=True)
        elif a != b:
            raise ValueError(f"Dataset divergente: {f.name}")


def prepare_data():
    """Legacy pickles are read only from the checked-in, hash-verified source inventory."""
    from app.ingestion import fundeb_dataset as fd
    from app.services.bases import carregar_base_arquivo, conferir_arquivos

    inventory = json.loads((ROOT / "data/manifesto_arquivos.json").read_text())
    originals = {}
    for record in inventory["files"]:
        content = (ROOT / record["path"]).read_bytes()
        if sha256(content) != record["sha256"]:
            raise ValueError(
                f"Arquivo divergente: {record['path']}. Crie outra versão explícita do inventário."
            )
        originals[record["path"]] = content
    save_cache = fd._salvar_cache
    fd._salvar_cache = lambda *_: (
        None
    )  # ETL validation must not rewrite the existing source caches.
    prepared = []
    try:
        fd._DATASETS.clear()
        for year in (2024, 2025, 2026):
            dataset = fd.carregar_dataset_arquivo(year)
            if year != 2024:
                fresh = getattr(fd, f"construir_dataset_{year}")(usar_cache=False)
                assert_dataset_equal(dataset, fresh)
            base = carregar_base_arquivo(f"fundeb-{year}")
            conferir_arquivos(base.manifesto)
            paths = [a["caminho"] for a in base.manifesto["arquivos"]]
            if year == 2024:
                paths += ["data/cenario_atual_agregada.rda", "data/cenario_ufs_atual.rda"]
            else:
                paths += [f"data/{year}/dataset.pkl"]
            sources = {p: originals[p] for p in paths}
            prepared.append((base, dataset, sources))
    finally:
        fd._salvar_cache = save_cache
    return inventory, originals, prepared


def import_data(*, engine=None, dry_run=False, activate=False):
    inventory, originals, prepared = prepare_data()
    report = {
        "source_commit": inventory["source_commit"],
        "files": len(originals),
        "bytes": sum(map(len, originals.values())),
        "bases": [],
        "dry_run": dry_run,
    }
    if dry_run:
        for base, dataset, _ in prepared:
            report["bases"].append(
                {
                    "base_id": base.base_id,
                    "entities": len(base.entes),
                    "categories": len(base.etapas),
                }
            )
        return report
    engine = engine or get_engine()
    etl_hash = sha256(
        b"".join(
            (ROOT / path).read_bytes()
            for path in [
                "app/ingestion/fundeb_dataset.py",
                "app/services/bases.py",
                "app/domain/calculo/motor.py",
            ]
        )
    )
    with engine.begin() as conn:
        for path, content in originals.items():
            kind = "historical" if path.endswith(".parquet") else "original"
            store_source(conn, path, content, inventory["source_commit"], kind)
        for base, dataset, sources in prepared:
            version = store_base(
                base,
                dataset,
                sources,
                etl_hash,
                inventory["source_commit"],
                engine=engine,
                connection=conn,
                activate=activate,
            )
            report["bases"].append(
                {
                    "base_id": base.base_id,
                    "version_id": version,
                    "entities": len(base.entes),
                    "categories": len(base.etapas),
                }
            )
    return report


def import_users(path, *, engine=None, dry_run=False):
    path = Path(path).resolve(strict=True)
    # SQLite backup API handles WAL consistently; no credentials are printed or rehashed.
    source = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    snapshot = sqlite3.connect(":memory:")
    try:
        source.backup(snapshot)
        snapshot.row_factory = sqlite3.Row
        rows = [
            dict(r)
            for r in snapshot.execute(
                "SELECT cpf,password_hash,role,nome,ativo,created_at FROM users"
            )
        ]
    finally:
        source.close()
        snapshot.close()
    for row in rows:
        if row["role"] not in ("admin", "usuario") or row["ativo"] not in (0, 1):
            raise ValueError("Perfil ou situação inválidos no banco de origem.")
        if not isinstance(row["password_hash"], str) or not row["password_hash"].startswith(
            ("$2a$", "$2b$", "$2y$")
        ):
            raise ValueError(
                "Hash de senha não reconhecido. Migração interrompida sem modificar a origem."
            )
    engine = engine or get_engine()
    created = existing = 0
    with engine.begin() as conn:
        for row in rows:
            previous = (
                conn.execute(select(s.users).where(s.users.c.cpf == row["cpf"])).mappings().first()
            )
            if previous:
                if dict(previous) != row:
                    raise ValueError(
                        "Conflito entre usuários de origem e destino. Nenhum usuário desta importação foi alterado."
                    )
                existing += 1
            else:
                if not dry_run:
                    conn.execute(s.users.insert().values(**row))
                created += 1
        if not dry_run:
            audit(
                conn, "users.import", "legacy-sqlite", {"imported": created, "identical": existing}
            )
    return {"imported": created, "identical": existing, "total": len(rows), "dry_run": dry_run}
