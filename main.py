"""
API Backend - Simulador FUNDEB v2
FastAPI + endpoints para simulação e consulta de dados
"""

import os
import math
from typing import Optional

import numpy as np
import pandas as pd
import pyreadr
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from simulador import simula_fundeb
from validacao import validar_interno

# ---------------------------------------------------------------------------
# Carregamento de dados
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def carregar_rda(nome: str) -> pd.DataFrame:
    caminho = os.path.join(DATA_DIR, nome)
    resultado = pyreadr.read_r(caminho)
    return list(resultado.values())[0]


print("Carregando dados...")
pesos = carregar_rda("pesos.rda")
matriculas = carregar_rda("matriculas.rda")
complementar = carregar_rda("complementar.rda")
cenario_atual = carregar_rda("cenario_atual.rda")
cenario_atual_agregada = carregar_rda("cenario_atual_agregada.rda")
cenario_ufs_atual = carregar_rda("cenario_ufs_atual.rda")

# Garantir que ibge seja inteiro em todas as tabelas
for df in [matriculas, complementar, cenario_atual]:
    if "ibge" in df.columns:
        df["ibge"] = df["ibge"].astype(int)
print("Dados carregados com sucesso.")

# Mapeamento de nomes amigáveis para as etapas de matrícula
ETAPAS_NOMES = {}
for _, row in pesos.iterrows():
    ETAPAS_NOMES[row["etapa"]] = row["nome"]

# Lista de estados
ESTADOS_REGIOES = {
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
}


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------

class SimulacaoRequest(BaseModel):
    complementacao_vaaf: float = 24153287047
    complementacao_vaat: float = 18114965285
    complementacao_vaar: float = 0
    max_nse: float = 1.1
    min_nse: float = 1.0
    max_nf: float = 1.0
    min_nf: float = 1.0
    pesos_vaaf: Optional[list[float]] = None
    pesos_vaat: Optional[list[float]] = None


class SimulacaoMunicipioRequest(BaseModel):
    ibge: int
    complementacao_vaaf: float = 24153287047
    complementacao_vaat: float = 18114965285
    complementacao_vaar: float = 0
    max_nse: float = 1.1
    min_nse: float = 1.0
    max_nf: float = 1.0
    min_nf: float = 1.0
    pesos_vaaf: Optional[list[float]] = None
    pesos_vaat: Optional[list[float]] = None
    matriculas_ajustadas: Optional[dict[str, float]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_for_json(obj):
    """Converte NaN/Inf para None para serialização JSON válida."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    return obj


def preparar_pesos(req: SimulacaoRequest | SimulacaoMunicipioRequest) -> pd.DataFrame:
    """Prepara dataframe de pesos a partir dos dados do request."""
    p = pesos.copy()
    if req.pesos_vaaf is not None and len(req.pesos_vaaf) == len(p):
        p["peso_vaaf"] = req.pesos_vaaf
    if req.pesos_vaat is not None and len(req.pesos_vaat) == len(p):
        p["peso_vaat"] = req.pesos_vaat
    return p


def executar_simulacao(req: SimulacaoRequest | SimulacaoMunicipioRequest,
                       mat: pd.DataFrame | None = None) -> pd.DataFrame:
    """Executa a simulação com os parâmetros dados."""
    p = preparar_pesos(req)
    dados_mat = mat if mat is not None else matriculas
    return simula_fundeb(
        dados_matriculas=dados_mat,
        dados_complementar=complementar,
        dados_peso=p,
        complementacao_vaaf=req.complementacao_vaaf,
        complementacao_vaat=req.complementacao_vaat,
        complementacao_vaar=req.complementacao_vaar,
        max_nse=req.max_nse,
        min_nse=req.min_nse,
        max_nf=req.max_nf,
        min_nf=req.min_nf,
    )


def gerar_resumo(sim: pd.DataFrame, atual: pd.DataFrame) -> dict:
    """Gera métricas resumo comparando simulação com cenário atual."""
    merged = sim.merge(atual, on=["ibge", "nome", "uf"], suffixes=("_sim", "_atual"))

    vaaf_min_sim = sim["vaaf_final"].min()
    vaaf_min_atual = atual["vaaf_final"].min()

    # Filtrar habilitados (pode ser bool ou string)
    hab_sim = sim[~sim["inabilitados_vaat"].isin([True, "Verdadeiro"])]
    if "inabilitados_vaat" in atual.columns:
        hab_atual = atual[~atual["inabilitados_vaat"].isin([True, "Verdadeiro"])]
    else:
        hab_atual = atual

    vaat_min_sim = hab_sim["vaat_final"].min() if len(hab_sim) > 0 else 0
    vaat_min_atual = hab_atual["vaat_final"].min() if len(hab_atual) > 0 else 0

    compl_mun = sim.loc[sim["ibge"] > 100, "complemento_uniao"].sum()
    compl_est = sim.loc[sim["ibge"] < 100, "complemento_uniao"].sum()
    perc_compl = (sim["complemento_uniao"] > 0).mean()

    dif_recursos = merged["recursos_fundeb_sim"] - merged["recursos_fundeb_atual"]
    dif_pct = dif_recursos / merged["recursos_fundeb_atual"]

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
        "maior_aumento_pct": round(dif_pct.max() * 100, 2),
        "maior_reducao_pct": round(dif_pct.min() * 100, 2),
        "media_mudanca_pct": round(dif_pct.mean() * 100, 2),
        "mediana_mudanca_pct": round(dif_pct.median() * 100, 2),
        "maior_aumento_abs": round(dif_recursos.max(), 2),
        "maior_reducao_abs": round(dif_recursos.min(), 2),
        "total_complementacao_vaaf": round(sim["complemento_vaaf"].sum(), 2),
        "total_complementacao_vaat": round(sim["complemento_vaat"].sum(), 2),
        "total_complementacao_vaar": round(sim["complemento_vaar"].sum(), 2),
    })


def gerar_dados_por_uf(sim: pd.DataFrame) -> list[dict]:
    """Agrega dados da simulação por UF para gráficos."""
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


def gerar_vencedores_perdedores(sim: pd.DataFrame, atual: pd.DataFrame) -> dict:
    """Gera tabela de vencedores e perdedores por região."""
    merged = sim.merge(atual, on=["ibge", "nome", "uf"], suffixes=("_sim", "_atual"))
    regiao_map = {}
    for reg, ufs in ESTADOS_REGIOES.items():
        for uf in ufs:
            regiao_map[uf] = reg
    merged["regiao"] = merged["uf"].map(regiao_map)

    merged["dif_vaaf_pct"] = (
        (merged["recursos_vaaf_final_sim"] - merged["recursos_vaaf_final_atual"])
        / merged["recursos_vaaf_final_atual"] * 100
    )
    merged["dif_vaat_pct"] = (
        (merged["recursos_vaat_final_sim"] - merged["recursos_vaat_final_atual"])
        / merged["recursos_vaat_final_atual"] * 100
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

    return {
        "vaaf": agrupar("resultado_vaaf", "dif_vaaf_pct"),
        "vaat": agrupar("resultado_vaat", "dif_vaat_pct"),
    }


# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(title="Simulador FUNDEB v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Rotas de dados
# ---------------------------------------------------------------------------

@app.get("/api/estados")
def listar_estados():
    ufs = sorted(complementar["uf"].unique().tolist())
    return {"estados": ufs, "regioes": ESTADOS_REGIOES}


@app.get("/api/municipios")
def listar_municipios(uf: str):
    df = complementar[complementar["uf"] == uf][["ibge", "nome", "uf"]].sort_values("nome")
    return sanitize_for_json(df.to_dict(orient="records"))


@app.get("/api/pesos")
def obter_pesos():
    return sanitize_for_json(pesos.to_dict(orient="records"))


@app.get("/api/etapas")
def obter_etapas():
    """Retorna as etapas de matrícula com nomes amigáveis."""
    return ETAPAS_NOMES


@app.get("/api/municipio/{ibge}/matriculas")
def obter_matriculas_municipio(ibge: int):
    row = matriculas[matriculas["ibge"] == ibge]
    if len(row) == 0:
        raise HTTPException(404, "Município não encontrado")
    etapas = pesos["etapa"].tolist()
    row_dict = row.iloc[0].to_dict()
    mat = {e: row_dict.get(e, 0) for e in etapas}
    info = complementar[complementar["ibge"] == ibge].iloc[0].to_dict()
    return sanitize_for_json({
        "ibge": ibge,
        "nome": info.get("nome", ""),
        "uf": info.get("uf", ""),
        "matriculas": mat,
        "recursos_vaaf": info.get("recursos_vaaf", 0),
        "recursos_vaat": info.get("recursos_vaat", 0),
        "nse": info.get("nse", 1),
        "nf": info.get("nf", 1),
        "peso_vaar": info.get("peso_vaar", 0),
        "inabilitados_vaat": bool(info.get("inabilitados_vaat", False)),
    })


@app.get("/api/cenario-atual/resumo")
def resumo_cenario_atual():
    """Retorna dados do cenário atual para comparação."""
    ufs = cenario_ufs_atual.to_dict(orient="records") if cenario_ufs_atual is not None else []
    agregada = cenario_atual_agregada.to_dict(orient="records") if cenario_atual_agregada is not None else []
    return sanitize_for_json({"ufs": ufs, "agregada": agregada})


# ---------------------------------------------------------------------------
# Rotas de simulação
# ---------------------------------------------------------------------------

@app.post("/api/simular")
def simular(req: SimulacaoRequest):
    try:
        sim = executar_simulacao(req)
        resumo = gerar_resumo(sim, cenario_atual)
        dados_uf = gerar_dados_por_uf(sim)
        vp = gerar_vencedores_perdedores(sim, cenario_atual)

        # Complementação por UF e destino
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

        # Diferença com cenário atual
        sim_agg = sim.groupby("uf", as_index=False).agg(complemento_sim=("complemento_uniao", "sum"))
        diff_uf = sim_agg.merge(cenario_atual_agregada, on="uf", how="left")
        diff_uf["diferenca"] = diff_uf["complemento_sim"] - diff_uf["complemento_uniao"]
        diff_uf = diff_uf[["uf", "diferenca"]].round(2)

        # Dados completos (primeiros 100 para preview, endpoint separado para todos)
        dados_tabela = sim.fillna(0).head(200).to_dict(orient="records")

        # RF-10: Validação interna dos resultados
        validacao = validar_interno(sim, complementar)
        validacao_dict = {
            "valido": validacao.valido,
            "erros": validacao.erros,
            "avisos": validacao.avisos,
            "checagens": validacao.checagens,
        }

        return sanitize_for_json({
            "resumo": resumo,
            "por_uf": dados_uf,
            "vencedores_perdedores": vp,
            "complementacao_por_uf": compl_por_uf.to_dict(orient="records"),
            "complementacao_destino": compl_destino.to_dict(orient="records"),
            "diferenca_uf": diff_uf.to_dict(orient="records"),
            "dados_tabela": dados_tabela,
            "validacao": validacao_dict,
        })
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/simular/completo")
def simular_completo(req: SimulacaoRequest):
    """Retorna todos os dados da simulação (para download/tabela completa)."""
    try:
        sim = executar_simulacao(req)
        sim["inabilitados_vaat"] = sim["inabilitados_vaat"].apply(
            lambda x: "Verdadeiro" if x else "Falso"
        )
        return sanitize_for_json(sim.fillna(0).to_dict(orient="records"))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/simular/municipio")
def simular_municipio(req: SimulacaoMunicipioRequest):
    """Simula alteração de matrículas para um município específico."""
    try:
        # Cria cópia das matrículas com ajustes
        mat = matriculas.copy()
        if req.matriculas_ajustadas:
            idx = mat.index[mat["ibge"] == req.ibge]
            if len(idx) == 0:
                raise HTTPException(404, "Município não encontrado")
            for etapa, valor in req.matriculas_ajustadas.items():
                if etapa in mat.columns:
                    mat.loc[idx, etapa] = valor

        # Simulação com matrículas originais
        sim_original = executar_simulacao(req, matriculas)
        # Simulação com matrículas ajustadas
        sim_ajustada = executar_simulacao(req, mat)

        # Filtra município
        mun_original = sim_original[sim_original["ibge"] == req.ibge].iloc[0].to_dict()
        mun_ajustado = sim_ajustada[sim_ajustada["ibge"] == req.ibge].iloc[0].to_dict()

        # Impacto no estado
        uf = mun_original["uf"]
        estado_original = sim_original[sim_original["uf"] == uf].to_dict(orient="records")
        estado_ajustado = sim_ajustada[sim_ajustada["uf"] == uf].to_dict(orient="records")

        return sanitize_for_json({
            "municipio_original": mun_original,
            "municipio_ajustado": mun_ajustado,
            "estado_original": estado_original,
            "estado_ajustado": estado_ajustado,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# Servir frontend
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
