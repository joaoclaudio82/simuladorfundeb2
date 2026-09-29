import json
import zipfile
from sqlalchemy import select
from app.db import schema as s
from app.db.session import get_engine
from app.db.codec import unpack, sha256, json_dumps
from app.repositories.common import audit


def import_live(path, *, engine=None, dry_run=False):
    engine = engine or get_engine()
    rows = []
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "fundeb-live-scenarios-v1":
            raise ValueError("Formato de captura inválido.")
        for record in manifest["scenarios"]:
            payload = archive.read(record["file"])
            result = unpack(payload, record["sha256"])
            if result["cenario_id"] != record["id"]:
                raise ValueError("ID de cenário divergente.")
            rows.append((result, payload, record["sha256"]))
    added = identical = 0
    with engine.begin() as conn:
        for result, payload, digest in rows:
            ident = result["cenario_id"]
            old = conn.execute(
                select(s.scenarios.c.snapshot_sha256).where(s.scenarios.c.id == ident)
            ).scalar()
            if old:
                if old != digest:
                    raise ValueError(
                        "Captura conflita com um cenário existente. Importação cancelada."
                    )
                identical += 1
                continue
            if not dry_run:
                # Unknown ownership/base processing version remains unknown; do not invent provenance.
                conn.execute(
                    s.scenarios.insert().values(
                        id=ident,
                        created_at=result["criado_em"],
                        owner_cpf=None,
                        base_id=result["base"].get("base_id"),
                        base_version=None,
                        engine_version=result["versao_motor"],
                        request_json=json_dumps(result["requisicao"]),
                        snapshot=payload,
                        snapshot_sha256=digest,
                        response_json=None,
                    )
                )
                from app.repositories.scenarios import store_result_projection

                store_result_projection(conn, ident, result["resultados"])
                audit(
                    conn, "scenario.import-live", ident, {"sha256": digest, "ownership": "unknown"}
                )
            added += 1
    return {"imported": added, "identical": identical, "dry_run": dry_run}
