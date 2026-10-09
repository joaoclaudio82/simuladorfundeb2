"""Experimentos contrafactuais: baseline, transições, otimização e spillovers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analises.fundeb_ceara.config import (
    ANOS,
    PERCENTUAIS_CONJUNTOS,
    PERCENTUAIS_DISCRETOS,
    PERCENTUAIS_FACTIVEL_CONJUNTO,
    PERCENTUAIS_GRANULARES,
    RESULTADOS_DIR,
    Transicao,
)
from analises.fundeb_ceara.dataset import carregar_contexto
from analises.fundeb_ceara.motor import MotorAno, linha_baseline_municipio
from analises.fundeb_ceara.transformacoes import (
    aplicar_varias,
    assert_nao_negativas,
    concentrar_em_etapa,
    converter_percentual,
    total_alunos,
)


def _salvar(df: pd.DataFrame, nome: str) -> Path:
    Path(RESULTADOS_DIR).mkdir(parents=True, exist_ok=True)
    path = Path(RESULTADOS_DIR) / nome
    df.to_csv(path, index=False)
    return path


def tabela_pesos(ctx) -> pd.DataFrame:
    p = ctx.ds.pesos.copy()
    p["ano"] = ctx.ano
    p = p[["ano", "etapa", "nome", "peso_vaaf", "peso_vaat"]]
    p["rank_vaaf"] = p["peso_vaaf"].rank(ascending=False, method="min")
    p["rank_vaat"] = p["peso_vaat"].rank(ascending=False, method="min")
    return p.sort_values(["peso_vaaf", "peso_vaat"], ascending=False)


def _linha_cenario(
    motor: MotorAno,
    sim,
    sim_base,
    mun,
    trans: Transicao | None,
    cenario_id: str,
    familia: str,
    percentual: float | None,
    alunos_movidos: float,
    extra: dict | None = None,
) -> dict:
    base = motor.linha_ente(sim_base, int(mun["ibge"]))
    m = motor.metricas_alvo(sim, int(mun["ibge"]), base, alunos_movidos)
    imp = motor.impacto_ce(sim, sim_base, int(mun["ibge"]))
    row = {
        "ano": motor.ctx.ano,
        "municipio": mun["municipio"],
        "ibge": int(mun["ibge"]),
        "cenario_id": cenario_id,
        "familia": familia,
        "codigo_transicao": trans.codigo if trans else "",
        "transformacao": trans.rotulo if trans else familia,
        "origem": trans.origem if trans else "",
        "destino": trans.destino if trans else "",
        "percentual": percentual if percentual is not None else float("nan"),
        **m,
        **imp,
    }
    if extra:
        row.update(extra)
    return row


def _destinos_matematicos(ctx, k: int = 5) -> pd.DataFrame:
    p = ctx.ds.pesos.copy()
    p["score"] = p["peso_vaaf"] + p["peso_vaat"]
    return p.sort_values(["score", "peso_vaat", "peso_vaaf"], ascending=False).head(k)


def executar_ano(ano: int, granular: bool = True) -> dict[str, pd.DataFrame]:
    ctx = carregar_contexto(ano)
    motor = MotorAno(ctx)
    print(f"\n=== Exercício {ano} | etapas={len(ctx.etapas)} | CE municípios={len(ctx.ce_municipios_ibges)} ===")
    print("  transições detectadas:")
    for t in ctx.transicoes:
        print(f"    {t.codigo}: {t.origem} → {t.destino}  "
              f"VAAF {t.peso_vaaf_origem:.3f}→{t.peso_vaaf_destino:.3f}  "
              f"VAAT {t.peso_vaat_origem:.3f}→{t.peso_vaat_destino:.3f}")

    sim_base = motor.simular()
    pesos = tabela_pesos(ctx)

    baseline = pd.DataFrame([
        linha_baseline_municipio(motor, sim_base, row)
        for _, row in ctx.municipios.iterrows()
    ])

    pcts = list(PERCENTUAIS_GRANULARES) if granular else [0, *PERCENTUAIS_DISCRETOS, 100]
    simulacoes: list[dict] = []
    impactos_detalhe: list[pd.DataFrame] = []
    detalhar_pct = {50, 100}

    n_total = len(ctx.municipios) * len(ctx.transicoes) * len([p for p in pcts if p > 0])
    feito = 0
    for _, mun in ctx.municipios.iterrows():
        ibge = int(mun["ibge"])
        for trans in ctx.transicoes:
            for pct in pcts:
                if pct == 0:
                    continue
                mat, n = converter_percentual(
                    motor.mat_base, ibge, trans.origem, trans.destino, pct, ctx.etapas,
                )
                assert_nao_negativas(mat, ctx.etapas)
                total_antes = total_alunos(motor.mat_base, ibge, ctx.etapas)
                total_depois = total_alunos(mat, ibge, ctx.etapas)
                if abs(total_antes - total_depois) > 1e-6:
                    raise AssertionError(f"Conservação falhou {mun['municipio']} {trans.codigo} {pct}%")
                sim = motor.simular(mat)
                cid = f"S_{trans.codigo}_{pct:03d}"
                simulacoes.append(_linha_cenario(
                    motor, sim, sim_base, mun, trans, cid, "transicao_individual", pct, n,
                ))
                if pct in detalhar_pct:
                    impactos_detalhe.append(motor.detalhes_outros(
                        sim, sim_base, ibge, mun["municipio"], cid,
                    ))
                feito += 1
                if feito % 200 == 0:
                    print(f"  transições {feito}/{n_total}  t={motor.cronometro.tempo_total_s:.1f}s")

    # Ótimo factível: as quatro transições simultâneas
    for _, mun in ctx.municipios.iterrows():
        ibge = int(mun["ibge"])
        for pct in PERCENTUAIS_FACTIVEL_CONJUNTO:
            pares = [(t.origem, t.destino, float(pct)) for t in ctx.transicoes]
            mat, n = aplicar_varias(motor.mat_base, ibge, pares, ctx.etapas)
            assert_nao_negativas(mat, ctx.etapas)
            sim = motor.simular(mat)
            cid = f"OTIMO_FACTIVEL_{pct:03d}"
            simulacoes.append(_linha_cenario(
                motor, sim, sim_base, mun, None, cid, "otimo_factivel", pct, n,
                extra={"nota": "somente transições A–D; educacionalmente factível"},
            ))
            if pct == 100:
                impactos_detalhe.append(motor.detalhes_outros(
                    sim, sim_base, ibge, mun["municipio"], cid,
                ))

    # Ótimo matemático (teórico): concentrar todo o estoque nas K etapas de maior peso
    destinos = _destinos_matematicos(ctx, k=5)
    for _, mun in ctx.municipios.iterrows():
        ibge = int(mun["ibge"])
        melhor = None
        melhor_sim = None
        for _, dest in destinos.iterrows():
            mat, n = concentrar_em_etapa(motor.mat_base, ibge, dest["etapa"], ctx.etapas)
            assert_nao_negativas(mat, ctx.etapas)
            sim = motor.simular(mat)
            cid = f"OTIMO_MATEMATICO_{dest['etapa']}"
            row = _linha_cenario(
                motor, sim, sim_base, mun, None, cid, "otimo_matematico", 100.0, n,
                extra={
                    "destino": dest["etapa"],
                    "transformacao": f"Concentrar 100% em {dest['nome']}",
                    "nota": "cenário teórico, não educacionalmente factível",
                    "peso_vaaf_destino": float(dest["peso_vaaf"]),
                    "peso_vaat_destino": float(dest["peso_vaat"]),
                },
            )
            simulacoes.append(row)
            if melhor is None or row["delta_r"] > melhor["delta_r"]:
                melhor, melhor_sim = row, sim
        if melhor is not None and melhor_sim is not None:
            impactos_detalhe.append(motor.detalhes_outros(
                melhor_sim, sim_base, ibge, mun["municipio"], melhor["cenario_id"],
            ))

    # Sensibilidade: +1 aluno nas transições A–D, na origem e após 50% convertido
    for _, mun in ctx.municipios.iterrows():
        ibge = int(mun["ibge"])
        for trans in ctx.transicoes:
            i = motor.mat_base.index[motor.mat_base["ibge"] == ibge][0]
            disp = float(motor.mat_base.at[i, trans.origem] or 0)
            if disp < 1:
                continue
            from analises.fundeb_ceara.transformacoes import transferir_alunos
            mat, _ = converter_percentual(
                motor.mat_base, ibge, trans.origem, trans.destino, 0, ctx.etapas,
            )
            mat1 = transferir_alunos(motor.mat_base, ibge, trans.origem, trans.destino, 1.0, ctx.etapas)
            sim = motor.simular(mat1)
            simulacoes.append(_linha_cenario(
                motor, sim, sim_base, mun, trans, f"SENS_{trans.codigo}_M0",
                "sensibilidade", None, 1.0,
                extra={"nota": "efeito marginal de 1 aluno a partir do baseline"},
            ))
            if disp >= 2:
                mat50, _ = converter_percentual(
                    motor.mat_base, ibge, trans.origem, trans.destino, 50, ctx.etapas,
                )
                i50 = mat50.index[mat50["ibge"] == ibge][0]
                if float(mat50.at[i50, trans.origem] or 0) >= 1:
                    mat50_1 = transferir_alunos(mat50, ibge, trans.origem, trans.destino, 1.0, ctx.etapas)
                    sim50 = motor.simular(mat50)
                    sim50_1 = motor.simular(mat50_1)
                    base50 = motor.linha_ente(sim50, ibge)
                    m50 = motor.metricas_alvo(sim50_1, ibge, base50, 1.0)
                    simulacoes.append({
                        "ano": ano,
                        "municipio": mun["municipio"],
                        "ibge": ibge,
                        "cenario_id": f"SENS_{trans.codigo}_M50",
                        "familia": "sensibilidade",
                        "codigo_transicao": trans.codigo,
                        "transformacao": trans.rotulo,
                        "origem": trans.origem,
                        "destino": trans.destino,
                        "percentual": 50.0,
                        **m50,
                        **motor.impacto_ce(sim50_1, sim50, ibge),
                        "nota": "efeito marginal de 1 aluno após 50% já convertido",
                    })

    df_sim = pd.DataFrame(simulacoes)

    # Otimização conjunta e Pareto: aplicar a mesma política nos 10
    g10_rows = []
    ibges10 = [int(x) for x in ctx.municipios["ibge"].tolist()]
    nomes10 = dict(zip(ctx.municipios["ibge"], ctx.municipios["municipio"]))
    r_base_10 = {
        int(r["ibge"]): float(motor.linha_ente(sim_base, int(r["ibge"]))["recursos_fundeb"])
        for _, r in ctx.municipios.iterrows()
    }
    soma_base = sum(r_base_10.values())

    def _aplicar_em_dez(mat0, pares_por_ibge: dict[int, list[tuple[str, str, float]]]):
        mat = mat0
        movidos = {}
        for ibge, pares in pares_por_ibge.items():
            mat, n = aplicar_varias(mat, ibge, pares, ctx.etapas)
            movidos[ibge] = n
        assert_nao_negativas(mat, ctx.etapas)
        return mat, movidos

    for pct in PERCENTUAIS_CONJUNTOS:
        if pct == 0:
            continue
        pares = {ib: [(t.origem, t.destino, float(pct)) for t in ctx.transicoes] for ib in ibges10}
        mat, movidos = _aplicar_em_dez(motor.mat_base, pares)
        sim = motor.simular(mat)
        rs = {ib: float(motor.linha_ente(sim, ib)["recursos_fundeb"]) for ib in ibges10}
        deltas = {ib: rs[ib] - r_base_10[ib] for ib in ibges10}
        pcts_i = {ib: (100 * deltas[ib] / r_base_10[ib] if r_base_10[ib] else float("nan")) for ib in ibges10}
        g10_rows.append({
            "ano": ano,
            "cenario_id": f"G10_FACTIVEL_{pct:03d}",
            "familia": "conjunto_g10",
            "percentual": pct,
            "g10": sum(deltas.values()),
            "g10_percentual": 100 * sum(deltas.values()) / soma_base if soma_base else float("nan"),
            "min_delta_pct": min(pcts_i.values()),
            "max_delta_pct": max(pcts_i.values()),
            "soma_base": soma_base,
            "soma_cenario": sum(rs.values()),
            "alunos_movidos": sum(movidos.values()),
            "nota": "quatro transições factíveis aplicadas simultaneamente nos 10 municípios",
            **{f"delta_{nomes10[ib]}": deltas[ib] for ib in ibges10},
            **{f"pct_{nomes10[ib]}": pcts_i[ib] for ib in ibges10},
        })

    # Cada município na sua melhor transição individual (maior delta_r em transicao_individual)
    ind = df_sim[df_sim["familia"] == "transicao_individual"]
    melhores_ind = ind.sort_values("delta_r", ascending=False).groupby("ibge", as_index=False).first()
    pares_best = {}
    for _, r in melhores_ind.iterrows():
        pares_best[int(r["ibge"])] = [(r["origem"], r["destino"], float(r["percentual"]))]
    mat, movidos = _aplicar_em_dez(motor.mat_base, pares_best)
    sim = motor.simular(mat)
    rs = {ib: float(motor.linha_ente(sim, ib)["recursos_fundeb"]) for ib in ibges10}
    deltas = {ib: rs[ib] - r_base_10[ib] for ib in ibges10}
    pcts_i = {ib: (100 * deltas[ib] / r_base_10[ib] if r_base_10[ib] else float("nan")) for ib in ibges10}
    g10_rows.append({
        "ano": ano,
        "cenario_id": "G10_MELHOR_INDIVIDUAL",
        "familia": "conjunto_g10",
        "percentual": float("nan"),
        "g10": sum(deltas.values()),
        "g10_percentual": 100 * sum(deltas.values()) / soma_base if soma_base else float("nan"),
        "min_delta_pct": min(pcts_i.values()),
        "max_delta_pct": max(pcts_i.values()),
        "soma_base": soma_base,
        "soma_cenario": sum(rs.values()),
        "alunos_movidos": sum(movidos.values()),
        "nota": "cada um dos 10 aplica a transformação individual de maior ΔR$ encontrada",
        **{f"delta_{nomes10[ib]}": deltas[ib] for ib in ibges10},
        **{f"pct_{nomes10[ib]}": pcts_i[ib] for ib in ibges10},
    })

    g10 = pd.DataFrame(g10_rows)
    pareto = g10[g10["cenario_id"].str.startswith("G10_FACTIVEL")].copy()
    if len(pareto):
        idx = pareto["min_delta_pct"].idxmax()
        g10.loc[idx, "familia"] = "pareto_equidade"
        g10.loc[idx, "nota"] = (
            g10.loc[idx, "nota"] + " | selecionado como maximin (max min Δ%)"
        )

    linearidade = _analisar_linearidade(df_sim)
    melhores = _melhores_cenarios(df_sim)
    rankings = _rankings(df_sim)
    tabela_final = _tabela_final(melhores, baseline)

    meta = pd.DataFrame([{
        "ano": ano,
        "n_entes": ctx.evidencias_ano["n_entes"],
        "n_etapas": ctx.evidencias_ano["n_etapas"],
        "n_municipios_ce": ctx.evidencias_ano["n_municipios_ce"],
        "modo_ponderador": ctx.evidencias_ano["modo_ponderador"],
        "complementacao_vaaf": ctx.evidencias_ano["defaults_complementacao"].get("vaaf"),
        "complementacao_vaat": ctx.evidencias_ano["defaults_complementacao"].get("vaat"),
        "complementacao_vaar": ctx.evidencias_ano["defaults_complementacao"].get("vaar"),
        "fonte": ctx.evidencias_ano["fonte"],
        "n_cenarios": motor.cronometro.n_cenarios,
        "n_validos": motor.cronometro.n_validos,
        "n_invalidos": motor.cronometro.n_invalidos,
        "tempo_total_s": motor.cronometro.tempo_total_s,
        "tempo_medio_s": motor.cronometro.tempo_medio_s,
        "erros_validacao": " | ".join(motor.cronometro.erros),
    }])

    impactos = pd.concat(impactos_detalhe, ignore_index=True) if impactos_detalhe else pd.DataFrame()

    print(f"  concluído: {motor.cronometro.n_cenarios} cenários, "
          f"{motor.cronometro.tempo_total_s:.1f}s, média {motor.cronometro.tempo_medio_s*1000:.1f} ms")

    return {
        "pesos": pesos,
        "baseline": baseline,
        "simulacoes": df_sim,
        "otimizacao": df_sim[df_sim["familia"].isin(["otimo_factivel", "otimo_matematico"])].copy(),
        "g10": g10,
        "linearidade": linearidade,
        "melhores_cenarios": melhores,
        "rankings": rankings,
        "tabela_final": tabela_final,
        "impactos_outros_municipios": impactos,
        "meta": meta,
        "transicoes": pd.DataFrame([t.__dict__ for t in ctx.transicoes]).assign(ano=ano),
    }


def _analisar_linearidade(sim: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sub = sim[sim["familia"] == "transicao_individual"].copy()
    for (ano, ibge, codigo), g in sub.groupby(["ano", "ibge", "codigo_transicao"]):
        g = g.sort_values("percentual")
        x = g["percentual"].to_numpy(dtype=float)
        y = g["delta_r"].to_numpy(dtype=float)
        if len(g) < 5 or np.allclose(y, y[0]):
            r2 = float("nan")
            max_resid = float("nan")
        else:
            coef = np.polyfit(x, y, 1)
            yhat = np.polyval(coef, x)
            ss_res = float(np.sum((y - yhat) ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
            max_resid = float(np.max(np.abs(y - yhat)))
        dy = np.diff(y)
        ddy = np.diff(dy) if len(dy) > 1 else np.array([])
        rows.append({
            "ano": ano,
            "ibge": ibge,
            "municipio": g["municipio"].iloc[0],
            "codigo_transicao": codigo,
            "transformacao": g["transformacao"].iloc[0],
            "n_pontos": len(g),
            "r2_linear": r2,
            "max_residuo_abs": max_resid,
            "delta_r_min": float(y.min()),
            "delta_r_max": float(y.max()),
            "sinal_primeira_diff_unico": int(len(set(np.sign(dy[np.abs(dy) > 1e-6]))) <= 1) if len(dy) else 1,
            "max_abs_segunda_diff": float(np.max(np.abs(ddy))) if len(ddy) else 0.0,
            "quase_linear": bool(r2 >= 0.995) if pd.notna(r2) else False,
        })
    return pd.DataFrame(rows)


def _melhores_cenarios(sim: pd.DataFrame) -> pd.DataFrame:
    """Melhor transformação factível individual por município (maior ΔR$)."""
    sub = sim[sim["familia"] == "transicao_individual"].copy()
    if sub.empty:
        return sub
    idx = sub.groupby(["ano", "ibge"])["delta_r"].idxmax()
    return sub.loc[idx].reset_index(drop=True)


def _rankings(sim: pd.DataFrame) -> pd.DataFrame:
    sub = sim[sim["familia"] == "transicao_individual"].copy()
    if sub.empty:
        return sub
    best = sub.sort_values("delta_r", ascending=False).groupby(["ano", "ibge"], as_index=False).first()
    rows = []
    for ano, g in best.groupby("ano"):
        for metrica, nome in (
            ("delta_r", "A_ganho_absoluto"),
            ("delta_r_percentual", "B_ganho_percentual"),
            ("ganho_por_aluno", "C_ganho_por_aluno"),
        ):
            gg = g.sort_values(metrica, ascending=False).reset_index(drop=True)
            for i, r in gg.iterrows():
                rows.append({
                    "ano": ano,
                    "ranking": nome,
                    "posicao": i + 1,
                    "municipio": r["municipio"],
                    "ibge": r["ibge"],
                    "transformacao": r["transformacao"],
                    "percentual": r["percentual"],
                    "alunos_movidos": r["alunos_movidos"],
                    "valor": r[metrica],
                    "delta_r": r["delta_r"],
                    "delta_r_percentual": r["delta_r_percentual"],
                    "ganho_por_aluno": r["ganho_por_aluno"],
                })
        # Ranking D: transições mais eficientes (mediana do ganho por aluno no melhor % de cada mun)
        d = g.groupby("codigo_transicao").agg(
            transformacao=("transformacao", "first"),
            mediana_ganho_aluno=("ganho_por_aluno", "median"),
            media_delta_r=("delta_r", "mean"),
            media_delta_pct=("delta_r_percentual", "mean"),
        ).sort_values("mediana_ganho_aluno", ascending=False).reset_index()
        for i, r in d.iterrows():
            rows.append({
                "ano": ano,
                "ranking": "D_transicao_eficiente",
                "posicao": i + 1,
                "municipio": "",
                "ibge": "",
                "transformacao": r["transformacao"],
                "percentual": float("nan"),
                "alunos_movidos": float("nan"),
                "valor": r["mediana_ganho_aluno"],
                "delta_r": r["media_delta_r"],
                "delta_r_percentual": r["media_delta_pct"],
                "ganho_por_aluno": r["mediana_ganho_aluno"],
            })
    return pd.DataFrame(rows)


def _tabela_final(melhores: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    if melhores.empty:
        return melhores
    b = baseline[["ano", "ibge", "total_matriculas"]].copy()
    t = melhores.merge(b, on=["ano", "ibge"], how="left")
    return t[[
        "ano", "municipio", "ibge", "transformacao", "percentual", "alunos_movidos",
        "r_base", "r_cenario", "delta_r", "delta_r_percentual", "ganho_por_aluno",
        "total_matriculas",
    ]].rename(columns={
        "percentual": "pct_convertido",
        "alunos_movidos": "alunos",
        "r_base": "base_r",
        "r_cenario": "novo_r",
        "delta_r": "delta_r",
        "delta_r_percentual": "delta_pct",
        "ganho_por_aluno": "r_por_aluno",
    })


def executar_estudo(anos: tuple[int, ...] = ANOS, granular: bool = True) -> dict[str, pd.DataFrame]:
    blocos: dict[str, list[pd.DataFrame]] = {}
    for ano in anos:
        parte = executar_ano(ano, granular=granular)
        for k, df in parte.items():
            blocos.setdefault(k, []).append(df)
    saida = {k: pd.concat(v, ignore_index=True) for k, v in blocos.items()}
    nomes = {
        "pesos": "pesos.csv",
        "baseline": "baseline.csv",
        "simulacoes": "simulacoes.csv",
        "melhores_cenarios": "melhores_cenarios.csv",
        "impactos_outros_municipios": "impactos_outros_municipios.csv",
        "otimizacao": "otimizacao.csv",
        "g10": "otimizacao_conjunta.csv",
        "linearidade": "linearidade.csv",
        "rankings": "rankings.csv",
        "tabela_final": "tabela_final.csv",
        "meta": "meta_execucao.csv",
        "transicoes": "transicoes_detectadas.csv",
    }
    for chave, arquivo in nomes.items():
        _salvar(saida[chave], arquivo)
    return saida
