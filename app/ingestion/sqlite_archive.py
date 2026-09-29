"""Migração somente de leitura do banco unificado legado para PostgreSQL.

SQLite é aceito apenas como arquivo de origem; nunca como banco da aplicação.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import zipfile

from app.db.backup import _encode, restore, verify_backup
from app.db.codec import json_dumps
from app.db.schema import metadata


def _archive_sqlite(source_path, destination):
    source_path = Path(source_path).resolve(strict=True)
    manifest = {"format": "fundeb-database-v1", "revision": "0001", "tables": {}}
    with TemporaryDirectory(prefix="fundeb-legacy-") as directory:
        # backup() includes committed WAL transactions without altering the source file.
        source = sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True)
        snapshot = sqlite3.connect(str(Path(directory) / "snapshot.db"))
        snapshot.row_factory = sqlite3.Row
        try:
            source.backup(snapshot)
            tables = {
                r[0]
                for r in snapshot.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            if tables != set(metadata.tables) | {"alembic_version"}:
                raise ValueError(
                    "Esquema SQLite não reconhecido integralmente; nenhum dado foi migrado. Para o banco antigo de usuários, use import-users."
                )
            revisions = [r[0] for r in snapshot.execute("SELECT version_num FROM alembic_version")]
            if revisions != ["0001"]:
                raise ValueError("Revisão SQLite não suportada; origem preservada.")
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with (
                os.fdopen(descriptor, "wb") as file,
                zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED) as archive,
            ):
                for table in metadata.sorted_tables:
                    columns = {r[1] for r in snapshot.execute(f'PRAGMA table_info("{table.name}")')}
                    if columns != set(table.columns.keys()):
                        raise ValueError(
                            f"Colunas divergentes na tabela {table.name}; importação cancelada."
                        )
                    keys = ",".join('"' + c.name + '"' for c in table.primary_key.columns)
                    query = f'SELECT * FROM "{table.name}" ORDER BY {keys}'
                    digest, count = hashlib.sha256(), 0
                    with archive.open(table.name + ".jsonl", "w") as member:
                        for row in snapshot.execute(query):
                            line = (json_dumps(_encode(dict(row))) + "\n").encode()
                            member.write(line)
                            digest.update(line)
                            count += 1
                    manifest["tables"][table.name] = {"rows": count, "sha256": digest.hexdigest()}
                archive.writestr("manifest.json", json_dumps(manifest))
        finally:
            source.close()
            snapshot.close()
    return verify_backup(destination)


def import_sqlite(path, *, engine=None, dry_run=False):
    with TemporaryDirectory(prefix="fundeb-transfer-") as directory:
        archive = Path(directory) / "legacy.zip"
        manifest = _archive_sqlite(path, archive)
        if not dry_run:
            restore(archive, engine=engine)
    return {
        "source": "legacy-sqlite",
        "destination": "postgresql",
        "dry_run": dry_run,
        "tables": {name: value["rows"] for name, value in manifest["tables"].items()},
    }
