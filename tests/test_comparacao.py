"""FND-07 / FND-11 — recortes, totais, diferenças e participação."""
import numpy as np
import pytest

from schemas.cenarios import CenarioRequest
from services.cenarios import executar_cenario
from services.comparacao import (
    ErroRecorte, ibges_recorte, montar_comparacao, tabela_comparativa, totais_recorte, variacao_pct,
)


@pytest.fixture
def resultado(base_sintetica):
    return executar_cenario(CenarioRequest(
        ajustes=[{"ibge": 22, "categoria": "medio_integral", "operacao": "acrescentar", "valor": 40}],
        receita={"tipo": "crescimento", "taxa": 0.05},
    ), base_sintetica)


def test_recorte_estaduais_df_inclui_inabilitados_vaat(resultado):
    ids = ibges_recorte(resultado, "estaduais_df")
    assert ids == [22, 23, 53]  # DF é inabilitado VAAT na base sintética e não pode sumir
    tab = tabela_comparativa(resultado, "estaduais_df")
    assert set(tab["ibge"]) == {22, 23, 53}


def test_total_corresponde_as_linhas(resultado):
    ids = ibges_recorte(resultado, "estaduais_df")
    tab = tabela_comparativa(resultado, "estaduais_df")
    tot = totais_recorte(resultado, ids)
    for c in resultado.cenarios:
        assert tot["por_cenario"][c]["recursos_fundeb"] == pytest.approx(tab[f"recursos_fundeb_{c}"].sum())


def test_valor_por_aluno_usa_razao_de_somas(resultado):
    ids = ibges_recorte(resultado, "estaduais_df")
    a = resultado.resultados["A"].set_index("ibge").loc[ids]
    tot = totais_recorte(resultado, ids)["por_cenario"]["A"]
    assert tot["vaaf_final"] == pytest.approx(a["recursos_vaaf_final"].sum() / a["matriculas_vaaf"].sum())
    assert tot["vaaf_final"] != pytest.approx(a["vaaf_final"].sum())


def test_efeitos_abcd_calculados(resultado):
    comp = montar_comparacao(resultado)
    assert set(comp["efeitos"]) == {"B_A", "C_A", "D_A", "D_C"}
    t = comp["totais"]["por_cenario"]
    ef = comp["totais"]["efeitos"]
    assert ef["D_A"]["indicadores"]["recursos_fundeb"]["diferenca"] == pytest.approx(
        t["D"]["recursos_fundeb"] - t["A"]["recursos_fundeb"])
    assert ef["D_C"]["indicadores"]["recursos_fundeb"]["diferenca"] == pytest.approx(
        t["D"]["recursos_fundeb"] - t["C"]["recursos_fundeb"])
    part = comp["participacao"]
    assert part["variacao_pp"]["B_A"] == pytest.approx(part["participacao_pct"]["B"] - part["participacao_pct"]["A"])


def test_denominador_zero_nao_gera_infinito():
    pct = variacao_pct([10.0, 0.0, 5.0], [0.0, 0.0, 4.0])
    assert np.isnan(pct[0]) and np.isnan(pct[1])
    assert pct[2] == pytest.approx(25.0)


def test_complemento_zero_vira_nulo_no_json(resultado):
    comp = montar_comparacao(resultado)
    for linha in comp["linhas"]:
        for chave, valor in linha.items():
            assert not (isinstance(valor, float) and not np.isfinite(valor)), chave


def test_recorte_selecionadas_usa_ajustes_por_padrao(resultado):
    assert ibges_recorte(resultado, "selecionadas") == [22]
    assert ibges_recorte(resultado, "selecionadas", [23, 53]) == [23, 53]
    with pytest.raises(ErroRecorte):
        ibges_recorte(resultado, "selecionadas", [12345])


def test_recorte_propag_exige_grupo_validado(resultado):
    assert ibges_recorte(resultado, "propag") == [22, 53]
    resultado.grupos = {"propag": None}
    with pytest.raises(ErroRecorte, match="Propag"):
        ibges_recorte(resultado, "propag")


def test_universo_mostra_efeito_em_redes_sem_ajuste(resultado):
    comp = montar_comparacao(resultado)
    assert comp["universo"]["redes_sem_ajuste_afetadas"] > 0
    assert comp["recorte"]["quantidade_redes"] == 3


def test_comparacao_mostra_apenas_cenarios_executados(base_sintetica):
    res = executar_cenario(
        CenarioRequest(
            modo_cenarios="matriculas_independentes",
            cenarios_ativos=["C"],
            ajustes_por_cenario={
                "C": [{"ibge": 23, "categoria": "fundamental", "operacao": "acrescentar", "valor": 80}],
            },
        ),
        base_sintetica,
    )
    assert res.cenarios == ["A", "C"]
    comp = montar_comparacao(res, recorte="selecionadas")
    assert set(comp["efeitos"]) == {"C_A"}
    assert set(comp["totais"]["por_cenario"]) == {"A", "C"}
    linha = comp["linhas"][0]
    assert "recursos_fundeb_C" in linha
    assert "recursos_fundeb_B" not in linha and "recursos_fundeb_D" not in linha
    assert set(comp["universo"]["por_cenario"]) == {"C"}


def test_comparacao_cenarios_independentes_entre_si_e_com_referencia(base_sintetica):
    res = executar_cenario(
        CenarioRequest(
            modo_cenarios="matriculas_independentes",
            ajustes_por_cenario={
                "B": [{"ibge": 22, "categoria": "medio_integral", "operacao": "acrescentar", "valor": 40}],
                "C": [{"ibge": 23, "categoria": "fundamental", "operacao": "acrescentar", "valor": 80}],
                "D": [{"ibge": 2200001, "categoria": "fundamental", "operacao": "acrescentar", "valor": 50}],
            },
        ),
        base_sintetica,
    )
    comp = montar_comparacao(res, recorte="selecionadas")
    assert set(comp["efeitos"]) == {"B_A", "C_A", "D_A", "C_B", "D_B", "D_C"}
    # As três redes com ajustes em B, C e D aparecem no recorte 'selecionadas' e têm valores em A, B, C e D
    ibges = {linha["ibge"] for linha in comp["linhas"]}
    assert ibges == {22, 23, 2200001}
    for linha in comp["linhas"]:
        for c in ("A", "B", "C", "D"):
            assert f"recursos_fundeb_{c}" in linha
        assert linha["recursos_fundeb_dif_C_B"] == pytest.approx(
            linha["recursos_fundeb_C"] - linha["recursos_fundeb_B"]
        )
        assert linha["recursos_fundeb_dif_D_B"] == pytest.approx(
            linha["recursos_fundeb_D"] - linha["recursos_fundeb_B"]
        )
        assert linha["recursos_fundeb_dif_D_C"] == pytest.approx(
            linha["recursos_fundeb_D"] - linha["recursos_fundeb_C"]
        )
