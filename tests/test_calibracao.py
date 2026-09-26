"""FND-04 — comparação do cenário sem alterações com os valores oficiais por ente."""
import pytest

from services.bases import carregar_base
from services.calibracao import comparar_com_oficial


@pytest.fixture(scope="module")
def calibracao_2026():
    return comparar_com_oficial(carregar_base("fundeb-2026"))


def test_totais_nacionais_batem_com_oficial(calibracao_2026):
    assert calibracao_2026["disponivel"]
    assert calibracao_2026["cobertura"]["sem_valor_oficial"] == []
    for ind in calibracao_2026["indicadores"]:
        assert ind["total_simulado"] == pytest.approx(ind["total_oficial"], rel=1e-6), ind["indicador"]


def test_divergencias_por_ente_sao_reportadas(calibracao_2026):
    """As diferenças por ente não somem nos totais: o relatório as expõe."""
    vaaf = next(i for i in calibracao_2026["indicadores"] if i["indicador"] == "complemento_vaaf")
    assert vaaf["entes_acima_da_tolerancia"] > 0
    ufs = {u["uf"]: u for u in calibracao_2026["por_uf"]}
    assert ufs["PE"]["acima_da_tolerancia"]  # divergência de PE levantada na reunião
    assert len(calibracao_2026["maiores_diferencas"]) == 15


def test_base_sem_valores_oficiais():
    assert comparar_com_oficial(carregar_base("fundeb-2024"))["disponivel"] is False
