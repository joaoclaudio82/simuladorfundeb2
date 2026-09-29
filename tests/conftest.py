"""Fixtures compartilhadas: base sintética pequena e base real do catálogo."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from services.bases import carregar_base, montar_base

ETAPAS = ["fundamental", "medio_integral"]


def _dados_sinteticos():
    pesos = pd.DataFrame(
        {
            "etapa": ETAPAS,
            "nome": ["Ensino fundamental", "Ensino médio integral"],
            "peso_vaaf": [1.0, 1.5],
            "peso_vaat": [1.0, 1.7],
        }
    )
    entes = [
        # ibge, uf, nome, rec_vaaf, rec_vaat, nse, nf, inab, fund, medio
        (22, "PI", "Piauí", 900_000.0, 1_300_000.0, 1.0, 1.0, False, 100.0, 80.0),
        (2200001, "PI", "Mun PI 1", 500_000.0, 700_000.0, 0.97, 1.0, False, 120.0, 0.0),
        (2200002, "PI", "Mun PI 2", 300_000.0, 350_000.0, 1.02, 1.0, True, 90.0, 0.0),
        (23, "CE", "Ceará", 2_000_000.0, 2_600_000.0, 1.0, 1.0, False, 150.0, 90.0),
        (2300001, "CE", "Mun CE 1", 1_200_000.0, 1_500_000.0, 0.99, 1.0, False, 200.0, 0.0),
        (53, "DF", "Distrito Federal", 3_000_000.0, 4_000_000.0, 1.03, 1.0, True, 180.0, 60.0),
    ]
    complementar = pd.DataFrame(
        [
            {
                "ibge": e[0],
                "uf": e[1],
                "nome": e[2],
                "recursos_vaaf": e[3],
                "recursos_vaat": e[4],
                "nse": e[5],
                "nf": e[6],
                "peso_vaar": 1 / len(entes),
                "inabilitados_vaat": e[7],
            }
            for e in entes
        ]
    )
    matriculas = pd.DataFrame(
        [{"ibge": e[0], "fundamental": e[8], "medio_integral": e[9]} for e in entes]
    )
    return pesos, complementar, matriculas


MANIFESTO = {
    "base_id": "sintetica",
    "descricao": "Base sintética de testes",
    "ano_exercicio": 2026,
    "situacao": "teste",
    "homologada": False,
    "arquivos": [{"papel": "matriculas", "caminho": "-", "sha256": "0" * 64}],
    "parametros_referencia": {
        "complementacao_vaaf": 400_000.0,
        "complementacao_vaat": 300_000.0,
        "complementacao_vaar": 50_000.0,
        "max_nse": 1.05,
        "min_nse": 0.95,
        "max_nf": 1.0,
        "min_nf": 1.0,
    },
    "grupos": {"propag": [22, 53]},
}


@pytest.fixture
def base_sintetica():
    pesos, complementar, matriculas = _dados_sinteticos()
    return montar_base(
        "sintetica", MANIFESTO, matriculas, complementar, pesos, exigir_todas_ufs=False
    )


@pytest.fixture(scope="session")
def base_real():
    return carregar_base("fundeb-2026")


@pytest.fixture(scope="session")
def postgres_engine_factory():
    """Somente schemas próprios, com nomes aleatórios, em PostgreSQL de teste explícito."""
    import uuid
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from app.db.session import engine_for, get_engine

    url = os.getenv("FUNDEB_TEST_DATABASE_URL")
    if not url:
        raise pytest.UsageError(
            "Configure FUNDEB_TEST_DATABASE_URL com um PostgreSQL exclusivo de testes."
        )
    admin = engine_for(url)
    created = []

    def create():
        schema = "test_" + uuid.uuid4().hex
        with admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        scoped = (
            make_url(url)
            .update_query_dict({"options": "-csearch_path=" + schema})
            .render_as_string(hide_password=False)
        )
        engine = engine_for(scoped)
        created.append((schema, engine))
        return get_engine(scoped)

    try:
        yield create
    finally:
        for schema, engine in reversed(created):
            engine.dispose()
            with admin.begin() as conn:
                conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.fixture(scope="session", autouse=True)
def postgres_seed(postgres_engine_factory):
    from app.ingestion.migrate import import_data

    patch = pytest.MonkeyPatch()
    patch.setenv("FUNDEB_ENV", "test")
    engine = postgres_engine_factory()
    patch.setenv("FUNDEB_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    patch.setenv("FUNDEB_DATA_SOURCE", "database")
    try:
        report = import_data(engine=engine)
        assert len(report["bases"]) == 3
        yield engine
    finally:
        patch.undo()


@pytest.fixture(autouse=True)
def isolated_application_database(postgres_seed):
    """Bases imutáveis compartilhadas; registros operacionais isolados por teste."""
    from app.db.schema import metadata

    operational = {
        "users",
        "scenarios",
        "scenario_results",
        "exports",
        "legacy_runs",
        "audit_events",
    }

    def clean():
        with postgres_seed.begin() as conn:
            for table in reversed(metadata.sorted_tables):
                if table.name in operational:
                    conn.execute(table.delete())

    clean()
    yield
    clean()


@pytest.fixture
def engine(postgres_engine_factory):
    return postgres_engine_factory()
