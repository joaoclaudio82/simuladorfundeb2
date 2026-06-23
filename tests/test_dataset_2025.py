"""Testes do dataset FUNDEB 2025 (consulta ou simulação conforme arquivos brutos)."""

from dados.fundeb_dataset import (
    COMPLEMENTACAO_2025,
    MENSAGEM_BLOQUEIO_2025,
    RAW_ARQUIVOS,
    carregar_dataset,
    dados_auxiliares_completos,
)


def test_arquivos_2025_mapeados():
    assert 2025 in RAW_ARQUIVOS
    assert {"receita", "nse", "drec", "vaat"}.issubset(RAW_ARQUIVOS[2025])
    assert "nse_pdf" in RAW_ARQUIVOS[2025]
    assert "drec_pdf" in RAW_ARQUIVOS[2025]


def test_dataset_2025_carrega():
    ds = carregar_dataset(2025)
    assert ds.ano == 2025
    assert len(ds.matriculas) > 5000
    assert len(ds.etapas) >= 300
    assert ds.modo_ponderador == "drec"


def test_dataset_2025_modo_conforme_arquivos():
    ds = carregar_dataset(2025)
    completos = dados_auxiliares_completos(2025)
    if completos:
        assert ds.simulacao_habilitada is True
        assert ds.mensagem_bloqueio is None
        assert ds.complementar["recursos_vaaf"].sum() > 0
    else:
        assert ds.simulacao_habilitada is False
        assert ds.mensagem_bloqueio == MENSAGEM_BLOQUEIO_2025
        assert ds.complementar["recursos_vaaf"].sum() == 0
        assert ds.defaults_complementacao == COMPLEMENTACAO_2025
