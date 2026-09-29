"""Backup lógico verificável e restauração transacional somente em banco vazio."""

import base64
import hashlib
import json
import os
from pathlib import Path
import zipfile
from sqlalchemy import select, func, text
from app.db.schema import metadata
from app.db.session import get_engine
from app.db.codec import json_dumps


def _encode(row):
    return {
        k: {"__binary__": base64.b64encode(v).decode("ascii")} if isinstance(v, bytes) else v
        for k, v in row.items()
    }


def _decode(row):
    return {
        k: base64.b64decode(v["__binary__"], validate=True)
        if isinstance(v, dict) and set(v) == {"__binary__"}
        else v
        for k, v in row.items()
    }


def backup(path, *, engine=None):
    engine = engine or get_engine()
    path = Path(path)
    # O_EXCL prevents accidental replacement of an existing backup; mode protects password hashes/CPF.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    manifest = {"format": "fundeb-database-v1", "revision": "0001", "tables": {}}
    try:
        with os.fdopen(descriptor, "wb") as target, engine.connect() as conn:
            if engine.dialect.name == "postgresql":
                conn = conn.execution_options(isolation_level="REPEATABLE READ")
            with (
                conn.begin(),
                zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive,
            ):
                if engine.dialect.name == "sqlite":
                    conn.exec_driver_sql("BEGIN")
                manifest["revision"] = conn.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                for table in metadata.sorted_tables:
                    h, count = hashlib.sha256(), 0
                    with archive.open(table.name + ".jsonl", "w") as member:
                        query = select(table).order_by(*table.primary_key.columns)
                        for row in conn.execute(query.execution_options(yield_per=500)).mappings():
                            line = (json_dumps(_encode(dict(row))) + "\n").encode("utf-8")
                            member.write(line)
                            h.update(line)
                            count += 1
                    manifest["tables"][table.name] = {"rows": count, "sha256": h.hexdigest()}
                archive.writestr("manifest.json", json_dumps(manifest))
        verify_backup(path)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return manifest


def verify_backup(path):
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "fundeb-database-v1" or manifest.get("revision") != "0001":
            raise ValueError("Backup incompatível.")
        if set(manifest["tables"]) != set(metadata.tables):
            raise ValueError("Backup incompleto: tabelas divergentes.")
        names = ["manifest.json"] + [t + ".jsonl" for t in metadata.tables]
        if len(archive.namelist()) != len(names) or set(archive.namelist()) != set(names):
            raise ValueError("Estrutura do backup inválida.")
        for name, expected in manifest["tables"].items():
            h, count = hashlib.sha256(), 0
            with archive.open(name + ".jsonl") as member:
                for line in member:
                    h.update(line)
                    count += 1
                    _decode(json.loads(line))
            if count != expected["rows"] or h.hexdigest() != expected["sha256"]:
                raise ValueError(f"Backup corrompido na tabela {name}.")
    return manifest


def restore(path, *, engine=None):
    manifest = verify_backup(path)
    engine = engine or get_engine()
    with engine.begin() as conn, zipfile.ZipFile(path) as archive:
        for table in metadata.sorted_tables:
            if conn.execute(select(func.count()).select_from(table)).scalar_one():
                raise ValueError("Restauração exige banco vazio; nenhum registro foi substituído.")
        for table in metadata.sorted_tables:
            rows = []
            with archive.open(table.name + ".jsonl") as member:
                for line in member:
                    rows.append(_decode(json.loads(line)))
                    if len(rows) >= 500:
                        conn.execute(table.insert(), rows)
                        rows.clear()
            if rows:
                conn.execute(table.insert(), rows)
    return manifest
