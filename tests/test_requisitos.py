"""
Testes de requisitos funcionais, regras de negócio e critérios de aceite.
RF, RN e CA conforme documentação do projeto.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from simulador import simula_fundeb
from validacao import validar_interno


# ---------------------------------------------------------------------------
# Dados sintéticos para CA-02: 1000/10000 = 10%; 1100/10100 ≈ 10,89%
# ---------------------------------------------------------------------------
def _dados_ca02(recursos_estado: float = 1_000_000):
    """Cria dados mínimos: 2 municípios, estado TE. Mun A: 1000, Mun B: 9000 matrículas."""
    etapas = ["etapa_teste"]
    pesos = pd.DataFrame({
        "etapa": etapas,
        "nome": ["Etapa Teste"],
        "peso_vaaf": [1.0],
        "peso_vaat": [1.0],
    })
    # Recursos iniciais proporcionalmente 10% e 90%
    r_a = recursos_estado * 0.10
    r_b = recursos_estado * 0.90
    complementar = pd.DataFrame([
        {"ibge": 99001, "uf": "TE", "nome": "Mun A", "recursos_vaaf": r_a, "recursos_vaat": r_a, "nse": 1.0, "nf": 1.0, "peso_vaar": 0.0, "inabilitados_vaat": False},
        {"ibge": 99002, "uf": "TE", "nome": "Mun B", "recursos_vaaf": r_b, "recursos_vaat": r_b, "nse": 1.0, "nf": 1.0, "peso_vaar": 0.0, "inabilitados_vaat": False},
    ])
    return pesos, complementar


def _matriculas_ca02(mat_a: float, mat_b: float):
    """Matrículas brutas (com peso 1 = ponderadas)."""
    return pd.DataFrame([
        {"ibge": 99001, "etapa_teste": mat_a},
        {"ibge": 99002, "etapa_teste": mat_b},
    ])


# ---------------------------------------------------------------------------
# CA-02: Validação do rateio 1000/10000 e 1100/10100
# ---------------------------------------------------------------------------
def test_ca02_participacao_10_percent():
    """CA-02: Ao alterar matrículas, participação = mat_mun / total_estado. Caso 1000/10000 = 10%."""
    pesos, complementar = _dados_ca02()
    mat = _matriculas_ca02(1000, 9000)
    sim = simula_fundeb(
        mat, complementar, pesos,
        complementacao_vaaf=0, complementacao_vaat=0, complementacao_vaar=0,
        max_nse=1.0, min_nse=1.0, max_nf=1.0, min_nf=1.0,
    )
    total = sim["matriculas_vaaf"].sum()
    part_a = sim.loc[sim["ibge"] == 99001, "matriculas_vaaf"].values[0] / total
    assert total == 10_000, f"Total esperado 10000, obtido {total}"
    assert abs(part_a - 0.10) < 0.001, f"Participação A esperada 10%, obtida {part_a*100:.2f}%"


def test_ca02_participacao_1089_percent():
    """CA-02: Caso 1100/10100 ≈ 10,89%."""
    pesos, complementar = _dados_ca02()
    mat = _matriculas_ca02(1100, 9000)
    sim = simula_fundeb(
        mat, complementar, pesos,
        complementacao_vaaf=0, complementacao_vaat=0, complementacao_vaar=0,
        max_nse=1.0, min_nse=1.0, max_nf=1.0, min_nf=1.0,
    )
    total = sim["matriculas_vaaf"].sum()
    part_a = sim.loc[sim["ibge"] == 99001, "matriculas_vaaf"].values[0] / total
    expected = 1100 / 10100  # ≈ 0.10891
    assert total == 10_100, f"Total esperado 10100, obtido {total}"
    assert abs(part_a - expected) < 0.001, f"Participação A esperada {expected*100:.2f}%, obtida {part_a*100:.2f}%"


def test_ca02_recursos_proporcionais():
    """CA-02: Recursos municipais devem seguir rateio proporcional às matrículas ponderadas."""
    recursos_estado = 1_000_000
    pesos, complementar = _dados_ca02(recursos_estado)
    mat = _matriculas_ca02(1100, 9000)
    sim = simula_fundeb(
        mat, complementar, pesos,
        complementacao_vaaf=0, complementacao_vaat=0, complementacao_vaar=0,
        max_nse=1.0, min_nse=1.0, max_nf=1.0, min_nf=1.0,
    )
    rec_a = sim.loc[sim["ibge"] == 99001, "recursos_vaaf"].values[0]
    rec_b = sim.loc[sim["ibge"] == 99002, "recursos_vaaf"].values[0]
    expected_a = recursos_estado * (1100 / 10100)
    expected_b = recursos_estado * (9000 / 10100)
    assert abs(rec_a - expected_a) < 1, f"Recursos A esperados ~{expected_a:.2f}, obtidos {rec_a}"
    assert abs(rec_b - expected_b) < 1, f"Recursos B esperados ~{expected_b:.2f}, obtidos {rec_b}"


# ---------------------------------------------------------------------------
# RF-10 / Validação interna
# ---------------------------------------------------------------------------
def test_validacao_soma_recursos_igual_total_estadual():
    """RF-10: Validação interna - soma dos recursos municipais = total estadual."""
    pesos, complementar = _dados_ca02(recursos_estado=500_000)
    mat = _matriculas_ca02(1000, 9000)
    sim = simula_fundeb(
        mat, complementar, pesos,
        complementacao_vaaf=0, complementacao_vaat=0, complementacao_vaar=0,
        max_nse=1.0, min_nse=1.0, max_nf=1.0, min_nf=1.0,
    )
    soma_recursos = sim["recursos_vaaf"].sum()
    total_estado = complementar["recursos_vaaf"].sum()
    assert abs(soma_recursos - total_estado) < 1, f"Soma recursos ({soma_recursos}) != total estado ({total_estado})"


def test_validacao_vaaf_igual_recursos_div_matriculas():
    """RF-10: VAAF = recursos_vaaf_final / matriculas_vaaf."""
    pesos, complementar = _dados_ca02()
    mat = _matriculas_ca02(1000, 9000)
    sim = simula_fundeb(
        mat, complementar, pesos,
        complementacao_vaaf=100_000, complementacao_vaat=0, complementacao_vaar=0,
        max_nse=1.0, min_nse=1.0, max_nf=1.0, min_nf=1.0,
    )
    for _, row in sim.iterrows():
        if row["matriculas_vaaf"] > 0:
            vaaf_calc = row["recursos_vaaf_final"] / row["matriculas_vaaf"]
            assert abs(row["vaaf_final"] - vaaf_calc) < 0.01, f"VAAF inconsistente para {row['nome']}"


# ---------------------------------------------------------------------------
# RN-03: Alteração em um município redistribui todos
# ---------------------------------------------------------------------------
def test_rn03_alteracao_redistribui_todos():
    """RN-03: Alterar matrículas de um mun deve redistribuir recursos de todos os entes do estado."""
    pesos, complementar = _dados_ca02()
    mat_orig = _matriculas_ca02(1000, 9000)
    mat_alt = _matriculas_ca02(1100, 9000)  # só Mun A alterado
    sim_orig = simula_fundeb(mat_orig, complementar, pesos, 0, 0, 0, 1, 1, 1, 1)
    sim_alt = simula_fundeb(mat_alt, complementar, pesos, 0, 0, 0, 1, 1, 1, 1)
    rec_a_orig = sim_orig.loc[sim_orig["ibge"] == 99001, "recursos_vaaf"].values[0]
    rec_a_alt = sim_alt.loc[sim_alt["ibge"] == 99001, "recursos_vaaf"].values[0]
    rec_b_orig = sim_orig.loc[sim_orig["ibge"] == 99002, "recursos_vaaf"].values[0]
    rec_b_alt = sim_alt.loc[sim_alt["ibge"] == 99002, "recursos_vaaf"].values[0]
    assert rec_a_alt != rec_a_orig, "Mun A deve ter recursos alterados"
    assert rec_b_alt != rec_b_orig, "Mun B também deve ser redistribuído"
    assert abs((sim_alt["recursos_vaaf"].sum() - sim_orig["recursos_vaaf"].sum())) < 1, "Total estadual deve ser fixo"


# ---------------------------------------------------------------------------
# RF-10: Validação interna retorna resultado consistente
# ---------------------------------------------------------------------------
def test_validar_interno_retorna_valido_para_dados_consistentes():
    """RF-10: validar_interno deve retornar valido=True para simulação consistente."""
    pesos, complementar = _dados_ca02()
    mat = _matriculas_ca02(1000, 9000)
    sim = simula_fundeb(
        mat, complementar, pesos,
        complementacao_vaaf=0, complementacao_vaat=0, complementacao_vaar=0,
        max_nse=1.0, min_nse=1.0, max_nf=1.0, min_nf=1.0,
    )
    r = validar_interno(sim, complementar)
    assert r.valido, f"Validação falhou: {r.erros}"
    assert len(r.erros) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
