"""Parâmetros fixos do estudo contrafactual FUNDEB — Ceará."""

from __future__ import annotations

import os
from dataclasses import dataclass

SEED = 20260902

ANOS = (2024, 2025, 2026)

NOMES_MUNICIPIOS = (
    "Fortaleza",
    "Caucaia",
    "Maracanaú",
    "Sobral",
    "Juazeiro do Norte",
    "Crato",
    "Itapipoca",
    "Maranguape",
    "Quixadá",
    "Iguatu",
)

PERCENTUAIS_DISCRETOS = (5, 10, 20, 30, 50)
PERCENTUAIS_GRANULARES = tuple(range(0, 101))
PERCENTUAIS_CONJUNTOS = tuple(range(0, 101, 10))
PERCENTUAIS_FACTIVEL_CONJUNTO = (25, 50, 75, 100)

# Aliases detectados nos datasets (2024 vs 2025/2026). A primeira etapa
# existente no ano é usada; os nomes oficiais nunca são inventados.
TRANSICOES_CANONICAS = {
    "A": {
        "id": "creche_parcial_integral",
        "rotulo": "Creche parcial → creche integral (rede pública)",
        "origens": ("creche_parcial_rede_publica", "creche_parcial_publica"),
        "destinos": ("creche_integral_rede_publica", "creche_integral_publica"),
    },
    "B": {
        "id": "pre_escola_parcial_integral",
        "rotulo": "Pré-escola parcial → pré-escola integral (rede pública)",
        "origens": ("pre_escola_parcial_rede_publica", "pre_escola_parcial_publica"),
        "destinos": ("pre_escola_integral_rede_publica", "pre_escola_integral_publica"),
    },
    "C": {
        "id": "fund_iniciais_urbano_integral",
        "rotulo": "Fundamental anos iniciais urbano → fundamental integral",
        "origens": (
            "ens_fundamental_series_iniciais_urbano_rede_publica",
            "anos_iniciais_fundamental",
        ),
        "destinos": (
            "ens_fundamental_integral_rede_publica",
            "ensino_fundamental_integral",
        ),
    },
    "D": {
        "id": "fund_finais_urbano_integral",
        "rotulo": "Fundamental anos finais urbano → fundamental integral",
        "origens": (
            "ens_fundamental_series_finais_urbano_rede_publica",
            "anos_finais_fundamental",
        ),
        "destinos": (
            "ens_fundamental_integral_rede_publica",
            "ensino_fundamental_integral",
        ),
    },
}

COLUNAS_RESULTADO = (
    "ibge",
    "uf",
    "nome",
    "matriculas_vaaf",
    "matriculas_vaat",
    "recursos_vaaf",
    "complemento_vaaf",
    "complemento_vaat",
    "complemento_vaar",
    "complemento_uniao",
    "recursos_fundeb",
    "vaaf_final",
    "vaat_final",
)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ANALISE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTADOS_DIR = os.path.join(ANALISE_DIR, "resultados")
FIGURAS_DIR = os.path.join(ANALISE_DIR, "figuras")
SCRIPTS_DIR = os.path.join(ANALISE_DIR, "scripts")


@dataclass(frozen=True)
class Transicao:
    codigo: str
    id: str
    rotulo: str
    origem: str
    destino: str
    origem_nome: str
    destino_nome: str
    peso_vaaf_origem: float
    peso_vaaf_destino: float
    peso_vaat_origem: float
    peso_vaat_destino: float
