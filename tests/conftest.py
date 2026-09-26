from copy import deepcopy
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.bases import Base
from services.cenarios import CenarioService
from services.storage import ScenarioStore


@pytest.fixture
def base_teste():
    entes = pd.DataFrame([
        [23, "CE", "Ceará", "estadual"], [2300011, "CE", "Rede municipal CE", "municipal"],
        [22, "PI", "Piauí", "estadual"], [2200011, "PI", "Rede municipal PI", "municipal"],
        [16, "AP", "Amapá", "estadual"], [53, "DF", "Distrito Federal", "distrital"],
    ], columns=["ibge", "uf", "nome", "tipo"])
    mat = pd.DataFrame({"ibge": entes.ibge, "regular": [100, 200, 150, 120, 75, 50], "tecnico": [20, 0, 10, 0, 5, 10]})
    pesos = pd.DataFrame({"etapa": ["regular", "tecnico"], "nome": ["Ensino regular", "Ensino técnico"],
                          "peso_vaaf": [1., 1.3], "peso_vaat": [1., 1.5]})
    comp = entes[["ibge", "uf", "nome"]].copy()
    comp["recursos_vaaf"] = [20000., 40000., 10000., 8000., 20000., 15000.]
    comp["recursos_vaat"] = [25000., 45000., 15000., 12000., 25000., 20000.]
    comp["nse"] = 1.
    comp["nf"] = 1.
    comp["peso_vaar"] = [0.1, 0.2, 0.2, 0.2, 0.1, 0.2]
    comp["inabilitados_vaat"] = [False, False, False, True, False, False]
    meta = {"id": "teste", "nome": "Base sintética de teste", "ano_exercicio": 2026, "status": "preliminar",
            "modo_vaat": "fixo", "etapas_ept": ["tecnico"], "pendencias": ["Exemplo sintético, sem validade oficial."],
            "propag": {"status": "pendente"}, "amazonico": {"status": "pendente"},
            "parametros": {"complementacao_vaaf": 10000., "complementacao_vaat": 8000., "complementacao_vaar": 0.,
                           "min_nse": 1., "max_nse": 1., "min_nf": 1., "max_nf": 1.}}
    return Base(meta, {"matriculas": mat, "complementar": comp, "pesos": pesos, "entes": entes}, "a" * 64)


@pytest.fixture
def servico(base_teste, tmp_path):
    class Bases:
        def obter(self, base_id):
            if base_id != "teste":
                raise ValueError("Base não encontrada.")
            return deepcopy(base_teste)
    return CenarioService(Bases(), ScenarioStore(tmp_path / "cenarios.sqlite3"))
