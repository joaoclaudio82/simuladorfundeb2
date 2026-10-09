"""01 — Inspeção dos dados e identificação do ano."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from analises.fundeb_ceara.config import RESULTADOS_DIR
from analises.fundeb_ceara.dataset import carregar_contexto, inspecionar_rda
from analises.fundeb_ceara.experimentos import tabela_pesos, _salvar
from dados.fundeb_dataset import DATA_DIR, dados_auxiliares_completos


def main() -> None:
    Path(RESULTADOS_DIR).mkdir(parents=True, exist_ok=True)
    rda = inspecionar_rda(DATA_DIR)
    payload = {
        "rda": rda,
        "auxiliares_2025_completos": dados_auxiliares_completos(2025),
        "anos": {},
    }
    pesos_all = []
    for ano in (2024, 2025, 2026):
        ctx = carregar_contexto(ano)
        payload["anos"][str(ano)] = {
            **ctx.evidencias_ano,
            "municipios": ctx.municipios.to_dict(orient="records"),
            "transicoes": [t.__dict__ for t in ctx.transicoes],
        }
        pesos_all.append(tabela_pesos(ctx))
        print(f"Ano {ano}: {ctx.evidencias_ano}")
        print(ctx.municipios.to_string(index=False))
    _salvar(pd_concat(pesos_all), "pesos.csv")
    path = Path(RESULTADOS_DIR) / "inspecao.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Inspecção gravada em {path}")


def pd_concat(frames):
    import pandas as pd
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    main()
