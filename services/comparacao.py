import numpy as np
import pandas as pd

METRICAS = {
    "recursos_fundeb": "Recursos totais do Fundeb (R$)",
    "complemento_vaaf": "Complementação VAAF (R$)",
    "complemento_vaat": "Complementação VAAT (R$)",
    "complemento_vaar": "Complementação VAAR (R$)",
    "matriculas_brutas": "Matrículas: soma das categorias da base",
    "matriculas_ept": "Matrículas nas categorias EPT selecionadas na base",
    "matriculas_vaaf": "Matrículas ponderadas VAAF",
    "matriculas_vaat": "Matrículas ponderadas VAAT",
    "vaaf_final": "VAAF (R$/aluno/ano)",
    "vaat_final": "VAAT (R$/aluno/ano)",
}


def registros(df):
    clean = df.replace([np.inf, -np.inf], np.nan)
    return clean.astype(object).where(clean.notna(), None).to_dict("records")


def diferenca(a, b):
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b):
        return {"base": a if a is not None and np.isfinite(a) else None,
                "simulado": b if b is not None and np.isfinite(b) else None,
                "delta": None, "percentual": None}
    delta = float(b-a)
    return {"base": float(a), "simulado": float(b), "delta": delta,
            "percentual": 100 * delta / a if a != 0 else None}


def totais(df):
    t = {m: float(df[m].sum()) for m in METRICAS if m not in {"vaaf_final", "vaat_final"}}
    for modalidade in ("vaaf", "vaat"):
        denominador = t[f"matriculas_{modalidade}"]
        t[f"{modalidade}_final"] = float(df[f"recursos_{modalidade}_final"].sum()) / denominador if denominador else None
    return t


def selecionar_ids(base, recorte, ajustes):
    entes = base.tabelas["entes"]
    filtro = entes.copy()
    denominador = "Todas as redes do Brasil"
    if recorte.tipo in {"estaduais", "propag"}:
        filtro = filtro[filtro.tipo.isin(["estadual", "distrital"])]
        denominador = "Todas as redes estaduais e a rede do Distrito Federal"
    if recorte.tipo == "selecionadas":
        filtro = filtro[filtro.ibge.isin({a.ibge for a in ajustes})]
        if filtro.empty:
            raise ValueError("Recorte selecionadas exige pelo menos uma rede com ajuste.")
    if recorte.tipo == "propag":
        grupo = base.meta.get("propag", {})
        if grupo.get("status") != "validado":
            raise ValueError("Composição do grupo Propag ainda não validada nesta base.")
        filtro = filtro[filtro.uf.isin(grupo["ufs"])]
    if recorte.ufs:
        if len(recorte.ufs) != len(set(recorte.ufs)) or not set(recorte.ufs) <= set(entes.uf):
            raise ValueError("Filtro contém UF inválida ou repetida.")
        filtro = filtro[filtro.uf.isin(recorte.ufs)]
    if filtro.empty:
        raise ValueError("Nenhuma rede corresponde ao recorte escolhido.")
    universo = entes[entes.tipo.isin(["estadual", "distrital"])] if recorte.tipo in {"estaduais", "propag"} else entes
    return set(filtro.ibge), set(universo.ibge), denominador


def comparar(original, alterado, ids, universo):
    a = original[original.ibge.isin(ids)].sort_values(["uf", "tipo", "nome"]).set_index("ibge")
    b = alterado.set_index("ibge").loc[a.index]
    if set(a.index) != ids:
        raise ValueError("O resultado não cobre todas as redes do recorte.")
    total_a = original.loc[original.ibge.isin(universo), "recursos_fundeb"].sum()
    total_b = alterado.loc[alterado.ibge.isin(universo), "recursos_fundeb"].sum()
    linhas = []
    for ibge in a.index:
        row = {"ibge": int(ibge), "uf": a.at[ibge, "uf"], "nome": a.at[ibge, "nome"], "tipo": a.at[ibge, "tipo"]}
        row["indicadores"] = {m: diferenca(a.at[ibge, m], b.at[ibge, m]) for m in METRICAS}
        part_a = 100 * a.at[ibge, "recursos_fundeb"] / total_a if total_a else None
        part_b = 100 * b.at[ibge, "recursos_fundeb"] / total_b if total_b else None
        row["participacao"] = {"base_pct": part_a, "simulado_pct": part_b,
                               "delta_pp": part_b-part_a if part_a is not None and part_b is not None else None}
        linhas.append(row)
    ta, tb = totais(a), totais(b)
    return {"linhas": linhas, "totais": {m: diferenca(ta[m], tb[m]) for m in METRICAS},
            "denominador_participacao": {"base": float(total_a), "simulado": float(total_b)}}
