"""
FND-07 / FND-11 — Comparação entre cenários, recortes e consolidações.
Valores financeiros e contagens são somados; valores por aluno nunca são somados:
nos totais usam razão de somas compatíveis.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from app.services.bases import TIPO_DF, TIPO_ESTADUAL
from app.services.cenarios import ResultadoCenario

# (coluna, rótulo, unidade, tipo)
INDICADORES = [
    ("matriculas_total", "Matrículas (sem ponderação)", "matrículas", "soma"),
    ("matriculas_vaaf", "Matrículas ponderadas VAAF", "matrículas ponderadas", "soma"),
    ("matriculas_vaat", "Matrículas ponderadas VAAT", "matrículas ponderadas", "soma"),
    ("recursos_fundeb", "Recursos totais do Fundeb", "R$", "soma"),
    ("complemento_vaaf", "Complementação VAAF", "R$", "soma"),
    ("complemento_vaat", "Complementação VAAT", "R$", "soma"),
    ("complemento_vaar", "Complementação VAAR", "R$", "soma"),
    ("complemento_uniao", "Complementação da União (total)", "R$", "soma"),
    ("vaaf_final", "VAAF por aluno", "R$/aluno/ano", "razao"),
    ("vaat_final", "VAAT por aluno", "R$/aluno/ano", "razao"),
]
# Razão de somas usada para os indicadores por aluno nos totais.
RAZOES = {
    "vaaf_final": ("recursos_vaaf_final", "matriculas_vaaf"),
    "vaat_final": ("recursos_vaat_final", "matriculas_vaat"),
}
ROTULOS = {c: r for c, r, _, _ in INDICADORES}
UNIDADES = {c: u for c, _, u, _ in INDICADORES}

EFEITOS = {
    "B_A": ("B", "A", "Efeito das matrículas com a receita original"),
    "C_A": ("C", "A", "Efeito da receita com as matrículas originais"),
    "D_A": ("D", "A", "Efeito combinado"),
    "D_C": ("D", "C", "Efeito das matrículas com a receita ampliada"),
}

DESCRICAO_RECORTES = {
    "estaduais_df": "Todas as redes estaduais e a rede do Distrito Federal",
    "selecionadas": "Redes selecionadas",
    "propag": "Grupo Propag",
    "universo": "Universo completo (todas as redes)",
}


class ErroRecorte(ValueError):
    pass


def variacao_pct(novo, antigo):
    """Variação percentual; None quando o denominador é zero ou algum valor está ausente."""
    novo = np.asarray(novo, dtype=float)
    antigo = np.asarray(antigo, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        pct = (novo - antigo) / antigo * 100
    pct = np.where((antigo == 0) | ~np.isfinite(pct), np.nan, pct)
    return pct


def efeitos_disponiveis(res: ResultadoCenario) -> list[str]:
    return [k for k, (x, y, _) in EFEITOS.items() if x in res.resultados and y in res.resultados]


def ibges_recorte(res: ResultadoCenario, recorte: str, selecionadas: list[int] | None = None) -> list[int]:
    entes = res.entes
    if recorte == "estaduais_df":
        ids = entes.loc[entes["tipo_rede"].isin([TIPO_ESTADUAL, TIPO_DF]), "ibge"]
    elif recorte == "universo":
        ids = entes["ibge"]
    elif recorte == "selecionadas":
        sel = list(selecionadas or [])
        if not sel:
            sel = res.ajustes["ibge"].unique().tolist() if len(res.ajustes) else []
        if not sel:
            raise ErroRecorte("recorte 'selecionadas' sem redes: informe 'selecionadas' ou inclua ajustes")
        inexistentes = sorted(set(sel) - set(entes["ibge"]))
        if inexistentes:
            raise ErroRecorte(f"redes selecionadas inexistentes na base: {inexistentes}")
        ids = pd.Series(sel)
    elif recorte == "propag":
        grupo = (res.grupos or {}).get("propag")
        if not grupo:
            raise ErroRecorte("composição do grupo Propag ainda não validada nem versionada no catálogo da base")
        ids = pd.Series(grupo)
    else:
        raise ErroRecorte(f"recorte desconhecido: {recorte}")
    return sorted(set(int(i) for i in ids))


def _tabela_cenario(res: ResultadoCenario, cenario: str) -> pd.DataFrame:
    sim = res.resultados[cenario].merge(res.matriculas_total[cenario], on="ibge", how="left",
                                        validate="one_to_one")
    return sim.set_index("ibge")


def tabela_comparativa(res: ResultadoCenario, recorte: str = "estaduais_df",
                       selecionadas: list[int] | None = None) -> pd.DataFrame:
    """Uma linha por rede do recorte, com valores por cenário, diferenças e participação."""
    ids = ibges_recorte(res, recorte, selecionadas)
    base = res.entes.set_index("ibge").loc[ids, ["uf", "nome", "tipo_rede"]]
    por_cenario = {c: _tabela_cenario(res, c).loc[ids] for c in res.cenarios}
    colunas = {"inabilitado_vaat": por_cenario["A"]["inabilitados_vaat"].astype(bool).values}

    for col, _, _, _ in INDICADORES:
        for c, df in por_cenario.items():
            colunas[f"{col}_{c}"] = df[col].values
    efeitos = efeitos_disponiveis(res)
    for ef in efeitos:
        x, y, _ = EFEITOS[ef]
        for col, _, _, _ in INDICADORES:
            colunas[f"{col}_dif_{ef}"] = colunas[f"{col}_{x}"] - colunas[f"{col}_{y}"]
            colunas[f"{col}_pct_{ef}"] = variacao_pct(colunas[f"{col}_{x}"], colunas[f"{col}_{y}"])

    # Participação no total nacional de recursos do Fundeb (todas as redes) de cada cenário.
    for c in res.cenarios:
        total_nacional = res.resultados[c]["recursos_fundeb"].sum()
        colunas[f"participacao_nacional_pct_{c}"] = (
            por_cenario[c]["recursos_fundeb"].values / total_nacional * 100
            if total_nacional else np.full(len(ids), np.nan)
        )
    for ef in efeitos:
        x, y, _ = EFEITOS[ef]
        colunas[f"participacao_nacional_pp_{ef}"] = (
            colunas[f"participacao_nacional_pct_{x}"] - colunas[f"participacao_nacional_pct_{y}"]
        )
    tab = pd.concat([base, pd.DataFrame(colunas, index=base.index)], axis=1)
    tab = tab.reset_index().rename(columns={"index": "ibge"})
    ordem_tipo = {TIPO_ESTADUAL: 0, TIPO_DF: 0}
    tab["_ordem"] = tab["tipo_rede"].map(ordem_tipo).fillna(1)
    return tab.sort_values(["_ordem", "uf", "nome"]).drop(columns="_ordem").reset_index(drop=True)


def totais_recorte(res: ResultadoCenario, ids: list[int]) -> dict:
    """Totais por cenário: soma para valores financeiros/contagens, razão de somas para valores por aluno."""
    totais = {}
    for c in res.cenarios:
        df = _tabela_cenario(res, c).loc[ids]
        t = {}
        for col, _, _, tipo in INDICADORES:
            if tipo == "soma":
                t[col] = float(df[col].sum())
            else:
                num, den = RAZOES[col]
                d = df[den].sum()
                t[col] = float(df[num].sum() / d) if d else None
        totais[c] = t
    efeitos = {}
    for ef in efeitos_disponiveis(res):
        x, y, desc = EFEITOS[ef]
        efeitos[ef] = {"descricao": desc, "indicadores": {}}
        for col, _, _, _ in INDICADORES:
            vx, vy = totais[x][col], totais[y][col]
            dif = None if vx is None or vy is None else vx - vy
            pct = None if dif is None or not vy else dif / vy * 100
            efeitos[ef]["indicadores"][col] = {"diferenca": dif, "variacao_pct": pct}
    return {"por_cenario": totais, "efeitos": efeitos}


def participacao_recorte(res: ResultadoCenario, ids: list[int]) -> dict:
    """Participação do recorte no total nacional de recursos do Fundeb, por cenário (FND-11)."""
    out = {}
    for c in res.cenarios:
        df = res.resultados[c]
        nacional = df["recursos_fundeb"].sum()
        parte = df.loc[df["ibge"].isin(ids), "recursos_fundeb"].sum()
        out[c] = float(parte / nacional * 100) if nacional else None
    variacoes = {}
    for ef in efeitos_disponiveis(res):
        x, y, _ = EFEITOS[ef]
        variacoes[ef] = None if out[x] is None or out[y] is None else out[x] - out[y]
    return {
        "denominador": "Recursos totais do Fundeb de todas as redes (universo nacional) em cada cenário",
        "participacao_pct": out,
        "variacao_pp": variacoes,
    }


def efeitos_fora_do_recorte(res: ResultadoCenario, ids: list[int]) -> dict:
    """Inspeção do universo: impacto sobre redes fora do recorte e redes sem alteração direta."""
    a, b = res.resultados["A"].set_index("ibge"), res.resultados["B"].set_index("ibge")
    dif = b["recursos_fundeb"] - a["recursos_fundeb"]
    alteradas = set(res.ajustes["ibge"]) if len(res.ajustes) else set()
    fora = ~dif.index.isin(ids)
    sem_ajuste = ~dif.index.isin(list(alteradas))
    tipos = res.entes.set_index("ibge")["tipo_rede"].reindex(dif.index)
    municipal = (tipos == "rede municipal").values
    return {
        "redes_fora_do_recorte_afetadas": int(((dif.abs() > 0.5) & fora).sum()),
        "variacao_fora_do_recorte": float(dif[fora].sum()),
        "redes_sem_ajuste_afetadas": int(((dif.abs() > 0.5) & sem_ajuste).sum()),
        "variacao_redes_municipais": float(dif[municipal].sum()),
        "variacao_total_nacional": float(dif.sum()),
    }


def _limpar(v):
    if isinstance(v, (float, np.floating)):
        return None if not math.isfinite(float(v)) else float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, dict):
        return {k: _limpar(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_limpar(x) for x in v]
    return v


def montar_comparacao(res: ResultadoCenario, recorte: str = "estaduais_df",
                      selecionadas: list[int] | None = None) -> dict:
    ids = ibges_recorte(res, recorte, selecionadas)
    tab = tabela_comparativa(res, recorte, selecionadas)
    return _limpar({
        "recorte": {
            "id": recorte,
            "descricao": DESCRICAO_RECORTES[recorte],
            "quantidade_redes": len(ids),
        },
        "indicadores": [{"coluna": c, "rotulo": r, "unidade": u, "agregacao": t} for c, r, u, t in INDICADORES],
        "efeitos": {k: EFEITOS[k][2] for k in efeitos_disponiveis(res)},
        "linhas": tab.to_dict(orient="records"),
        "totais": totais_recorte(res, ids),
        "participacao": participacao_recorte(res, ids),
        "universo": efeitos_fora_do_recorte(res, ids),
    })
