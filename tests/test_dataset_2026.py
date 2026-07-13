"""Testes do dataset e simulação FUNDEB 2026."""

import os

import pandas as pd
import pytest

from dados.fundeb_dataset import RAW_DIR, carregar_dataset, COMPLEMENTACAO_2026, listar_entes_por_uf, _caminho_matriculas
from simulador import simula_fundeb
from validacao import validar_interno


@pytest.fixture(scope="module")
def ds2026():
    return carregar_dataset(2026)


def test_etapas_alinhadas_matriculas_pesos(ds2026):
    etapas = set(ds2026.etapas)
    cols = set(ds2026.matriculas.columns) - {"ibge", "uf", "nome"}
    assert len(etapas) >= 300
    assert etapas == cols
    assert ds2026.pesos["etapa"].is_unique


def test_simular_api_path_2026(ds2026):
    from api_simulacao import executar_simulacao, SimulacaoRequest

    sim = executar_simulacao(SimulacaoRequest(), ds2026)
    assert len(sim) > 0
    assert "vaaf_final" in sim.columns


def test_rf10_vaaf_consistente_2026(ds2026):
    mat = ds2026.matriculas.drop(columns=["uf", "nome"], errors="ignore")
    sim = simula_fundeb(
        mat,
        ds2026.complementar,
        ds2026.pesos,
        COMPLEMENTACAO_2026["vaaf"],
        COMPLEMENTACAO_2026["vaat"],
        0,
        1.0, 1.0, 1.0, 1.0,
        modo_ponderador="drec",
    )
    mask = sim["matriculas_vaaf"] > 0
    vaaf_calc = sim.loc[mask, "recursos_vaaf_final"] / sim.loc[mask, "matriculas_vaaf"]
    diff = (sim.loc[mask, "vaaf_final"] - vaaf_calc).abs()
    assert (diff > 0.1).sum() == 0


def test_receita_fundo_estadual_bate_com_anexo_ods_2026(ds2026):
    """Totais por UF de recursos_vaaf devem coincidir com TOTAL GERAL do Anexo I STN."""
    ods_path = os.path.join(RAW_DIR, "Receitas Fundos 2026.ods")
    if not os.path.isfile(ods_path):
        pytest.skip("Arquivo Receitas Fundos 2026.ods não encontrado")

    ods = pd.read_excel(ods_path, sheet_name="Reest-26_1q", header=5)
    ods = ods.rename(columns={"UF": "uf", "TOTAL GERAL (20%)": "total_geral_ods"})
    ods = ods[ods["uf"].notna() & (ods["uf"] != "UF")].copy()
    ods["total_geral_ods"] = pd.to_numeric(ods["total_geral_ods"], errors="coerce")

    sim_por_uf = ds2026.complementar.groupby("uf")["recursos_vaaf"].sum().reset_index()
    cmp = ods.merge(sim_por_uf, on="uf", how="inner")
    cmp["diff"] = (cmp["total_geral_ods"] - cmp["recursos_vaaf"]).abs()
    assert len(cmp) == 27
    assert cmp["diff"].max() < 1.0, cmp[cmp["diff"] >= 1.0][["uf", "total_geral_ods", "recursos_vaaf", "diff"]]


def test_validacao_interna_2026(ds2026):
    mat = ds2026.matriculas.drop(columns=["uf", "nome"], errors="ignore")
    sim = simula_fundeb(
        mat,
        ds2026.complementar,
        ds2026.pesos,
        COMPLEMENTACAO_2026["vaaf"],
        COMPLEMENTACAO_2026["vaat"],
        COMPLEMENTACAO_2026["vaar"],
        1.0, 1.0, 1.0, 1.0,
        modo_ponderador="drec",
    )
    r = validar_interno(sim, ds2026.complementar)
    assert r.valido, r.erros


def test_dataset_2025_bloqueado(ds2026):
    from dados.fundeb_dataset import dados_auxiliares_completos

    ds = carregar_dataset(2025)
    if dados_auxiliares_completos(2025):
        assert ds.simulacao_habilitada is True
    else:
        assert ds.simulacao_habilitada is False
        assert ds.mensagem_bloqueio


def test_matriculas_2026_arquivo_dedicado():
    path = _caminho_matriculas(2026)
    assert path.endswith("Matrículas Fundeb 2026.xlsx")
    assert os.path.isfile(path)


def test_inabilitados_vaat_lista_oficial_2026(ds2026):
    """Inabilitados devem vir da lista oficial FNDE (25 entes, incluindo MG)."""
    inab = ds2026.complementar[ds2026.complementar["inabilitados_vaat"] == True]
    assert len(inab) == 25, f"esperados 25 inabilitados, obtidos {len(inab)}"
    assert 31 in inab["ibge"].values  # Minas Gerais (ente estadual)


def test_inabilitados_nao_recebem_complemento_vaat_2026(ds2026):
    mat = ds2026.matriculas.drop(columns=["uf", "nome"], errors="ignore")
    sim = simula_fundeb(
        mat,
        ds2026.complementar,
        ds2026.pesos,
        COMPLEMENTACAO_2026["vaaf"],
        COMPLEMENTACAO_2026["vaat"],
        0,
        1.0, 1.0, 1.0, 1.0,
        modo_ponderador="drec",
    )
    inab = sim[sim["inabilitados_vaat"] == True]
    assert len(inab) == 25
    assert (inab["complemento_vaat"].abs() < 0.01).all()


def test_entes_estaduais_em_complementar_2026(ds2026):
    estados = ds2026.complementar[ds2026.complementar["ibge"] < 100]
    assert len(estados) == 27
    ac = listar_entes_por_uf(ds2026.complementar, "AC")
    assert ac.iloc[0]["ibge"] == 12
    assert ac.iloc[0]["nome"] == "Acre"
