"""Experimentos nacionais: município-alvo, demais da UF e ente estadual."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analises.fundeb_ceara.dataset import (
    colunas_etapa,
    detectar_transicoes,
    normaliza_nome,
    total_matriculas_linha,
)
from analises.fundeb_ceara.motor import MotorAno, linha_baseline_municipio
from analises.fundeb_ceara.transformacoes import (
    assert_nao_negativas,
    converter_percentual,
    total_alunos,
    transferir_alunos,
)
from analises.fundeb_regioes.config import (
    ALVOS,
    ANOS,
    FIGURAS_DIR,
    PERCENTUAIS,
    PERCENTUAIS_DETALHE,
    RESULTADOS_DIR,
    UF_REGIAO,
)
from dados.fundeb_dataset import carregar_dataset


class CtxRegioes:
    def __init__(self, ano: int):
        self.ano = ano
        self.ds = carregar_dataset(ano)
        if not self.ds.simulacao_habilitada:
            raise RuntimeError(f"Simulação bloqueada em {ano}")
        self.etapas = colunas_etapa(self.ds)
        self.transicoes = detectar_transicoes(self.ds)
        self.municipios = identificar_alvos(self.ds)
        self.ce_ibges = []  # MotorAno.recorte_ce não é usado
        self.ce_municipios_ibges = []
        self.evidencias_ano = {"ano_dataset": ano, "modo_ponderador": self.ds.modo_ponderador}


def identificar_alvos(ds) -> pd.DataFrame:
    comp = ds.complementar.copy()
    comp["nn"] = comp["nome"].map(normaliza_nome)
    linhas = []
    for nome, uf, regiao in ALVOS:
        hits = comp[(comp["nn"] == normaliza_nome(nome)) & (comp["uf"] == uf) & (comp["ibge"] > 100)]
        if len(hits) != 1:
            raise KeyError(f"{nome}/{uf}: {len(hits)} linhas municipais no ano {ds.ano}")
        r = hits.iloc[0]
        linhas.append({
            "municipio": nome,
            "ibge": int(r["ibge"]),
            "nome_oficial": r["nome"],
            "uf": uf,
            "regiao": regiao,
            "ano": ds.ano,
        })
    return pd.DataFrame(linhas)


def ente_estadual(ds, uf: str) -> int | None:
    sub = ds.complementar[(ds.complementar["uf"] == uf) & (ds.complementar["ibge"] < 100)]
    if sub.empty:
        return None
    return int(sub.iloc[0]["ibge"])


def impacto_uf(sim: pd.DataFrame, sim_base: pd.DataFrame, ibge_alvo: int, uf: str, ibge_estado: int | None) -> dict:
    mun = sim_base[(sim_base["uf"] == uf) & (sim_base["ibge"] > 100)]
    mun_n = sim[(sim["uf"] == uf) & (sim["ibge"] > 100)]
    b = mun.set_index("ibge")["recursos_fundeb"]
    n = mun_n.set_index("ibge")["recursos_fundeb"]
    comum = b.index.intersection(n.index)
    delta = (n.loc[comum] - b.loc[comum]).astype(float)
    outros = delta.drop(labels=[ibge_alvo], errors="ignore")
    out = {
        "uf": uf,
        "regiao": UF_REGIAO.get(uf, ""),
        "delta_alvo": float(delta.loc[ibge_alvo]) if ibge_alvo in delta.index else float("nan"),
        "delta_demais_mun": float(outros.sum()),
        "delta_uf_municipal": float(delta.sum()),
        "n_mun_uf": int(len(delta)),
        "n_prejudicados": int((outros < -0.01).sum()),
        "n_beneficiados": int((outros > 0.01).sum()),
        "delta_ente_estadual": float("nan"),
        "delta_uf_total": float("nan"),
        "r_estado_base": float("nan"),
        "r_estado_novo": float("nan"),
    }
    if ibge_estado is not None:
        e0 = float(sim_base.loc[sim_base["ibge"] == ibge_estado, "recursos_fundeb"].iloc[0])
        e1 = float(sim.loc[sim["ibge"] == ibge_estado, "recursos_fundeb"].iloc[0])
        out["r_estado_base"] = e0
        out["r_estado_novo"] = e1
        out["delta_ente_estadual"] = e1 - e0
        uf0 = float(sim_base.loc[sim_base["uf"] == uf, "recursos_fundeb"].sum())
        uf1 = float(sim.loc[sim["uf"] == uf, "recursos_fundeb"].sum())
        out["delta_uf_total"] = uf1 - uf0
    return out


def _salvar(df: pd.DataFrame, nome: str) -> None:
    Path(RESULTADOS_DIR).mkdir(parents=True, exist_ok=True)
    df.to_csv(Path(RESULTADOS_DIR) / nome, index=False)


def executar_ano(ano: int) -> dict[str, pd.DataFrame]:
    ctx = CtxRegioes(ano)
    motor = MotorAno(ctx)
    print(f"\n=== {ano} | {len(ctx.municipios)} municípios | {len(ctx.transicoes)} transições ===")
    sim_base = motor.simular()
    baseline = pd.DataFrame([
        {**linha_baseline_municipio(motor, sim_base, row), "regiao": row["regiao"], "uf": row["uf"]}
        for _, row in ctx.municipios.iterrows()
    ])

    rows = []
    estados = {uf: ente_estadual(ctx.ds, uf) for uf in ctx.municipios["uf"].unique()}

    for _, mun in ctx.municipios.iterrows():
        ibge = int(mun["ibge"])
        uf = mun["uf"]
        ibge_est = estados[uf]
        for trans in ctx.transicoes:
            for pct in PERCENTUAIS:
                if pct == 0:
                    continue
                mat, n = converter_percentual(
                    motor.mat_base, ibge, trans.origem, trans.destino, pct, ctx.etapas,
                )
                assert_nao_negativas(mat, ctx.etapas)
                if abs(total_alunos(mat, ibge, ctx.etapas) - total_alunos(motor.mat_base, ibge, ctx.etapas)) > 1e-6:
                    raise AssertionError("conservação falhou")
                sim = motor.simular(mat)
                base = motor.linha_ente(sim_base, ibge)
                met = motor.metricas_alvo(sim, ibge, base, n)
                imp = impacto_uf(sim, sim_base, ibge, uf, ibge_est)
                row_sim = motor.linha_ente(sim, ibge)
                rows.append({
                    "ano": ano,
                    "municipio": mun["municipio"],
                    "ibge": ibge,
                    "uf": uf,
                    "regiao": mun["regiao"],
                    "cenario_id": f"{trans.codigo}_{pct:03d}",
                    "familia": "parcial_para_integral",
                    "codigo_transicao": trans.codigo,
                    "transformacao": trans.rotulo,
                    "origem": trans.origem,
                    "destino": trans.destino,
                    "percentual": pct,
                    "sentido": "peso_sobe",
                    **met,
                    **imp,
                    "d_vaaf": float(row_sim["recursos_vaaf"]) - float(base["recursos_vaaf"]),
                    "d_cvaaf": float(row_sim["complemento_vaaf"]) - float(base["complemento_vaaf"]),
                    "d_cvaat": float(row_sim["complemento_vaat"]) - float(base["complemento_vaat"]),
                    "d_cvaar": float(row_sim["complemento_vaar"]) - float(base["complemento_vaar"]),
                })

            # Controle: sentido inverso (integral → parcial) a 50% e 100%
            for pct in PERCENTUAIS_DETALHE:
                i = motor.mat_base.index[motor.mat_base["ibge"] == ibge][0]
                disp = float(motor.mat_base.at[i, trans.destino] or 0)
                n = disp * (pct / 100.0)
                if n <= 0:
                    continue
                mat = transferir_alunos(motor.mat_base, ibge, trans.destino, trans.origem, n, ctx.etapas)
                sim = motor.simular(mat)
                base = motor.linha_ente(sim_base, ibge)
                met = motor.metricas_alvo(sim, ibge, base, n)
                imp = impacto_uf(sim, sim_base, ibge, uf, ibge_est)
                rows.append({
                    "ano": ano,
                    "municipio": mun["municipio"],
                    "ibge": ibge,
                    "uf": uf,
                    "regiao": mun["regiao"],
                    "cenario_id": f"REV_{trans.codigo}_{pct:03d}",
                    "familia": "integral_para_parcial",
                    "codigo_transicao": trans.codigo,
                    "transformacao": f"INVERSO: {trans.rotulo}",
                    "origem": trans.destino,
                    "destino": trans.origem,
                    "percentual": pct,
                    "sentido": "peso_desce",
                    **met,
                    **imp,
                })

    sim = pd.DataFrame(rows)
    ida = sim[sim["familia"] == "parcial_para_integral"]
    melhores = ida.sort_values("delta_r", ascending=False).groupby(["ano", "ibge"], as_index=False).first()
    ctrl = sim[(sim["familia"] == "integral_para_parcial") & (sim["percentual"] == 100)]

    print(f"  {motor.cronometro.n_cenarios} cenários, {motor.cronometro.tempo_total_s:.1f}s")
    meta = pd.DataFrame([{
        "ano": ano,
        "n_cenarios": motor.cronometro.n_cenarios,
        "n_validos": motor.cronometro.n_validos,
        "tempo_s": motor.cronometro.tempo_total_s,
        "regioes": ",".join(sorted(ctx.municipios["regiao"].unique())),
        "ufs": ",".join(sorted(ctx.municipios["uf"].unique())),
    }])
    trans = pd.DataFrame([t.__dict__ for t in ctx.transicoes]).assign(ano=ano)
    return {
        "baseline": baseline,
        "simulacoes": sim,
        "melhores": melhores,
        "controle_inverso": ctrl,
        "meta": meta,
        "transicoes": trans,
        "municipios": ctx.municipios,
    }


def executar(anos: tuple[int, ...] = ANOS) -> dict[str, pd.DataFrame]:
    Path(RESULTADOS_DIR).mkdir(parents=True, exist_ok=True)
    Path(FIGURAS_DIR).mkdir(parents=True, exist_ok=True)
    blocos: dict[str, list] = {}
    for ano in anos:
        parte = executar_ano(ano)
        for k, df in parte.items():
            blocos.setdefault(k, []).append(df)
    out = {k: pd.concat(v, ignore_index=True) for k, v in blocos.items()}
    nomes = {
        "baseline": "baseline.csv",
        "simulacoes": "simulacoes.csv",
        "melhores": "melhores.csv",
        "controle_inverso": "controle_inverso.csv",
        "meta": "meta.csv",
        "transicoes": "transicoes.csv",
        "municipios": "municipios.csv",
    }
    for k, arq in nomes.items():
        _salvar(out[k], arq)
    return out
