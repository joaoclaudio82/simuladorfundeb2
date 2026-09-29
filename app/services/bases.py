"""
FND-03 — Catálogo de bases.
Identifica cada exercício (data/catalogo.json), confere os arquivos de origem por hash e
entrega matrículas, receitas, pesos e referências compatíveis. O ETL continua em
dados/fundeb_dataset.py; este módulo só valida e organiza o que ele produz.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd

RAIZ = str(__import__("pathlib").Path(__file__).resolve().parents[2])
CATALOGO_PATH = os.path.join(RAIZ, "data", "catalogo.json")

COLUNAS_COMPLEMENTAR = [
    "ibge", "uf", "nome", "recursos_vaaf", "recursos_vaat",
    "nse", "nf", "peso_vaar", "inabilitados_vaat",
]
COLUNAS_PESOS = ["etapa", "nome", "peso_vaaf", "peso_vaat"]

# Códigos IBGE de UF (dois dígitos). Usados para identificar a rede estadual.
CODIGOS_UF = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35,
    "PR": 41, "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}

TIPO_ESTADUAL = "rede estadual"
TIPO_MUNICIPAL = "rede municipal"
TIPO_DF = "rede do Distrito Federal"


class ErroBase(ValueError):
    """Base inexistente, adulterada ou incompatível."""


@dataclass
class Base:
    base_id: str
    manifesto: dict
    matriculas: pd.DataFrame
    complementar: pd.DataFrame
    pesos: pd.DataFrame
    referencia: pd.DataFrame
    entes: pd.DataFrame
    modo_ponderador: str = "nf"
    parametros_referencia: dict = field(default_factory=dict)
    referencia_oficial: pd.DataFrame | None = None
    avisos: list[str] = field(default_factory=list)

    @property
    def etapas(self) -> list[str]:
        return self.pesos["etapa"].tolist()

    @property
    def ano_exercicio(self) -> int | None:
        return self.manifesto.get("ano_exercicio")

    def identificacao(self) -> dict:
        m = self.manifesto
        return {
            "base_id": self.base_id,
            "descricao": m.get("descricao"),
            "ano_exercicio": m.get("ano_exercicio"),
            "ano_censo": m.get("ano_censo"),
            "periodo_receita": m.get("periodo_receita"),
            "data_publicacao": m.get("data_publicacao"),
            "situacao": m.get("situacao"),
            "homologada": bool(m.get("homologada")),
            "modo_ponderador": self.modo_ponderador,
            "hashes": {a["caminho"]: a["sha256"] for a in m.get("arquivos", [])},
        }


def sha256_arquivo(caminho: str) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_catalogo(caminho: str = CATALOGO_PATH) -> dict:
    from app.core.config import database_source
    if database_source() and caminho == CATALOGO_PATH:
        from app.repositories.bases import catalog
        return catalog()
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def resolver_base_id(base_id: str | None, ano_exercicio: int | None = None,
                     caminho: str = CATALOGO_PATH) -> str:
    """Escolhe a base pelo id ou pelo exercício; sem ambos, usa a base padrão."""
    cat = ler_catalogo(caminho)
    if base_id:
        return base_id
    if ano_exercicio is not None:
        candidatas = [b["base_id"] for b in cat["bases"] if b.get("ano_exercicio") == ano_exercicio]
        if not candidatas:
            raise ErroBase(f"nenhuma base cadastrada para o exercício {ano_exercicio}")
        if len(candidatas) > 1:
            raise ErroBase(f"mais de uma base para o exercício {ano_exercicio}: informe base_id ({candidatas})")
        return candidatas[0]
    return cat["base_padrao"]


def listar_bases(caminho: str = CATALOGO_PATH) -> list[dict]:
    cat = ler_catalogo(caminho)
    return [
        {
            "base_id": b["base_id"],
            "descricao": b.get("descricao"),
            "ano_exercicio": b.get("ano_exercicio"),
            "periodo_receita": b.get("periodo_receita"),
            "situacao": b.get("situacao"),
            "homologada": bool(b.get("homologada")),
            "padrao": b["base_id"] == cat.get("base_padrao"),
            "pendencias": b.get("pendencias", []),
        }
        for b in cat["bases"]
    ]


def conferir_arquivos(manifesto: dict, raiz: str = RAIZ) -> None:
    for arq in manifesto.get("arquivos", []):
        caminho = os.path.join(raiz, arq["caminho"])
        if not os.path.isfile(caminho):
            raise ErroBase(f"arquivo de origem ausente: {arq['caminho']}")
        if sha256_arquivo(caminho) != arq["sha256"]:
            raise ErroBase(
                f"hash divergente em {arq['caminho']}: arquivo alterado sem atualizar data/catalogo.json"
            )


def classificar_entes(complementar: pd.DataFrame, exigir_todas_ufs: bool = True) -> pd.DataFrame:
    """
    Cadastro de entes com tipo de rede explícito.
    A rede estadual é identificada pelo código IBGE da UF (não por limite numérico),
    e a convenção é verificada: cada UF precisa ter exatamente uma rede estadual.
    """
    ent = complementar[["ibge", "uf", "nome"]].copy()
    codigo_uf = ent["uf"].map(CODIGOS_UF)
    if codigo_uf.isna().any():
        ufs = sorted(ent.loc[codigo_uf.isna(), "uf"].unique())
        raise ErroBase(f"UF sem código IBGE conhecido: {ufs}")
    eh_estadual = ent["ibge"] == codigo_uf
    ent["tipo_rede"] = TIPO_MUNICIPAL
    ent.loc[eh_estadual, "tipo_rede"] = TIPO_ESTADUAL
    ent.loc[eh_estadual & (ent["uf"] == "DF"), "tipo_rede"] = TIPO_DF

    contagem = ent[eh_estadual].groupby("uf").size()
    faltantes = sorted(set(CODIGOS_UF) - set(contagem.index))
    if exigir_todas_ufs and faltantes:
        raise ErroBase(f"UF sem rede estadual/distrital na base: {faltantes}")
    if (contagem > 1).any():
        raise ErroBase(f"UF com mais de uma rede estadual: {contagem[contagem > 1].to_dict()}")
    # Códigos de dois dígitos que não coincidem com a UF indicam cadastro inconsistente.
    suspeitos = ent[(ent["ibge"] < 100) & ~eh_estadual]
    if len(suspeitos):
        raise ErroBase(f"Identificadores de UF associados a outra UF: {suspeitos['ibge'].tolist()}")
    return ent.sort_values(["uf", "tipo_rede", "nome"]).reset_index(drop=True)


def validar_schema(matriculas: pd.DataFrame, complementar: pd.DataFrame,
                   pesos: pd.DataFrame, referencia: pd.DataFrame) -> list[str]:
    """Verifica colunas, duplicidades e cobertura. Erros levantam ErroBase; retorna avisos."""
    avisos = []
    faltam = [c for c in COLUNAS_COMPLEMENTAR if c not in complementar.columns]
    if faltam:
        raise ErroBase(f"complementar sem colunas: {faltam}")
    faltam = [c for c in COLUNAS_PESOS if c not in pesos.columns]
    if faltam:
        raise ErroBase(f"pesos sem colunas: {faltam}")

    etapas = pesos["etapa"].tolist()
    if pesos["etapa"].duplicated().any():
        raise ErroBase("pesos com etapas duplicadas")
    faltam = [e for e in etapas if e not in matriculas.columns]
    if faltam:
        raise ErroBase(f"matriculas sem as etapas: {faltam[:10]}")
    extras = sorted(set(matriculas.columns) - set(etapas) - {"ibge"})
    if extras:
        avisos.append(f"matriculas com colunas sem peso (ignoradas no cálculo): {extras[:10]}")

    for nome, df in [("matriculas", matriculas), ("complementar", complementar), ("referencia", referencia)]:
        if df["ibge"].duplicated().any():
            dup = df.loc[df["ibge"].duplicated(), "ibge"].tolist()[:10]
            raise ErroBase(f"{nome} com identificadores duplicados: {dup}")

    ids_mat, ids_comp = set(matriculas["ibge"]), set(complementar["ibge"])
    if ids_mat != ids_comp:
        raise ErroBase(
            f"cobertura divergente: {len(ids_mat - ids_comp)} só em matriculas, "
            f"{len(ids_comp - ids_mat)} só em complementar"
        )
    ids_ref = set(referencia["ibge"])
    if ids_ref != ids_comp:
        avisos.append(
            f"referência com cobertura diferente: {len(ids_comp - ids_ref)} entes sem referência, "
            f"{len(ids_ref - ids_comp)} entes só na referência"
        )

    valores = matriculas[etapas]
    if valores.isna().any().any():
        raise ErroBase("matriculas com valores ausentes; ausência não pode ser tratada como zero")
    if (valores < 0).any().any():
        raise ErroBase("matriculas com valores negativos")
    return avisos


def _normalizar_ibge(df: pd.DataFrame) -> pd.DataFrame:
    if "ibge" in df.columns:
        if df["ibge"].isna().any():
            raise ErroBase("identificador ibge ausente")
        df["ibge"] = df["ibge"].astype(int)
    return df


def _normalizar_inabilitados(serie: pd.Series) -> pd.Series:
    if serie.dtype == bool:
        return serie
    mapa = {"Verdadeiro": True, "Falso": False, "TRUE": True, "FALSE": False, True: True, False: False}
    convertido = serie.map(mapa)
    if convertido.isna().any():
        raise ErroBase(f"valores não reconhecidos em inabilitados_vaat: {serie[convertido.isna()].unique()[:5]}")
    return convertido.astype(bool)


def montar_base(base_id: str, manifesto: dict, matriculas: pd.DataFrame,
                complementar: pd.DataFrame, pesos: pd.DataFrame,
                referencia: pd.DataFrame | None = None,
                modo_ponderador: str = "nf",
                parametros_referencia: dict | None = None,
                referencia_oficial: pd.DataFrame | None = None,
                exigir_todas_ufs: bool = True) -> Base:
    """Valida e monta uma Base a partir de tabelas já lidas (também usado nos testes)."""
    matriculas = _normalizar_ibge(matriculas.drop(columns=["uf", "nome"], errors="ignore").copy())
    complementar = _normalizar_ibge(complementar.copy())
    complementar["inabilitados_vaat"] = _normalizar_inabilitados(complementar["inabilitados_vaat"])
    referencia = _normalizar_ibge(referencia.copy()) if referencia is not None else complementar[["ibge"]].copy()
    avisos = validar_schema(matriculas, complementar, pesos, referencia)
    entes = classificar_entes(complementar, exigir_todas_ufs=exigir_todas_ufs)
    parametros = dict(parametros_referencia or manifesto.get("parametros_referencia", {}))
    return Base(
        base_id=base_id,
        manifesto=manifesto,
        matriculas=matriculas[["ibge"] + pesos["etapa"].tolist()],
        complementar=complementar,
        pesos=pesos.reset_index(drop=True),
        referencia=referencia,
        entes=entes,
        modo_ponderador=modo_ponderador,
        parametros_referencia=parametros,
        referencia_oficial=referencia_oficial,
        avisos=avisos,
    )


def _referencia_oficial(ano: int) -> pd.DataFrame | None:
    """Valores oficiais por ente (planilha de receita prevista), quando existirem."""
    from app.ingestion import fundeb_dataset as fd

    if ano not in fd.RAW_ARQUIVOS or not fd._arquivo_raw_existe(ano, "receita"):
        return None
    rec = fd._ler_receita_total(ano)
    return rec[["ibge", "recursos_contribuicao", "comp_vaaf_oficial", "comp_vaat_oficial",
                "comp_vaar_oficial", "comp_uniao_total", "recursos_fundeb_total"]].copy()


def carregar_base(base_id: str | None = None, caminho_catalogo: str = CATALOGO_PATH,
                  verificar_hash: bool = True) -> Base:
    """Carrega uma base do catálogo. Resultado é compartilhado: consumidores devem copiar antes de alterar."""
    from app.ingestion.fundeb_dataset import carregar_dataset

    from app.core.config import database_source
    if database_source() and caminho_catalogo == CATALOGO_PATH:
        from app.repositories.bases import load_base
        try:
            return load_base(base_id or ler_catalogo()["base_padrao"])
        except ValueError as exc:
            raise ErroBase(str(exc)) from exc
    cat = ler_catalogo(caminho_catalogo)
    base_id = base_id or cat["base_padrao"]
    entradas = {b["base_id"]: b for b in cat["bases"]}
    if base_id not in entradas:
        raise ErroBase(f"base_id desconhecido: {base_id}")
    manifesto = entradas[base_id]
    if verificar_hash:
        conferir_arquivos(manifesto)

    ano = manifesto["ano_exercicio"]
    ds = carregar_dataset(ano)
    if not ds.simulacao_habilitada:
        raise ErroBase(ds.mensagem_bloqueio or f"simulação indisponível para {ano}")
    comp = ds.defaults_complementacao
    parametros = {
        "complementacao_vaaf": float(comp.get("vaaf", 0)),
        "complementacao_vaat": float(comp.get("vaat", 0)),
        "complementacao_vaar": float(comp.get("vaar", 0)),
        # O NSE oficial não é reescalado pelo motor; o NF só é reescalado no modo 'nf' (2024).
        "max_nse": 1.0, "min_nse": 1.0, "max_nf": 1.0, "min_nf": 1.0,
    }
    return montar_base(
        base_id, manifesto,
        matriculas=ds.matriculas,
        complementar=ds.complementar,
        pesos=ds.pesos,
        referencia=ds.cenario_atual,
        modo_ponderador=ds.modo_ponderador,
        parametros_referencia=parametros,
        referencia_oficial=_referencia_oficial(ano),
    )
