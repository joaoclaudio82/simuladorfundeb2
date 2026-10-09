"""Dez municípios em pelo menos um estado de cada região brasileira."""

from __future__ import annotations

import os

from dados.fundeb_dataset import ESTADOS_REGIOES

ANOS = (2024, 2025, 2026)
SEED = 20260902
PERCENTUAIS = tuple(range(0, 101, 5))
PERCENTUAIS_DETALHE = (50, 100)

# Nome de exibição, UF esperada. IBGE resolvido nos dados (município: ibge > 100).
ALVOS = (
    ("Manaus", "AM", "Norte"),
    ("Belém", "PA", "Norte"),
    ("Fortaleza", "CE", "Nordeste"),
    ("Salvador", "BA", "Nordeste"),
    ("São Paulo", "SP", "Sudeste"),
    ("Belo Horizonte", "MG", "Sudeste"),
    ("Rio de Janeiro", "RJ", "Sudeste"),
    ("Curitiba", "PR", "Sul"),
    ("Porto Alegre", "RS", "Sul"),
    ("Goiânia", "GO", "Centro-Oeste"),
)

UF_REGIAO = {uf: reg for reg, ufs in ESTADOS_REGIOES.items() for uf in ufs}

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ANALISE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTADOS_DIR = os.path.join(ANALISE_DIR, "resultados")
FIGURAS_DIR = os.path.join(ANALISE_DIR, "figuras")
