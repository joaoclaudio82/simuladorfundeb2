"""Conferência operacional das fontes e bases já carregadas no PostgreSQL."""

from sqlalchemy import select, func
from app.db import schema as s
from app.db.codec import sha256, unpack
from app.db.session import get_engine


def inventory(engine=None):
    engine = engine or get_engine()
    report = {"database": "postgresql", "files": 0, "bytes": 0, "bases": []}
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="REPEATABLE READ")
        with conn.begin():
            for row in conn.execute(select(s.source_files)).mappings():
                if sha256(row["content"]) != row["sha256"] or len(row["content"]) != row["size"]:
                    raise ValueError("Arquivo original corrompido no banco.")
                report["files"] += 1
                report["bytes"] += row["size"]
            bases = (
                conn.execute(
                    select(s.base_versions)
                    .join(
                        s.base_aliases, s.base_aliases.c.version_id == s.base_versions.c.version_id
                    )
                    .order_by(s.base_versions.c.year)
                )
                .mappings()
                .all()
            )
            for row in bases:
                bundle = unpack(row["snapshot"], row["snapshot_sha256"])
                base = bundle["base"]
                version = row["version_id"]
                counts = {
                    name: conn.execute(
                        select(func.count()).select_from(table).where(table.c.version_id == version)
                    ).scalar_one()
                    for name, table in [
                        ("entities", s.entities),
                        ("categories", s.categories),
                        ("enrollments", s.enrollments),
                    ]
                }
                matrix = base["matriculas"][base["pesos"]["etapa"].tolist()]
                if (
                    counts["entities"] != len(base["entes"])
                    or counts["categories"] != len(base["pesos"])
                    or counts["enrollments"] != int((matrix != 0).sum().sum())
                ):
                    raise ValueError(f"Contagens inconsistentes na base {row['base_id']}.")
                report["bases"].append(
                    {
                        "year": row["year"],
                        "base_id": row["base_id"],
                        "version_id": version,
                        **counts,
                    }
                )
            if {row["year"] for row in bases} != {2024, 2025, 2026}:
                raise ValueError("É necessário importar as bases 2024, 2025 e 2026.")
            for name, table in [
                ("users", s.users),
                ("scenarios", s.scenarios),
                ("exports", s.exports),
                ("legacy_runs", s.legacy_runs),
            ]:
                report[name] = conn.execute(select(func.count()).select_from(table)).scalar_one()
    return report
