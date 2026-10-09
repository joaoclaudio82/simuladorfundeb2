"""Gráficos obrigatórios do estudo contrafactual."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from analises.fundeb_ceara.config import FIGURAS_DIR

sns.set_theme(style="whitegrid", context="talk")
plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 160,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "legend.fontsize": 8,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "font.family": "DejaVu Sans",
})


def _dir(ano: int | None = None) -> Path:
    path = Path(FIGURAS_DIR)
    if ano is not None:
        path = path / str(ano)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fmt_mi(x, _pos=None):
    return f"{x/1e6:.1f}"


def gerar_figuras(dados: dict[str, pd.DataFrame]) -> list[Path]:
    gerados: list[Path] = []
    sim = dados["simulacoes"]
    baseline = dados["baseline"]
    melhores = dados["melhores_cenarios"]
    impactos = dados["impactos_outros_municipios"]
    otim = dados["otimizacao"]
    for ano in sorted(sim["ano"].unique()):
        gerados.extend(_figuras_ano(
            ano=int(ano),
            sim=sim[sim["ano"] == ano],
            baseline=baseline[baseline["ano"] == ano],
            melhores=melhores[melhores["ano"] == ano],
            impactos=impactos[impactos["ano"] == ano] if len(impactos) else impactos,
            otim=otim[otim["ano"] == ano],
        ))
    gerados.extend(_figura_comparacao_anos(melhores))
    return gerados


def _figuras_ano(ano, sim, baseline, melhores, impactos, otim) -> list[Path]:
    out = []
    d = _dir(ano)
    ind = sim[sim["familia"] == "transicao_individual"].copy()

    # 1. % convertido × Δ recursos
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    trans = list(ind["codigo_transicao"].unique())
    for ax, codigo in zip(axes.ravel(), trans):
        g = ind[ind["codigo_transicao"] == codigo]
        rotulo = g["transformacao"].iloc[0] if len(g) else codigo
        for mun, gg in g.groupby("municipio"):
            gg = gg.sort_values("percentual")
            ax.plot(gg["percentual"], gg["delta_r"] / 1e6, label=mun, lw=1.4)
        ax.set_title(rotulo, fontsize=10)
        ax.set_xlabel("% convertido")
        ax.set_ylabel("Δ recursos FUNDEB (R$ milhões)")
        ax.axhline(0, color="0.5", lw=0.6)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(f"Gráfico 1 — Conversão percentual × Δ recursos ({ano})", y=1.01)
    fig.tight_layout()
    p = d / "01_percentual_delta.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    out.append(p)

    # 2. Município × ganho máximo %
    fig, ax = plt.subplots(figsize=(9, 5))
    m = melhores.sort_values("delta_r_percentual")
    ax.barh(m["municipio"], m["delta_r_percentual"], color="#3b6d8c")
    ax.set_xlabel("Ganho máximo Δ % (melhor transição individual)")
    ax.set_title(f"Gráfico 2 — Ganho percentual máximo por município ({ano})")
    fig.tight_layout()
    p = d / "02_ganho_percentual.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(p)

    # 3. Ganho por aluno
    fig, ax = plt.subplots(figsize=(9, 5))
    m = melhores.sort_values("ganho_por_aluno")
    ax.barh(m["municipio"], m["ganho_por_aluno"], color="#6b8f71")
    ax.set_xlabel("R$ por aluno convertido (melhor ΔR$)")
    ax.set_title(f"Gráfico 3 — Ganho por aluno convertido ({ano})")
    fig.tight_layout()
    p = d / "03_ganho_por_aluno.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(p)

    # 4. Heatmap município × transformação (Δ % no melhor percentual de cada célula)
    pivot_src = (
        ind.sort_values("delta_r_percentual", ascending=False)
        .groupby(["municipio", "codigo_transicao"], as_index=False)
        .first()
    )
    heat = pivot_src.pivot(index="municipio", columns="codigo_transicao", values="delta_r_percentual")
    labels = {
        r["codigo_transicao"]: r["transformacao"].split("(")[0].strip()
        for _, r in pivot_src.drop_duplicates("codigo_transicao").iterrows()
    }
    heat = heat.rename(columns=labels)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    sns.heatmap(heat, annot=True, fmt=".2f", cmap="YlGnBu", ax=ax, cbar_kws={"label": "Δ %"})
    ax.set_title(f"Gráfico 4 — Heatmap Δ% (melhor % de cada transição) ({ano})")
    ax.set_xlabel("Transformação")
    ax.set_ylabel("Município")
    fig.tight_layout()
    p = d / "04_heatmap.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(p)

    # 5. Efeito sobre os demais municípios (50% da melhor transição de cada alvo)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    resumo = (
        ind[ind["percentual"] == 50]
        .sort_values("delta_r", ascending=False)
        .groupby("municipio", as_index=False)
        .first()
    )
    if len(resumo):
        x = np.arange(len(resumo))
        w = 0.38
        ax.bar(x - w / 2, resumo["delta_alvo"] / 1e6, w, label="Município-alvo", color="#3b6d8c")
        ax.bar(x + w / 2, resumo["delta_demais"] / 1e6, w, label="Demais municípios do CE", color="#c47c5c")
        ax.set_xticks(x)
        ax.set_xticklabels(resumo["municipio"], rotation=35, ha="right")
        ax.axhline(0, color="0.4", lw=0.7)
        ax.set_ylabel("Δ recursos (R$ milhões)")
        ax.set_title(f"Gráfico 5 — Efeito intraestadual a 50% da melhor transição ({ano})")
        ax.legend()
    fig.tight_layout()
    p = d / "05_spillover_ce.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(p)

    # 6. Baseline × ótimo factível 100%
    fact = otim[otim["cenario_id"] == "OTIMO_FACTIVEL_100"]
    if fact.empty:
        fact = otim[otim["familia"] == "otimo_factivel"].sort_values("percentual").groupby("ibge", as_index=False).last()
    fig, ax = plt.subplots(figsize=(7.5, 6))
    if len(fact):
        ax.scatter(fact["r_base"] / 1e6, fact["r_cenario"] / 1e6, s=55, c="#3b6d8c")
        for _, r in fact.iterrows():
            ax.annotate(r["municipio"], (r["r_base"] / 1e6, r["r_cenario"] / 1e6), fontsize=8, xytext=(4, 4), textcoords="offset points")
        lim = max(fact["r_base"].max(), fact["r_cenario"].max()) / 1e6
        ax.plot([0, lim], [0, lim], ls="--", c="0.5", lw=1, label="identidade")
        ax.set_xlabel("Recursos FUNDEB baseline (R$ milhões)")
        ax.set_ylabel("Recursos no ótimo factível 100% (R$ milhões)")
        ax.set_title(f"Gráfico 6 — Baseline × ótimo factível ({ano})")
        ax.legend()
    fig.tight_layout()
    p = d / "06_baseline_vs_otimo.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(p)

    # extra: tamanho da rede × ganho %
    fig, ax = plt.subplots(figsize=(7.5, 5))
    j = melhores.merge(baseline[["ibge", "total_matriculas"]], on="ibge")
    ax.scatter(j["total_matriculas"], j["delta_r_percentual"], s=60, c="#3b6d8c")
    for _, r in j.iterrows():
        ax.annotate(r["municipio"], (r["total_matriculas"], r["delta_r_percentual"]), fontsize=8)
    ax.set_xlabel("Tamanho da rede (matrículas totais)")
    ax.set_ylabel("Ganho máximo Δ %")
    ax.set_title(f"Tamanho da rede × ganho percentual ({ano})")
    fig.tight_layout()
    p = d / "07_tamanho_vs_ganho.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(p)
    return out


def _figura_comparacao_anos(melhores: pd.DataFrame) -> list[Path]:
    d = _dir()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    if melhores.empty:
        return []
    pv = melhores.pivot(index="municipio", columns="ano", values="delta_r_percentual")
    pv.plot(kind="bar", ax=ax, color=["#8aa2b2", "#3b6d8c", "#1f4a63"])
    ax.set_ylabel("Ganho máximo Δ %")
    ax.set_xlabel("Município")
    ax.set_title("Comparação entre exercícios — ganho percentual máximo")
    ax.legend(title="Ano")
    plt.xticks(rotation=35, ha="right")
    fig.tight_layout()
    p = d / "comparacao_anos_ganho_percentual.png"
    fig.savefig(p)
    plt.close(fig)
    return [p]
