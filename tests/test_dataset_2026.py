"""Testes do dataset e simulação FUNDEB 2026."""

import pytest

from dados.fundeb_dataset import carregar_dataset, COMPLEMENTACAO_2026
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
    ds = carregar_dataset(2025)
    assert ds.simulacao_habilitada is False
    assert ds.mensagem_bloqueio
