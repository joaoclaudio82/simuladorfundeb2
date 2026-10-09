"""Testes do estudo contrafactual: conservação de alunos e ligação com o motor."""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analises.fundeb_ceara.dataset import carregar_contexto, identificar_municipios, detectar_transicoes
from analises.fundeb_ceara.motor import MotorAno
from analises.fundeb_ceara.transformacoes import (
    TransformacaoInvalida,
    converter_percentual,
    concentrar_em_etapa,
    total_alunos,
    transferir_alunos,
)
from dados.fundeb_dataset import carregar_dataset
from simulador import simula_fundeb


def test_identificar_dez_municipios_ce_2024():
    ds = carregar_dataset(2024)
    muns = identificar_municipios(ds)
    assert len(muns) == 10
    assert set(muns["ibge"]) == {
        2304400, 2303709, 2307650, 2312908, 2307304,
        2304202, 2306405, 2307700, 2311306, 2305506,
    }
    assert muns["ibge"].is_unique


def test_transicoes_abcd_existem_nos_tres_anos():
    for ano in (2024, 2025, 2026):
        ds = carregar_dataset(ano)
        tr = detectar_transicoes(ds)
        assert {t.codigo for t in tr} == {"A", "B", "C", "D"}
        etapas = set(ds.etapas)
        for t in tr:
            assert t.origem in etapas
            assert t.destino in etapas
            assert t.origem != t.destino


def test_conservacao_e_nao_negatividade():
    mat = pd.DataFrame({
        "ibge": [1, 2],
        "a": [100.0, 50.0],
        "b": [20.0, 10.0],
        "c": [0.0, 5.0],
    })
    etapas = ["a", "b", "c"]
    antes = total_alunos(mat, 1, etapas)
    out = transferir_alunos(mat, 1, "a", "b", 30, etapas)
    assert total_alunos(out, 1, etapas) == pytest.approx(antes)
    assert out.loc[out["ibge"] == 1, "a"].iloc[0] == pytest.approx(70)
    assert out.loc[out["ibge"] == 1, "b"].iloc[0] == pytest.approx(50)
    assert (out[["a", "b", "c"]] >= -1e-12).all().all()
    with pytest.raises(TransformacaoInvalida):
        transferir_alunos(mat, 1, "a", "b", 999, etapas)
    with pytest.raises(TransformacaoInvalida):
        transferir_alunos(mat, 1, "a", "b", -1, etapas)


def test_percentual_zero_nao_altera():
    mat = pd.DataFrame({"ibge": [9], "a": [10.0], "b": [3.0]})
    out, n = converter_percentual(mat, 9, "a", "b", 0, ["a", "b"])
    assert n == 0
    assert out.equals(mat)


def test_concentrar_conserva_total():
    mat = pd.DataFrame({"ibge": [1], "a": [10.0], "b": [4.0], "c": [6.0]})
    out, n = concentrar_em_etapa(mat, 1, "c", ["a", "b", "c"])
    assert n == pytest.approx(20)
    assert total_alunos(out, 1, ["a", "b", "c"]) == pytest.approx(20)
    assert out.loc[0, "a"] == 0
    assert out.loc[0, "b"] == 0
    assert out.loc[0, "c"] == pytest.approx(20)


def test_cenario_fortaleza_creche_bate_com_motor():
    """Alunos saídos de A = alunos em B; resultado financeiro vem de simula_fundeb."""
    ctx = carregar_contexto(2024)
    motor = MotorAno(ctx)
    trans = next(t for t in ctx.transicoes if t.codigo == "A")
    ibge = int(ctx.municipios.loc[ctx.municipios["municipio"] == "Fortaleza", "ibge"].iloc[0])
    i = motor.mat_base.index[motor.mat_base["ibge"] == ibge][0]
    origem_antes = float(motor.mat_base.at[i, trans.origem])
    destino_antes = float(motor.mat_base.at[i, trans.destino])
    total_antes = total_alunos(motor.mat_base, ibge, ctx.etapas)

    mat, n = converter_percentual(motor.mat_base, ibge, trans.origem, trans.destino, 10, ctx.etapas)
    j = mat.index[mat["ibge"] == ibge][0]
    origem_depois = float(mat.at[j, trans.origem])
    destino_depois = float(mat.at[j, trans.destino])
    assert origem_antes - origem_depois == pytest.approx(n)
    assert destino_depois - destino_antes == pytest.approx(n)
    assert total_alunos(mat, ibge, ctx.etapas) == pytest.approx(total_antes)
    assert (mat[ctx.etapas] >= -1e-9).all().all()

    sim_pkg = motor.simular(mat)
    sim_direto = simula_fundeb(
        dados_matriculas=mat[["ibge"] + ctx.etapas],
        dados_complementar=ctx.ds.complementar,
        dados_peso=ctx.ds.pesos,
        complementacao_vaaf=float(ctx.ds.defaults_complementacao["vaaf"]),
        complementacao_vaat=float(ctx.ds.defaults_complementacao["vaat"]),
        complementacao_vaar=float(ctx.ds.defaults_complementacao.get("vaar") or 0),
        max_nse=1.0, min_nse=1.0, max_nf=1.0, min_nf=1.0,
        modo_ponderador=ctx.ds.modo_ponderador,
    )
    r1 = float(sim_pkg.loc[sim_pkg["ibge"] == ibge, "recursos_fundeb"].iloc[0])
    r2 = float(sim_direto.loc[sim_direto["ibge"] == ibge, "recursos_fundeb"].iloc[0])
    assert r1 == pytest.approx(r2, abs=0.05)


def test_pesos_2024_confirmados():
    ds = carregar_dataset(2024)
    p = ds.pesos.set_index("etapa")
    assert p.loc["creche_integral_rede_publica", "peso_vaaf"] == pytest.approx(1.50)
    assert p.loc["creche_integral_rede_publica", "peso_vaat"] == pytest.approx(1.80)
    assert p.loc["creche_parcial_rede_publica", "peso_vaaf"] == pytest.approx(1.25)
    assert p.loc["pre_escola_integral_rede_publica", "peso_vaaf"] == pytest.approx(1.40)
    assert p.loc["ens_fundamental_integral_rede_publica", "peso_vaaf"] == pytest.approx(1.40)
    assert p.loc["ens_fundamental_series_iniciais_urbano_rede_publica", "peso_vaaf"] == pytest.approx(1.00)
    assert p.loc["ens_fundamental_series_finais_urbano_rede_publica", "peso_vaaf"] == pytest.approx(1.10)
