"""
API Backend - Simulador FUNDEB v2
FastAPI + endpoints para simulação e consulta de dados
"""

from __future__ import annotations

import os
import math
import re
import unicodedata
from typing import Optional

import numpy as np
import pandas as pd
from pypdf import PdfReader
from fastapi import Depends, FastAPI, HTTPException
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
ARQ_DADOS_UNIFICADOS = "dados_unificados.xlsx"
ARQ_PONDERADOR_NSE = "PonderadorNSE 2024.pdf"


def carregar_rda(nome: str) -> pd.DataFrame:
    import pyreadr

    caminho = os.path.join(DATA_DIR, nome)
    resultado = pyreadr.read_r(caminho)
    return list(resultado.values())[0]


def normaliza_texto(texto: str) -> str:
    """Normaliza texto removendo acentos, caracteres especiais e caixa."""
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"\s+", " ", texto).strip().lower()


def coluna_por_alias(df: pd.DataFrame, alias: str) -> str | None:
    """Busca coluna por nome normalizado."""
    alias_norm = normaliza_texto(alias)
    for col in df.columns:
        if normaliza_texto(col) == alias_norm:
            return col
    return None


def soma_colunas(df: pd.DataFrame, aliases: list[str]) -> pd.Series | None:
    """Soma uma lista de colunas (por alias normalizado)."""
    cols = []
    for alias in aliases:
        col = coluna_por_alias(df, alias)
        if col:
            cols.append(col)
    if not cols:
        return None
    return df[cols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)


# Mapeia etapas do simulador para colunas da planilha unificada.
# Quando uma etapa não existe na planilha, usamos fallback do matriculas.rda.
MAPEAMENTO_XLSX_ETAPAS = {
    "creche_integral_rede_publica": [
        "Creche Integral Pública Urbano",
        "Creche Integral Pública Campo",
        "Creche Integral Pública Indígena",
        "Creche Integral Pública Quilombola",
    ],
    "creche_parcial_rede_publica": [
        "Creche Parcial Pública Urbano",
        "Creche Parcial Pública Campo",
        "Creche Parcial Pública Indígena",
        "Creche Parcial Pública Quilombola",
    ],
    "pre_escola_integral_rede_publica": [
        "Pré-Escola Integral Pública Urbano",
        "Pré-Escola Integral Pública Campo",
        "Pré-Escola Integral Pública Indígena",
        "Pré-Escola Integral Pública Quilombola",
    ],
    "pre_escola_parcial_rede_publica": [
        "Pré-Escola Parcial Pública Urbano",
        "Pré-Escola Parcial Pública Campo",
        "Pré-Escola Parcial Pública Indígena",
        "Pré-Escola Parcial Pública Quilombola",
    ],
    "ens_fundamental_series_iniciais_urbano_rede_publica": ["Anos Iniciais Fundamental Urbano"],
    "ens_fundamental_series_iniciais_rural_rede_publica": [
        "Anos Iniciais Fundamental Campo",
        "Anos Iniciais Fundamental Indígena",
        "Anos Iniciais Fundamental Quilombola",
    ],
    "ens_fundamental_series_finais_urbano_rede_publica": ["Anos Finais Fundamental Urbano"],
    "ens_fundamental_series_finais_rural_rede_publica": [
        "Anos Finais Fundamental Campo",
        "Anos Finais Fundamental Indígena",
        "Anos Finais Fundamental Quilombola",
    ],
    "ens_fundamental_integral_rede_publica": [
        "Ensino Fundamental Integral Urbano",
        "Ensino Fundamental Integral Campo",
        "Ensino Fundamental Integral Indígena",
        "Ensino Fundamental Integral Quilombola",
    ],
    "ensino_medio_urbano_rede_publica": ["Ensino Médio Parcial Urbano"],
    "ensino_medio_rural_rede_publica": [
        "Ensino Médio Parcial Campo",
        "Ensino Médio Parcial Indígena",
        "Ensino Médio Parcial Quilombola",
    ],
    "ensino_medio_integral_rede_publica": [
        "Ensino Médio Integral Urbano",
        "Ensino Médio Integral Campo",
        "Ensino Médio Integral Indígena",
        "Ensino Médio Integral Quilombola",
    ],
    "educacao_especial_rede_publica": [
        "Educação Especial - Demais segmentos Urbano",
        "Educação Especial - Demais segmentos Campo",
        "Educação Especial - Demais segmentos Indígena",
        "Educação Especial - Demais segmentos Quilombola",
    ],
    "atendimento_educacional_especializado_aee": ["Atendimento Educacional Especializado"],
    "educacao_de_jovens_e_adultos_com_avaliacao_no_processo_rede_publica": [
        "EJA Urbano",
        "EJA Campo",
        "EJA Indígena",
        "EJA Quilombola",
    ],
    "creche_integral_rede_conveniada": [
        "Creche Integral Conveniada Urbano",
        "Creche Integral Conveniada Campo",
        "Creche Integral Conveniada Indígena",
        "Creche Integral Conveniada Quilombola",
    ],
    "creche_parcial_rede_conveniada": [
        "Creche Parcial Conveniada Urbano",
        "Creche Parcial Conveniada Campo",
        "Creche Parcial Conveniada Indígena",
        "Creche Parcial Conveniada Quilombola",
    ],
    "pre_escola_integral_rede_conveniada": [
        "Pré-Escola Integral Conveniada Urbano",
        "Pré-Escola Integral Conveniada Campo",
        "Pré-Escola Integral Conveniada Indígena",
        "Pré-Escola Integral Conveniada Quilombola",
    ],
    "pre_escola_parcial_rede_conveniada": [
        "Pré-Escola Parcial Conveniada Urbano",
        "Pré-Escola Parcial Conveniada Campo",
        "Pré-Escola Parcial Conveniada Indígena",
        "Pré-Escola Parcial Conveniada Quilombola",
    ],
    "ed_ind_quil_creche": [
        "Creche Integral Pública Indígena",
        "Creche Integral Pública Quilombola",
        "Creche Parcial Pública Indígena",
        "Creche Parcial Pública Quilombola",
        "Creche Integral Conveniada Indígena",
        "Creche Integral Conveniada Quilombola",
        "Creche Parcial Conveniada Indígena",
        "Creche Parcial Conveniada Quilombola",
    ],
    "ed_ind_quil_pre_escola": [
        "Pré-Escola Integral Pública Indígena",
        "Pré-Escola Integral Pública Quilombola",
        "Pré-Escola Parcial Pública Indígena",
        "Pré-Escola Parcial Pública Quilombola",
        "Pré-Escola Integral Conveniada Indígena",
        "Pré-Escola Integral Conveniada Quilombola",
        "Pré-Escola Parcial Conveniada Indígena",
        "Pré-Escola Parcial Conveniada Quilombola",
    ],
    "ed_esp_creche": [
        "Educação Especial - Creche Urbano",
        "Educação Especial - Creche Campo",
        "Educação Especial - Creche Indígena",
        "Educação Especial - Creche Quilombola",
    ],
    "ed_esp_pre_escola": [
        "Educação Especial - Pré-Escola Urbano",
        "Educação Especial - Pré-Escola Campo",
        "Educação Especial - Pré-Escola Indígena",
        "Educação Especial - Pré-Escola Quilombola",
    ],
}


def carregar_nse_pdf(nome_pdf: str) -> pd.DataFrame:
    """Extrai NSE por IBGE do PDF oficial de ponderadores."""
    caminho_data = os.path.join(DATA_DIR, nome_pdf)
    caminho_raiz = os.path.join(os.path.dirname(__file__), nome_pdf)
    if os.path.exists(caminho_data):
        caminho = caminho_data
    elif os.path.exists(caminho_raiz):
        caminho = caminho_raiz
    else:
        raise FileNotFoundError(f"Arquivo de NSE não encontrado: {nome_pdf}")

    reader = PdfReader(caminho)
    padrao = re.compile(r"^[A-Z]{2}\s+.+?\s+(\d{1,7})\s+(\d+,\d+)$")

    dados = []
    for pagina in reader.pages:
        texto = pagina.extract_text() or ""
        for linha in texto.splitlines():
            linha = re.sub(r"\s+", " ", linha).strip()
            match = padrao.match(linha)
            if not match:
                continue
            ibge = int(match.group(1))
            nse = float(match.group(2).replace(",", "."))
            dados.append((ibge, nse))

    nse_df = pd.DataFrame(dados, columns=["ibge", "nse_pdf"]).drop_duplicates(subset=["ibge"], keep="last")
    if nse_df.empty:
        raise RuntimeError("Não foi possível extrair NSE do PDF oficial.")
    return nse_df


def carregar_matriculas_da_planilha(nome_xlsx: str, etapas: list[str], fallback_rda: pd.DataFrame) -> pd.DataFrame:
    """Monta matrículas no formato do motor usando planilha unificada + fallback rda."""
    caminho = os.path.join(DATA_DIR, nome_xlsx)
    xlsx = pd.read_excel(caminho)

    col_ibge_x = coluna_por_alias(xlsx, "Código IBGE_x")
    col_ibge_y = coluna_por_alias(xlsx, "Código IBGE_y")
    if not col_ibge_x or not col_ibge_y:
        raise RuntimeError("Colunas de chave IBGE não encontradas na planilha unificada.")

    xlsx["ibge"] = pd.to_numeric(xlsx[col_ibge_x], errors="coerce").astype("Int64")
    if xlsx["ibge"].isna().any():
        raise RuntimeError("Existem valores IBGE inválidos na planilha unificada.")
    xlsx["ibge"] = xlsx["ibge"].astype(int)

    divergencias = (xlsx[col_ibge_x].astype(str) != xlsx[col_ibge_y].astype(str)).sum()
    if divergencias:
        print(f"Aviso: {divergencias} divergência(s) entre Código IBGE_x e Código IBGE_y; usando Código IBGE_x como chave canônica.")

    if xlsx["ibge"].duplicated().any():
        raise RuntimeError("Planilha unificada possui IBGE duplicado em Código IBGE_x.")

    mat = xlsx[["ibge"]].copy()
    faltantes_no_xlsx = []
    for etapa in etapas:
        aliases = MAPEAMENTO_XLSX_ETAPAS.get(etapa, [])
        serie = soma_colunas(xlsx, aliases) if aliases else None
        if serie is None:
            mat[etapa] = np.nan
            faltantes_no_xlsx.append(etapa)
        else:
            mat[etapa] = serie

    fallback = fallback_rda[["ibge"] + etapas].copy()
    fallback["ibge"] = fallback["ibge"].astype(int)
    mat = mat.merge(fallback, on="ibge", how="left", suffixes=("", "_rda"))

    for etapa in etapas:
        mat[etapa] = pd.to_numeric(mat[etapa], errors="coerce")
        mat[f"{etapa}_rda"] = pd.to_numeric(mat[f"{etapa}_rda"], errors="coerce")
        mat[etapa] = mat[etapa].fillna(mat[f"{etapa}_rda"]).fillna(0)
        mat.drop(columns=[f"{etapa}_rda"], inplace=True)

    if faltantes_no_xlsx:
        print(
            f"Aviso: {len(faltantes_no_xlsx)} etapa(s) sem coluna equivalente na planilha; "
            "valores preenchidos com fallback do matriculas.rda."
        )

    return mat


def carregar_campos_tecnicos_xlsx(nome_xlsx: str) -> pd.DataFrame:
    """Carrega campos técnicos disponíveis na planilha unificada (por IBGE)."""
    caminho = os.path.join(DATA_DIR, nome_xlsx)
    xlsx = pd.read_excel(caminho)

    col_ibge_x = coluna_por_alias(xlsx, "Código IBGE_x")
    if not col_ibge_x:
        raise RuntimeError("Coluna Código IBGE_x não encontrada na planilha unificada.")

    out = pd.DataFrame()
    out["ibge"] = pd.to_numeric(xlsx[col_ibge_x], errors="coerce").astype("Int64")
    if out["ibge"].isna().any():
        raise RuntimeError("Existem IBGEs inválidos na planilha unificada.")
    out["ibge"] = out["ibge"].astype(int)

    col_comp_vaar = coluna_por_alias(xlsx, "Complementação VAAR")
    if col_comp_vaar:
        out["complementacao_vaar_oficial"] = pd.to_numeric(
            xlsx[col_comp_vaar], errors="coerce"
        ).fillna(0)

    if out["ibge"].duplicated().any():
        raise RuntimeError("Planilha unificada possui IBGE duplicado em Código IBGE_x.")

    return out


from auth.database import init_db, seed_admin_if_empty
from auth.routes import router as auth_router
from dados.fundeb_dataset import ESTADOS_REGIOES, carregar_dataset
from auth.deps import get_current_user
from auth.models import UserRecord
from api_simulacao import (
    SimulacaoRequest,
    SimulacaoMunicipioRequest,
    _resposta_simular,
    executar_simulacao,
    extrair_detalhes_municipio,
    registrar_rotas_ano,
    sanitize_for_json,
)

print("Carregando dados 2024...")
_DS2024 = carregar_dataset(2024)
pesos = _DS2024.pesos
matriculas = _DS2024.matriculas
complementar = _DS2024.complementar
cenario_atual = _DS2024.cenario_atual
cenario_atual_agregada = _DS2024.cenario_atual_agregada
cenario_ufs_atual = _DS2024.cenario_ufs_atual
ETAPAS_NOMES = _DS2024.etapas_nomes
print("Dados 2024 carregados.")

# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(title="Simulador FUNDEB v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth_router, prefix="/api")


@app.on_event("startup")
def startup_auth():
    init_db()
    seed_admin_if_empty()


# ---------------------------------------------------------------------------
# Rotas de dados
# ---------------------------------------------------------------------------

@app.get("/api/estados")
def listar_estados(_user: UserRecord = Depends(get_current_user)):
    ufs = sorted(complementar["uf"].unique().tolist())
    return {"estados": ufs, "regioes": ESTADOS_REGIOES}


@app.get("/api/municipios")
def listar_municipios(uf: str, _user: UserRecord = Depends(get_current_user)):
    df = complementar[complementar["uf"] == uf][["ibge", "nome", "uf"]].sort_values("nome")
    return sanitize_for_json(df.to_dict(orient="records"))


@app.get("/api/pesos")
def obter_pesos(_user: UserRecord = Depends(get_current_user)):
    from dados.fundeb_dataset import familia_segmento

    out = pesos.to_dict(orient="records")
    for row in out:
        row["familia"] = familia_segmento(row["nome"])
    return sanitize_for_json(out)


@app.get("/api/etapas")
def obter_etapas(_user: UserRecord = Depends(get_current_user)):
    """Retorna as etapas de matrícula com nomes amigáveis."""
    return ETAPAS_NOMES


@app.get("/api/municipio/{ibge}/matriculas")
def obter_matriculas_municipio(ibge: int, _user: UserRecord = Depends(get_current_user)):
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
def resumo_cenario_atual(_user: UserRecord = Depends(get_current_user)):
    """Retorna dados do cenário atual para comparação."""
    ufs = cenario_ufs_atual.to_dict(orient="records") if cenario_ufs_atual is not None else []
    agregada = cenario_atual_agregada.to_dict(orient="records") if cenario_atual_agregada is not None else []
    return sanitize_for_json({"ufs": ufs, "agregada": agregada})


# ---------------------------------------------------------------------------
# Rotas de simulação
# ---------------------------------------------------------------------------

@app.post("/api/simular")
def simular(req: SimulacaoRequest, user: UserRecord = Depends(get_current_user)):
    try:
        return _resposta_simular(req, 2024, user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/simular/completo")
def simular_completo(req: SimulacaoRequest, user: UserRecord = Depends(get_current_user)):
    try:
        sim = executar_simulacao(req, _DS2024, user=user)
        sim["inabilitados_vaat"] = sim["inabilitados_vaat"].apply(
            lambda x: "Verdadeiro" if x else "Falso"
        )
        return sanitize_for_json(sim.fillna(0).to_dict(orient="records"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/simular/municipio")
def simular_municipio(req: SimulacaoMunicipioRequest, user: UserRecord = Depends(get_current_user)):
    try:
        mat = matriculas.copy()
        if req.matriculas_ajustadas:
            idx = mat.index[mat["ibge"] == req.ibge]
            if len(idx) == 0:
                raise HTTPException(404, "Município não encontrado")
            for etapa, valor in req.matriculas_ajustadas.items():
                if etapa in mat.columns:
                    mat.loc[idx, etapa] = valor
        sim_original = executar_simulacao(req, _DS2024, matriculas, user=user)
        sim_ajustada = executar_simulacao(req, _DS2024, mat, user=user)
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


# Rotas por exercício (2025 e 2026)
registrar_rotas_ano(app, 2025)
registrar_rotas_ano(app, 2026)


# ---------------------------------------------------------------------------
# Servir frontend
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/login.html")
def serve_login():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))


@app.get("/admin.html")
def serve_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import uvicorn
    # reload=False evita reinícios em loop no Windows ao salvar arquivos do projeto
    reload = os.environ.get("FUNDEB_RELOAD", "").lower() in ("1", "true", "yes")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload)
