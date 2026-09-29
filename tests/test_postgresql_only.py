"""PostgreSQL obrigatório e origem SQLite estritamente de leitura na migração."""

import builtins
import json
from pathlib import Path
import sqlite3

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import sqlite as sqlite_dialect

from app.core.config import database_url, validate_configuration
from app.db import schema as s
from app.db.codec import dataclass_values, pack, sha256
from app.db.session import engine_for
from app.db.backup import backup
from app.ingestion.sqlite_archive import import_sqlite
from app.repositories.scenarios import RepositorioCenarios
from app.schemas.cenarios import CenarioRequest
from app.services.cenarios import executar_cenario


@pytest.mark.parametrize(
    "url", ["sqlite:///fundeb.db", "sqlite:///:memory:", "mysql+pymysql://example/fundeb"]
)
def test_no_non_postgresql_backend(url, monkeypatch):
    monkeypatch.setenv("FUNDEB_DATABASE_URL", url)
    with pytest.raises(ValueError, match="PostgreSQL"):
        database_url()
    with pytest.raises(ValueError, match="PostgreSQL"):
        engine_for(url)


def test_missing_connection_does_not_create_sqlite(monkeypatch):
    monkeypatch.delenv("FUNDEB_DATABASE_URL", raising=False)
    monkeypatch.delenv("FUNDEB_DB_HOST", raising=False)
    monkeypatch.setenv("FUNDEB_USERS_DB", "/tmp/must-not-be-used.db")
    with pytest.raises(RuntimeError, match="PostgreSQL é obrigatório"):
        database_url()


def test_files_configuration_rejected(monkeypatch):
    monkeypatch.setenv("FUNDEB_DATA_SOURCE", "files")
    with pytest.raises(RuntimeError, match="somente PostgreSQL"):
        validate_configuration()


def test_missing_database_base_never_falls_back_to_files(engine, monkeypatch):
    monkeypatch.setenv("FUNDEB_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    from app.ingestion.fundeb_dataset import carregar_dataset

    with pytest.raises(ValueError, match="Base não importada"):
        carregar_dataset(2024)


def test_every_exercise_runs_without_reading_original_files(postgres_seed, monkeypatch):
    import app.main as main
    from app.auth.deps import get_current_user
    from app.auth.models import Role, UserRecord
    from app.core.config import ROOT

    blocked = {
        str((ROOT / row["path"]).resolve())
        for row in json.loads((ROOT / "data/manifesto_arquivos.json").read_text())["files"]
    }
    original_open, original_path_open = builtins.open, Path.open

    def guard(file):
        if isinstance(file, (str, Path)) and str(Path(file).resolve()) in blocked:
            raise AssertionError("A aplicação tentou ler um arquivo de dados durante a execução.")

    def checked_open(file, *args, **kwargs):
        guard(file)
        return original_open(file, *args, **kwargs)

    def checked_path_open(file, *args, **kwargs):
        guard(file)
        return original_path_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", checked_open)
    monkeypatch.setattr(Path, "open", checked_path_open)
    main.app.dependency_overrides[get_current_user] = lambda: UserRecord(
        cpf="52998224725", role=Role.admin
    )
    try:
        with TestClient(main.app) as client:
            assert client.get("/api/bases").status_code == 200
            for year in (2024, 2025, 2026):
                prefix = "/api" if year == 2024 else f"/api/{year}"
                for endpoint in ["estados", "pesos", "etapas", "cenario-atual/resumo"]:
                    assert client.get(prefix + "/" + endpoint).status_code == 200
                response = client.post(prefix + "/simular", json={})
                assert response.status_code == 200, response.text
                assert response.headers["x-simulation-id"]
                assert client.get(f"/api/bases/fundeb-{year}/calibracao").status_code == 200
    finally:
        main.app.dependency_overrides.clear()


def test_database_inventory_checks_all_sources(postgres_seed):
    from app.services.database_inventory import inventory

    report = inventory(engine=postgres_seed)
    assert report["database"] == "postgresql"
    assert report["files"] == 33
    assert [(r["year"], r["entities"], r["categories"]) for r in report["bases"]] == [
        (2024, 5595, 41),
        (2025, 5595, 319),
        (2026, 5596, 319),
    ]


def test_unified_sqlite_migration_preserves_entire_database(
    engine, postgres_engine_factory, base_sintetica, tmp_path
):
    from app.repositories.bases import store_source
    from app.auth.security import hash_password, verify_password

    result = executar_cenario(CenarioRequest(), base_sintetica)
    repository = RepositorioCenarios(engine=engine)
    repository.guardar(result)
    repository.exportar(result, "xlsx", "universo", [], lambda *_: b"PK-original-export")
    password_hash = hash_password("preserved-password")
    with engine.begin() as conn:
        store_source(conn, "original.xlsx", b"original\x00\xff", "legacy")
        conn.execute(
            s.users.insert().values(
                cpf="52998224725",
                password_hash=password_hash,
                role="admin",
                nome="João",
                ativo=1,
                created_at="2024-01-01T12:00:00",
            )
        )
    source = tmp_path / "fundeb.db"
    # Reproduce the old unified SQLite layout; it is only a migration input.
    with sqlite3.connect(source) as sqlite, engine.connect() as conn:
        sqlite.execute("CREATE TABLE alembic_version(version_num TEXT PRIMARY KEY)")
        sqlite.execute("INSERT INTO alembic_version VALUES ('0001')")
        for table in s.metadata.sorted_tables:
            sqlite.execute(str(CreateTable(table).compile(dialect=sqlite_dialect.dialect())))
            names = ",".join('"' + c.name + '"' for c in table.columns)
            placeholders = ",".join("?" for _ in table.columns)
            for row in conn.execute(select(table)):
                sqlite.execute(
                    f'INSERT INTO "{table.name}" ({names}) VALUES ({placeholders})', tuple(row)
                )
    before = source.read_bytes()
    target = postgres_engine_factory()
    dry = import_sqlite(source, engine=target, dry_run=True)
    assert dry["tables"]["scenarios"] == 1
    assert import_sqlite(source, engine=target)["tables"] == dry["tables"]
    restored = RepositorioCenarios(engine=target).obter(result.cenario_id)
    assert sha256(pack(dataclass_values(restored))) == sha256(pack(dataclass_values(result)))
    with target.connect() as conn:
        saved_hash = conn.execute(select(s.users.c.password_hash)).scalar_one()
        assert saved_hash == password_hash
        assert verify_password("preserved-password", saved_hash)
        assert conn.execute(select(s.exports.c.content)).scalar_one() == b"PK-original-export"
    assert backup(tmp_path / "original.zip", engine=engine) == backup(
        tmp_path / "restored.zip", engine=target
    )
    assert source.read_bytes() == before
    with pytest.raises(ValueError, match="banco vazio"):
        import_sqlite(source, engine=target)
