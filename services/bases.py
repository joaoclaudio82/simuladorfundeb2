"""Bases imutáveis por versão, com verificação de conteúdo e cobertura."""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadr

from simulador import simula_fundeb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "catalogo.json"
UF_CODIGOS = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
              21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
              28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
              42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}


def hash_arquivo(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def ler_tabela(path):
    if path.suffix.lower() == ".rda":
        objetos = pyreadr.read_r(str(path))
        if len(objetos) != 1:
            raise ValueError(f"{path.name}: esperado um único objeto tabular.")
        return next(iter(objetos.values())).copy()
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    raise ValueError("Use tabelas .rda ou CSV UTF-8 separado por vírgulas.")


def booleano(valor):
    if isinstance(valor, (bool, np.bool_)):
        return bool(valor)
    texto = str(valor).strip().lower()
    if texto in {"true", "verdadeiro", "1", "1.0"}:
        return True
    if texto in {"false", "falso", "0", "0.0"}:
        return False
    raise ValueError(f"Indicador de habilitação inválido: {valor!r}.")


def conferir_numeros(df, colunas, nome, positivo=False):
    for coluna in colunas:
        if coluna not in df:
            raise ValueError(f"{nome}: coluna ausente: {coluna}.")
        df[coluna] = pd.to_numeric(df[coluna], errors="raise")
    a = df[colunas].to_numpy(dtype=float)
    if not np.isfinite(a).all() or (a < 0).any() or (positivo and (a <= 0).any()):
        raise ValueError(f"{nome}: valores ausentes, não finitos ou fora do domínio.")


@dataclass
class Base:
    meta: dict
    tabelas: dict
    fingerprint: str

    @property
    def etapas(self):
        return self.tabelas["pesos"]["etapa"].tolist()

    def resumo(self):
        cadastro = self.tabelas["entes"]
        return {**deepcopy(self.meta), "fingerprint": self.fingerprint,
                "redes": len(cadastro), "ufs": sorted(cadastro.uf.unique()),
                "tipos": cadastro.tipo.value_counts().to_dict(), "categorias": len(self.etapas),
                "etapas": self.tabelas["pesos"].to_dict("records")}


def carregar_base(root, meta, verificar_hash=True):
    root = Path(root).resolve()
    meta = deepcopy(meta)
    for campo in ("id", "nome", "arquivos", "parametros", "status", "modo_vaat"):
        if campo not in meta:
            raise ValueError(f"Manifesto sem campo {campo}.")
    if meta["modo_vaat"] not in {"fixo", "componentes"}:
        raise ValueError("modo_vaat deve ser fixo ou componentes.")
    if meta["status"] not in {"pendente", "preliminar", "homologada"}:
        raise ValueError("Status da base inválido.")
    for campo in ("ano_exercicio", "ano_censo"):
        valor = meta.get(campo)
        if valor is not None and (type(valor) is not int or not 1900 <= valor <= 2100):
            raise ValueError(f"{campo}: ano inválido.")
    for tipo in ("matriculas", "complementar", "pesos", "entes"):
        if tipo not in meta["arquivos"]:
            raise ValueError(f"Manifesto sem tabela {tipo}.")
    tabelas, hashes = {}, {}
    for nome, relativo in meta["arquivos"].items():
        arquivo = (root / relativo).resolve()
        if not arquivo.is_relative_to(root):
            raise ValueError("Arquivo fora do diretório da base.")
        hashes[nome] = hash_arquivo(arquivo)
        if verificar_hash and meta.get("hashes", {}).get(nome) != hashes[nome]:
            raise ValueError(f"Conteúdo de {nome} mudou: registre uma nova versão da base.")
        tabelas[nome] = ler_tabela(arquivo)
    meta["hashes"] = hashes
    for nome in ("matriculas", "complementar", "entes"):
        d = tabelas[nome]
        conferir_numeros(d, ["ibge"], nome, positivo=True)
        if (d.ibge != np.floor(d.ibge)).any() or d.ibge.duplicated().any():
            raise ValueError(f"{nome}: identificadores fracionários ou duplicados.")
        d["ibge"] = d.ibge.astype("int64")
    ids = set(tabelas["entes"].ibge)
    for nome in ("matriculas", "complementar"):
        outros = set(tabelas[nome].ibge)
        if ids != outros:
            raise ValueError(f"Cobertura de {nome} diferente do cadastro: "
                             f"{len(ids-outros)} ausentes e {len(outros-ids)} extras.")
    entes = tabelas["entes"]
    for c in ("nome", "uf", "tipo"):
        if c not in entes or entes[c].isna().any():
            raise ValueError(f"Cadastro sem {c} válido.")
    if not set(entes.tipo) <= {"estadual", "municipal", "distrital"}:
        raise ValueError("Tipo de rede inválido no cadastro.")
    if not set(entes.uf) <= set(UF_CODIGOS.values()):
        raise ValueError("UF desconhecida no cadastro.")
    estaduais = entes[entes.tipo.isin(["estadual", "distrital"])]
    if estaduais.uf.duplicated().any():
        raise ValueError("Mais de uma rede estadual/distrital na mesma UF.")
    if ((entes.tipo == "distrital") != (entes.uf == "DF")).any():
        raise ValueError("Cadastro do Distrito Federal inconsistente.")
    pesos = tabelas["pesos"]
    if "etapa" not in pesos or pesos.etapa.isna().any() or pesos.etapa.duplicated().any():
        raise ValueError("Categorias de ponderação ausentes ou duplicadas.")
    if "nome" not in pesos or pesos.nome.isna().any():
        raise ValueError("Categorias sem nome de apresentação.")
    conferir_numeros(pesos, ["peso_vaaf", "peso_vaat"], "pesos", positivo=True)
    mat = tabelas["matriculas"]
    extras = set(mat.columns) - {"ibge"} - set(pesos.etapa)
    if not extras <= set(meta.get("colunas_informativas_matriculas", [])):
        raise ValueError("Matrículas contêm colunas não mapeadas nos pesos ou no manifesto: " + ", ".join(sorted(extras)))
    conferir_numeros(mat, pesos.etapa.tolist(), "matrículas")
    fracionarias = [c for c in pesos.etapa if (mat[c] != np.floor(mat[c])).any()]
    if not set(fracionarias) <= set(meta.get("categorias_fracionarias", [])):
        raise ValueError("Categorias com matrículas fracionárias não declaradas no manifesto.")
    comp = tabelas["complementar"]
    conferir_numeros(comp, ["recursos_vaaf", "recursos_vaat", "nse", "nf", "peso_vaar"], "receitas")
    if "inabilitados_vaat" not in comp:
        raise ValueError("Receitas sem indicador de habilitação VAAT.")
    comp["inabilitados_vaat"] = comp.inabilitados_vaat.map(booleano)
    cadastro = entes.set_index("ibge")
    if "uf" in comp and not comp.uf.equals(comp.ibge.map(cadastro.uf)):
        raise ValueError("UFs das receitas não correspondem ao cadastro.")
    comp["uf"] = comp.ibge.map(cadastro.uf)
    comp["nome"] = comp.ibge.map(cadastro.nome)
    if meta["modo_vaat"] == "componentes":
        conferir_numeros(comp, ["outras_receitas_vaat"], "outras receitas VAAT")
    if not set(meta.get("etapas_ept", [])) <= set(pesos.etapa):
        raise ValueError("Recorte EPT contém categorias inexistentes.")
    from schemas.cenarios import Parametros
    parametros = Parametros(**meta["parametros"])
    for campo in ("complementacao_vaaf", "complementacao_vaat", "complementacao_vaar",
                  "min_nse", "max_nse", "min_nf", "max_nf"):
        if getattr(parametros, campo) is None:
            raise ValueError(f"Parâmetro obrigatório na base: {campo}.")
    if parametros.min_nse > parametros.max_nse or parametros.min_nf > parametros.max_nf:
        raise ValueError("Intervalos de ponderação inválidos na base.")
    grupo = meta.get("propag", {})
    if grupo.get("status") == "validado":
        if not grupo.get("fonte") or not grupo.get("ufs") or not set(grupo["ufs"]) <= set(entes.uf):
            raise ValueError("Grupo Propag sem fonte ou com UFs inválidas.")
    if meta["status"] == "homologada":
        obrigatorios = (meta.get("ano_exercicio"), meta.get("fontes"), meta.get("homologacao"),
                       tabelas.get("referencia") is not None)
        if not all(obrigatorios):
            raise ValueError("Homologação exige exercício, fontes, referência e registro do responsável.")
    if "fatores_amazonicos" in tabelas:
        f = tabelas["fatores_amazonicos"]
        conferir_numeros(f, ["ibge", "fator_vaaf", "fator_vaat"], "fatores amazônicos", positivo=True)
        if f.ibge.duplicated().any() or set(f.ibge) != ids:
            raise ValueError("Fatores amazônicos não cobrem exatamente o cadastro de redes.")
    regra = meta.get("amazonico", {})
    if regra.get("status") == "validado":
        if not regra.get("norma") or not regra.get("responsavel_validacao") or "fatores_amazonicos" not in tabelas:
            raise ValueError("Regra amazônica validada exige norma, responsável e tabela de fatores.")
        anos = [regra.get("ano_inicio"), regra.get("ano_fim")]
        if not all(type(a) is int and 1900 <= a <= 2100 for a in anos) or anos[0] > anos[1]:
            raise ValueError("Vigência da regra amazônica inválida.")
        if regra.get("incidencia") != "matriculas_ponderadas_por_ente":
            raise ValueError("Incidência amazônica não suportada por este adaptador.")
    for c in ("matriculas_vaaf", "matriculas_vaat"):
        w = pesos["peso_" + c.split("_")[1]].to_numpy()
        por_uf = pd.Series(mat[pesos.etapa].to_numpy() @ w, index=mat.ibge).groupby(cadastro.uf).sum()
        if (por_uf <= 0).any():
            raise ValueError("Base contém UF sem matrículas ponderadas.")
    fingerprint = sha256(json.dumps(meta, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return Base(meta, tabelas, fingerprint)


class BaseRepository:
    def __init__(self, catalogo=DEFAULT_CATALOG):
        self.catalogo = Path(catalogo)

    def listar(self):
        data = json.loads(self.catalogo.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            raise ValueError("Versão de catálogo não suportada.")
        bases = data["bases"]
        if len({b["id"] for b in bases}) != len(bases):
            raise ValueError("IDs de base duplicados no catálogo.")
        return bases

    def obter(self, base_id):
        meta = next((b for b in self.listar() if b["id"] == base_id), None)
        if meta is None:
            raise ValueError("Base não encontrada no catálogo.")
        return carregar_base(self.catalogo.parent, meta)


def calibrar(base):
    """Confronto por ID; a referência legada não é presumida oficial."""
    ref = base.tabelas.get("referencia")
    if ref is None:
        return {"comparavel": False, "aprovada": False, "motivo": "Sem referência tabular."}
    if "ibge" not in ref or ref.ibge.duplicated().any() or ref.ibge.isna().any():
        raise ValueError("Referência sem identificadores únicos válidos.")
    ref = ref.copy()
    indicadores = ["recursos_fundeb", "complemento_vaaf", "complemento_vaat", "vaaf_final", "vaat_final"]
    conferir_numeros(ref, ["ibge"] + [c for c in indicadores if c in ref], "referência")
    if (ref.ibge != np.floor(ref.ibge)).any():
        raise ValueError("Referência com identificadores fracionários.")
    ref["ibge"] = ref.ibge.astype("int64")
    p = {k: v for k, v in base.meta["parametros"].items() if not k.startswith("pesos_")}
    sim = simula_fundeb(base.tabelas["matriculas"], base.tabelas["complementar"],
                        base.tabelas["pesos"], **p, modo_vaat=base.meta["modo_vaat"], arredondar=False)
    ids, oficiais = set(sim.ibge), set(ref.ibge)
    m = sim.merge(ref, on="ibge", suffixes=("_sim", "_ref"), validate="one_to_one")
    atol = base.meta.get("tolerancias", {}).get("absoluta", 1.0)
    rtol = base.meta.get("tolerancias", {}).get("relativa", 0.0001)
    if not np.isfinite([atol, rtol]).all() or min(atol, rtol) < 0:
        raise ValueError("Tolerâncias inválidas.")
    medidas = []
    for coluna in indicadores:
        if coluna not in ref:
            continue
        a, b = m[coluna + "_sim"], m[coluna + "_ref"]
        diff = (a - b).abs()
        fora = ~np.isclose(a, b, atol=atol, rtol=rtol, equal_nan=False)
        top = m.assign(desvio=diff).sort_values("desvio", ascending=False).head(10)
        por_uf = m.assign(uf=m.ibge.map(sim.set_index("ibge").uf), fora=fora, desvio=diff).groupby("uf", as_index=False).agg(
            redes=("ibge", "size"), fora_tolerancia=("fora", "sum"), maior_desvio_absoluto=("desvio", "max"))
        medidas.append({"indicador": coluna, "fora_tolerancia": int(fora.sum()),
                        "maior_desvio_absoluto": float(diff.max()) if len(diff) else None,
                        "maiores_desvios": top[["ibge", "desvio"]].to_dict("records"), "por_uf": por_uf.to_dict("records")})
    aprovada = ids == oficiais and len(medidas) == 5 and all(x["fora_tolerancia"] == 0 for x in medidas)
    return {"comparavel": bool(len(m)), "aprovada": aprovada,
            "referencia_oficial": bool(base.meta.get("referencia_oficial", False)),
            "redes_em_comum": len(m), "ausentes_na_referencia": sorted(ids-oficiais),
            "extras_na_referencia": sorted(oficiais-ids), "tolerancia_absoluta": atol,
            "tolerancia_relativa": rtol, "indicadores": medidas}
