"""python -m analises.fundeb_regioes.run"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analises.fundeb_regioes.config import ANOS, FIGURAS_DIR, RESULTADOS_DIR, SEED


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anos", nargs="+", type=int, default=list(ANOS))
    parser.add_argument(
        "--apenas-relatorio",
        action="store_true",
        help="Regera figuras, Markdown e PDF a partir dos CSVs já salvos.",
    )
    args = parser.parse_args(argv)
    os.environ.setdefault("MPLCONFIGDIR", str(Path(RESULTADOS_DIR) / ".mpl"))
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    Path(RESULTADOS_DIR).mkdir(parents=True, exist_ok=True)
    Path(FIGURAS_DIR).mkdir(parents=True, exist_ok=True)
    import numpy as np
    np.random.seed(SEED)

    from analises.fundeb_regioes.figuras import gerar
    from analises.fundeb_regioes.relatorio import escrever
    from analises.fundeb_regioes.gerar_pdf import construir

    print("Estudo nacional FUNDEB — cinco regiões")
    if args.apenas_relatorio:
        import pandas as pd
        dados = {
            nome: pd.read_csv(Path(RESULTADOS_DIR) / f"{nome}.csv")
            for nome in (
                "baseline", "simulacoes", "melhores",
                "controle_inverso", "meta", "municipios",
            )
        }
    else:
        from analises.fundeb_regioes.estudo import executar
        dados = executar(anos=tuple(args.anos))
    figs = gerar(dados)
    md = escrever(dados)
    pdf = construir()
    print("Figuras:")
    for f in figs:
        print(f"  {f}")
    print(f"Relatório: {md}")
    print(f"PDF: {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
