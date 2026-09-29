"""Contratos que evitam perda: reinício, precisão, idempotência, rollback e restore."""

from dataclasses import fields
from pathlib import Path
from io import BytesIO
import copy
import importlib.util
import json
import math
import os
import sqlite3
import uuid
import zipfile
import pandas as pd
import pytest
from sqlalchemy import select, func, text
from app.db import schema as s
from app.db.codec import pack, unpack, sha256
from app.db.session import get_engine, engine_for, migrate
from app.repositories.scenarios import RepositorioCenarios
from app.repositories.bases import store_base, load_base
from app.ingestion.migrate import import_users
from app.db.backup import backup, restore, verify_backup
from services.cenarios import executar_cenario
from schemas.cenarios import CenarioRequest


def assert_result_equal(a, b):
    for f in fields(a):
        left, right = getattr(a, f.name), getattr(b, f.name)
        if isinstance(left, pd.DataFrame):
            pd.testing.assert_frame_equal(left, right, check_exact=True)
        elif (
            isinstance(left, dict) and left and isinstance(next(iter(left.values())), pd.DataFrame)
        ):
            assert list(left) == list(right)
            for key in left:
                pd.testing.assert_frame_equal(left[key], right[key], check_exact=True)
        else:
            assert left == right, f.name


def test_codec_exact_values_types_index_order():
    frame = pd.DataFrame(
        {
            "ibge": [23, 22, 53],
            "fraction": [0.5, 1.2345678901234567, -0.0],
            "optional": [float("nan"), float("inf"), -float("inf")],
            "flag": [True, False, True],
            "text": pd.Series(["Piauí", None, "São Paulo"], dtype=object),
            "category": pd.Categorical(["b", "a", "b"], categories=["b", "a", "z"], ordered=True),
            "nullable": pd.Series([1, None, 3], dtype="Int64"),
        },
        index=[0, 1, 2],
    )
    frame.index.name = "origem"
    payload = pack({"frame": frame, "tuple": (None, 0.1), "nan": float("nan")})
    restored = unpack(payload, sha256(payload))
    pd.testing.assert_frame_equal(frame, restored["frame"], check_exact=True)
    assert math.copysign(1, restored["frame"].fraction.iloc[2]) == -1
    assert restored["tuple"] == (None, 0.1)
    assert math.isnan(restored["nan"])
    with pytest.raises(ValueError, match="SHA-256"):
        unpack(payload + b"x", sha256(payload))


def test_scenarios_survive_restart_and_exceed_30(engine, base_sintetica):
    repository = RepositorioCenarios(engine=engine)
    result = executar_cenario(
        CenarioRequest(receita={"tipo": "crescimento", "taxa": 0.04}), base_sintetica
    )
    original = copy.deepcopy(result)
    repository.guardar(result)
    result.resultados["A"].iloc[0, 0] = 999
    for _ in range(31):
        another = copy.deepcopy(original)
        another.cenario_id = uuid.uuid4().hex
        repository.guardar(another)
    engine.dispose()
    restored = RepositorioCenarios(engine=engine).obter(original.cenario_id)
    assert_result_equal(original, restored)
    with pytest.raises(ValueError, match="imutável"):
        repository.guardar(result)
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(s.scenarios)).scalar_one() == 32


def test_export_bytes_are_preserved_and_no_recalculation(engine, base_sintetica, monkeypatch):
    from services import cenarios

    repository = RepositorioCenarios(engine=engine)
    result = executar_cenario(CenarioRequest(), base_sintetica)
    repository.guardar(result, resposta={"complete": "unchanged"})

    def fail(*args, **kwargs):
        raise AssertionError("Motor/exportador não deve ser chamado na leitura já armazenada")

    original = b"PK-original-xlsx-content"
    assert repository.exportar(result, "xlsx", "universo", [], lambda *_: original) == original
    monkeypatch.setattr(cenarios, "simula_fundeb", fail)
    assert (
        repository.exportar(repository.obter(result.cenario_id), "xlsx", "universo", [], fail)
        == original
    )
    assert repository.resposta_original(result.cenario_id) == {"complete": "unchanged"}


def _legacy_users(path):
    from auth.security import hash_password

    rows = [
        (
            "52998224725",
            hash_password("a-test-password"),
            "admin",
            "João",
            1,
            "2024-01-02T10:15:16+00:00",
        ),
        (
            "11144477735",
            hash_password("another-password"),
            "usuario",
            None,
            0,
            "2025-03-04T11:00:00",
        ),
    ]
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE users(cpf TEXT PRIMARY KEY,password_hash TEXT,role TEXT,nome TEXT,ativo INTEGER,created_at TEXT)"
        )
        conn.executemany("INSERT INTO users VALUES (?,?,?,?,?,?)", rows)
    return rows


def test_user_migration_preserves_hash_and_login(engine, tmp_path):
    from auth.security import verify_password

    source = tmp_path / "users.db"
    expected = _legacy_users(source)
    before = source.read_bytes()
    assert import_users(source, engine=engine, dry_run=True)["imported"] == 2
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(s.users)).scalar_one() == 0
    assert import_users(source, engine=engine)["imported"] == 2
    assert import_users(source, engine=engine)["identical"] == 2
    with engine.connect() as conn:
        rows = conn.execute(select(s.users).order_by(s.users.c.created_at)).all()
    assert [tuple(row) for row in rows] == expected
    assert verify_password("a-test-password", rows[0].password_hash)
    assert source.read_bytes() == before


def test_user_conflict_rolls_back_every_insert(engine, tmp_path):
    source = tmp_path / "users.db"
    expected = _legacy_users(source)
    with engine.begin() as conn:
        conn.execute(
            s.users.insert().values(
                cpf=expected[1][0],
                password_hash="different",
                role="usuario",
                ativo=0,
                created_at="old",
            )
        )
    with pytest.raises(ValueError, match="Conflito"):
        import_users(source, engine=engine)
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(s.users)).scalar_one() == 1


def test_backup_restore_is_exact_and_refuses_nonempty(
    engine, tmp_path, base_sintetica, postgres_engine_factory
):
    from app.repositories.bases import store_source

    result = executar_cenario(CenarioRequest(), base_sintetica)
    RepositorioCenarios(engine=engine).guardar(result)
    source = tmp_path / "users.db"
    _legacy_users(source)
    import_users(source, engine=engine)
    with engine.begin() as conn:
        store_source(conn, "original.xlsx", b"original\x00\xff", "commit")
    archive = tmp_path / "backup.zip"
    manifest = backup(archive, engine=engine)
    assert verify_backup(archive) == manifest
    with pytest.raises(ValueError, match="vazio"):
        restore(archive, engine=engine)
    with pytest.raises(FileExistsError):
        backup(archive, engine=engine)
    target = postgres_engine_factory()
    assert restore(archive, engine=target) == manifest
    assert_result_equal(result, RepositorioCenarios(engine=target).obter(result.cenario_id))
    second = tmp_path / "second.zip"
    assert (
        backup(second, engine=target) == manifest
    )  # every table count and every byte checksum matches


def test_corrupt_backup_rejected_before_write(engine, tmp_path):
    archive = tmp_path / "backup.zip"
    backup(archive, engine=engine)
    content = BytesIO()
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(content, "w") as dest:
        for name in src.namelist():
            dest.writestr(name, b"{}\n" if name == "users.jsonl" else src.read(name))
    archive.write_bytes(content.getvalue())
    with pytest.raises(ValueError, match="corrompido"):
        restore(archive, engine=engine)
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(s.users)).scalar_one() == 0


def test_capture_live_import_exact_idempotent(engine, tmp_path, base_sintetica):
    import threading
    from collections import OrderedDict
    from app.ingestion.live_scenarios import import_live

    path = Path(__file__).resolve().parents[1] / "scripts/capture_legacy_memory.py"
    spec = importlib.util.spec_from_file_location("capture_script", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = executar_cenario(CenarioRequest(), base_sintetica)

    class Legacy:
        _lock = threading.Lock()
        _itens = OrderedDict([(result.cenario_id, result)])

    file = tmp_path / "live.zip"
    assert mod.capturar(Legacy(), file)["captured"] == 1
    assert import_live(file, engine=engine, dry_run=True)["imported"] == 1
    assert import_live(file, engine=engine)["imported"] == 1
    assert import_live(file, engine=engine)["identical"] == 1
    assert_result_equal(result, RepositorioCenarios(engine=engine).obter(result.cenario_id))


def test_versioning_never_replaces_old_result(engine, base_sintetica):
    from dados.fundeb_dataset import FundebDataset

    dataset = FundebDataset(
        2026,
        base_sintetica.matriculas,
        base_sintetica.pesos,
        base_sintetica.complementar,
        base_sintetica.referencia,
        pd.DataFrame(),
        pd.DataFrame(),
    )
    v1 = store_base(base_sintetica, dataset, {"source": b"first"}, "etl1", "commit", engine=engine)
    v2 = store_base(base_sintetica, dataset, {"source": b"second"}, "etl1", "commit", engine=engine)
    assert v1 != v2
    assert load_base("sintetica", engine=engine).version_id == v1
    store_base(
        base_sintetica,
        dataset,
        {"source": b"second"},
        "etl1",
        "commit",
        engine=engine,
        activate=True,
    )
    assert load_base("sintetica", engine=engine).version_id == v2
    assert load_base(version=v1, engine=engine).version_id == v1
    with engine.connect() as conn:
        rows = (
            conn.execute(select(s.enrollments.c.value).where(s.enrollments.c.version_id == v1))
            .scalars()
            .all()
        )
    assert sum(rows) == float(base_sintetica.matriculas[base_sintetica.etapas].sum().sum())
