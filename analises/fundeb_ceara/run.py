"""Ponto de entrada: python -m analises.fundeb_ceara.run"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Garante a raiz do repositório no path quando executado como módulo.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analises.fundeb_ceara.config import ANOS, RESULTADOS_DIR, SEED
from analises.fundeb_ceara.experimentos import executar_estudo
from analises.fundeb_ceara.figuras import gerar_figuras
from analises.fundeb_ceara.relatorio import escrever_resultados, resumo_terminal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estudo contrafactual FUNDEB — municípios do Ceará")
    parser.add_argument("--anos", nargs="+", type=int, default=list(ANOS))
    parser.add_argument("--rapido", action="store_true", help="Usa grade 0/5/10/20/30/50/100 em vez de 0–100.")
    args = parser.parse_args(argv)

    import os
    os.environ.setdefault("MPLCONFIGDIR", str(Path(RESULTADOS_DIR) / ".mpl"))
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    import numpy as np
    np.random.seed(SEED)

    print("Simulador FUNDEB — análise contrafactual Ceará")
    print(f"Anos: {args.anos}  granular={not args.rapido}  seed={SEED}")
    Path(RESULTADOS_DIR).mkdir(parents=True, exist_ok=True)

    dados = executar_estudo(anos=tuple(args.anos), granular=not args.rapido)
    figs = gerar_figuras(dados)
    md = escrever_resultados(dados)
    resumo = resumo_terminal(dados)
    (Path(RESULTADOS_DIR) / "resumo_terminal.txt").write_text(resumo + "\n", encoding="utf-8")
    print("\nFiguras:")
    for p in figs:
        print(f"  {p}")
    print(f"\nRelatório: {md}")
    print("\n" + resumo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
