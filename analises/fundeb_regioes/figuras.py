"""Gráficos do estudo nacional por região."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from analises.fundeb_regioes.config import FIGURAS_DIR

sns.set_theme(style="whitegrid", context="paper")
plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 180,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 7.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "font.family": "DejaVu Sans",
})

CORES_REGIAO = {
    "Norte": "#2a6f4e",
    "Nordeste": "#c47c2c",
    "Sudeste": "#3b6d8c",
    "Sul": "#6b4c9a",
    "Centro-Oeste": "#8b3a3a",
}


def _dir() -> Path:
    p = Path(FIGURAS_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cor(df: pd.DataFrame) -> list:
    return [CORES_REGIAO.get(r, "#555") for r in df["regiao"]]


def gerar(dados: dict[str, pd.DataFrame]) -> list[Path]:
    out = []
    d = _dir()
    sim = dados["simulacoes"]
    melhores = dados["melhores"]
    ctrl = dados["controle_inverso"]
    ida = sim[sim["familia"] == "parcial_para_integral"].copy()
    ano = int(ida["ano"].max())
    ida26 = ida[ida["ano"] == ano]
    mel26 = melhores[melhores["ano"] == ano].sort_values("delta_r_percentual")

    # 1. Δ% melhor cenário, cor = região
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    ax.barh(mel26["municipio"], mel26["delta_r_percentual"], color=_cor(mel26))
    ax.set_xlabel("Δ recursos FUNDEB (%)")
    ax.set_title(f"Ganho percentual máximo por município ({ano})")
    _legenda_regiao(ax)
    fig.tight_layout()
    out.append(_save(fig, d / "01_ganho_percentual.png"))

    # 2. Δ R$ milhões
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    m = melhores[melhores["ano"] == ano].sort_values("delta_r")
    ax.barh(m["municipio"], m["delta_r"] / 1e6, color=_cor(m))
    ax.set_xlabel("Δ recursos FUNDEB (R$ milhões)")
    ax.set_title(f"Ganho absoluto máximo por município ({ano})")
    _legenda_regiao(ax)
    fig.tight_layout()
    out.append(_save(fig, d / "02_ganho_absoluto.png"))

    # 3. Heatmap mun × transição (Δ% no melhor % de cada célula)
    src = (
        ida26.sort_values("delta_r_percentual", ascending=False)
        .groupby(["municipio", "codigo_transicao"], as_index=False).first()
    )
    heat = src.pivot(index="municipio", columns="codigo_transicao", values="delta_r_percentual")
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    sns.heatmap(heat, annot=True, fmt=".2f", cmap="YlGnBu", ax=ax, cbar_kws={"label": "Δ %"})
    ax.set_title(f"Δ% máximo — município × transição ({ano})")
    fig.tight_layout()
    out.append(_save(fig, d / "03_heatmap.png"))

    # 4. Curvas % × ΔR$ (transição C, todos os mun)
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    c = ida26[ida26["codigo_transicao"] == "C"].copy()
    for mun, g in c.groupby("municipio"):
        g = g.sort_values("percentual")
        reg = g["regiao"].iloc[0]
        ax.plot(g["percentual"], g["delta_r"] / 1e6, label=f"{mun} ({reg})", color=CORES_REGIAO[reg], lw=1.6)
    ax.set_xlabel("% convertido (iniciais urbano → integral)")
    ax.set_ylabel("Δ recursos (R$ milhões)")
    ax.set_title(f"Quase-linearidade da transição C ({ano})")
    ax.axhline(0, color="0.5", lw=0.6)
    ax.legend(ncol=2, fontsize=7)
    fig.tight_layout()
    out.append(_save(fig, d / "04_curvas_transicao_c.png"))

    # 5. Quatro transições — média Δ% a 100% por região
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    cem = ida26[ida26["percentual"] == 100]
    pv = cem.groupby(["regiao", "codigo_transicao"])["delta_r_percentual"].mean().unstack()
    pv.plot(kind="bar", ax=ax, color=["#7aa2b2", "#c47c5c", "#3b6d8c", "#6b8f71"])
    ax.set_ylabel("Δ % médio a 100%")
    ax.set_xlabel("Região")
    ax.set_title(f"Quatro transições factíveis, por região ({ano})")
    ax.legend(title="Transição", loc="upper right")
    plt.xticks(rotation=0)
    fig.tight_layout()
    out.append(_save(fig, d / "05_transicoes_por_regiao.png"))

    # 6. Alvo vs demais mun vs ente estadual (melhor trans. 100%)
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    s = ida26[(ida26["percentual"] == 100)]
    s = s.sort_values("delta_r", ascending=False).groupby("municipio", as_index=False).first()
    s = s.sort_values("regiao")
    x = np.arange(len(s))
    w = 0.25
    ax.bar(x - w, s["delta_alvo"] / 1e6, w, label="Município-alvo", color="#3b6d8c")
    ax.bar(x, s["delta_demais_mun"] / 1e6, w, label="Demais municípios da UF", color="#c47c5c")
    ax.bar(x + w, s["delta_ente_estadual"] / 1e6, w, label="Ente estadual", color="#6b8f71")
    ax.set_xticks(x)
    ax.set_xticklabels(s["municipio"], rotation=35, ha="right")
    ax.axhline(0, color="0.4", lw=0.7)
    ax.set_ylabel("Δ R$ milhões")
    ax.set_title(f"Quem ganha e quem perde na UF ({ano}, 100% da melhor transição)")
    ax.legend()
    fig.tight_layout()
    out.append(_save(fig, d / "06_alvo_uf_estado.png"))

    # 7. Decomposição VAAF / VAAT
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    s = s.sort_values("municipio")
    x = np.arange(len(s))
    ax.bar(x - w, s["d_vaaf"] / 1e6, w, label="Δ recursos VAAF (fundo estadual)", color="#3b6d8c")
    ax.bar(x, s["d_cvaaf"] / 1e6, w, label="Δ complemento VAAF União", color="#7aa2b2")
    ax.bar(x + w, s["d_cvaat"] / 1e6, w, label="Δ complemento VAAT União", color="#c47c5c")
    ax.set_xticks(x)
    ax.set_xticklabels(s["municipio"], rotation=35, ha="right")
    ax.axhline(0, color="0.4", lw=0.7)
    ax.set_ylabel("Δ R$ milhões")
    ax.set_title(f"De onde vem o ganho municipal ({ano})")
    ax.legend(fontsize=7)
    fig.tight_layout()
    out.append(_save(fig, d / "07_decomposicao.png"))

    # 8. Controle inverso: ida 100% C vs volta 100% C
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    a = ida26[(ida26["codigo_transicao"] == "C") & (ida26["percentual"] == 100)][["municipio", "regiao", "delta_r"]]
    v = ctrl[(ctrl["ano"] == ano) & (ctrl["codigo_transicao"] == "C")][["municipio", "delta_r"]]
    j = a.merge(v, on="municipio", suffixes=("_ida", "_volta"))
    x = np.arange(len(j))
    ax.bar(x - 0.2, j["delta_r_ida"] / 1e6, 0.4, label="Parcial/urbano → integral", color="#2a6f4e")
    ax.bar(x + 0.2, j["delta_r_volta"] / 1e6, 0.4, label="Integral → parcial/urbano (controle)", color="#8b3a3a")
    ax.set_xticks(x)
    ax.set_xticklabels(j["municipio"], rotation=35, ha="right")
    ax.axhline(0, color="0.4", lw=0.7)
    ax.set_ylabel("Δ R$ milhões")
    ax.set_title(f"Controle: a direção do peso determina o sinal ({ano}, transição C)")
    ax.legend()
    fig.tight_layout()
    out.append(_save(fig, d / "08_controle_inverso.png"))

    # 9. Baseline × cenário ótimo
    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    ax.scatter(mel26["r_base"] / 1e6, mel26["r_cenario"] / 1e6, s=70, c=_cor(mel26))
    for _, r in mel26.iterrows():
        ax.annotate(r["municipio"], (r["r_base"] / 1e6, r["r_cenario"] / 1e6), fontsize=7, xytext=(3, 3), textcoords="offset points")
    lim = max(mel26["r_base"].max(), mel26["r_cenario"].max()) / 1e6
    ax.plot([0, lim], [0, lim], ls="--", c="0.5", lw=1)
    ax.set_xlabel("Recursos baseline (R$ milhões)")
    ax.set_ylabel("Recursos no melhor cenário factível (R$ milhões)")
    ax.set_title(f"Todos os pontos acima da identidade ({ano})")
    fig.tight_layout()
    out.append(_save(fig, d / "09_baseline_vs_cenario.png"))

    # 10. Comparação entre anos (Δ%)
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    pv = melhores.pivot(index="municipio", columns="ano", values="delta_r_percentual")
    pv.plot(kind="bar", ax=ax, color=["#8aa2b2", "#3b6d8c", "#1f4a63"])
    ax.set_ylabel("Δ % no melhor cenário")
    ax.set_title("O sinal positivo se repete nos três exercícios")
    plt.xticks(rotation=35, ha="right")
    ax.legend(title="Ano")
    fig.tight_layout()
    out.append(_save(fig, d / "10_anos.png"))

    # 11. Δ UF total vs Δ ente estadual
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    s = ida26[(ida26["percentual"] == 100)].sort_values("delta_r", ascending=False).groupby("municipio", as_index=False).first()
    ax.scatter(s["delta_ente_estadual"] / 1e6, s["delta_uf_total"] / 1e6, s=70, c=_cor(s))
    for _, r in s.iterrows():
        ax.annotate(r["municipio"], (r["delta_ente_estadual"] / 1e6, r["delta_uf_total"] / 1e6), fontsize=7)
    ax.axhline(0, color="0.5", lw=0.6)
    ax.axvline(0, color="0.5", lw=0.6)
    ax.set_xlabel("Δ ente estadual (R$ milhões)")
    ax.set_ylabel("Δ UF inteira (R$ milhões)")
    ax.set_title(f"UF pode subir mesmo com ente estadual em queda ({ano})")
    fig.tight_layout()
    out.append(_save(fig, d / "11_estado_vs_uf.png"))

    # 12. R$/aluno da melhor transição
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    m = mel26.sort_values("ganho_por_aluno")
    ax.barh(m["municipio"], m["ganho_por_aluno"], color=_cor(m))
    ax.set_xlabel("R$ por aluno convertido")
    ax.set_title(f"Retorno por aluno no melhor cenário ({ano})")
    fig.tight_layout()
    out.append(_save(fig, d / "12_por_aluno.png"))

    return out


def _legenda_regiao(ax):
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=r) for r, c in CORES_REGIAO.items()], fontsize=7, loc="lower right")


def _save(fig, path: Path) -> Path:
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path
