"""Gera RESULTADOS.md e o resumo terminal a partir dos CSVs computados."""

from __future__ import annotations

import datetime as dt
import os
import platform
import subprocess
import sys
from pathlib import Path

import pandas as pd

from analises.fundeb_ceara.config import ANALISE_DIR, RESULTADOS_DIR, ROOT_DIR


def brl(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    s = f"{float(x):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, casas: int = 3) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{float(x):.{casas}f}%".replace(".", ",")


def num(x, casas: int = 1) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    s = f"{float(x):,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _ler(nome: str) -> pd.DataFrame:
    return pd.read_csv(Path(RESULTADOS_DIR) / nome)


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT_DIR, text=True,
        ).strip()
    except Exception:
        return "desconhecido"


def metadados_execucao() -> dict:
    return {
        "python": sys.version.replace("\n", " "),
        "plataforma": platform.platform(),
        "data_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "commit": _git_commit(),
        "cwd": ROOT_DIR,
    }


def _melhor_linha(df: pd.DataFrame, coluna: str) -> pd.Series:
    sub = df.dropna(subset=[coluna])
    return sub.loc[sub[coluna].idxmax()]


def resumo_terminal(dados: dict[str, pd.DataFrame] | None = None) -> str:
    if dados is None:
        dados = {
            "baseline": _ler("baseline.csv"),
            "simulacoes": _ler("simulacoes.csv"),
            "melhores_cenarios": _ler("melhores_cenarios.csv"),
            "tabela_final": _ler("tabela_final.csv"),
            "g10": _ler("otimizacao_conjunta.csv"),
            "meta": _ler("meta_execucao.csv"),
            "rankings": _ler("rankings.csv"),
            "otimizacao": _ler("otimizacao.csv"),
            "linearidade": _ler("linearidade.csv"),
        }
    meta = dados["meta"]
    melhores = dados["melhores_cenarios"]
    sim = dados["simulacoes"]
    g10 = dados["g10"]
    lin = dados["linearidade"]
    ind = sim[sim["familia"] == "transicao_individual"]

    anos = ", ".join(str(int(a)) for a in sorted(meta["ano"].unique()))
    n_cen = int(meta["n_cenarios"].sum())
    n_ok = int(meta["n_validos"].sum())
    ttot = float(meta["tempo_total_s"].sum())

    abs_ = _melhor_linha(melhores, "delta_r")
    perc = _melhor_linha(melhores, "delta_r_percentual")
    aluno = _melhor_linha(melhores, "ganho_por_aluno")

    linhas_estrategia = []
    for ano in sorted(melhores["ano"].unique()):
        linhas_estrategia.append(f"  [{int(ano)}]")
        for _, r in melhores[melhores["ano"] == ano].sort_values("municipio").iterrows():
            linhas_estrategia.append(
                f"    {r['municipio']}: {r['transformacao']} @ {r['percentual']:.0f}% "
                f"({num(r['alunos_movidos'], 0)} alunos)  Δ {brl(r['delta_r'])} ({pct(r['delta_r_percentual'])})"
            )

    g10_txt = []
    for ano in sorted(g10["ano"].unique()):
        sub = g10[(g10["ano"] == ano) & (g10["cenario_id"].str.startswith("G10_FACTIVEL"))]
        if sub.empty:
            continue
        best = sub.loc[sub["g10"].idxmax()]
        g10_txt.append(
            f"  {int(ano)} G10 factível {int(best['percentual'])}%: {brl(best['g10'])} "
            f"({pct(best['g10_percentual'])} sobre a soma dos 10)"
        )

    quase = lin["quase_linear"].mean() if len(lin) and "quase_linear" in lin.columns else float("nan")
    principal = (
        "A composição das matrículas altera os recursos simulados via fatores de ponderação "
        "e equalização VAAF/VAAT. A expansão contrafactual do tempo integral aumenta a "
        "participação relativa de alguns municípios, com magnitude dependente da estrutura "
        f"da rede e com redistribuição intraestadual. Linearidade média (fração quase-linear R²≥0,995): "
        f"{pct(100*quase, 1) if pd.notna(quase) else '—'} dos pares município×transição."
    )

    txt = f"""
ANO/DATASET ANALISADO: {anos} (2024 = .rda legado; 2025 e 2026 = planilhas oficiais)
MUNICÍPIOS: 10
CENÁRIOS EXECUTADOS: {n_cen}
CENÁRIOS VÁLIDOS: {n_ok}
TEMPO DE EXECUÇÃO: {ttot:.1f} s (média {1000*ttot/max(n_cen,1):.1f} ms/cenário)

MAIOR GANHO ABSOLUTO:
município: {abs_['municipio']} ({int(abs_['ano'])})
transformação: {abs_['transformacao']}
alunos: {num(abs_['alunos_movidos'], 1)}
ganho R$: {brl(abs_['delta_r'])}
ganho %: {pct(abs_['delta_r_percentual'])}

MAIOR GANHO PERCENTUAL:
município: {perc['municipio']} ({int(perc['ano'])})
transformação: {perc['transformacao']}
alunos: {num(perc['alunos_movidos'], 1)}
ganho R$: {brl(perc['delta_r'])}
ganho %: {pct(perc['delta_r_percentual'])}

MAIOR GANHO POR ALUNO:
município: {aluno['municipio']} ({int(aluno['ano'])})
transformação: {aluno['transformacao']}
alunos: {num(aluno['alunos_movidos'], 1)}
ganho R$: {brl(aluno['delta_r'])}
R$/aluno: {brl(aluno['ganho_por_aluno'])}

MELHOR ESTRATÉGIA PARA CADA MUNICÍPIO:
{chr(10).join(linhas_estrategia)}

GANHO AGREGADO DOS 10:
{chr(10).join(g10_txt)}

PRINCIPAL RESULTADO CIENTÍFICO:
{principal}

LIMITAÇÕES:
- Um snapshot por exercício (sem painel de matrículas longitudinais além dos três anos disponíveis).
- Ótimo matemático é teórico e não educacionalmente factível.
- Resultados não são recomendação para reclassificar alunos.
- O efeito mede incentivos implícitos nos fatores de ponderação e na equalização, não o custo pedagógico da jornada integral.
""".strip()
    return txt


def escrever_resultados(dados: dict[str, pd.DataFrame] | None = None) -> Path:
    if dados is None:
        dados = {k: _ler(n) for k, n in {
            "baseline": "baseline.csv",
            "simulacoes": "simulacoes.csv",
            "melhores_cenarios": "melhores_cenarios.csv",
            "tabela_final": "tabela_final.csv",
            "g10": "otimizacao_conjunta.csv",
            "meta": "meta_execucao.csv",
            "rankings": "rankings.csv",
            "otimizacao": "otimizacao.csv",
            "linearidade": "linearidade.csv",
            "pesos": "pesos.csv",
            "transicoes": "transicoes_detectadas.csv",
            "impactos": "impactos_outros_municipios.csv",
        }.items()}
    meta_run = metadados_execucao()
    meta = dados["meta"]
    baseline = dados["baseline"]
    melhores = dados["melhores_cenarios"]
    tabela = dados["tabela_final"]
    sim = dados["simulacoes"]
    g10 = dados["g10"]
    lin = dados["linearidade"]
    otim = dados["otimizacao"]
    trans = dados["transicoes"]
    pesos = dados["pesos"]
    rank = dados["rankings"]
    ind = sim[sim["familia"] == "transicao_individual"]

    def _tabela_md(df: pd.DataFrame, cols: list[str], fmt: dict | None = None) -> str:
        fmt = fmt or {}
        header = "| " + " | ".join(cols) + " |"
        sep = "| " + " | ".join("---" for _ in cols) + " |"
        lines = [header, sep]
        for _, r in df.iterrows():
            cells = []
            for c in cols:
                v = r[c]
                if c in fmt:
                    cells.append(fmt[c](v))
                else:
                    cells.append(str(v))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    partes = []
    partes.append("# Resultados: composição das matrículas e transferências do FUNDEB no Ceará")
    partes.append("")
    partes.append("Estudo contrafactual. Os números abaixo foram lidos diretamente dos CSVs em `resultados/`.")
    partes.append("Não se trata de recomendação para reclassificar alunos.")
    partes.append("")
    partes.append("## 1. Dados utilizados")
    partes.append("")
    partes.append("| Ano | Entes | Etapas | Municípios CE | Ponderador | VAAF União | VAAT União | VAAR União | Fonte |")
    partes.append("| ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |")
    for _, r in meta.iterrows():
        partes.append(
            f"| {int(r['ano'])} | {int(r['n_entes'])} | {int(r['n_etapas'])} | {int(r['n_municipios_ce'])} | "
            f"{r['modo_ponderador']} | {brl(r['complementacao_vaaf'])} | {brl(r['complementacao_vaat'])} | "
            f"{brl(r['complementacao_vaar'])} | {r['fonte']} |"
        )
    partes.append("")
    partes.append("## 2. Ano identificado")
    partes.append("")
    partes.append(
        "Os arquivos `data/*.rda` **não trazem o ano no nome**. A identificação de **2024** "
        "baseia-se em: (i) `carregar_dataset_2024()` em `dados/fundeb_dataset.py`; "
        "(ii) `PonderadorNSE 2024.pdf`; (iii) montantes-padrão de complementação da União "
        "usados no dataset legado; (iv) documentação do próprio repositório "
        "(`manual-do-sistema.md`, `README.md`). Os exercícios **2025** e **2026** vêm das "
        "planilhas em `20252026/`, filtradas pela coluna de ano quando ela existe."
    )
    partes.append("")
    partes.append(
        "Há três snapshots, não uma série construída artificialmente. Cada exercício foi "
        "simulado por completo com o motor `simula_fundeb`."
    )
    partes.append("")
    partes.append("## 3. Metodologia")
    partes.append("")
    partes.append(
        "Para cada cenário, as matrículas de um (ou dez) município(s) são alteradas "
        "conservando o total de alunos e a não-negatividade. O motor completo do FUNDEB "
        "é reexecutado sobre todos os entes. O baseline `S0_BASELINE` usa pesos, NSE/DREC "
        "e montantes oficiais, com `max_nse=min_nse=max_nf=min_nf=1.0` — o mesmo critério "
        "do cenário de referência dos exercícios 2025/2026. Em 2024 isso achata o NF para 1 "
        "após o reescalonamento interno do motor; o NSE oficial permanece. A validação "
        "interna (`validar_interno`, RF-10) roda após cada simulação."
    )
    partes.append("")
    partes.append("Transições factíveis detectadas:")
    partes.append("")
    partes.append(_tabela_md(
        trans,
        ["ano", "codigo", "origem", "destino", "peso_vaaf_origem", "peso_vaaf_destino", "peso_vaat_origem", "peso_vaat_destino"],
        {"ano": lambda x: str(int(x)),
         "peso_vaaf_origem": lambda x: f"{float(x):.4f}",
         "peso_vaaf_destino": lambda x: f"{float(x):.4f}",
         "peso_vaat_origem": lambda x: f"{float(x):.4f}",
         "peso_vaat_destino": lambda x: f"{float(x):.4f}"},
    ))
    partes.append("")
    partes.append("## 4. Municípios")
    partes.append("")
    mun_tab = baseline[["ano", "municipio", "ibge", "total_matriculas"]].drop_duplicates()
    partes.append(_tabela_md(
        mun_tab.sort_values(["ano", "municipio"]),
        ["ano", "municipio", "ibge", "total_matriculas"],
        {"ano": lambda x: str(int(x)), "ibge": lambda x: str(int(x)),
         "total_matriculas": lambda x: num(x, 0)},
    ))
    partes.append("")
    partes.append("Códigos IBGE obtidos por correspondência de nome normalizado na UF CE, sem hardcode prévio.")
    partes.append("")
    partes.append("## 5. Baseline")
    partes.append("")
    partes.append(_tabela_md(
        baseline.sort_values(["ano", "municipio"]),
        ["ano", "municipio", "ibge", "total_matriculas", "matriculas_vaaf", "matriculas_vaat",
         "recursos_vaaf", "complemento_vaaf", "complemento_vaat", "complemento_vaar",
         "complemento_uniao", "recursos_fundeb", "vaaf_final", "vaat_final"],
        {
            "ano": lambda x: str(int(x)),
            "ibge": lambda x: str(int(x)),
            "total_matriculas": lambda x: num(x, 0),
            "matriculas_vaaf": lambda x: num(x, 1),
            "matriculas_vaat": lambda x: num(x, 1),
            "recursos_vaaf": brl,
            "complemento_vaaf": brl,
            "complemento_vaat": brl,
            "complemento_vaar": brl,
            "complemento_uniao": brl,
            "recursos_fundeb": brl,
            "vaaf_final": brl,
            "vaat_final": brl,
        },
    ))
    partes.append("")
    partes.append("## 6. Cenários")
    partes.append("")
    partes.append(
        f"Foram executados **{int(meta['n_cenarios'].sum())}** cenários, "
        f"dos quais **{int(meta['n_validos'].sum())}** passaram na validação interna. "
        f"Tempo total: **{float(meta['tempo_total_s'].sum()):.1f} s**."
    )
    partes.append("")
    partes.append("| Ano | Cenários | Válidos | Tempo (s) | Tempo médio (ms) |")
    partes.append("| ---: | ---: | ---: | ---: | ---: |")
    for _, r in meta.iterrows():
        partes.append(
            f"| {int(r['ano'])} | {int(r['n_cenarios'])} | {int(r['n_validos'])} | "
            f"{r['tempo_total_s']:.1f} | {1000*r['tempo_medio_s']:.2f} |"
        )
    partes.append("")
    partes.append(
        "Famílias: transições individuais A–D em 0–100%; ótimo factível (A–D simultâneas); "
        "ótimo matemático (concentração teórica); sensibilidade +1 aluno; G10 conjunto e maximin."
    )
    partes.append("")
    partes.append("## 7. Resultados")
    partes.append("")
    if len(ind):
        abs_ = _melhor_linha(ind, "delta_r")
        perc = _melhor_linha(ind, "delta_r_percentual")
        partes.append(
            f"Maior ΔR$ individual: **{abs_['municipio']}** ({int(abs_['ano'])}), "
            f"{abs_['transformacao']} a {abs_['percentual']:.0f}% → {brl(abs_['delta_r'])} "
            f"({pct(abs_['delta_r_percentual'])})."
        )
        partes.append("")
        partes.append(
            f"Maior Δ%: **{perc['municipio']}** ({int(perc['ano'])}), "
            f"{perc['transformacao']} a {perc['percentual']:.0f}% → {pct(perc['delta_r_percentual'])} "
            f"({brl(perc['delta_r'])})."
        )
    partes.append("")
    partes.append("## 8. Melhor transformação de cada município")
    partes.append("")
    partes.append(_tabela_md(
        tabela.sort_values(["ano", "municipio"]),
        ["ano", "municipio", "transformacao", "pct_convertido", "alunos", "base_r", "novo_r", "delta_r", "delta_pct", "r_por_aluno"],
        {
            "ano": lambda x: str(int(x)),
            "pct_convertido": lambda x: f"{float(x):.0f}",
            "alunos": lambda x: num(x, 1),
            "base_r": brl, "novo_r": brl, "delta_r": brl,
            "delta_pct": lambda x: pct(x, 3),
            "r_por_aluno": brl,
        },
    ))
    partes.append("")
    partes.append("## 9. Ótimo matemático")
    partes.append("")
    partes.append(
        "Cenário **teórico**: todo o estoque de matrículas do município é concentrado na etapa "
        "de maior soma de pesos VAAF+VAAT entre as cinco mais altas. **Não é educacionalmente factível.**"
    )
    partes.append("")
    mat = otim[otim["familia"] == "otimo_matematico"]
    if len(mat):
        best_mat = mat.sort_values("delta_r", ascending=False).groupby(["ano", "ibge"], as_index=False).first()
        partes.append(_tabela_md(
            best_mat.sort_values(["ano", "municipio"]),
            ["ano", "municipio", "transformacao", "alunos_movidos", "delta_r", "delta_r_percentual"],
            {
                "ano": lambda x: str(int(x)),
                "alunos_movidos": lambda x: num(x, 0),
                "delta_r": brl,
                "delta_r_percentual": lambda x: pct(x, 2),
            },
        ))
    partes.append("")
    partes.append("## 10. Ótimo factível")
    partes.append("")
    partes.append(
        "Apenas as transições A–D (parcial→integral na educação infantil pública e "
        "fundamental urbano→integral). Conversão simultânea a 25%, 50%, 75% e 100%."
    )
    partes.append("")
    fact = otim[otim["familia"] == "otimo_factivel"]
    if len(fact):
        best_f = fact.sort_values("delta_r", ascending=False).groupby(["ano", "ibge"], as_index=False).first()
        partes.append(_tabela_md(
            best_f.sort_values(["ano", "municipio"]),
            ["ano", "municipio", "percentual", "alunos_movidos", "delta_r", "delta_r_percentual", "ganho_por_aluno"],
            {
                "ano": lambda x: str(int(x)),
                "percentual": lambda x: f"{float(x):.0f}",
                "alunos_movidos": lambda x: num(x, 1),
                "delta_r": brl,
                "delta_r_percentual": lambda x: pct(x, 3),
                "ganho_por_aluno": brl,
            },
        ))
    partes.append("")
    partes.append("## 11. Impacto sobre os demais municípios")
    partes.append("")
    spill = ind[ind["percentual"] == 50].sort_values("delta_r", ascending=False).groupby(["ano", "municipio"], as_index=False).first()
    if len(spill):
        partes.append("A 50% da transição individual de maior ΔR$ de cada alvo:")
        partes.append("")
        partes.append(_tabela_md(
            spill.sort_values(["ano", "municipio"]),
            ["ano", "municipio", "delta_alvo", "delta_demais", "delta_ce_municipal", "n_beneficiados", "n_prejudicados"],
            {
                "ano": lambda x: str(int(x)),
                "delta_alvo": brl,
                "delta_demais": brl,
                "delta_ce_municipal": brl,
                "n_beneficiados": lambda x: str(int(x)),
                "n_prejudicados": lambda x: str(int(x)),
            },
        ))
        partes.append("")
        partes.append(
            "Se `delta_ce_municipal` é pequeno frente a `delta_alvo` e `delta_demais` tem sinal "
            "oposto, o mecanismo está sobretudo **redistribuindo** o fundo estadual/a equalização, "
            "não criando recursos novos na mesma magnitude do ganho do alvo."
        )
    partes.append("")
    partes.append("## 12. Otimização conjunta")
    partes.append("")
    if len(g10):
        partes.append(_tabela_md(
            g10.sort_values(["ano", "cenario_id"]),
            ["ano", "cenario_id", "percentual", "g10", "g10_percentual", "min_delta_pct", "max_delta_pct", "alunos_movidos"],
            {
                "ano": lambda x: str(int(x)),
                "percentual": lambda x: "—" if pd.isna(x) else f"{float(x):.0f}",
                "g10": brl,
                "g10_percentual": lambda x: pct(x, 3),
                "min_delta_pct": lambda x: pct(x, 3),
                "max_delta_pct": lambda x: pct(x, 3),
                "alunos_movidos": lambda x: num(x, 0),
            },
        ))
    partes.append("")
    partes.append(
        "O cenário marcado como `pareto_equidade` maximiza o menor ganho percentual entre os dez "
        "(maximin) no grid de conversão factível conjunta."
    )
    partes.append("")
    partes.append("## 13. Análise de sensibilidade")
    partes.append("")
    sens = sim[sim["familia"] == "sensibilidade"]
    if len(sens):
        resumo_s = (
            sens.groupby(["ano", "codigo_transicao"], as_index=False)
            .agg(
                transformacao=("transformacao", "first"),
                mediana_dR=("delta_r", "median"),
                media_dR=("delta_r", "mean"),
            )
        )
        partes.append("Efeito de converter **mais um aluno** (mediana entre os 10 municípios):")
        partes.append("")
        partes.append(_tabela_md(
            resumo_s.sort_values(["ano", "codigo_transicao"]),
            ["ano", "codigo_transicao", "transformacao", "mediana_dR", "media_dR"],
            {"ano": lambda x: str(int(x)), "mediana_dR": brl, "media_dR": brl},
        ))
    partes.append("")
    partes.append("## 14. Linearidade e tamanho da rede")
    partes.append("")
    if len(lin):
        frac = 100 * lin["quase_linear"].mean()
        partes.append(
            f"Fração de curvas município×transição com R² linear ≥ 0,995: **{pct(frac, 1)}**. "
            "Valores abaixo disso indicam não-linearidade associada à equalização VAAF/VAAT "
            "(mudança de quem é complementado)."
        )
        partes.append("")
        nlin = lin[~lin["quase_linear"]].sort_values("r2_linear")
        if len(nlin):
            partes.append("Pares menos lineares:")
            partes.append("")
            partes.append(_tabela_md(
                nlin.head(15),
                ["ano", "municipio", "codigo_transicao", "r2_linear", "max_residuo_abs", "delta_r_max"],
                {
                    "ano": lambda x: str(int(x)),
                    "r2_linear": lambda x: f"{float(x):.4f}",
                    "max_residuo_abs": brl,
                    "delta_r_max": brl,
                },
            ))
        hip = melhores.merge(baseline[["ano", "ibge", "total_matriculas"]], on=["ano", "ibge"])
        if len(hip) >= 5:
            corr = hip["total_matriculas"].corr(hip["delta_r_percentual"])
            partes.append("")
            partes.append(
                f"Correlação de Pearson entre tamanho da rede e ganho % máximo: **{corr:.3f}**. "
                "A hipótese de que municípios menores têm ganho percentual diferente dos maiores "
                "é avaliada por esse coeficiente (não por causalidade)."
            )
    partes.append("")
    partes.append("## 15. Limitações")
    partes.append("")
    partes.append("- Três snapshots (2024, 2025, 2026), não um painel de matrículas idêntico ao longo do tempo.")
    partes.append("- Em 2025/2026 as transições usam o segmento urbano/padrão, não todos os sufixos campo/indígena/quilombola.")
    partes.append("- O ótimo matemático ignora restrições pedagógicas, de infraestrutura e de etapa etária.")
    partes.append("- VAAR entra com o peso observado; não modelamos mudança de condicionalidades VAAR.")
    partes.append("- NF de 2024 é reescalonado para 1 pelo motor quando max=min=1; DREC de 2025+ permanece oficial.")
    partes.append("- Custos da jornada integral e efeitos de aprendizagem estão fora do modelo.")
    partes.append("")
    partes.append("## 16. Implicações para políticas públicas")
    partes.append("")
    partes.append(
        "O experimento contrafactual indica que a composição das matrículas altera os recursos "
        "simulados devido aos fatores de ponderação do FUNDEB e aos mecanismos de equalização "
        "VAAF, VAAT e VAAR. A expansão efetiva da oferta em tempo integral apresenta "
        "simultaneamente implicações educacionais e fiscais, cuja magnitude pode ser estimada "
        "pelo modelo. Isso descreve **incentivos financeiros implícitos**, não uma prescrição "
        "para transferir alunos entre etapas."
    )
    partes.append("")
    partes.append("## 17. Possíveis extensões")
    partes.append("")
    partes.append("- Incluir sufixos campo/indígena/quilombola e rede conveniada como transições factíveis adicionais.")
    partes.append("- Custo-efetividade: ΔFUNDEB versus custo da vaga em tempo integral.")
    partes.append("- Otimização com restrições de capacidade (teto de vagas integrais).")
    partes.append("- Repetir o desenho para outras UFs.")
    partes.append("- Painel verdadeiro se o INEP/FNDE publicar matrículas comparáveis por mais anos.")
    partes.append("")
    partes.append("## Reprodutibilidade")
    partes.append("")
    partes.append(f"- Python: `{meta_run['python']}`")
    partes.append(f"- Plataforma: `{meta_run['plataforma']}`")
    partes.append(f"- Data: {meta_run['data_utc']}")
    partes.append(f"- Commit: `{meta_run['commit']}`")
    partes.append("- Comando: `python -m analises.fundeb_ceara.run`")
    partes.append("")
    partes.append("## Rankings (melhor transição individual por município)")
    partes.append("")
    for ano in sorted(rank["ano"].unique()):
        partes.append(f"### Exercício {int(ano)}")
        for rk in ["A_ganho_absoluto", "B_ganho_percentual", "C_ganho_por_aluno", "D_transicao_eficiente"]:
            sub = rank[(rank["ano"] == ano) & (rank["ranking"] == rk)].sort_values("posicao")
            if sub.empty:
                continue
            partes.append(f"**{rk}**")
            partes.append("")
            fmt_valor = (lambda x: pct(x, 3)) if rk == "B_ganho_percentual" else brl
            partes.append(_tabela_md(
                sub,
                ["posicao", "municipio", "transformacao", "percentual", "valor"],
                {
                    "posicao": lambda x: str(int(x)),
                    "percentual": lambda x: "—" if pd.isna(x) else f"{float(x):.0f}",
                    "valor": fmt_valor,
                },
            ))
            partes.append("")

    path = Path(ANALISE_DIR) / "RESULTADOS.md"
    path.write_text("\n".join(partes), encoding="utf-8")
    return path
