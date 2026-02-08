"""
Motor de Simulação do FUNDEB - Versão Python
Reimplementação do pacote R simulador.fundeb
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------------------------

def reescala_vetor(var: np.ndarray, maximo: float = 1.05, minimo: float = 0.95) -> np.ndarray:
    """Reescala um vetor numérico para o intervalo [minimo, maximo] via min-max."""
    maior = np.max(var)
    menor = np.min(var)
    if maior == menor:
        return var.copy()
    return minimo + (maximo - minimo) * (var - menor) / (maior - menor)


# ---------------------------------------------------------------------------
# Etapas da simulação
# ---------------------------------------------------------------------------

def pondera_matriculas_etapa(dados_matriculas: pd.DataFrame, dados_peso: pd.DataFrame) -> pd.DataFrame:
    """Pondera matrículas pelos pesos de cada etapa/modalidade (multiplicação matricial)."""
    df = dados_matriculas.sort_values("ibge").reset_index(drop=True)
    etapas = dados_peso["etapa"].tolist()
    matriz = df[etapas].values.astype(float)

    matriculas_vaaf = matriz @ dados_peso["peso_vaaf"].values.astype(float)
    matriculas_vaat = matriz @ dados_peso["peso_vaat"].values.astype(float)

    return pd.DataFrame({
        "ibge": df["ibge"].values,
        "matriculas_vaaf": matriculas_vaaf,
        "matriculas_vaat": matriculas_vaat,
    })


def pondera_matriculas_sociofiscal(dados_matriculas: pd.DataFrame, dados_complementar: pd.DataFrame) -> pd.DataFrame:
    """Aplica os fatores socioeconômico (NSE) e fiscal (NF) às matrículas ponderadas."""
    df = dados_matriculas.merge(dados_complementar, on="ibge")
    df["matriculas_vaaf"] = df["matriculas_vaaf"] * df["nse"] * df["nf"]
    df["matriculas_vaat"] = df["matriculas_vaat"] * df["nse"]
    return df


def gera_fundo_estadual(dados_entes: pd.DataFrame) -> pd.DataFrame:
    """Agrega dados por UF para gerar os fundos estaduais usados na equalização VAAF."""
    df = dados_entes.groupby("uf", as_index=False).agg(
        matriculas_estado_vaaf=("matriculas_vaaf", "sum"),
        recursos_estado_vaaf=("recursos_vaaf", "sum"),
    )
    df["vaaf_estado_inicial"] = df["recursos_estado_vaaf"] / df["matriculas_estado_vaaf"]
    return df


def equaliza_fundo(
    dados: pd.DataFrame,
    complementacao_uniao: float,
    var_ordem: str,
    var_matriculas: str,
    var_recursos: str,
    identificador: str,
    entes_excluidos: list | None = None,
) -> pd.DataFrame:
    """
    Algoritmo de equalização do FUNDEB.
    Redistribui a complementação da União de baixo para cima, igualando o
    valor-aluno dos entes mais pobres até esgotar o montante disponível.
    """
    if entes_excluidos:
        df_excluidos = dados[dados["ibge"].isin(entes_excluidos)].copy()
        df = dados[~dados["ibge"].isin(entes_excluidos)].copy()
    else:
        df = dados.copy()
        df_excluidos = None

    df = df.sort_values(var_ordem).reset_index(drop=True)
    df["matriculas_acumulados"] = df[var_matriculas].cumsum()
    df["recursos_acumulados"] = df[var_recursos].cumsum()
    df["complementacao_necessaria"] = (
        df["matriculas_acumulados"] * df[var_ordem] - df["recursos_acumulados"]
    )

    complementados = df["complementacao_necessaria"] < complementacao_uniao
    df_complementar = df[complementados].copy()
    df_nao_complementar = df[~complementados].copy()

    if df_excluidos is not None and len(df_excluidos) > 0:
        df_excluidos["complementacao_necessaria"] = 0.0
        df_excluidos["recursos_acumulados"] = 0.0
        df_excluidos["matriculas_acumulados"] = 0.0
        df_nao_complementar = pd.concat([df_nao_complementar, df_excluidos], ignore_index=True)

    if len(df_complementar) > 0:
        total_recursos = df_complementar[var_recursos].sum()
        total_matriculas = df_complementar[var_matriculas].sum()
        df_complementar["recursos_pos"] = (
            df_complementar[var_matriculas] * (total_recursos + complementacao_uniao) / total_matriculas
        )
    df_nao_complementar["recursos_pos"] = df_nao_complementar[var_recursos]

    resultado = pd.concat([df_nao_complementar, df_complementar], ignore_index=True)
    return resultado[[identificador, "recursos_pos"]]


def une_vaaf(
    dados_entes: pd.DataFrame,
    dados_estados: pd.DataFrame,
    dados_fundos_estaduais: pd.DataFrame,
) -> pd.DataFrame:
    """Une a equalização VAAF com a tabela de entes e redistribui intra-estado."""
    df = dados_entes.merge(
        dados_estados[["uf", "recursos_estado_vaaf", "matriculas_estado_vaaf"]],
        on="uf", how="left",
    )
    df = df.merge(dados_fundos_estaduais, on="uf", how="left")

    df["recursos_vaaf_final"] = df["matriculas_vaaf"] * df["recursos_pos"] / df["matriculas_estado_vaaf"]
    df["recursos_vaaf"] = df["matriculas_vaaf"] * df["recursos_estado_vaaf"] / df["matriculas_estado_vaaf"]
    df["vaaf_final"] = df["recursos_vaaf_final"] / df["matriculas_vaaf"]

    df.drop(columns=["matriculas_estado_vaaf", "recursos_pos", "recursos_estado_vaaf"], inplace=True)
    return df


def une_vaat(dados_entes: pd.DataFrame, dados_complementacao_vaat: pd.DataFrame) -> pd.DataFrame:
    """Une a equalização VAAT com a tabela de entes."""
    df = dados_entes.merge(dados_complementacao_vaat, on="ibge", how="left")
    df.rename(columns={"recursos_pos": "recursos_vaat_final"}, inplace=True)
    df["vaat_final"] = df["recursos_vaat_final"] / df["matriculas_vaat"]
    return df


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def simula_fundeb(
    dados_matriculas: pd.DataFrame,
    dados_complementar: pd.DataFrame,
    dados_peso: pd.DataFrame,
    complementacao_vaaf: float,
    complementacao_vaat: float,
    complementacao_vaar: float = 0,
    max_nse: float = 1.05,
    min_nse: float = 0.95,
    max_nf: float = 1.05,
    min_nf: float = 0.95,
) -> pd.DataFrame:
    """
    Função principal de simulação do FUNDEB.
    Reproduz fielmente a lógica do pacote R simulador.fundeb.
    """
    entes_excluidos = dados_complementar.loc[
        dados_complementar["inabilitados_vaat"] == True, "ibge"
    ].tolist()

    # 1 - Pondera matrículas por etapa
    df_matriculas = pondera_matriculas_etapa(dados_matriculas, dados_peso)

    # 2 - Reescala NSE e NF
    compl = dados_complementar.copy()
    compl["nse"] = reescala_vetor(compl["nse"].values, maximo=max_nse, minimo=min_nse)
    compl["nf"] = reescala_vetor(compl["nf"].values, maximo=max_nf, minimo=min_nf)

    # 3 - Ponderação sociofiscal
    df_entes = pondera_matriculas_sociofiscal(df_matriculas, compl)

    # 4 - Fundos estaduais
    df_estados = gera_fundo_estadual(df_entes)

    # 5 - Equalização VAAF (fundos estaduais)
    df_fundo_estadual = equaliza_fundo(
        df_estados, complementacao_vaaf,
        "vaaf_estado_inicial", "matriculas_estado_vaaf",
        "recursos_estado_vaaf", "uf", None,
    )

    # 6 - Redistribuição intra-estadual
    df_entes = une_vaaf(df_entes, df_estados, df_fundo_estadual)

    # 7 - VAAT pré-complementação
    df_entes["vaat_pre"] = df_entes["recursos_vaat"] / df_entes["matriculas_vaat"]

    # 8 - Equalização VAAT (entes individuais)
    fundo_vaat = equaliza_fundo(
        df_entes, complementacao_vaat,
        "vaat_pre", "matriculas_vaat",
        "recursos_vaat", "ibge", entes_excluidos,
    )

    # 9 - Unir VAAT
    df_entes = une_vaat(df_entes, fundo_vaat)

    # 10 - VAAR
    df_entes["complemento_vaar"] = df_entes["peso_vaar"] * complementacao_vaar

    # 11 - Colunas finais
    df_entes["complemento_vaaf"] = df_entes["recursos_vaaf_final"] - df_entes["recursos_vaaf"]
    df_entes["complemento_vaat"] = df_entes["recursos_vaat_final"] - df_entes["recursos_vaat"]
    df_entes["complemento_uniao"] = (
        df_entes["complemento_vaar"] + df_entes["complemento_vaat"] + df_entes["complemento_vaaf"]
    )
    df_entes["recursos_fundeb"] = df_entes["recursos_vaaf"] + df_entes["complemento_uniao"]

    colunas = [
        "ibge", "uf", "nome", "matriculas_vaaf", "matriculas_vaat",
        "recursos_vaaf", "recursos_vaat", "nse", "nf", "inabilitados_vaat",
        "peso_vaar", "recursos_vaaf_final", "vaaf_final", "vaat_pre",
        "recursos_vaat_final", "vaat_final", "complemento_vaaf",
        "complemento_vaat", "complemento_vaar", "complemento_uniao", "recursos_fundeb",
    ]
    return df_entes[colunas].round(2)
