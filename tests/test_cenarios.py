"""FND-05 / FND-10 / FND-11 — contrato de cenário, ajustes simultâneos e receita."""
import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from schemas.cenarios import Ajuste, CenarioRequest, HipoteseReceita
from services.bases import ErroBase, classificar_entes, montar_base
from services.cenarios import ErroCenario, aplicar_ajustes, executar_cenario
from simulador import simula_fundeb


def _req(**kw):
    return CenarioRequest(**kw)


def _executar_direto(base, mat, par):
    return simula_fundeb(mat, base.complementar, base.pesos, par["complementacao_vaaf"],
                         par["complementacao_vaat"], par["complementacao_vaar"],
                         par["max_nse"], par["min_nse"], par["max_nf"], par["min_nf"])


def test_sem_ajustes_b_igual_a(base_sintetica):
    res = executar_cenario(_req(), base_sintetica)
    pd.testing.assert_frame_equal(res.resultados["A"], res.resultados["B"])
    assert res.resumo_ajustes["quantidade"] == 0


def test_base_original_nao_e_alterada(base_sintetica):
    antes = base_sintetica.matriculas.copy()
    comp_antes = base_sintetica.complementar.copy()
    executar_cenario(_req(
        ajustes=[{"ibge": 22, "categoria": "fundamental", "operacao": "acrescentar", "valor": 50}],
        receita={"tipo": "crescimento", "taxa": 0.1},
    ), base_sintetica)
    pd.testing.assert_frame_equal(antes, base_sintetica.matriculas)
    pd.testing.assert_frame_equal(comp_antes, base_sintetica.complementar)


def test_ajustes_simultaneos_igual_execucao_direta(base_sintetica):
    ajustes = [
        {"ibge": 22, "categoria": "medio_integral", "operacao": "acrescentar", "valor": 40},
        {"ibge": 23, "categoria": "fundamental", "operacao": "definir", "valor": 120},
    ]
    res = executar_cenario(_req(ajustes=ajustes), base_sintetica)
    mat = base_sintetica.matriculas.copy()
    mat.loc[mat.ibge == 22, "medio_integral"] += 40
    mat.loc[mat.ibge == 23, "fundamental"] = 120
    direto = _executar_direto(base_sintetica, mat, res.parametros_efetivos)
    pd.testing.assert_frame_equal(res.resultados["B"], direto)


def test_ordem_dos_ajustes_nao_altera_resultado(base_sintetica):
    ajustes = [
        {"ibge": 22, "categoria": "fundamental", "operacao": "converter", "valor": 30,
         "categoria_destino": "medio_integral"},
        {"ibge": 22, "categoria": "medio_integral", "operacao": "acrescentar", "valor": 10},
        {"ibge": 23, "categoria": "fundamental", "operacao": "definir", "valor": 100},
    ]
    r1 = executar_cenario(_req(ajustes=ajustes), base_sintetica)
    r2 = executar_cenario(_req(ajustes=list(reversed(ajustes))), base_sintetica)
    pd.testing.assert_frame_equal(r1.resultados["B"], r2.resultados["B"])


def test_conversao_preserva_total_e_rejeita_negativo(base_sintetica):
    aj = Ajuste(ibge=22, categoria="fundamental", operacao="converter", valor=60,
                categoria_destino="medio_integral")
    mat, tab = aplicar_ajustes(base_sintetica.matriculas, [aj], base_sintetica)
    linha_antes = base_sintetica.matriculas.set_index("ibge").loc[22]
    linha_depois = mat.set_index("ibge").loc[22]
    assert linha_depois.sum() == pytest.approx(linha_antes.sum())
    assert tab["convertidas"].sum() == 60
    with pytest.raises(ErroCenario, match="negativas"):
        aplicar_ajustes(base_sintetica.matriculas, [aj.model_copy(update={"valor": 101})], base_sintetica)


def test_nova_matricula_incrementa_total_sem_duplicar_linhas(base_sintetica):
    res = executar_cenario(_req(ajustes=[
        {"ibge": 23, "categoria": "medio_integral", "operacao": "acrescentar", "valor": 25}]), base_sintetica)
    a, b = res.matriculas_total["A"], res.matriculas_total["B"]
    assert len(a) == len(b) == len(res.resultados["B"])
    assert b["matriculas_total"].sum() - a["matriculas_total"].sum() == 25
    assert res.resumo_ajustes["matriculas_acrescidas"] == 25
    assert res.resumo_ajustes["matriculas_convertidas"] == 0


@pytest.mark.parametrize("ajuste, mensagem", [
    ({"ibge": 999, "categoria": "fundamental", "valor": 1}, "não existe"),
    ({"ibge": 22, "categoria": "inexistente", "valor": 1}, "categoria inexistente"),
])
def test_ente_ou_categoria_inexistente(base_sintetica, ajuste, mensagem):
    with pytest.raises(ErroCenario, match=mensagem):
        executar_cenario(_req(ajustes=[ajuste]), base_sintetica)


def test_ajustes_conflitantes(base_sintetica):
    with pytest.raises(ErroCenario, match="conflitantes"):
        executar_cenario(_req(ajustes=[
            {"ibge": 22, "categoria": "fundamental", "valor": 1},
            {"ibge": 22, "categoria": "fundamental", "valor": 2}]), base_sintetica)
    with pytest.raises(ErroCenario, match="combinado"):
        executar_cenario(_req(ajustes=[
            {"ibge": 22, "categoria": "fundamental", "valor": 1},
            {"ibge": 22, "categoria": "fundamental", "operacao": "acrescentar", "valor": 2}]), base_sintetica)


@pytest.mark.parametrize("valor", [-1, float("nan"), float("inf")])
def test_valores_invalidos_rejeitados(valor):
    with pytest.raises(ValidationError):
        Ajuste(ibge=22, categoria="fundamental", valor=valor)


def test_exercicio_divergente_rejeitado(base_sintetica):
    with pytest.raises(ErroCenario, match="exercício"):
        executar_cenario(_req(ano_exercicio=2025), base_sintetica)


def test_pesos_com_tamanho_errado_rejeitados(base_sintetica):
    with pytest.raises(ErroCenario, match="pesos_vaaf"):
        executar_cenario(_req(parametros={"pesos_vaaf": [1.0]}), base_sintetica)


def test_cenarios_distintos_sem_contaminacao(base_sintetica):
    r1 = executar_cenario(_req(ajustes=[{"ibge": 22, "categoria": "fundamental", "valor": 500}]), base_sintetica)
    r2 = executar_cenario(_req(), base_sintetica)
    pd.testing.assert_frame_equal(r2.resultados["A"], r2.resultados["B"])
    assert r1.cenario_id != r2.cenario_id
    pd.testing.assert_frame_equal(r1.resultados["A"], r2.resultados["A"])


# FND-10 / FND-11 ------------------------------------------------------------

def test_crescimento_zero_reproduz_base(base_sintetica):
    res = executar_cenario(_req(
        ajustes=[{"ibge": 22, "categoria": "fundamental", "operacao": "acrescentar", "valor": 10}],
        receita={"tipo": "crescimento", "taxa": 0.0}), base_sintetica)
    pd.testing.assert_frame_equal(res.resultados["A"], res.resultados["C"])
    pd.testing.assert_frame_equal(res.resultados["B"], res.resultados["D"])


def test_crescimento_nao_altera_matriculas_e_so_rubricas_escolhidas(base_sintetica):
    res = executar_cenario(_req(receita={"tipo": "crescimento", "taxa": 0.1, "rubricas": ["recursos_vaaf"]}),
                           base_sintetica)
    a, c = res.resultados["A"], res.resultados["C"]
    pd.testing.assert_series_equal(a["matriculas_vaaf"], c["matriculas_vaaf"])
    assert c["recursos_vaaf"].sum() == pytest.approx(a["recursos_vaaf"].sum() * 1.1, rel=1e-6)
    assert c["recursos_vaat"].sum() == pytest.approx(a["recursos_vaat"].sum(), rel=1e-9)
    # Complementações fixas por padrão
    assert c["complemento_vaaf"].sum() == pytest.approx(a["complemento_vaaf"].sum(), abs=1)


def test_receita_constante_com_taxa_rejeitada():
    with pytest.raises(ValidationError):
        HipoteseReceita(tipo="constante", taxa=0.05)


# Cadastro ---------------------------------------------------------------------

def test_cadastro_identifica_tipos_de_rede(base_sintetica):
    tipos = base_sintetica.entes.set_index("ibge")["tipo_rede"]
    assert tipos[22] == "rede estadual"
    assert tipos[53] == "rede do Distrito Federal"
    assert tipos[2200001] == "rede municipal"


def test_identificador_repetido_rejeitado(base_sintetica):
    comp = pd.concat([base_sintetica.complementar, base_sintetica.complementar.iloc[[1]]])
    mat = pd.concat([base_sintetica.matriculas, base_sintetica.matriculas.iloc[[1]]])
    with pytest.raises(ErroBase, match="duplicados"):
        montar_base("x", {}, mat, comp, base_sintetica.pesos, exigir_todas_ufs=False)


def test_codigo_de_uf_em_outra_uf_rejeitado(base_sintetica):
    comp = base_sintetica.complementar.copy()
    comp.loc[comp.ibge == 23, "uf"] = "PI"
    with pytest.raises(ErroBase):
        classificar_entes(comp, exigir_todas_ufs=False)


# Bases reais ---------------------------------------------------------------------

@pytest.mark.parametrize("base_id", ["fundeb-2024", "fundeb-2025", "fundeb-2026"])
def test_base_real_reproduz_referencia(base_id):
    from services.bases import carregar_base
    base = carregar_base(base_id)
    res = executar_cenario(_req(), base)
    m = res.resultados["A"].merge(base.referencia, on="ibge", suffixes=("", "_ref"))
    assert len(m) == len(base.referencia)
    for col in ["recursos_fundeb", "complemento_vaaf", "complemento_vaat"]:
        assert np.abs(m[col] - m[f"{col}_ref"]).max() < 0.05, col
    # O motor atual recalcula o valor por aluno após arredondar recursos e matrículas;
    # a referência de 2024 foi gerada antes dessa mudança.
    for col in ["vaaf_final", "vaat_final"]:
        assert (np.abs(m[col] - m[f"{col}_ref"]) / m[f"{col}_ref"]).max() < 1e-4, col
    assert res.validacoes["A"]["valido"], res.validacoes["A"]["erros"]


def test_base_real_cadastro(base_real):
    contagem = base_real.entes["tipo_rede"].value_counts()
    assert contagem["rede estadual"] == 26
    assert contagem["rede do Distrito Federal"] == 1
    assert base_real.modo_ponderador == "drec"
    assert base_real.ano_exercicio == 2026


def test_hash_divergente_bloqueia_base(tmp_path):
    import json
    from services.bases import CATALOGO_PATH, conferir_arquivos
    cat = json.load(open(CATALOGO_PATH, encoding="utf-8"))
    manifesto = cat["bases"][0]
    manifesto["arquivos"][0]["sha256"] = "0" * 64
    with pytest.raises(ErroBase, match="hash divergente"):
        conferir_arquivos(manifesto)


def test_resolver_base_por_exercicio():
    from services.bases import resolver_base_id
    assert resolver_base_id(None, 2025) == "fundeb-2025"
    assert resolver_base_id(None, None) == "fundeb-2026"
    with pytest.raises(ErroBase):
        resolver_base_id(None, 2019)
