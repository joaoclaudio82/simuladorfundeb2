"""Hashes capturados do commit b34590c antes da refatoração, cobrindo todas as células."""

import hashlib
import json
from pathlib import Path
import os
import pandas as pd
import pytest
from sqlalchemy import select, func
from app.db import schema as s
from app.db.session import get_engine
from app.repositories.bases import load_dataset, load_base
from app.ingestion.migrate import import_data
from services.bases import carregar_base
from services.cenarios import executar_cenario
from dados.fundeb_dataset import carregar_dataset
from schemas.cenarios import CenarioRequest
from api_simulacao import SimulacaoRequest, executar_simulacao, _resposta_simular

BASELINE = json.loads((Path(__file__).parent / "golden/legacy_b34590c.json").read_text())


def digest(df):
    header = json.dumps(
        {
            "columns": df.columns.tolist(),
            "dtypes": [str(x) for x in df.dtypes],
            "index_names": df.index.names,
        },
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(
        header + pd.util.hash_pandas_object(df, index=True).values.tobytes()
    ).hexdigest()


@pytest.fixture(scope="module")
def imported_engine(tmp_path_factory):
    existing = os.getenv("FUNDEB_IMPORTED_TEST_URL")
    engine = get_engine(
        existing or "sqlite:///" + str(tmp_path_factory.mktemp("full-import") / "fundeb.db")
    )
    if not existing:
        report = import_data(engine=engine)
        assert len(report["bases"]) == 3
    return engine


def test_motor_source_preserved_byte_for_byte():
    path = Path(__file__).resolve().parents[1] / "app/domain/calculo/motor.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == BASELINE["motor_sha256"]


@pytest.mark.parametrize("year", [2024, 2025, 2026])
def test_all_dataset_cells_and_all_scenarios_exact(year, imported_engine):
    expected = BASELINE["years"][str(year)]
    legacy = carregar_dataset(year)
    stored = load_dataset(year, engine=imported_engine)
    for field, checksum in expected["datasets"].items():
        assert digest(getattr(legacy, field)) == checksum, field
        assert digest(getattr(stored, field)) == checksum, field
        pd.testing.assert_frame_equal(
            getattr(legacy, field), getattr(stored, field), check_exact=True
        )
    base = load_base(f"fundeb-{year}", engine=imported_engine)
    for profile in expected["profiles"].values():
        result = executar_cenario(CenarioRequest(base_id=base.base_id, **profile["request"]), base)
        assert {k: digest(v) for k, v in result.resultados.items()} == profile["results"]
    assert digest(executar_simulacao(SimulacaoRequest(), stored)) == expected["legacy_default"]


@pytest.mark.parametrize("year", [2024, 2025, 2026])
def test_legacy_response_exact_with_database_source(year, imported_engine, monkeypatch):
    import app.api.legacy as api

    monkeypatch.setattr(api, "_ds", lambda y: load_dataset(y, engine=imported_engine))
    payload = json.dumps(
        _resposta_simular(SimulacaoRequest(), year),
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    )
    assert (
        hashlib.sha256(payload.encode()).hexdigest()
        == BASELINE["years"][str(year)]["legacy_response"]
    )


def test_every_original_file_is_archived_with_exact_bytes(imported_engine):
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((root / "data/manifesto_arquivos.json").read_text())
    with imported_engine.connect() as conn:
        for item in inventory["files"]:
            row = (
                conn.execute(
                    select(s.source_files).where(s.source_files.c.sha256 == item["sha256"])
                )
                .mappings()
                .one()
            )
            assert row["content"] == (root / item["path"]).read_bytes()
            assert hashlib.sha256(row["content"]).hexdigest() == item["sha256"]
