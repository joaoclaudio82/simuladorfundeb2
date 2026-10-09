"""Transferências de matrículas com conservação do total e sem valores negativos."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


class TransformacaoInvalida(ValueError):
    """Transferência que violaria conservação ou não-negatividade."""


def _indice_unico(mat: pd.DataFrame, ibge: int) -> int:
    idx = mat.index[mat["ibge"] == ibge]
    if len(idx) != 1:
        raise TransformacaoInvalida(f"IBGE {ibge} não é único em matrículas ({len(idx)} linhas).")
    return int(idx[0])


def total_alunos(mat: pd.DataFrame, ibge: int, etapas: Iterable[str]) -> float:
    i = _indice_unico(mat, ibge)
    cols = [c for c in etapas if c in mat.columns]
    return float(pd.to_numeric(mat.loc[i, cols], errors="coerce").fillna(0).sum())


def transferir_alunos(
    mat: pd.DataFrame,
    ibge: int,
    origem: str,
    destino: str,
    n: float,
    etapas: Iterable[str],
) -> pd.DataFrame:
    """Move n alunos de origem para destino, conservando o total do município."""
    if n < 0:
        raise TransformacaoInvalida(f"n negativo: {n}")
    if origem not in mat.columns:
        raise TransformacaoInvalida(f"Coluna de origem ausente: {origem}")
    if destino not in mat.columns:
        raise TransformacaoInvalida(f"Coluna de destino ausente: {destino}")

    out = mat.copy()
    i = _indice_unico(out, ibge)
    total_antes = total_alunos(out, ibge, etapas)
    atual_origem = float(out.at[i, origem] or 0)
    atual_destino = float(out.at[i, destino] or 0)

    if n == 0:
        return out
    if n - atual_origem > 1e-9:
        raise TransformacaoInvalida(
            f"Tentativa de mover {n} alunos de {origem} (disponível {atual_origem})."
        )

    out[origem] = out[origem].astype("float64")
    out[destino] = out[destino].astype("float64")
    out.at[i, origem] = atual_origem - n
    out.at[i, destino] = atual_destino + n

    if float(out.at[i, origem]) < -1e-9:
        raise TransformacaoInvalida("Matrícula negativa após transferência.")

    total_depois = total_alunos(out, ibge, etapas)
    if abs(total_antes - total_depois) > 1e-6:
        raise TransformacaoInvalida(
            f"Total de alunos não conservado: {total_antes} → {total_depois}"
        )
    return out


def converter_percentual(
    mat: pd.DataFrame,
    ibge: int,
    origem: str,
    destino: str,
    percentual: float,
    etapas: Iterable[str],
) -> tuple[pd.DataFrame, float]:
    """Converte `percentual` da origem para o destino. Retorna (mat, alunos_movidos)."""
    if percentual < 0 or percentual > 100:
        raise TransformacaoInvalida(f"Percentual fora de [0, 100]: {percentual}")
    i = _indice_unico(mat, ibge)
    disponivel = float(mat.at[i, origem] or 0)
    n = disponivel * (percentual / 100.0)
    return transferir_alunos(mat, ibge, origem, destino, n, etapas), n


def aplicar_varias(
    mat: pd.DataFrame,
    ibge: int,
    pares: list[tuple[str, str, float]],
    etapas: Iterable[str],
) -> tuple[pd.DataFrame, float]:
    """Aplica várias conversões percentuais no mesmo município. pares=(origem, destino, %)."""
    out = mat
    total_movidos = 0.0
    for origem, destino, percentual in pares:
        out, n = converter_percentual(out, ibge, origem, destino, percentual, etapas)
        total_movidos += n
    return out, total_movidos


def concentrar_em_etapa(
    mat: pd.DataFrame,
    ibge: int,
    destino: str,
    etapas: Iterable[str],
) -> tuple[pd.DataFrame, float]:
    """Cenário teórico: todo o estoque de matrículas vai para uma única etapa."""
    cols = [c for c in etapas if c in mat.columns]
    if destino not in cols:
        raise TransformacaoInvalida(f"Destino inexistente: {destino}")
    out = mat.copy()
    for c in cols:
        out[c] = out[c].astype("float64")
    i = _indice_unico(out, ibge)
    total = total_alunos(out, ibge, cols)
    for c in cols:
        out.at[i, c] = 0.0
    out.at[i, destino] = total
    if abs(total_alunos(out, ibge, cols) - total) > 1e-6:
        raise TransformacaoInvalida("Falha ao concentrar matrículas.")
    return out, total


def assert_nao_negativas(mat: pd.DataFrame, etapas: Iterable[str]) -> None:
    cols = [c for c in etapas if c in mat.columns]
    minimo = pd.to_numeric(mat[cols].stack(), errors="coerce").min()
    if pd.notna(minimo) and float(minimo) < -1e-9:
        raise TransformacaoInvalida(f"Há matrículas negativas (mínimo={minimo}).")
