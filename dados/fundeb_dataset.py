"""
Carregamento e ETL dos datasets FUNDEB por exercício (2024, 2025, 2026).
"""

from __future__ import annotations

import os
import pickle
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
import pyreadr
from pypdf import PdfReader

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
RAW_DIR = os.path.join(ROOT_DIR, "20252026")

# Montantes oficiais Portaria MEC/MF nº 6/2026 (1º quadrimestre)
COMPLEMENTACAO_2026 = {
    "vaaf": 60_249_853_912.98,
    "vaat": 63_262_346_608.62,
    "vaar": 15_062_463_478.24,
}

# Incrementar ao alterar ETL (invalida dataset.pkl em data/{ano}/)
DATASET_CACHE_VERSION = 2

ESTADOS_REGIOES = {
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
}


def normaliza_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"\s+", " ", texto).strip().lower()


def slug_etapa(nome: str) -> str:
    """Gera identificador estável a partir do nome do segmento."""
    s = normaliza_texto(nome)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:120]


def normalizar_ibge(valor) -> int | None:
    if pd.isna(valor):
        return None
    try:
        v = int(float(valor))
    except (ValueError, TypeError):
        return None
    if v < 100:
        return v
    return v


def familia_segmento(nome: str) -> str:
    """Agrupa segmento para UI (remove sufixos localização/modalidade)."""
    n = str(nome)
    for suf in (
        " Campo", " Indígena", " Indigena", " Quilombola",
        " Especial", " Bilíngue De Surdos", " Bilingue De Surdos",
        " Urbano", " Rural",
    ):
        if suf in n:
            n = n.split(suf)[0]
    return n.strip()


@dataclass
class FundebDataset:
    ano: int
    matriculas: pd.DataFrame
    pesos: pd.DataFrame
    complementar: pd.DataFrame
    cenario_atual: pd.DataFrame
    cenario_atual_agregada: pd.DataFrame
    cenario_ufs_atual: pd.DataFrame
    etapas_nomes: dict[str, str] = field(default_factory=dict)
    familias: dict[str, list[str]] = field(default_factory=dict)
    modo_ponderador: Literal["nf", "drec"] = "nf"
    simulacao_habilitada: bool = True
    mensagem_bloqueio: str | None = None
    defaults_complementacao: dict[str, float] = field(default_factory=dict)

    @property
    def etapas(self) -> list[str]:
        return self.pesos["etapa"].tolist()


def _ler_matriculas_fp(ano: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    caminho = os.path.join(RAW_DIR, "Matrículas Fundeb 2025 e 2026.xlsx")
    det = pd.read_excel(caminho, sheet_name="Detalhadas", header=2)
    fps = pd.read_excel(caminho, sheet_name="FPs")

    col_ano = "ANO"
    col_uf = "UF"
    col_nome = "Ente Federado"
    col_ibge = "Cód IBGE"

    det = det[det[col_ano] == ano].copy().reset_index(drop=True)
    det[col_ibge] = det[col_ibge].apply(normalizar_ibge)
    det = det[det[col_ibge].notna()].copy()
    det[col_ibge] = det[col_ibge].astype(int)

    fps = fps.rename(columns={
        fps.columns[0]: "nome",
        fps.columns[1]: "peso_vaaf",
        fps.columns[2]: "peso_vaat",
    })
    fps["etapa"] = fps["nome"].apply(slug_etapa)
    fps["peso_vaaf"] = pd.to_numeric(fps["peso_vaaf"], errors="coerce").fillna(0)
    fps["peso_vaat"] = pd.to_numeric(fps["peso_vaat"], errors="coerce").fillna(0)
    # Aba FPs pode repetir o mesmo segmento; manter 1 linha por etapa (alinhado às colunas de matrículas)
    fps = fps.drop_duplicates(subset=["etapa"], keep="first").reset_index(drop=True)

    segmentos = fps["nome"].tolist()
    etapas = fps["etapa"].tolist()

    meta = det[[col_ibge, col_uf, col_nome]].copy()
    meta.columns = ["ibge", "uf", "nome"]
    col_map = {normaliza_texto(c): c for c in det.columns}
    cols_etapa = {}
    for nome_seg, etapa in zip(segmentos, etapas):
        col_real = col_map.get(normaliza_texto(nome_seg))
        if col_real:
            cols_etapa[etapa] = pd.to_numeric(det[col_real], errors="coerce").fillna(0)
        else:
            cols_etapa[etapa] = 0.0
    mat = pd.concat([meta.reset_index(drop=True), pd.DataFrame(cols_etapa)], axis=1)
    etapa_cols = [c for c in mat.columns if c not in ("ibge", "uf", "nome")]
    mat = mat.groupby(["ibge", "uf", "nome"], as_index=False)[etapa_cols].sum()
    mat["ibge"] = mat["ibge"].astype(int)
    for c in etapa_cols:
        mat[c] = mat[c].fillna(0)
    return mat, fps[["nome", "etapa", "peso_vaaf", "peso_vaat"]]


def _ler_nse() -> pd.DataFrame:
    caminho = os.path.join(RAW_DIR, "ponderador-de-nivel-socioeconomico.xlsx")
    df = pd.read_excel(caminho, header=9)
    df = df.rename(columns={
        df.columns[0]: "uf",
        df.columns[1]: "nome",
        df.columns[2]: "ibge",
        df.columns[3]: "nse",
    })
    df["ibge"] = df["ibge"].apply(normalizar_ibge)
    df = df[df["ibge"].notna()].copy()
    df["ibge"] = df["ibge"].astype(int)
    df["nse"] = pd.to_numeric(df["nse"], errors="coerce").fillna(1.0)
    return df[["ibge", "nse"]]


def _ler_drec() -> pd.DataFrame:
    caminho = os.path.join(RAW_DIR, "ponderador-de-disponibilidade-de-recursos.xlsx")
    df = pd.read_excel(caminho, header=8)
    df = df.rename(columns={
        df.columns[0]: "uf",
        df.columns[1]: "nome",
        df.columns[2]: "ibge",
        df.columns[3]: "drec",
    })
    df["ibge"] = df["ibge"].apply(normalizar_ibge)
    df = df[df["ibge"].notna()].copy()
    df["ibge"] = df["ibge"].astype(int)
    df["drec"] = pd.to_numeric(df["drec"], errors="coerce").fillna(1.0)
    return df[["ibge", "drec"]]


def _ler_receita_total() -> pd.DataFrame:
    caminho = os.path.join(RAW_DIR, "1-receita-total-do-fundeb-por-ente-federado.xlsx")
    df = pd.read_excel(caminho, header=9)
    cols = list(df.columns)
    df = df.rename(columns={
        cols[0]: "uf",
        cols[1]: "ibge",
        cols[2]: "nome",
        cols[3]: "recursos_contribuicao",
        cols[4]: "comp_vaaf_oficial",
        cols[5]: "comp_vaat_oficial",
        cols[6]: "comp_vaar_oficial",
        cols[7]: "comp_uniao_total",
        cols[8]: "recursos_fundeb_total",
    })
    df["ibge"] = df["ibge"].apply(normalizar_ibge)
    df = df[df["ibge"].notna()].copy()
    df["ibge"] = df["ibge"].astype(int)
    for c in [
        "recursos_contribuicao", "comp_vaaf_oficial", "comp_vaat_oficial",
        "comp_vaar_oficial", "comp_uniao_total", "recursos_fundeb_total",
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def _ler_vaat_receitas() -> pd.DataFrame:
    caminho = os.path.join(RAW_DIR, "MemriadeClculoVAAT2026 (2).xlsx")
    df = pd.read_excel(caminho, header=6)
    df = df.iloc[1:].copy()
    col_ibge = [c for c in df.columns if "IBGE" in str(c)][0]
    col_rec = [c for c in df.columns if "Corre" in str(c) and "Monet" in str(c)][0]
    col_fundeb_vaaf = [c for c in df.columns if "Fundeb" in str(c) and "VAAF" in str(c)][0]
    col_mat_vaat = [c for c in df.columns if "Matr" in str(c) and "VAAT" in str(c)][0]

    out = pd.DataFrame()
    out["ibge"] = df[col_ibge].apply(normalizar_ibge)
    out = out[out["ibge"].notna()].copy()
    out["ibge"] = out["ibge"].astype(int)
    out["recursos_vaat"] = pd.to_numeric(df[col_rec], errors="coerce").fillna(0)
    out["recursos_vaaf_fundeb"] = pd.to_numeric(df[col_fundeb_vaaf], errors="coerce").fillna(0)
    out["matriculas_vaat_ref"] = pd.to_numeric(df[col_mat_vaat], errors="coerce").fillna(0)
    return out


def _montar_complementar_2026(mat: pd.DataFrame, pesos: pd.DataFrame) -> pd.DataFrame:
    nse = _ler_nse()
    drec = _ler_drec()
    receita = _ler_receita_total()
    vaat = _ler_vaat_receitas()

    base = mat[["ibge", "uf", "nome"]].drop_duplicates("ibge")
    base["ibge"] = base["ibge"].astype(int)
    compl = base.merge(nse, on="ibge", how="left")
    compl = compl.merge(drec, on="ibge", how="left")
    compl = compl.merge(
        receita.drop(columns=["uf", "nome"], errors="ignore"),
        on="ibge", how="left",
    )
    compl = compl.merge(vaat, on="ibge", how="left")

    compl["nse"] = compl["nse"].fillna(1.0)
    compl["drec"] = compl["drec"].fillna(1.0)
    compl["nf"] = compl["drec"]

    compl["recursos_vaaf"] = compl["recursos_vaaf_fundeb"].fillna(compl["recursos_contribuicao"]).fillna(0)
    compl["recursos_vaat"] = compl["recursos_vaat"].fillna(0)

    total_vaar = float(compl["comp_vaar_oficial"].sum())
    if total_vaar > 0:
        compl["peso_vaar"] = compl["comp_vaar_oficial"] / total_vaar
    else:
        compl["peso_vaar"] = 0.0

    compl["inabilitados_vaat"] = compl["matriculas_vaat_ref"].fillna(0) <= 0

    cols = [
        "ibge", "uf", "nome", "recursos_vaaf", "recursos_vaat",
        "nse", "drec", "nf", "peso_vaar", "inabilitados_vaat",
    ]
    return compl[cols].copy()


def _gerar_cenario_referencia(
    mat: pd.DataFrame,
    compl: pd.DataFrame,
    pesos: pd.DataFrame,
    modo: Literal["nf", "drec"],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from simulador import simula_fundeb

    mat_sim = mat.drop(columns=["uf", "nome"], errors="ignore")
    cenario = simula_fundeb(
        dados_matriculas=mat_sim,
        dados_complementar=compl,
        dados_peso=pesos,
        complementacao_vaaf=COMPLEMENTACAO_2026["vaaf"],
        complementacao_vaat=COMPLEMENTACAO_2026["vaat"],
        complementacao_vaar=COMPLEMENTACAO_2026["vaar"],
        max_nse=1.0,
        min_nse=1.0,
        max_nf=1.0,
        min_nf=1.0,
        modo_ponderador=modo,
    )
    if "uf" not in cenario.columns:
        cenario = cenario.merge(compl[["ibge", "nome", "uf"]], on="ibge", how="left")

    agregada = cenario.groupby("uf", as_index=False).agg(
        complemento_uniao=("complemento_uniao", "sum"),
        complemento_vaaf=("complemento_vaaf", "sum"),
        complemento_vaat=("complemento_vaat", "sum"),
        complemento_vaar=("complemento_vaar", "sum"),
        recursos_fundeb=("recursos_fundeb", "sum"),
    ).round(2)

    ufs = cenario.groupby("uf", as_index=False).agg(
        vaaf_final=("vaaf_final", "mean"),
        vaat_final=("vaat_final", "mean"),
        complemento_uniao=("complemento_uniao", "sum"),
    ).round(2)

    return cenario, agregada, ufs


def _etapas_nomes_familias(pesos: pd.DataFrame) -> tuple[dict, dict]:
    nomes = {row["etapa"]: row["nome"] for _, row in pesos.iterrows()}
    familias: dict[str, list[str]] = {}
    for etapa, nome in nomes.items():
        fam = familia_segmento(nome)
        familias.setdefault(fam, []).append(etapa)
    return nomes, familias


def _cache_path(ano: int) -> str:
    return os.path.join(DATA_DIR, str(ano), "dataset.pkl")


def _salvar_cache(ano: int, ds: FundebDataset) -> None:
    cache_dir = os.path.join(DATA_DIR, str(ano))
    os.makedirs(cache_dir, exist_ok=True)
    payload = {
        "cache_version": DATASET_CACHE_VERSION,
        "matriculas": ds.matriculas,
        "pesos": ds.pesos,
        "complementar": ds.complementar,
        "cenario_atual": ds.cenario_atual,
        "cenario_atual_agregada": ds.cenario_atual_agregada,
        "cenario_ufs_atual": ds.cenario_ufs_atual,
        "etapas_nomes": ds.etapas_nomes,
        "familias": ds.familias,
        "modo_ponderador": ds.modo_ponderador,
        "simulacao_habilitada": ds.simulacao_habilitada,
        "mensagem_bloqueio": ds.mensagem_bloqueio,
        "defaults_complementacao": ds.defaults_complementacao,
    }
    with open(_cache_path(ano), "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)


def _carregar_cache(ano: int) -> FundebDataset | None:
    path = _cache_path(ano)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
    except Exception:
        return None

    if payload.get("cache_version") != DATASET_CACHE_VERSION:
        return None

    return FundebDataset(
        ano=ano,
        matriculas=payload["matriculas"],
        pesos=payload["pesos"],
        complementar=payload["complementar"],
        cenario_atual=payload["cenario_atual"],
        cenario_atual_agregada=payload["cenario_atual_agregada"],
        cenario_ufs_atual=payload["cenario_ufs_atual"],
        etapas_nomes=payload["etapas_nomes"],
        familias=payload["familias"],
        modo_ponderador=payload.get("modo_ponderador", "drec" if ano >= 2025 else "nf"),
        simulacao_habilitada=payload.get("simulacao_habilitada", ano != 2025),
        mensagem_bloqueio=payload.get("mensagem_bloqueio"),
        defaults_complementacao=payload.get("defaults_complementacao", {}),
    )


def construir_dataset_2026(usar_cache: bool = True) -> FundebDataset:
    if usar_cache:
        cached = _carregar_cache(2026)
        if cached is not None:
            return cached

    mat, pesos = _ler_matriculas_fp(2026)
    compl = _montar_complementar_2026(mat, pesos)
    cenario, agregada, ufs = _gerar_cenario_referencia(mat, compl, pesos, "drec")
    nomes, familias = _etapas_nomes_familias(pesos)

    ds = FundebDataset(
        ano=2026,
        matriculas=mat,
        pesos=pesos,
        complementar=compl,
        cenario_atual=cenario,
        cenario_atual_agregada=agregada,
        cenario_ufs_atual=ufs,
        etapas_nomes=nomes,
        familias=familias,
        modo_ponderador="drec",
        simulacao_habilitada=True,
        defaults_complementacao=COMPLEMENTACAO_2026.copy(),
    )
    try:
        _salvar_cache(2026, ds)
    except Exception:
        pass
    return ds


def construir_dataset_2025(usar_cache: bool = True) -> FundebDataset:
    if usar_cache:
        cached = _carregar_cache(2025)
        if cached is not None:
            return cached

    mat, pesos = _ler_matriculas_fp(2025)
    nomes, familias = _etapas_nomes_familias(pesos)

    compl = pd.DataFrame({
        "ibge": mat["ibge"],
        "uf": mat["uf"],
        "nome": mat["nome"],
        "recursos_vaaf": 0.0,
        "recursos_vaat": 0.0,
        "nse": 1.0,
        "drec": 1.0,
        "nf": 1.0,
        "peso_vaar": 0.0,
        "inabilitados_vaat": False,
    })

    cenario_vazio = compl.copy()
    for col in [
        "matriculas_vaaf", "matriculas_vaat", "recursos_vaaf_final", "vaaf_final",
        "vaat_pre", "recursos_vaat_final", "vaat_final", "complemento_vaaf",
        "complemento_vaat", "complemento_vaar", "complemento_uniao", "recursos_fundeb",
    ]:
        cenario_vazio[col] = 0.0

    ds = FundebDataset(
        ano=2025,
        matriculas=mat,
        pesos=pesos,
        complementar=compl,
        cenario_atual=cenario_vazio,
        cenario_atual_agregada=pd.DataFrame(columns=["uf", "complemento_uniao"]),
        cenario_ufs_atual=pd.DataFrame(columns=["uf", "vaaf_final", "vaat_final"]),
        etapas_nomes=nomes,
        familias=familias,
        modo_ponderador="drec",
        simulacao_habilitada=False,
        mensagem_bloqueio=(
            "Receitas e ponderadores oficiais de 2025 ainda não disponíveis. "
            "Matrículas carregadas apenas para consulta."
        ),
    )
    try:
        _salvar_cache(2025, ds)
    except Exception:
        pass
    return ds


def carregar_nse_pdf(nome_pdf: str) -> pd.DataFrame:
    caminho_data = os.path.join(DATA_DIR, nome_pdf)
    caminho_raiz = os.path.join(ROOT_DIR, nome_pdf)
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


def carregar_dataset_2024() -> FundebDataset:
    """Carrega dataset legado 2024 (.rda + PDF)."""

    def carregar_rda(nome: str) -> pd.DataFrame:
        caminho = os.path.join(DATA_DIR, nome)
        resultado = pyreadr.read_r(caminho)
        return list(resultado.values())[0]

    pesos = carregar_rda("pesos.rda")
    matriculas_rda = carregar_rda("matriculas.rda")
    complementar = carregar_rda("complementar.rda")
    cenario_atual = carregar_rda("cenario_atual.rda")
    cenario_atual_agregada = carregar_rda("cenario_atual_agregada.rda")
    cenario_ufs_atual = carregar_rda("cenario_ufs_atual.rda")

    etapas = pesos["etapa"].tolist()
    matriculas = matriculas_rda[["ibge"] + etapas].copy()

    nse_pdf = carregar_nse_pdf("PonderadorNSE 2024.pdf")
    complementar = complementar.copy()
    complementar["ibge"] = complementar["ibge"].astype(int)
    complementar = complementar.merge(nse_pdf, on="ibge", how="left")
    complementar["nse"] = complementar["nse_pdf"].fillna(complementar["nse"])
    complementar.drop(columns=["nse_pdf"], inplace=True, errors="ignore")
    if "drec" not in complementar.columns:
        complementar["drec"] = complementar["nf"]

    for df in [matriculas, complementar, cenario_atual]:
        if "ibge" in df.columns:
            df["ibge"] = df["ibge"].astype(int)

    nomes = {row["etapa"]: row["nome"] for _, row in pesos.iterrows()}
    familias = {nomes[e]: [e] for e in etapas}

    return FundebDataset(
        ano=2024,
        matriculas=matriculas,
        pesos=pesos,
        complementar=complementar,
        cenario_atual=cenario_atual,
        cenario_atual_agregada=cenario_atual_agregada,
        cenario_ufs_atual=cenario_ufs_atual,
        etapas_nomes=nomes,
        familias=familias,
        modo_ponderador="nf",
        simulacao_habilitada=True,
        defaults_complementacao={
            "vaaf": 24_153_287_047,
            "vaat": 18_114_965_285,
            "vaar": 0,
        },
    )


_DATASETS: dict[int, FundebDataset] = {}


def carregar_dataset(ano: int, lazy: bool = True) -> FundebDataset:
    if ano in _DATASETS:
        return _DATASETS[ano]
    if ano == 2024:
        ds = carregar_dataset_2024()
    elif ano == 2025:
        ds = construir_dataset_2025()
    elif ano == 2026:
        ds = construir_dataset_2026()
    else:
        raise ValueError(f"Ano não suportado: {ano}")
    if not lazy:
        pass
    _DATASETS[ano] = ds
    return ds


def get_dataset(ano: int) -> FundebDataset:
    return carregar_dataset(ano)
