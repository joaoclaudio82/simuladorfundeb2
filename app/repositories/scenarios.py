"""Cenários duráveis e imutáveis; leitura e exportação nunca chamam o motor."""

import json
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db import schema as s
from app.db.session import get_engine
from app.db.codec import pack, unpack, sha256, json_dumps, dataclass_values
from app.repositories.common import now, audit


class RepositorioCenarios:
    def __init__(self, capacidade=None, *, engine=None):
        self._engine = engine

    @property
    def engine(self):
        return self._engine or get_engine()

    def guardar(self, resultado, *, owner_cpf=None, base_version=None, resposta=None):
        payload = pack(dataclass_values(resultado))
        digest = sha256(payload)
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(s.scenarios.c.snapshot_sha256).where(
                    s.scenarios.c.id == resultado.cenario_id
                )
            ).scalar()
            if existing:
                if existing != digest:
                    raise ValueError("Cenário imutável: o ID já possui um resultado diferente.")
                return resultado.cenario_id
            conn.execute(
                s.scenarios.insert().values(
                    id=resultado.cenario_id,
                    created_at=resultado.criado_em,
                    owner_cpf=owner_cpf,
                    base_id=resultado.base.get("base_id"),
                    base_version=base_version,
                    engine_version=resultado.versao_motor,
                    request_json=json_dumps(resultado.requisicao),
                    snapshot=payload,
                    snapshot_sha256=digest,
                    response_json=json_dumps(resposta) if resposta is not None else None,
                )
            )
            store_result_projection(conn, resultado.cenario_id, resultado.resultados)
            audit(
                conn,
                "scenario.save",
                resultado.cenario_id,
                {"base_version": base_version, "sha256": digest},
            )
        return resultado.cenario_id

    def obter(self, cenario_id):
        from app.services.cenarios import ResultadoCenario

        with self.engine.connect() as conn:
            row = conn.execute(
                select(s.scenarios.c.snapshot, s.scenarios.c.snapshot_sha256).where(
                    s.scenarios.c.id == cenario_id
                )
            ).first()
        return ResultadoCenario(**unpack(row.snapshot, row.snapshot_sha256)) if row else None

    def resposta_original(self, cenario_id):
        with self.engine.connect() as conn:
            result = conn.execute(
                select(s.scenarios.c.response_json).where(s.scenarios.c.id == cenario_id)
            ).scalar()
        return json.loads(result) if result else None

    def listar(self, owner_cpf, *, admin=False, limit=50, offset=0):
        query = select(
            s.scenarios.c.id,
            s.scenarios.c.created_at,
            s.scenarios.c.base_id,
            s.scenarios.c.base_version,
            s.scenarios.c.engine_version,
            s.scenarios.c.request_json,
        )
        if not admin:
            query = query.where(s.scenarios.c.owner_cpf == owner_cpf)
        with self.engine.connect() as conn:
            rows = conn.execute(
                query.order_by(s.scenarios.c.created_at.desc(), s.scenarios.c.id)
                .limit(limit)
                .offset(offset)
            ).mappings()
            return [{**dict(r), "request_json": json.loads(r["request_json"])} for r in rows]

    def exportar(self, resultado, formato, recorte, selecionadas, gerador):
        selection = json_dumps({"recorte": recorte, "selecionadas": selecionadas})
        key = sha256(json_dumps([resultado.cenario_id, formato, selection]).encode())
        with self.engine.connect() as conn:
            row = conn.execute(select(s.exports).where(s.exports.c.key == key)).mappings().first()
        if row:
            if sha256(row["content"]) != row["sha256"]:
                raise ValueError("Exportação corrompida.")
            return row["content"]
        content = gerador(resultado, recorte, selecionadas)
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    s.exports.insert().values(
                        key=key,
                        scenario_id=resultado.cenario_id,
                        format=formato,
                        selection_json=selection,
                        content=content,
                        sha256=sha256(content),
                        created_at=now(),
                    )
                )
                audit(
                    conn, "export.save", key, {"scenario": resultado.cenario_id, "format": formato}
                )
        except IntegrityError:
            # Another worker may have produced the same export; return the committed canonical bytes.
            with self.engine.connect() as conn:
                row = (
                    conn.execute(select(s.exports).where(s.exports.c.key == key)).mappings().first()
                )
                if row is None:
                    raise
                if sha256(row["content"]) != row["sha256"]:
                    raise ValueError("Exportação corrompida.")
                return row["content"]
        return content


def store_result_projection(conn, ident, results):
    from app.api.legacy import sanitize_for_json

    for variant, frame in results.items():
        rows = [
            {
                "scenario_id": ident,
                "variant": variant,
                "ibge": int(row["ibge"]),
                "position": i,
                "values_json": json_dumps(sanitize_for_json(row)),
            }
            for i, row in enumerate(frame.to_dict("records"))
        ]
        for offset in range(0, len(rows), 1000):
            conn.execute(s.scenario_results.insert(), rows[offset : offset + 1000])
