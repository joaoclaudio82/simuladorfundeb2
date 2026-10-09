"""Identificação da amostra nacional e conservação numa capital de outra região."""

from analises.fundeb_ceara.dataset import detectar_transicoes
from analises.fundeb_ceara.transformacoes import converter_percentual, total_alunos
from analises.fundeb_regioes.config import ALVOS
from analises.fundeb_regioes.estudo import identificar_alvos
from dados.fundeb_dataset import ESTADOS_REGIOES, carregar_dataset


def test_cinco_regioes_e_dez_municipios():
    ds = carregar_dataset(2026)
    muns = identificar_alvos(ds)
    assert len(muns) == 10
    assert muns["ibge"].is_unique
    assert (muns["ibge"] > 100).all()
    assert set(muns["regiao"]) == set(ESTADOS_REGIOES)
    for nome, uf, _reg in ALVOS:
        row = muns[muns["municipio"] == nome].iloc[0]
        assert row["uf"] == uf


def test_conservacao_sao_paulo():
    ds = carregar_dataset(2026)
    muns = identificar_alvos(ds)
    ibge = int(muns.loc[muns["municipio"] == "São Paulo", "ibge"].iloc[0])
    tr = next(t for t in detectar_transicoes(ds) if t.codigo == "C")
    etapas = [c for c in ds.etapas if c in ds.matriculas.columns]
    mat = ds.matriculas[["ibge"] + etapas].copy()
    antes = total_alunos(mat, ibge, etapas)
    out, n = converter_percentual(mat, ibge, tr.origem, tr.destino, 10, etapas)
    assert n > 0
    assert total_alunos(out, ibge, etapas) == antes
