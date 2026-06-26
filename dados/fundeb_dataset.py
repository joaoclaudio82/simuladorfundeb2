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

# Estimativa Cartilha FUNDEB 2025 (Portaria nº 14/2024); revisar com a portaria da planilha baixada
COMPLEMENTACAO_2025 = {
    "vaaf": 26_900_000_000.00,
    "vaat": 24_200_000_000.00,
    "vaar": 5_400_000_000.00,
}

# Arquivos brutos por exercício em 20252026/ (ver checklist-dados-2025.md)
RAW_ARQUIVOS: dict[int, dict[str, str]] = {
    2025: {
        "receita": "1-receita-total-do-fundeb-por-ente-federado-2025.xlsx",
        "nse": "ponderador-de-nivel-socioeconomico-2025.xlsx",
        "nse_pdf": "PonderadorNSEFundeb2025.pdf",
        "drec": "ponderador-de-disponibilidade-de-recursos-2025.xlsx",
        "drec_pdf": "PonderadorDRecFundeb2025.pdf",
        "vaat": "Receita STN 2023 VAAT 2025 para publicação.xlsx",
    },
    2026: {
        "receita": "1-receita-total-do-fundeb-por-ente-federado.xlsx",
        "nse": "ponderador-de-nivel-socioeconomico.xlsx",
        "drec": "ponderador-de-disponibilidade-de-recursos.xlsx",
        "vaat": "MemriadeClculoVAAT2026 (2).xlsx",
    },
}

MENSAGEM_BLOQUEIO_2025 = (
    "Receitas e ponderadores oficiais de 2025 ainda não disponíveis. "
    "Matrículas carregadas apenas para consulta. "
    "Veja checklist-dados-2025.md."
)

# Incrementar ao alterar ETL (invalida dataset.pkl em data/{ano}/)
DATASET_CACHE_VERSION = 6

NOMES_ESTADOS = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AM": "Amazonas",
    "AP": "Amapá",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MG": "Minas Gerais",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "PA": "Pará",
    "PB": "Paraíba",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "PR": "Paraná",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RO": "Rondônia",
    "RR": "Roraima",
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "SE": "Sergipe",
    "SP": "São Paulo",
    "TO": "Tocantins",
}

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


def _normalizar_nomes_entes_estaduais(df: pd.DataFrame) -> pd.DataFrame:
    """Alinha rótulo dos entes estaduais (ibge < 100) ao padrão de 2024."""
    mask = df["ibge"] < 100
    if mask.any():
        df = df.copy()
        df.loc[mask, "nome"] = df.loc[mask, "uf"].map(NOMES_ESTADOS).fillna(df.loc[mask, "nome"])
    return df


def listar_entes_por_uf(complementar: pd.DataFrame, uf: str) -> pd.DataFrame:
    """Lista entes da UF: governo estadual primeiro, depois municípios por nome."""
    df = complementar[complementar["uf"] == uf][["ibge", "nome", "uf"]].copy()
    df["_prio"] = np.where(df["ibge"] < 100, 0, 1)
    return df.sort_values(["_prio", "nome"]).drop(columns=["_prio"])


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
    mat = _normalizar_nomes_entes_estaduais(mat)
    return mat, fps[["nome", "etapa", "peso_vaaf", "peso_vaat"]]


def _path_raw(ano: int, chave: str) -> str:
    nome = RAW_ARQUIVOS[ano][chave]
    return os.path.join(RAW_DIR, nome)


def _arquivo_raw_existe(ano: int, chave: str) -> bool:
    if ano not in RAW_ARQUIVOS or chave not in RAW_ARQUIVOS[ano]:
        return False
    path = _path_raw(ano, chave)
    if not os.path.isfile(path):
        return False
    # Ignora placeholders de download falho (ex.: HTML 404 salvo como .xlsx)
    if path.endswith(".xlsx") and os.path.getsize(path) < 1024:
        return False
    return True


def dados_auxiliares_completos(ano: int) -> bool:
    """True se receita, NSE, DREC e VAAT estão disponíveis (xlsx e/ou pdf)."""
    if ano not in RAW_ARQUIVOS:
        return False
    tem_receita = _arquivo_raw_existe(ano, "receita")
    tem_nse = _arquivo_raw_existe(ano, "nse") or _arquivo_raw_existe(ano, "nse_pdf")
    tem_drec = _arquivo_raw_existe(ano, "drec") or _arquivo_raw_existe(ano, "drec_pdf")
    tem_vaat = _arquivo_raw_existe(ano, "vaat")
    return tem_receita and tem_nse and tem_drec and tem_vaat


def _extrair_ponderador_pdf(caminho: str, coluna: str) -> pd.DataFrame:
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
            valor = float(match.group(2).replace(",", "."))
            dados.append((ibge, valor))

    df = pd.DataFrame(dados, columns=["ibge", coluna]).drop_duplicates(subset=["ibge"], keep="last")
    if df.empty:
        raise RuntimeError(f"Não foi possível extrair {coluna} de {os.path.basename(caminho)}")
    return df


def _ler_nse(ano: int = 2026) -> pd.DataFrame:
    if _arquivo_raw_existe(ano, "nse"):
        caminho = _path_raw(ano, "nse")
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

    if _arquivo_raw_existe(ano, "nse_pdf"):
        return _extrair_ponderador_pdf(_path_raw(ano, "nse_pdf"), "nse")

    raise FileNotFoundError(f"NSE não encontrado para {ano}")


def _ler_drec(ano: int = 2026) -> pd.DataFrame:
    if _arquivo_raw_existe(ano, "drec"):
        caminho = _path_raw(ano, "drec")
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

    if _arquivo_raw_existe(ano, "drec_pdf"):
        return _extrair_ponderador_pdf(_path_raw(ano, "drec_pdf"), "drec")

    raise FileNotFoundError(f"DREC não encontrado para {ano}")


def _ler_receita_total(ano: int = 2026) -> pd.DataFrame:
    caminho = _path_raw(ano, "receita")
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


def _ler_vaat_stn(caminho: str) -> pd.DataFrame:
    """Planilha STN VAAT (ex.: Receita STN 2023 VAAT 2025 para publicação.xlsx)."""
    xl = pd.ExcelFile(caminho)
    sheet = "COM CORREÇÃO" if "COM CORREÇÃO" in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(caminho, sheet_name=sheet, header=0)
    col_ibge = [c for c in df.columns if "IBGE" in str(c).upper()][0]
    col_total = [c for c in df.columns if str(c).strip().lower() == "total"][0]
    col_fundeb = [c for c in df.columns if "Fundeb" in str(c) and "VAAF" in str(c)][0]

    ibge = df[col_ibge].apply(normalizar_ibge)
    mask = ibge.notna()
    return pd.DataFrame({
        "ibge": ibge[mask].astype(int).values,
        "recursos_vaat": pd.to_numeric(df.loc[mask, col_total], errors="coerce").fillna(0).values,
        "recursos_vaaf_fundeb": pd.to_numeric(df.loc[mask, col_fundeb], errors="coerce").fillna(0).values,
        "matriculas_vaat_ref": 0.0,
    })


def _matriculas_vaat_ref(mat: pd.DataFrame, pesos: pd.DataFrame) -> pd.Series:
    etapas = pesos["etapa"].tolist()
    peso_vaat = pesos.set_index("etapa")["peso_vaat"]
    cols = [c for c in etapas if c in mat.columns]
    m = mat.set_index("ibge")[cols].fillna(0)
    return (m * peso_vaat.reindex(cols).fillna(0)).sum(axis=1)


def _ler_vaat_receitas(ano: int = 2026, mat: pd.DataFrame | None = None, pesos: pd.DataFrame | None = None) -> pd.DataFrame:
    caminho = _path_raw(ano, "vaat")
    nome = os.path.basename(caminho).lower()
    if "stn" in nome or "vaat 2025" in nome:
        out = _ler_vaat_stn(caminho)
    else:
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
        out["recursos_vaat"] = pd.to_numeric(df[col_rec], errors="coerce").fillna(0).values
        out["recursos_vaaf_fundeb"] = pd.to_numeric(df[col_fundeb_vaaf], errors="coerce").fillna(0).values
        out["matriculas_vaat_ref"] = pd.to_numeric(df[col_mat_vaat], errors="coerce").fillna(0).values

    if out["matriculas_vaat_ref"].sum() <= 0 and mat is not None and pesos is not None:
        refs = _matriculas_vaat_ref(mat, pesos)
        out = out.drop(columns=["matriculas_vaat_ref"])
        out = out.merge(refs.rename("matriculas_vaat_ref"), on="ibge", how="left")
        out["matriculas_vaat_ref"] = out["matriculas_vaat_ref"].fillna(0)
    return out


def _complementacao_de_receita(receita: pd.DataFrame) -> dict[str, float]:
    """Deriva totais VAAF/VAAT/VAAR da planilha de receita quando disponível."""
    return {
        "vaaf": float(receita["comp_vaaf_oficial"].sum()),
        "vaat": float(receita["comp_vaat_oficial"].sum()),
        "vaar": float(receita["comp_vaar_oficial"].sum()),
    }


def _montar_complementar(mat: pd.DataFrame, ano: int, pesos: pd.DataFrame | None = None) -> pd.DataFrame:
    nse = _ler_nse(ano)
    drec = _ler_drec(ano)
    receita = _ler_receita_total(ano)
    vaat = _ler_vaat_receitas(ano, mat=mat, pesos=pesos)

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

    # Receita do fundo (Anexo I / Portaria): recursos_contribuicao. A coluna da memória VAAT
    # (recursos_vaaf_fundeb) é base VAAT e não substitui a contribuição oficial ao fundo.
    compl["recursos_vaaf"] = compl["recursos_contribuicao"].fillna(compl["recursos_vaaf_fundeb"]).fillna(0)
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
    complementacao: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from simulador import simula_fundeb

    mat_sim = mat.drop(columns=["uf", "nome"], errors="ignore")
    cenario = simula_fundeb(
        dados_matriculas=mat_sim,
        dados_complementar=compl,
        dados_peso=pesos,
        complementacao_vaaf=complementacao["vaaf"],
        complementacao_vaat=complementacao["vaat"],
        complementacao_vaar=complementacao.get("vaar", 0),
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
    compl = _montar_complementar(mat, 2026, pesos)
    receita = _ler_receita_total(2026)
    defaults = _complementacao_de_receita(receita)
    if defaults["vaaf"] <= 0:
        defaults = COMPLEMENTACAO_2026.copy()
    cenario, agregada, ufs = _gerar_cenario_referencia(mat, compl, pesos, "drec", defaults)
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
        defaults_complementacao=defaults,
    )
    try:
        _salvar_cache(2026, ds)
    except Exception:
        pass
    return ds


def _complementar_placeholder(mat: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
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


def _cenario_vazio(compl: pd.DataFrame) -> pd.DataFrame:
    cenario = compl.copy()
    for col in [
        "matriculas_vaaf", "matriculas_vaat", "recursos_vaaf_final", "vaaf_final",
        "vaat_pre", "recursos_vaat_final", "vaat_final", "complemento_vaaf",
        "complemento_vaat", "complemento_vaar", "complemento_uniao", "recursos_fundeb",
    ]:
        cenario[col] = 0.0
    return cenario


def construir_dataset_2025(usar_cache: bool = True) -> FundebDataset:
    if usar_cache:
        cached = _carregar_cache(2025)
        if cached is not None:
            return cached

    mat, pesos = _ler_matriculas_fp(2025)
    nomes, familias = _etapas_nomes_familias(pesos)

    if dados_auxiliares_completos(2025):
        compl = _montar_complementar(mat, 2025, pesos)
        receita = _ler_receita_total(2025)
        defaults = _complementacao_de_receita(receita)
        if defaults["vaaf"] <= 0:
            defaults = COMPLEMENTACAO_2025.copy()
        cenario, agregada, ufs = _gerar_cenario_referencia(mat, compl, pesos, "drec", defaults)
        simulacao_habilitada = True
        mensagem_bloqueio = None
    else:
        compl = _complementar_placeholder(mat)
        cenario = _cenario_vazio(compl)
        agregada = pd.DataFrame(columns=["uf", "complemento_uniao"])
        ufs = pd.DataFrame(columns=["uf", "vaaf_final", "vaat_final"])
        defaults = COMPLEMENTACAO_2025.copy()
        simulacao_habilitada = False
        mensagem_bloqueio = MENSAGEM_BLOQUEIO_2025

    ds = FundebDataset(
        ano=2025,
        matriculas=mat,
        pesos=pesos,
        complementar=compl,
        cenario_atual=cenario,
        cenario_atual_agregada=agregada,
        cenario_ufs_atual=ufs,
        etapas_nomes=nomes,
        familias=familias,
        modo_ponderador="drec",
        simulacao_habilitada=simulacao_habilitada,
        mensagem_bloqueio=mensagem_bloqueio,
        defaults_complementacao=defaults,
    )
    try:
        _salvar_cache(2025, ds)
    except Exception:
        pass
    return ds


def carregar_nse_pdf(nome_pdf: str) -> pd.DataFrame:
    caminho_data = os.path.join(DATA_DIR, nome_pdf)
    caminho_raiz = os.path.join(ROOT_DIR, nome_pdf)
    caminho_raw = os.path.join(RAW_DIR, nome_pdf)
    if os.path.exists(caminho_data):
        caminho = caminho_data
    elif os.path.exists(caminho_raw):
        caminho = caminho_raw
    elif os.path.exists(caminho_raiz):
        caminho = caminho_raiz
    else:
        raise FileNotFoundError(f"Arquivo de NSE não encontrado: {nome_pdf}")

    return _extrair_ponderador_pdf(caminho, "nse_pdf")


def carregar_dataset_2024() -> FundebDataset:
    """Carrega dataset legado 2024 (.rda + PDF)."""

    def carregar_rda(nome: str) -> pd.DataFrame:
        import pyreadr

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
