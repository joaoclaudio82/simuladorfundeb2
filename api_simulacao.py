"""
Handlers de simulação e consulta por exercício FUNDEB.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_user
from auth.models import UserRecord
from dados.fundeb_dataset import ESTADOS_REGIOES, FundebDataset, carregar_dataset
from simulador import simula_fundeb
from validacao import validar_interno

router_ano = APIRouter()


class SimulacaoRequest(BaseModel):
    complementacao_vaaf: float = 24_153_287_047
    complementacao_vaat: float = 18_114_965_285
    complementacao_vaar: float = 0
    max_nse: float = 1.1
    min_nse: float = 1.0
    max_nf: float = 1.0
    min_nf: float = 1.0
    pesos_vaaf: Optional[list[float]] = None
    pesos_vaat: Optional[list[float]] = None


class SimulacaoMunicipioRequest(SimulacaoRequest):
    ibge: int
    matriculas_ajustadas: Optional[dict[str, float]] = None


def sanitize_for_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    return obj


def _ds(ano: int) -> FundebDataset:
    return carregar_dataset(ano)


def _checar_simulacao(ds: FundebDataset):
    if not ds.simulacao_habilitada:
        raise HTTPException(
            503,
            ds.mensagem_bloqueio or f"Simulação não disponível para {ds.ano}.",
        )


def _defaults(req: SimulacaoRequest, ds: FundebDataset) -> SimulacaoRequest:
    d = ds.defaults_complementacao
    if req.complementacao_vaaf is None:
        req.complementacao_vaaf = d.get("vaaf", 0)
    if req.complementacao_vaat is None:
        req.complementacao_vaat = d.get("vaat", 0)
    return req


def preparar_pesos(
    req: SimulacaoRequest,
    ds: FundebDataset,
    user: UserRecord | None = None,
) -> pd.DataFrame:
    p = ds.pesos.copy()
    if user and user.role.value != "admin":
        return p
    if req.pesos_vaaf is not None and len(req.pesos_vaaf) == len(p):
        p["peso_vaaf"] = req.pesos_vaaf
    if req.pesos_vaat is not None and len(req.pesos_vaat) == len(p):
        p["peso_vaat"] = req.pesos_vaat
    return p


def executar_simulacao(
    req: SimulacaoRequest,
    ds: FundebDataset,
    mat: pd.DataFrame | None = None,
    user: UserRecord | None = None,
) -> pd.DataFrame:
    req = _defaults(req, ds)
    p = preparar_pesos(req, ds, user)
    etapas = list(dict.fromkeys(ds.etapas))
    dados_mat = mat if mat is not None else ds.matriculas
    cols = ["ibge"] + [c for c in etapas if c in dados_mat.columns]
    dados_mat = dados_mat.loc[:, cols].copy()
    return simula_fundeb(
        dados_matriculas=dados_mat,
        dados_complementar=ds.complementar,
        dados_peso=p,
        complementacao_vaaf=req.complementacao_vaaf,
        complementacao_vaat=req.complementacao_vaat,
        complementacao_vaar=req.complementacao_vaar,
        max_nse=req.max_nse,
        min_nse=req.min_nse,
        max_nf=req.max_nf,
        min_nf=req.min_nf,
        modo_ponderador=ds.modo_ponderador,
    )


def gerar_resumo(sim: pd.DataFrame, atual: pd.DataFrame) -> dict:
    merged = sim.merge(atual, on=["ibge", "nome", "uf"], suffixes=("_sim", "_atual"))
    vaaf_min_sim = sim["vaaf_final"].min()
    vaaf_min_atual = atual["vaaf_final"].min() if len(atual) else 0
    hab_sim = sim[~sim["inabilitados_vaat"].isin([True, "Verdadeiro"])]
    if "inabilitados_vaat" in atual.columns and len(atual):
        hab_atual = atual[~atual["inabilitados_vaat"].isin([True, "Verdadeiro"])]
    else:
        hab_atual = atual
    vaat_min_sim = hab_sim["vaat_final"].min() if len(hab_sim) > 0 else 0
    vaat_min_atual = hab_atual["vaat_final"].min() if len(hab_atual) > 0 else 0
    compl_mun = sim.loc[sim["ibge"] > 100, "complemento_uniao"].sum()
    compl_est = sim.loc[sim["ibge"] < 100, "complemento_uniao"].sum()
    perc_compl = (sim["complemento_uniao"] > 0).mean()
    dif_recursos = merged["recursos_fundeb_sim"] - merged["recursos_fundeb_atual"]
    dif_pct = dif_recursos / merged["recursos_fundeb_atual"].replace(0, np.nan)
    return sanitize_for_json({
        "vaaf_minimo_simulado": round(vaaf_min_sim, 2),
        "vaaf_minimo_atual": round(vaaf_min_atual, 2),
        "vaaf_diferenca_pct": round((vaaf_min_sim - vaaf_min_atual) / vaaf_min_atual * 100, 2) if vaaf_min_atual else 0,
        "vaat_minimo_simulado": round(vaat_min_sim, 2),
        "vaat_minimo_atual": round(vaat_min_atual, 2),
        "vaat_diferenca_pct": round((vaat_min_sim - vaat_min_atual) / vaat_min_atual * 100, 2) if vaat_min_atual else 0,
        "complementacao_municipios": round(compl_mun, 2),
        "complementacao_estados": round(compl_est, 2),
        "percentual_complementados": round(perc_compl * 100, 2),
        "maior_aumento_pct": round(dif_pct.max() * 100, 2) if len(dif_pct) else 0,
        "maior_reducao_pct": round(dif_pct.min() * 100, 2) if len(dif_pct) else 0,
        "media_mudanca_pct": round(dif_pct.mean() * 100, 2) if len(dif_pct) else 0,
        "mediana_mudanca_pct": round(dif_pct.median() * 100, 2) if len(dif_pct) else 0,
        "maior_aumento_abs": round(dif_recursos.max(), 2) if len(dif_recursos) else 0,
        "maior_reducao_abs": round(dif_recursos.min(), 2) if len(dif_recursos) else 0,
        "total_complementacao_vaaf": round(sim["complemento_vaaf"].sum(), 2),
        "total_complementacao_vaat": round(sim["complemento_vaat"].sum(), 2),
        "total_complementacao_vaar": round(sim["complemento_vaar"].sum(), 2),
    })


def gerar_dados_por_uf(sim: pd.DataFrame) -> list[dict]:
    hab = sim[~sim["inabilitados_vaat"].isin([True, "Verdadeiro"]) | (sim["uf"] == "DF")]
    por_uf = hab.groupby("uf", as_index=False).agg(
        vaaf_medio=("vaaf_final", "mean"),
        vaat_medio=("vaat_final", "mean"),
        complemento_vaaf=("complemento_vaaf", "sum"),
        complemento_vaat=("complemento_vaat", "sum"),
        complemento_vaar=("complemento_vaar", "sum"),
        complemento_uniao=("complemento_uniao", "sum"),
        recursos_fundeb=("recursos_fundeb", "sum"),
    ).round(2)
    return sanitize_for_json(por_uf.to_dict(orient="records"))


def calcular_vaat_minimo(sim: pd.DataFrame) -> float:
    hab = sim[~sim["inabilitados_vaat"].isin([True, "Verdadeiro"]) | (sim["uf"] == "DF")]
    if len(hab) == 0:
        return 0.0
    return float(hab["vaat_final"].min())


def extrair_detalhes_municipio(sim: pd.DataFrame, ibge: int) -> dict:
    linha = sim[sim["ibge"] == ibge]
    if len(linha) == 0:
        raise HTTPException(404, "Município não encontrado")
    mun = linha.iloc[0].to_dict()
    uf = mun["uf"]
    estado = sim[sim["uf"] == uf]
    mun["vaaf"] = float(mun["recursos_vaaf"] / mun["matriculas_vaaf"]) if mun["matriculas_vaaf"] else 0.0
    mun["vaat"] = float(mun["vaat_pre"])
    mun["vaaf_minimo"] = float(sim["vaaf_final"].min()) if len(sim) > 0 else 0.0
    mun["vaat_minimo"] = calcular_vaat_minimo(sim)
    matriculas_estado_vaaf = float(estado["matriculas_vaaf"].sum()) if len(estado) > 0 else 0.0
    mun["coeficiente"] = (
        float(mun["matriculas_vaaf"] / matriculas_estado_vaaf)
        if matriculas_estado_vaaf > 0 else 0.0
    )
    mun["fundo_estadual"] = {
        "uf": uf,
        "matriculas_pond_vaaf": matriculas_estado_vaaf,
        "matriculas_pond_vaat": float(estado["matriculas_vaat"].sum()) if len(estado) > 0 else 0.0,
        "receitas_vaaf": float(estado["recursos_vaaf"].sum()) if len(estado) > 0 else 0.0,
        "receitas_vaat": float(estado["recursos_vaat"].sum()) if len(estado) > 0 else 0.0,
    }
    return mun


def gerar_vencedores_perdedores(sim: pd.DataFrame, atual: pd.DataFrame) -> dict:
    merged = sim.merge(atual, on=["ibge", "nome", "uf"], suffixes=("_sim", "_atual"))
    regiao_map = {uf: reg for reg, ufs in ESTADOS_REGIOES.items() for uf in ufs}
    merged["regiao"] = merged["uf"].map(regiao_map)
    merged["dif_vaaf_pct"] = (
        (merged["recursos_vaaf_final_sim"] - merged["recursos_vaaf_final_atual"])
        / merged["recursos_vaaf_final_atual"].replace(0, np.nan) * 100
    )
    merged["dif_vaat_pct"] = (
        (merged["recursos_vaat_final_sim"] - merged["recursos_vaat_final_atual"])
        / merged["recursos_vaat_final_atual"].replace(0, np.nan) * 100
    )
    merged["resultado_vaaf"] = np.where(merged["dif_vaaf_pct"] >= 0, "Positivo", "Negativo")
    merged["resultado_vaat"] = np.where(merged["dif_vaat_pct"] >= 0, "Positivo", "Negativo")

    def agrupar(col_resultado, col_dif):
        grp = merged.groupby([col_resultado, "regiao"], as_index=False).agg(
            entes=(col_dif, "count"),
            media=(col_dif, "mean"),
            maximo=(col_dif, lambda x: x.abs().max()),
            minimo=(col_dif, lambda x: x.abs().min()),
        ).round(2)
        return sanitize_for_json(grp.to_dict(orient="records"))

    return {"vaaf": agrupar("resultado_vaaf", "dif_vaaf_pct"), "vaat": agrupar("resultado_vaat", "dif_vaat_pct")}


def _resposta_simular(req: SimulacaoRequest, ano: int, user: UserRecord | None = None):
    ds = _ds(ano)
    _checar_simulacao(ds)
    sim = executar_simulacao(req, ds, user=user)
    atual = ds.cenario_atual
    resumo = gerar_resumo(sim, atual)
    dados_uf = gerar_dados_por_uf(sim)
    vp = gerar_vencedores_perdedores(sim, atual)
    compl_por_uf = sim.groupby("uf", as_index=False).agg(
        complemento_vaaf=("complemento_vaaf", "sum"),
        complemento_vaat=("complemento_vaat", "sum"),
        complemento_vaar=("complemento_vaar", "sum"),
        complemento_uniao=("complemento_uniao", "sum"),
    ).round(2)
    compl_destino = sim.copy()
    compl_destino["tipo"] = np.where(compl_destino["ibge"] < 100, "Estado", "Município")
    compl_destino = compl_destino.groupby(["uf", "tipo"], as_index=False).agg(
        complemento=("complemento_uniao", "sum"),
    ).round(2)
    sim_agg = sim.groupby("uf", as_index=False).agg(complemento_sim=("complemento_uniao", "sum"))
    diff_uf = sim_agg.merge(ds.cenario_atual_agregada, on="uf", how="left")
    if "complemento_uniao" in diff_uf.columns:
        diff_uf["diferenca"] = diff_uf["complemento_sim"] - diff_uf["complemento_uniao"]
    else:
        diff_uf["diferenca"] = diff_uf["complemento_sim"]
    diff_uf = diff_uf[["uf", "diferenca"]].round(2)
    validacao = validar_interno(sim, ds.complementar)
    return sanitize_for_json({
        "ano": ano,
        "resumo": resumo,
        "por_uf": dados_uf,
        "vencedores_perdedores": vp,
        "complementacao_por_uf": compl_por_uf.to_dict(orient="records"),
        "complementacao_destino": compl_destino.to_dict(orient="records"),
        "diferenca_uf": diff_uf.to_dict(orient="records"),
        "dados_tabela": sim.fillna(0).head(200).to_dict(orient="records"),
        "validacao": {
            "valido": validacao.valido,
            "erros": validacao.erros,
            "avisos": validacao.avisos,
            "checagens": validacao.checagens,
        },
    })


def registrar_rotas_ano(app, ano: int, prefix: str | None = None):
    prefix = prefix or f"/api/{ano}"

    @app.get(f"{prefix}/meta")
    def meta(_user: UserRecord = Depends(get_current_user)):
        ds = _ds(ano)
        return sanitize_for_json({
            "ano": ano,
            "simulacao_habilitada": ds.simulacao_habilitada,
            "mensagem_bloqueio": ds.mensagem_bloqueio,
            "modo_ponderador": ds.modo_ponderador,
            "num_etapas": len(ds.etapas),
            "defaults_complementacao": ds.defaults_complementacao,
            "familias": list(ds.familias.keys()),
        })

    @app.get(f"{prefix}/estados")
    def listar_estados(_user: UserRecord = Depends(get_current_user)):
        ds = _ds(ano)
        ufs = sorted(ds.complementar["uf"].unique().tolist())
        return {"estados": ufs, "regioes": ESTADOS_REGIOES}

    @app.get(f"{prefix}/municipios")
    def listar_municipios(uf: str, _user: UserRecord = Depends(get_current_user)):
        ds = _ds(ano)
        df = ds.complementar[ds.complementar["uf"] == uf][["ibge", "nome", "uf"]].sort_values("nome")
        return sanitize_for_json(df.to_dict(orient="records"))

    @app.get(f"{prefix}/pesos")
    def obter_pesos(_user: UserRecord = Depends(get_current_user)):
        ds = _ds(ano)
        out = ds.pesos.to_dict(orient="records")
        for row in out:
            fam = familia_de_etapa(ds, row["etapa"])
            row["familia"] = fam
        return sanitize_for_json(out)

    @app.get(f"{prefix}/etapas")
    def obter_etapas(_user: UserRecord = Depends(get_current_user)):
        ds = _ds(ano)
        return sanitize_for_json({
            "etapas": ds.etapas_nomes,
            "familias": ds.familias,
        })

    @app.get(f"{prefix}/municipio/{{ibge}}/matriculas")
    def obter_matriculas_municipio(ibge: int, _user: UserRecord = Depends(get_current_user)):
        ds = _ds(ano)
        row = ds.matriculas[ds.matriculas["ibge"] == ibge]
        if len(row) == 0:
            raise HTTPException(404, "Município não encontrado")
        etapas = ds.etapas
        row_dict = row.iloc[0].to_dict()
        mat = {e: row_dict.get(e, 0) for e in etapas}
        info_rows = ds.complementar[ds.complementar["ibge"] == ibge]
        info = info_rows.iloc[0].to_dict() if len(info_rows) else {}
        resp = {
            "ibge": ibge,
            "nome": info.get("nome", row_dict.get("nome", "")),
            "uf": info.get("uf", row_dict.get("uf", "")),
            "matriculas": mat,
            "recursos_vaaf": info.get("recursos_vaaf", 0),
            "recursos_vaat": info.get("recursos_vaat", 0),
            "nse": info.get("nse", 1),
            "peso_vaar": info.get("peso_vaar", 0),
            "inabilitados_vaat": bool(info.get("inabilitados_vaat", False)),
        }
        if ds.modo_ponderador == "drec":
            resp["drec"] = info.get("drec", 1)
        else:
            resp["nf"] = info.get("nf", 1)
        return sanitize_for_json(resp)

    @app.get(f"{prefix}/cenario-atual/resumo")
    def resumo_cenario_atual(_user: UserRecord = Depends(get_current_user)):
        ds = _ds(ano)
        ufs = ds.cenario_ufs_atual.to_dict(orient="records") if len(ds.cenario_ufs_atual) else []
        agregada = ds.cenario_atual_agregada.to_dict(orient="records") if len(ds.cenario_atual_agregada) else []
        return sanitize_for_json({"ufs": ufs, "agregada": agregada})

    @app.post(f"{prefix}/simular")
    def simular(req: SimulacaoRequest, user: UserRecord = Depends(get_current_user)):
        try:
            return _resposta_simular(req, ano, user)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post(f"{prefix}/simular/completo")
    def simular_completo(req: SimulacaoRequest, user: UserRecord = Depends(get_current_user)):
        ds = _ds(ano)
        _checar_simulacao(ds)
        try:
            sim = executar_simulacao(req, ds, user=user)
            sim["inabilitados_vaat"] = sim["inabilitados_vaat"].apply(
                lambda x: "Verdadeiro" if x else "Falso"
            )
            return sanitize_for_json(sim.fillna(0).to_dict(orient="records"))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post(f"{prefix}/simular/municipio")
    def simular_municipio(req: SimulacaoMunicipioRequest, user: UserRecord = Depends(get_current_user)):
        ds = _ds(ano)
        _checar_simulacao(ds)
        try:
            mat = ds.matriculas.copy()
            if req.matriculas_ajustadas:
                idx = mat.index[mat["ibge"] == req.ibge]
                if len(idx) == 0:
                    raise HTTPException(404, "Município não encontrado")
                for etapa, valor in req.matriculas_ajustadas.items():
                    if etapa in mat.columns:
                        mat.loc[idx, etapa] = valor
            sim_original = executar_simulacao(req, ds, ds.matriculas, user=user)
            sim_ajustada = executar_simulacao(req, ds, mat, user=user)
            mun_original = extrair_detalhes_municipio(sim_original, req.ibge)
            mun_ajustado = extrair_detalhes_municipio(sim_ajustada, req.ibge)
            uf = mun_original["uf"]
            return sanitize_for_json({
                "municipio_original": mun_original,
                "municipio_ajustado": mun_ajustado,
                "estado_original": sim_original[sim_original["uf"] == uf].to_dict(orient="records"),
                "estado_ajustado": sim_ajustada[sim_ajustada["uf"] == uf].to_dict(orient="records"),
            })
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))


def familia_de_etapa(ds: FundebDataset, etapa: str) -> str:
    for fam, etapas in ds.familias.items():
        if etapa in etapas:
            return fam
    return etapa
