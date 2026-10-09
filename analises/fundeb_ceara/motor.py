"""Wrapper do motor FUNDEB: execução, métricas, validação e cronometragem."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd

from analises.fundeb_ceara.config import COLUNAS_RESULTADO
from analises.fundeb_ceara.dataset import ContextoAno, total_matriculas_linha
from simulador import simula_fundeb
from validacao import validar_interno


@dataclass
class Cronometro:
    n_cenarios: int = 0
    n_validos: int = 0
    n_invalidos: int = 0
    tempo_total_s: float = 0.0
    erros: list[str] = field(default_factory=list)

    @property
    def tempo_medio_s(self) -> float:
        return self.tempo_total_s / self.n_cenarios if self.n_cenarios else 0.0


class MotorAno:
    """Reexecuta `simula_fundeb` com os parâmetros oficiais do exercício."""

    def __init__(self, ctx: ContextoAno):
        self.ctx = ctx
        ds = ctx.ds
        self.etapas = ctx.etapas
        self.mat_base = self._preparar_matriculas(ds.matriculas)
        self.complementar = ds.complementar
        self.pesos = ds.pesos
        self.defaults = ds.defaults_complementacao
        self.modo = ds.modo_ponderador
        self.cronometro = Cronometro()
        self._sim_cache: dict[int, pd.DataFrame] = {}

    def _preparar_matriculas(self, mat: pd.DataFrame) -> pd.DataFrame:
        cols = ["ibge"] + [c for c in self.etapas if c in mat.columns]
        out = mat.loc[:, cols].copy()
        out["ibge"] = out["ibge"].astype(int)
        for c in cols[1:]:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0).astype("float64")
        return out.reset_index(drop=True)

    def simular(self, mat: pd.DataFrame | None = None, validar: bool = True) -> pd.DataFrame:
        dados = self.mat_base if mat is None else self._preparar_matriculas(mat)
        t0 = time.perf_counter()
        sim = simula_fundeb(
            dados_matriculas=dados,
            dados_complementar=self.complementar,
            dados_peso=self.pesos,
            complementacao_vaaf=float(self.defaults["vaaf"]),
            complementacao_vaat=float(self.defaults["vaat"]),
            complementacao_vaar=float(self.defaults.get("vaar", 0) or 0),
            max_nse=1.0,
            min_nse=1.0,
            max_nf=1.0,
            min_nf=1.0,
            modo_ponderador=self.modo,
        )
        dt = time.perf_counter() - t0
        self.cronometro.n_cenarios += 1
        self.cronometro.tempo_total_s += dt
        if "uf" not in sim.columns:
            sim = sim.merge(self.complementar[["ibge", "uf", "nome"]], on="ibge", how="left")
        if validar:
            r = validar_interno(sim, self.complementar)
            if r.valido:
                self.cronometro.n_validos += 1
            else:
                self.cronometro.n_invalidos += 1
                msg = f"ano={self.ctx.ano} erros={r.erros}"
                self.cronometro.erros.append(msg)
                raise RuntimeError(f"Validação interna falhou: {msg}")
        else:
            self.cronometro.n_validos += 1
        return sim

    def linha_ente(self, sim: pd.DataFrame, ibge: int) -> pd.Series:
        sub = sim.loc[sim["ibge"] == ibge]
        if len(sub) != 1:
            raise KeyError(f"IBGE {ibge} não único na simulação ({len(sub)}).")
        return sub.iloc[0]

    def recorte_ce(self, sim: pd.DataFrame, so_municipios: bool = False) -> pd.DataFrame:
        ibges = self.ctx.ce_municipios_ibges if so_municipios else self.ctx.ce_ibges
        return sim[sim["ibge"].isin(ibges)].copy()

    def metricas_alvo(
        self,
        sim: pd.DataFrame,
        ibge: int,
        base: pd.Series,
        alunos_movidos: float,
    ) -> dict:
        row = self.linha_ente(sim, ibge)
        r_base = float(base["recursos_fundeb"])
        r_novo = float(row["recursos_fundeb"])
        delta = r_novo - r_base
        delta_pct = 100.0 * delta / r_base if r_base else float("nan")
        ganho_aluno = delta / alunos_movidos if alunos_movidos > 1e-9 else float("nan")
        return {
            "matriculas_vaaf": float(row["matriculas_vaaf"]),
            "matriculas_vaat": float(row["matriculas_vaat"]),
            "recursos_vaaf": float(row["recursos_vaaf"]),
            "complemento_vaaf": float(row["complemento_vaaf"]),
            "complemento_vaat": float(row["complemento_vaat"]),
            "complemento_vaar": float(row["complemento_vaar"]),
            "complemento_uniao": float(row["complemento_uniao"]),
            "r_base": r_base,
            "r_cenario": r_novo,
            "delta_r": delta,
            "delta_r_percentual": delta_pct,
            "alunos_movidos": float(alunos_movidos),
            "ganho_por_aluno": ganho_aluno,
            "vaaf_final": float(row["vaaf_final"]),
            "vaat_final": float(row["vaat_final"]),
        }

    def impacto_ce(
        self,
        sim: pd.DataFrame,
        sim_base: pd.DataFrame,
        ibge_alvo: int,
    ) -> dict:
        ce_b = self.recorte_ce(sim_base, so_municipios=True).set_index("ibge")
        ce_n = self.recorte_ce(sim, so_municipios=True).set_index("ibge")
        comum = ce_b.index.intersection(ce_n.index)
        delta = (ce_n.loc[comum, "recursos_fundeb"] - ce_b.loc[comum, "recursos_fundeb"]).astype(float)
        nomes = ce_n.loc[comum, "nome"]
        alvo = float(delta.loc[ibge_alvo]) if ibge_alvo in delta.index else float("nan")
        outros = delta.drop(labels=[ibge_alvo], errors="ignore")
        top = outros.nlargest(5)
        bot = outros.nsmallest(5)
        return {
            "n_municipios_ce": int(len(delta)),
            "delta_alvo": alvo,
            "delta_demais": float(outros.sum()),
            "delta_ce_municipal": float(delta.sum()),
            "recursos_ce_base": float(ce_b.loc[comum, "recursos_fundeb"].sum()),
            "recursos_ce_cenario": float(ce_n.loc[comum, "recursos_fundeb"].sum()),
            "n_beneficiados": int((outros > 0.01).sum()),
            "n_prejudicados": int((outros < -0.01).sum()),
            "top5_beneficiados": "; ".join(
                f"{nomes.loc[i]} ({delta.loc[i]:,.2f})" for i in top.index
            ),
            "top5_prejudicados": "; ".join(
                f"{nomes.loc[i]} ({delta.loc[i]:,.2f})" for i in bot.index
            ),
        }

    def detalhes_outros(
        self,
        sim: pd.DataFrame,
        sim_base: pd.DataFrame,
        ibge_alvo: int,
        municipio_alvo: str,
        cenario_id: str,
    ) -> pd.DataFrame:
        ce_b = self.recorte_ce(sim_base, so_municipios=True)
        ce_n = self.recorte_ce(sim, so_municipios=True)
        m = ce_b.merge(ce_n, on="ibge", suffixes=("_base", "_novo"))
        m = m[m["ibge"] != ibge_alvo].copy()
        m["delta_r"] = m["recursos_fundeb_novo"] - m["recursos_fundeb_base"]
        m["municipio_alvo"] = municipio_alvo
        m["ibge_alvo"] = ibge_alvo
        m["cenario_id"] = cenario_id
        m["ano"] = self.ctx.ano
        m["municipio"] = m["nome_novo"]
        return m[[
            "ano", "cenario_id", "municipio_alvo", "ibge_alvo",
            "ibge", "municipio", "recursos_fundeb_base", "recursos_fundeb_novo", "delta_r",
        ]]


def linha_baseline_municipio(motor: MotorAno, sim: pd.DataFrame, mun_row: pd.Series) -> dict:
    ibge = int(mun_row["ibge"])
    row = motor.linha_ente(sim, ibge)
    mat_row = motor.mat_base.loc[motor.mat_base["ibge"] == ibge].iloc[0]
    total = total_matriculas_linha(mat_row, motor.etapas)
    out = {
        "ano": motor.ctx.ano,
        "municipio": mun_row["municipio"],
        "ibge": ibge,
        "total_matriculas": total,
        "cenario": "S0_BASELINE",
    }
    for col in COLUNAS_RESULTADO:
        if col in ("ibge", "uf", "nome"):
            continue
        out[col] = float(row[col]) if col in row.index else float("nan")
    return out
