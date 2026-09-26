"""
FND-04 — Comparação do cenário sem alterações com os valores oficiais por ente.
Usa a planilha de receita prevista do exercício (contribuição, complementações VAAF,
VAAT e VAAR e total). "Validação interna passou" não substitui esta comparação.
"""
from __future__ import annotations

import numpy as np

from schemas.cenarios import CenarioRequest
from services.bases import Base
from services.cenarios import executar_cenario

# (coluna simulada, coluna oficial, rótulo)
PARES = [
    ("recursos_vaaf", "recursos_contribuicao", "Contribuição de estados e municípios"),
    ("complemento_vaaf", "comp_vaaf_oficial", "Complementação VAAF"),
    ("complemento_vaat", "comp_vaat_oficial", "Complementação VAAT"),
    ("complemento_vaar", "comp_vaar_oficial", "Complementação VAAR"),
    ("recursos_fundeb", "recursos_fundeb_total", "Recursos totais do Fundeb"),
]

# Tolerâncias provisórias (FND-02 ainda precisa aprová-las).
TOLERANCIA_ENTE_REAIS = 1_000.0
TOLERANCIA_UF_PCT = 0.5


def comparar_com_oficial(base: Base) -> dict:
    if base.referencia_oficial is None:
        return {"disponivel": False, "motivo": "base sem valores oficiais por ente"}

    sim = executar_cenario(CenarioRequest(base_id=base.base_id), base).resultados["A"]
    oficial = base.referencia_oficial
    sem_oficial = sorted(set(sim["ibge"]) - set(oficial["ibge"]))
    sem_simulacao = sorted(set(oficial["ibge"]) - set(sim["ibge"]))
    m = sim.merge(oficial, on="ibge", how="inner", validate="one_to_one")

    indicadores = []
    for col_sim, col_of, rotulo in PARES:
        dif = m[col_sim] - m[col_of]
        recebe_sim, recebe_of = m[col_sim].abs() > 0.5, m[col_of].abs() > 0.5
        indicadores.append({
            "indicador": col_sim,
            "rotulo": rotulo,
            "total_simulado": float(m[col_sim].sum()),
            "total_oficial": float(m[col_of].sum()),
            "maior_diferenca_absoluta": float(dif.abs().max()),
            "soma_diferencas_absolutas": float(dif.abs().sum()),
            "entes_acima_da_tolerancia": int((dif.abs() > TOLERANCIA_ENTE_REAIS).sum()),
            "recebem_so_na_simulacao": int((recebe_sim & ~recebe_of).sum()),
            "recebem_so_no_oficial": int((~recebe_sim & recebe_of).sum()),
        })

    por_uf = m.groupby("uf").agg(
        fundeb_simulado=("recursos_fundeb", "sum"),
        fundeb_oficial=("recursos_fundeb_total", "sum"),
        vaaf_simulado=("complemento_vaaf", "sum"),
        vaaf_oficial=("comp_vaaf_oficial", "sum"),
        vaat_simulado=("complemento_vaat", "sum"),
        vaat_oficial=("comp_vaat_oficial", "sum"),
    ).reset_index()
    m["_desvio_abs"] = (m["recursos_fundeb"] - m["recursos_fundeb_total"]).abs()
    por_uf = por_uf.merge(m.groupby("uf")["_desvio_abs"].sum().rename("desvio_abs_fundeb").reset_index(), on="uf")
    with np.errstate(divide="ignore", invalid="ignore"):
        por_uf["desvio_abs_fundeb_pct"] = por_uf["desvio_abs_fundeb"] / por_uf["fundeb_oficial"] * 100
        por_uf["vaaf_dif_pct"] = np.where(
            por_uf["vaaf_oficial"] != 0,
            (por_uf["vaaf_simulado"] - por_uf["vaaf_oficial"]) / por_uf["vaaf_oficial"] * 100, np.nan)
    por_uf["acima_da_tolerancia"] = (
        (por_uf["desvio_abs_fundeb_pct"] > TOLERANCIA_UF_PCT) | (por_uf["vaaf_dif_pct"].abs() > TOLERANCIA_UF_PCT)
    )
    por_uf = por_uf.sort_values("desvio_abs_fundeb_pct", ascending=False)

    m["dif_fundeb"] = m["recursos_fundeb"] - m["recursos_fundeb_total"]
    with np.errstate(divide="ignore", invalid="ignore"):
        m["dif_fundeb_pct"] = np.where(m["recursos_fundeb_total"] != 0,
                                       m["dif_fundeb"] / m["recursos_fundeb_total"] * 100, np.nan)
    maiores = m.reindex(m["dif_fundeb"].abs().sort_values(ascending=False).index).head(15)
    vaat_divergente = m[(m["complemento_vaat"].abs() > 0.5) != (m["comp_vaat_oficial"].abs() > 0.5)]

    def registros(df, cols):
        return df[cols].replace({np.nan: None}).to_dict(orient="records")

    return {
        "disponivel": True,
        "base_id": base.base_id,
        "tolerancias": {"por_ente_reais": TOLERANCIA_ENTE_REAIS, "por_uf_pct": TOLERANCIA_UF_PCT,
                        "situacao": "provisórias, pendentes de aprovação (FND-02)"},
        "cobertura": {"entes_comparados": int(len(m)), "sem_valor_oficial": sem_oficial,
                      "sem_simulacao": sem_simulacao},
        "indicadores": indicadores,
        "por_uf": registros(por_uf, list(por_uf.columns)),
        "maiores_diferencas": registros(maiores, ["ibge", "uf", "nome", "recursos_fundeb", "recursos_fundeb_total",
                                                  "dif_fundeb", "dif_fundeb_pct"]),
        "vaat_elegibilidade_divergente": registros(vaat_divergente, ["ibge", "uf", "nome", "inabilitados_vaat",
                                                                     "complemento_vaat", "comp_vaat_oficial"]),
    }
