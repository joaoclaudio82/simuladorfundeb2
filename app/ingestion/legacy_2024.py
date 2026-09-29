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
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.domain.calculo.motor import simula_fundeb
from app.domain.calculo.validacao import validar_interno

# ---------------------------------------------------------------------------
# Carregamento de dados
# ---------------------------------------------------------------------------

DATA_DIR = str(__import__("pathlib").Path(__file__).resolve().parents[2] / "data")
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


