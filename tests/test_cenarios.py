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


# ---------------------------------------------------------------------------
# Cenários independentes A, B, C e D com receita constante
# ---------------------------------------------------------------------------

def test_caso1_mesma_rede_ajustes_diferentes_bcd_receita_constante(base_sintetica):
    """
    Caso 1 — Mesma rede, ajustes diferentes:
    - A mantém as matrículas originais.
    - Mesma rede em B recebe +100 matrículas em determinada etapa.
    - Mesma rede em C recebe +200 na mesma etapa.
    - D permanece original quando configurado sem ajustes.
    - A tabela mostra as edições de B e C separadamente com 'cenario' na 1ª coluna.
    - Receita, complementações e ponderadores são iguais em todos os cenários.
    """
    rede_id = 2300001
    etapa = "fundamental"
    orig_val = float(base_sintetica.matriculas.loc[base_sintetica.matriculas.ibge == rede_id, etapa].iloc[0])

    req = CenarioRequest(
        modo_cenarios="matriculas_independentes",
        cenarios_ativos=["B", "C", "D"],
        ajustes=[
            {"cenario": "B", "ibge": rede_id, "categoria": etapa, "operacao": "definir", "valor": orig_val + 100},
            {"cenario": "C", "ibge": rede_id, "categoria": etapa, "operacao": "definir", "valor": orig_val + 200},
        ],
    )
    res = executar_cenario(req, base_sintetica)

    assert res.cenarios == ["A", "B", "C", "D"]
    assert not res.eh_legado_receita
    assert res.modo_cenarios == "matriculas_independentes"

    # D configurado sem ajustes reproduz exatamente A (referência)
    pd.testing.assert_frame_equal(res.resultados["D"], res.resultados["A"])
    pd.testing.assert_frame_equal(res.matriculas_total["D"], res.matriculas_total["A"])

    # B aplica apenas +100 e C aplica apenas +200 (não acumula +100 de B em C)
    tot_a = float(res.matriculas_total["A"].set_index("ibge").loc[rede_id, "matriculas_total"])
    tot_b = float(res.matriculas_total["B"].set_index("ibge").loc[rede_id, "matriculas_total"])
    tot_c = float(res.matriculas_total["C"].set_index("ibge").loc[rede_id, "matriculas_total"])
    tot_d = float(res.matriculas_total["D"].set_index("ibge").loc[rede_id, "matriculas_total"])
    assert tot_b - tot_a == pytest.approx(100.0)
    assert tot_c - tot_a == pytest.approx(200.0)
    assert tot_d - tot_a == pytest.approx(0.0)

    # Tabela de ajustes tem 'cenario' como primeira coluna e linhas separadas para B e C
    assert res.ajustes.columns[0] == "cenario"
    assert list(res.ajustes["cenario"]) == ["B", "C"]
    assert list(res.ajustes["variacao_total"]) == [100.0, 200.0]

    # Parâmetros financeiros, ponderadores e contribuições (recursos_vaaf, recursos_vaat, complementações VAAF/VAAR) idênticos em A, B, C e D
    assert res.receita["tipo"] == "constante"
    assert res.receita["taxa"] == 0.0
    for col in ["recursos_vaaf", "recursos_vaat", "complemento_vaaf", "complemento_vaar"]:
        soma_a = float(res.resultados["A"][col].sum())
        for c in ("B", "C", "D"):
            assert float(res.resultados[c][col].sum()) == pytest.approx(soma_a, abs=0.05), (c, col)


def test_caso2_redes_diferentes_por_cenario_na_base_real():
    """
    Caso 2 — Redes diferentes na base real (Fortaleza em B, Sobral em C, Maracanaú em D):
    - B contém ajustes em Fortaleza (2304400).
    - C contém ajustes em Sobral (2312908).
    - D contém ajustes em Maracanaú (2307650).
    - Cada simulação parte da base original e aplica somente seus ajustes.
    """
    from app.services.bases import carregar_base_arquivo
    base = carregar_base_arquivo("fundeb-2026")
    etapa = base.etapas[0]
    fortaleza, sobral, maracanau = 2304400, 2312908, 2307650

    res = executar_cenario(
        CenarioRequest(
            modo_cenarios="matriculas_independentes",
            ajustes_por_cenario={
                "B": [{"ibge": fortaleza, "categoria": etapa, "operacao": "acrescentar", "valor": 100}],
                "C": [{"ibge": sobral, "categoria": etapa, "operacao": "acrescentar", "valor": 200}],
                "D": [{"ibge": maracanau, "categoria": etapa, "operacao": "acrescentar", "valor": 300}],
            },
        ),
        base,
    )

    assert res.cenarios == ["A", "B", "C", "D"]
    mat_a = res.matriculas_total["A"].set_index("ibge")["matriculas_total"]
    mat_b = res.matriculas_total["B"].set_index("ibge")["matriculas_total"]
    mat_c = res.matriculas_total["C"].set_index("ibge")["matriculas_total"]
    mat_d = res.matriculas_total["D"].set_index("ibge")["matriculas_total"]

    # Em B, só Fortaleza tem matrículas alteradas
    assert mat_b.loc[fortaleza] - mat_a.loc[fortaleza] == pytest.approx(100.0)
    assert mat_b.loc[sobral] == pytest.approx(mat_a.loc[sobral])
    assert mat_b.loc[maracanau] == pytest.approx(mat_a.loc[maracanau])

    # Em C, só Sobral tem matrículas alteradas
    assert mat_c.loc[fortaleza] == pytest.approx(mat_a.loc[fortaleza])
    assert mat_c.loc[sobral] - mat_a.loc[sobral] == pytest.approx(200.0)
    assert mat_c.loc[maracanau] == pytest.approx(mat_a.loc[maracanau])

    # Em D, só Maracanaú tem matrículas alteradas
    assert mat_d.loc[fortaleza] == pytest.approx(mat_a.loc[fortaleza])
    assert mat_d.loc[sobral] == pytest.approx(mat_a.loc[sobral])
    assert mat_d.loc[maracanau] - mat_a.loc[maracanau] == pytest.approx(300.0)


def test_equivalencia_a_b_e_compatibilidade_historica(base_sintetica):
    """
    Caso 3 — Equivalência de A/B e compatibilidade com registros históricos:
    - Resultados de A e B no novo fluxo são idênticos aos do fluxo anterior para as mesmas entradas.
    - Registro histórico com crescimento de receita preserva C/D segundo a regra original.
    """
    ajuste_b = [{"ibge": 22, "categoria": "fundamental", "operacao": "acrescentar", "valor": 45}]
    legado_ab = executar_cenario(CenarioRequest(ajustes=ajuste_b), base_sintetica)
    novo_abcd = executar_cenario(
        CenarioRequest(modo_cenarios="matriculas_independentes", ajustes=ajuste_b),
        base_sintetica,
    )
    pd.testing.assert_frame_equal(novo_abcd.resultados["A"], legado_ab.resultados["A"])
    pd.testing.assert_frame_equal(novo_abcd.resultados["B"], legado_ab.resultados["B"])

    # Histórico com receita ampliada continua identificado como legado_receita
    historico_cd = executar_cenario(
        CenarioRequest(ajustes=ajuste_b, receita={"tipo": "crescimento", "taxa": 0.08}),
        base_sintetica,
    )
    assert historico_cd.eh_legado_receita is True
    assert historico_cd.modo_cenarios == "legado_receita"
    assert "receita ampliada" in historico_cd.metadados()["cenarios"]["C"]
    assert "receita ampliada" in historico_cd.metadados()["cenarios"]["D"]

    # Novo fluxo identifica nomes oficiais e receita constante
    meta_novo = novo_abcd.metadados()
    assert meta_novo["modo_cenarios"] == "matriculas_independentes"
    assert meta_novo["nomes_cenarios"] == {
        "A": "Cenário A — Referência",
        "B": "Cenário B — Simulação 1",
        "C": "Cenário C — Simulação 2",
        "D": "Cenário D — Simulação 3",
    }
    assert "Matrículas originais da base selecionada." in meta_novo["cenarios"]["A"]
    assert "Ajustes próprios de matrículas, mantendo a mesma receita da referência." in meta_novo["cenarios"]["B"]


def test_rejeita_crescimento_em_cenarios_independentes_e_ajuste_em_cenario_excluido(base_sintetica):
    with pytest.raises(ValidationError, match="receita constante"):
        CenarioRequest(
            modo_cenarios="matriculas_independentes",
            receita={"tipo": "crescimento", "taxa": 0.05},
        )

    with pytest.raises(ErroCenario, match="excluído"):
        executar_cenario(
            CenarioRequest(
                modo_cenarios="matriculas_independentes",
                cenarios_ativos=["B", "C"],
                ajustes=[{"cenario": "D", "ibge": 22, "categoria": "fundamental", "valor": 150}],
            ),
            base_sintetica,
        )
