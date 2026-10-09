"""Carregamento, inspeção e identificação de municípios/transições."""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from analises.fundeb_ceara.config import (
    NOMES_MUNICIPIOS,
    TRANSICOES_CANONICAS,
    Transicao,
)
from dados.fundeb_dataset import FundebDataset, carregar_dataset, dados_auxiliares_completos


def normaliza_nome(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"\s+", " ", texto).strip().upper()


def colunas_etapa(ds: FundebDataset) -> list[str]:
    etapas = list(dict.fromkeys(ds.etapas))
    return [c for c in etapas if c in ds.matriculas.columns]


def total_matriculas_linha(row: pd.Series, etapas: list[str]) -> float:
    return float(pd.to_numeric(row[etapas], errors="coerce").fillna(0).sum())


def identificar_municipios(ds: FundebDataset) -> pd.DataFrame:
    """Resolve os 10 municípios pelos nomes oficiais do próprio dataset."""
    ce = ds.complementar[ds.complementar["uf"] == "CE"].copy()
    ce["nome_norm"] = ce["nome"].map(normaliza_nome)
    indice = {normaliza_nome(r.nome): r for r in ce.itertuples()}
    linhas = []
    for nome in NOMES_MUNICIPIOS:
        chave = normaliza_nome(nome)
        if chave not in indice:
            raise KeyError(f"Município '{nome}' não encontrado no dataset {ds.ano} (UF=CE).")
        r = indice[chave]
        linhas.append({
            "municipio": nome,
            "ibge": int(r.ibge),
            "nome_oficial": r.nome,
            "uf": "CE",
            "ano": ds.ano,
        })
    return pd.DataFrame(linhas)


def detectar_transicoes(ds: FundebDataset) -> list[Transicao]:
    etapas = set(ds.etapas)
    nomes = {row["etapa"]: row["nome"] for _, row in ds.pesos.iterrows()}
    pesos = ds.pesos.set_index("etapa")
    out: list[Transicao] = []
    for codigo, spec in TRANSICOES_CANONICAS.items():
        origem = next((e for e in spec["origens"] if e in etapas), None)
        destino = next((e for e in spec["destinos"] if e in etapas), None)
        if origem is None or destino is None:
            raise KeyError(
                f"Transição {codigo} sem colunas no ano {ds.ano}: "
                f"origem={origem} destino={destino}"
            )
        out.append(Transicao(
            codigo=codigo,
            id=spec["id"],
            rotulo=spec["rotulo"],
            origem=origem,
            destino=destino,
            origem_nome=str(nomes.get(origem, origem)),
            destino_nome=str(nomes.get(destino, destino)),
            peso_vaaf_origem=float(pesos.loc[origem, "peso_vaaf"]),
            peso_vaaf_destino=float(pesos.loc[destino, "peso_vaaf"]),
            peso_vaat_origem=float(pesos.loc[origem, "peso_vaat"]),
            peso_vaat_destino=float(pesos.loc[destino, "peso_vaat"]),
        ))
    return out


def inspecionar_rda(data_dir: str) -> list[dict[str, Any]]:
    import pyreadr

    registros = []
    for nome in (
        "pesos.rda",
        "matriculas.rda",
        "complementar.rda",
        "cenario_atual.rda",
        "cenario_atual_agregada.rda",
        "cenario_ufs_atual.rda",
    ):
        caminho = os.path.join(data_dir, nome)
        resultado = pyreadr.read_r(caminho)
        for obj_nome, df in resultado.items():
            registros.append({
                "arquivo": nome,
                "objeto_r": obj_nome,
                "linhas": int(len(df)),
                "colunas": int(df.shape[1]),
                "nomes_colunas": [str(c) for c in df.columns],
                "dtypes": {str(c): str(t) for c, t in df.dtypes.items()},
            })
    return registros


@dataclass
class ContextoAno:
    ano: int
    ds: FundebDataset
    municipios: pd.DataFrame
    transicoes: list[Transicao]
    etapas: list[str]
    ce_ibges: list[int]
    ce_municipios_ibges: list[int]
    evidencias_ano: dict[str, Any] = field(default_factory=dict)


def carregar_contexto(ano: int) -> ContextoAno:
    ds = carregar_dataset(ano)
    if not ds.simulacao_habilitada:
        raise RuntimeError(f"Simulação bloqueada para {ano}: {ds.mensagem_bloqueio}")
    municipios = identificar_municipios(ds)
    transicoes = detectar_transicoes(ds)
    etapas = colunas_etapa(ds)
    ce = ds.complementar[ds.complementar["uf"] == "CE"]
    ce_ibges = [int(x) for x in ce["ibge"].tolist()]
    ce_mun = [int(x) for x in ce.loc[ce["ibge"] > 100, "ibge"].tolist()]
    evidencias = {
        "ano_dataset": ds.ano,
        "modo_ponderador": ds.modo_ponderador,
        "n_entes": int(len(ds.matriculas)),
        "n_etapas": len(etapas),
        "n_municipios_ce": len(ce_mun),
        "n_entes_ce": len(ce_ibges),
        "defaults_complementacao": dict(ds.defaults_complementacao),
        "simulacao_habilitada": ds.simulacao_habilitada,
        "auxiliares_2025_completos": dados_auxiliares_completos(2025) if ano == 2025 else None,
        "fonte": (
            "data/*.rda + PonderadorNSE 2024.pdf"
            if ano == 2024
            else "20252026/ planilhas oficiais + cache data/{ano}/"
        ),
    }
    return ContextoAno(
        ano=ano,
        ds=ds,
        municipios=municipios,
        transicoes=transicoes,
        etapas=etapas,
        ce_ibges=ce_ibges,
        ce_municipios_ibges=ce_mun,
        evidencias_ano=evidencias,
    )
