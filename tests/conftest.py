"""Fixtures compartilhadas: base sintética pequena e base real do catálogo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from services.bases import carregar_base, montar_base

ETAPAS = ["fundamental", "medio_integral"]


def _dados_sinteticos():
    pesos = pd.DataFrame({
        "etapa": ETAPAS,
        "nome": ["Ensino fundamental", "Ensino médio integral"],
        "peso_vaaf": [1.0, 1.5],
        "peso_vaat": [1.0, 1.7],
    })
    entes = [
        # ibge, uf, nome, rec_vaaf, rec_vaat, nse, nf, inab, fund, medio
        (22, "PI", "Piauí", 900_000.0, 1_300_000.0, 1.0, 1.0, False, 100.0, 80.0),
        (2200001, "PI", "Mun PI 1", 500_000.0, 700_000.0, 0.97, 1.0, False, 120.0, 0.0),
        (2200002, "PI", "Mun PI 2", 300_000.0, 350_000.0, 1.02, 1.0, True, 90.0, 0.0),
        (23, "CE", "Ceará", 2_000_000.0, 2_600_000.0, 1.0, 1.0, False, 150.0, 90.0),
        (2300001, "CE", "Mun CE 1", 1_200_000.0, 1_500_000.0, 0.99, 1.0, False, 200.0, 0.0),
        (53, "DF", "Distrito Federal", 3_000_000.0, 4_000_000.0, 1.03, 1.0, True, 180.0, 60.0),
    ]
    complementar = pd.DataFrame([
        {"ibge": e[0], "uf": e[1], "nome": e[2], "recursos_vaaf": e[3], "recursos_vaat": e[4],
         "nse": e[5], "nf": e[6], "peso_vaar": 1 / len(entes), "inabilitados_vaat": e[7]}
        for e in entes
    ])
    matriculas = pd.DataFrame([{"ibge": e[0], "fundamental": e[8], "medio_integral": e[9]} for e in entes])
    return pesos, complementar, matriculas


MANIFESTO = {
    "base_id": "sintetica",
    "descricao": "Base sintética de testes",
    "ano_exercicio": 2026,
    "situacao": "teste",
    "homologada": False,
    "arquivos": [{"papel": "matriculas", "caminho": "-", "sha256": "0" * 64}],
    "parametros_referencia": {
        "complementacao_vaaf": 400_000.0, "complementacao_vaat": 300_000.0, "complementacao_vaar": 50_000.0,
        "max_nse": 1.05, "min_nse": 0.95, "max_nf": 1.0, "min_nf": 1.0,
    },
    "grupos": {"propag": [22, 53]},
}


@pytest.fixture
def base_sintetica():
    pesos, complementar, matriculas = _dados_sinteticos()
    return montar_base("sintetica", MANIFESTO, matriculas, complementar, pesos, exigir_todas_ufs=False)


@pytest.fixture(scope="session")
def base_real():
    return carregar_base("fundeb-2026")
