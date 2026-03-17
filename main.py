"""
API Backend - Simulador FUNDEB v2
FastAPI + endpoints para simulação e consulta de dados
"""

import os
import math
import re
import unicodedata
from typing import Optional

import numpy as np
import pandas as pd
import pyreadr
from pypdf import PdfReader
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
ARQ_DADOS_UNIFICADOS = "dados_unificados.xlsx"
ARQ_PONDERADOR_NSE = "PonderadorNSE 2024.pdf"


def carregar_rda(nome: str) -> pd.DataFrame:
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


print("Carregando dados...")
pesos = carregar_rda("pesos.rda")
matriculas_rda = carregar_rda("matriculas.rda")
complementar = carregar_rda("complementar.rda")
cenario_atual = carregar_rda("cenario_atual.rda")
cenario_atual_agregada = carregar_rda("cenario_atual_agregada.rda")
cenario_ufs_atual = carregar_rda("cenario_ufs_atual.rda")
nse_pdf = carregar_nse_pdf(ARQ_PONDERADOR_NSE)

etapas = pesos["etapa"].tolist()
# Fonte de verdade das 41 etapas do motor:
# manter matriculas.rda para preservar comparabilidade histórica dos resultados.
matriculas = matriculas_rda[["ibge"] + etapas].copy()
campos_tecnicos_xlsx = carregar_campos_tecnicos_xlsx(ARQ_DADOS_UNIFICADOS)

complementar = complementar.copy()
complementar["ibge"] = complementar["ibge"].astype(int)
complementar = complementar.merge(nse_pdf, on="ibge", how="left")
if complementar["nse_pdf"].isna().any():
    faltantes = int(complementar["nse_pdf"].isna().sum())
    print(f"Aviso: {faltantes} ente(s) sem NSE no PDF; mantendo valor de fallback do complementar.rda.")
complementar["nse"] = complementar["nse_pdf"].fillna(complementar["nse"])
complementar.drop(columns=["nse_pdf"], inplace=True)
complementar = complementar.merge(campos_tecnicos_xlsx, on="ibge", how="left")
if "complementacao_vaar_oficial" in complementar.columns:
    total_vaar = float(complementar["complementacao_vaar_oficial"].fillna(0).sum())
    if total_vaar > 0:
        peso_vaar_xlsx = complementar["complementacao_vaar_oficial"].fillna(0) / total_vaar
        complementar["peso_vaar"] = peso_vaar_xlsx.where(
            complementar["complementacao_vaar_oficial"].notna(),
            complementar["peso_vaar"],
        )
    complementar.drop(columns=["complementacao_vaar_oficial"], inplace=True)

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


def calcular_vaat_minimo(sim: pd.DataFrame) -> float:
    """Calcula VAAT mínimo considerando apenas entes habilitados (e DF)."""
    hab = sim[~sim["inabilitados_vaat"].isin([True, "Verdadeiro"]) | (sim["uf"] == "DF")]
    if len(hab) == 0:
        return 0.0
    return float(hab["vaat_final"].min())


def extrair_detalhes_municipio(sim: pd.DataFrame, ibge: int) -> dict:
    """Extrai métricas do município e do fundo estadual para exibição comparativa."""
    linha = sim[sim["ibge"] == ibge]
    if len(linha) == 0:
        raise HTTPException(404, "Município não encontrado")

    mun = linha.iloc[0].to_dict()
    uf = mun["uf"]
    estado = sim[sim["uf"] == uf]

    # Indicadores discriminados para testes de conferência
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

        # Filtra município e adiciona métricas discriminadas
        mun_original = extrair_detalhes_municipio(sim_original, req.ibge)
        mun_ajustado = extrair_detalhes_municipio(sim_ajustada, req.ibge)

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
