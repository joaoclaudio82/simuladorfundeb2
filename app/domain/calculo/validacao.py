"""
Módulo de validação interna dos resultados da simulação FUNDEB.
RF-10: Validação interna dos resultados.
CA-05: Comparação com dados oficiais (estrutura para expansão futura).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class ResultadoValidacao:
    """Resultado da validação interna com lista de erros e avisos."""
    valido: bool = True
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    checagens: list[str] = field(default_factory=list)


def validar_interno(simulacao: pd.DataFrame, complementar: pd.DataFrame) -> ResultadoValidacao:
    """
    RF-10: Validação interna dos resultados da simulação.
    Verifica consistência matemática e regras de negócio.
    """
    r = ResultadoValidacao()

    # 1. Soma dos recursos VAAF por UF = total estadual (antes da complementação)
    for uf in simulacao["uf"].unique():
        sub = simulacao[simulacao["uf"] == uf]
        soma_recursos = sub["recursos_vaaf"].sum()
        comp_uf = complementar[complementar["uf"] == uf]
        total_estadual = comp_uf["recursos_vaaf"].sum()
        if abs(soma_recursos - total_estadual) > 1:
            r.erros.append(
                f"UF {uf}: soma recursos_vaaf ({soma_recursos:,.0f}) != total estadual ({total_estadual:,.0f})"
            )
        else:
            r.checagens.append(f"UF {uf}: soma recursos = total estadual OK")

    # 2. VAAF = recursos_vaaf_final / matriculas_vaaf (onde matriculas > 0)
    mask = simulacao["matriculas_vaaf"] > 0
    if mask.any():
        vaaf_calc = simulacao.loc[mask, "recursos_vaaf_final"] / simulacao.loc[mask, "matriculas_vaaf"]
        diff = (simulacao.loc[mask, "vaaf_final"] - vaaf_calc).abs()
        if (diff > 0.1).any():
            n = (diff > 0.1).sum()
            r.erros.append(f"VAAF inconsistente em {n} entes (vaaf_final != recursos_vaaf_final/matriculas_vaaf)")
        else:
            r.checagens.append("VAAF = recursos_vaaf_final / matriculas_vaaf OK")

    # 3. Participação percentual = matrículas_mun / matrículas_estado
    for uf in simulacao["uf"].unique():
        sub = simulacao[simulacao["uf"] == uf]
        total_mat = sub["matriculas_vaaf"].sum()
        if total_mat <= 0:
            continue
        participacoes = sub["matriculas_vaaf"] / total_mat
        soma_part = participacoes.sum()
        if abs(soma_part - 1.0) > 0.001:
            r.erros.append(f"UF {uf}: soma das participações = {soma_part:.4f} (deveria ser 1)")
        else:
            r.checagens.append(f"UF {uf}: participações somam 100% OK")

    # 4. Recursos totais FUNDEB = recursos_vaaf + complemento_uniao
    calc_fundeb = simulacao["recursos_vaaf"] + simulacao["complemento_uniao"]
    diff_fundeb = (simulacao["recursos_fundeb"] - calc_fundeb).abs()
    if (diff_fundeb > 1).any():
        r.erros.append("recursos_fundeb != recursos_vaaf + complemento_uniao em alguns entes")
    else:
        r.checagens.append("recursos_fundeb = recursos_vaaf + complemento_uniao OK")

    r.valido = len(r.erros) == 0
    return r


def comparar_com_oficial(
    simulacao: pd.DataFrame,
    dados_oficiais: pd.DataFrame,
    colunas_comparar: Optional[list[str]] = None,
) -> ResultadoValidacao:
    """
    CA-05: Compara resultados da simulação com dados oficiais publicados do FUNDEB.
    Estrutura preparada para expansão futura quando dados oficiais estiverem disponíveis.
    """
    r = ResultadoValidacao()
    if colunas_comparar is None:
        colunas_comparar = ["recursos_fundeb", "vaaf_final", "vaat_final"]

    if "ibge" not in dados_oficiais.columns or "ibge" not in simulacao.columns:
        r.avisos.append("Dados oficiais sem coluna ibge; comparação não realizada")
        return r

    # Merge por ibge
    merged = simulacao.merge(
        dados_oficiais,
        on="ibge",
        how="inner",
        suffixes=("_sim", "_oficial"),
    )
    if len(merged) == 0:
        r.avisos.append("Nenhum ente em comum entre simulação e dados oficiais")
        return r

    for col in colunas_comparar:
        col_sim = f"{col}_sim" if f"{col}_sim" in merged.columns else col
        col_of = f"{col}_oficial" if f"{col}_oficial" in merged.columns else col
        if col_sim not in merged.columns or col_of not in merged.columns:
            r.avisos.append(f"Coluna {col} não encontrada para comparação")
            continue
        diff_pct = ((merged[col_sim] - merged[col_of]) / merged[col_of].replace(0, pd.NA)).abs()
        diff_pct = diff_pct.dropna()
        if len(diff_pct) > 0:
            media_diff = diff_pct.mean() * 100
            max_diff = diff_pct.max() * 100
            r.checagens.append(
                f"{col}: diferença média {media_diff:.2f}%, máxima {max_diff:.2f}% vs dados oficiais"
            )
            if max_diff > 50:
                r.avisos.append(f"Diferença elevada em {col} (>50%) em relação aos dados oficiais")

    return r
