"""Regenera figuras e RESULTADOS.md a partir dos CSVs já gravados."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from analises.fundeb_ceara.config import RESULTADOS_DIR
from analises.fundeb_ceara.figuras import gerar_figuras
from analises.fundeb_ceara.relatorio import escrever_resultados, resumo_terminal
import pandas as pd


def main() -> None:
    d = Path(RESULTADOS_DIR)
    dados = {
        "pesos": pd.read_csv(d / "pesos.csv"),
        "baseline": pd.read_csv(d / "baseline.csv"),
        "simulacoes": pd.read_csv(d / "simulacoes.csv"),
        "melhores_cenarios": pd.read_csv(d / "melhores_cenarios.csv"),
        "impactos_outros_municipios": pd.read_csv(d / "impactos_outros_municipios.csv"),
        "otimizacao": pd.read_csv(d / "otimizacao.csv"),
        "g10": pd.read_csv(d / "otimizacao_conjunta.csv"),
        "linearidade": pd.read_csv(d / "linearidade.csv"),
        "rankings": pd.read_csv(d / "rankings.csv"),
        "tabela_final": pd.read_csv(d / "tabela_final.csv"),
        "meta": pd.read_csv(d / "meta_execucao.csv"),
        "transicoes": pd.read_csv(d / "transicoes_detectadas.csv"),
    }
    gerar_figuras(dados)
    escrever_resultados(dados)
    print(resumo_terminal(dados))


if __name__ == "__main__":
    main()
