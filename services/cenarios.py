"""
FND-05 / FND-10 / FND-11 — Serviço de cenários.
Aplica ajustes de matrículas e hipóteses de receita a cópias da base e executa
o motor nacional uma vez por cenário (A, B e, com receita alterada, C e D).
"""
from __future__ import annotations

import hashlib
import os
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from schemas.cenarios import AVISO_METODOLOGICO, Ajuste, CenarioRequest, HipoteseReceita, ParametrosSimulacao
from services.bases import Base
from simulador import simula_fundeb
from validacao import validar_interno

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _versao_motor() -> str:
    h = hashlib.sha256()
    for nome in ["simulador.py", os.path.join("services", "cenarios.py")]:
        with open(os.path.join(_RAIZ, nome), "rb") as f:
            h.update(f.read())
    return "sha256:" + h.hexdigest()[:12]


VERSAO_MOTOR = _versao_motor()

DESCRICAO_CENARIOS = {
    "A": "Matrículas originais, receita original",
    "B": "Matrículas alteradas, receita original",
    "C": "Matrículas originais, receita ampliada",
    "D": "Matrículas alteradas, receita ampliada",
}


class ErroCenario(ValueError):
    """Entrada de cenário inválida."""


@dataclass
class ResultadoCenario:
    cenario_id: str
    criado_em: str
    base: dict
    versao_motor: str
    requisicao: dict
    parametros_efetivos: dict
    receita: dict
    ajustes: pd.DataFrame
    resumo_ajustes: dict
    matriculas_total: dict[str, pd.DataFrame]
    resultados: dict[str, pd.DataFrame]
    validacoes: dict[str, dict]
    entes: pd.DataFrame
    grupos: dict = field(default_factory=dict)
    aviso: str = AVISO_METODOLOGICO

    @property
    def cenarios(self) -> list[str]:
        return list(self.resultados.keys())

    def metadados(self) -> dict:
        return {
            "cenario_id": self.cenario_id,
            "criado_em": self.criado_em,
            "base": self.base,
            "versao_motor": self.versao_motor,
            "parametros": self.parametros_efetivos,
            "receita": self.receita,
            "cenarios": {k: DESCRICAO_CENARIOS[k] for k in self.cenarios},
            "resumo_ajustes": self.resumo_ajustes,
            "validacoes": self.validacoes,
            "aviso": self.aviso,
        }


# ---------------------------------------------------------------------------
# Ajustes de matrículas
# ---------------------------------------------------------------------------

_ORDEM_OPERACAO = {"definir": 0, "acrescentar": 1, "converter": 2}


def validar_ajustes(ajustes: list[Ajuste], base: Base) -> None:
    etapas = set(base.etapas)
    ids = set(base.matriculas["ibge"])
    erros = []
    definidos: dict[tuple[int, str], float] = {}
    outras_ops: set[tuple[int, str]] = set()
    for i, a in enumerate(ajustes):
        if a.ibge not in ids:
            erros.append(f"ajuste {i}: ente {a.ibge} não existe na base")
        for cat in [a.categoria, a.categoria_destino]:
            if cat is not None and cat not in etapas:
                erros.append(f"ajuste {i}: categoria inexistente '{cat}'")
        chave = (a.ibge, a.categoria)
        if a.operacao == "definir":
            if chave in definidos and definidos[chave] != a.valor:
                erros.append(f"ajuste {i}: valores conflitantes para {a.ibge}/{a.categoria}")
            definidos[chave] = a.valor
        else:
            outras_ops.add(chave)
            if a.operacao == "converter":
                outras_ops.add((a.ibge, a.categoria_destino))
    # 'definir' combinado com outra operação na mesma célula dependeria da ordem de entrada.
    for chave in sorted(set(definidos) & outras_ops):
        erros.append(f"{chave[0]}/{chave[1]}: 'definir' não pode ser combinado com outras operações na mesma categoria")
    if erros:
        raise ErroCenario("; ".join(erros))


def aplicar_ajustes(matriculas: pd.DataFrame, ajustes: list[Ajuste], base: Base) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Retorna (cópia ajustada das matrículas, tabela de ajustes normalizada).
    A base original nunca é modificada. A ordem canônica (definir → acrescentar → converter)
    torna o resultado independente da ordem de entrada.
    """
    validar_ajustes(ajustes, base)
    mat = matriculas.copy()
    pos = pd.Series(mat.index, index=mat["ibge"].values)
    ordenados = sorted(ajustes, key=lambda a: (_ORDEM_OPERACAO[a.operacao], a.ibge, a.categoria,
                                                a.categoria_destino or "", a.valor))
    registros = []
    for a in ordenados:
        linha = pos[a.ibge]
        antes = float(matriculas.at[linha, a.categoria])
        if a.operacao == "definir":
            mat.at[linha, a.categoria] = a.valor
            delta_novas, convertidas = a.valor - antes, 0.0
        elif a.operacao == "acrescentar":
            mat.at[linha, a.categoria] = mat.at[linha, a.categoria] + a.valor
            delta_novas, convertidas = a.valor, 0.0
        else:
            mat.at[linha, a.categoria] = mat.at[linha, a.categoria] - a.valor
            mat.at[linha, a.categoria_destino] = mat.at[linha, a.categoria_destino] + a.valor
            delta_novas, convertidas = 0.0, a.valor
        registros.append({
            "ibge": a.ibge, "operacao": a.operacao, "categoria": a.categoria,
            "categoria_destino": a.categoria_destino, "valor_informado": a.valor,
            "valor_original": antes, "variacao_total": delta_novas, "convertidas": convertidas,
        })

    negativos = []
    for (ibge, cat) in {(a.ibge, c) for a in ajustes for c in [a.categoria, a.categoria_destino] if c}:
        v = mat.at[pos[ibge], cat]
        if v < 0:
            negativos.append(f"{ibge}/{cat} = {v:g}")
    if negativos:
        raise ErroCenario("ajustes resultariam em matrículas negativas: " + "; ".join(sorted(negativos)))

    tabela = pd.DataFrame(registros, columns=[
        "ibge", "operacao", "categoria", "categoria_destino", "valor_informado",
        "valor_original", "variacao_total", "convertidas"])
    if len(tabela):
        tabela = tabela.merge(base.entes[["ibge", "uf", "nome", "tipo_rede"]], on="ibge", how="left")
        final = [mat.at[pos[r.ibge], r.categoria] for r in tabela.itertuples()]
        tabela["valor_final_categoria"] = final
    return mat, tabela


def resumir_ajustes(tabela: pd.DataFrame) -> dict:
    if len(tabela) == 0:
        return {"quantidade": 0, "redes_alteradas": 0, "matriculas_acrescidas": 0.0,
                "matriculas_reduzidas": 0.0, "variacao_liquida": 0.0, "matriculas_convertidas": 0.0}
    var = tabela["variacao_total"]
    return {
        "quantidade": int(len(tabela)),
        "redes_alteradas": int(tabela["ibge"].nunique()),
        "matriculas_acrescidas": float(var[var > 0].sum()),
        "matriculas_reduzidas": float(abs(var[var < 0].sum())),
        "variacao_liquida": float(var.sum()),
        "matriculas_convertidas": float(tabela["convertidas"].sum()),
    }


# ---------------------------------------------------------------------------
# Parâmetros e receita
# ---------------------------------------------------------------------------

def resolver_parametros(parametros: ParametrosSimulacao, base: Base) -> dict:
    ref = base.parametros_referencia
    efetivos = {}
    for campo in ["complementacao_vaaf", "complementacao_vaat", "complementacao_vaar",
                  "max_nse", "min_nse", "max_nf", "min_nf"]:
        valor = getattr(parametros, campo)
        if valor is None:
            if campo not in ref:
                raise ErroCenario(f"parâmetro {campo} não informado e sem valor de referência na base")
            valor = ref[campo]
        efetivos[campo] = float(valor)
    for par in [("min_nse", "max_nse"), ("min_nf", "max_nf")]:
        if efetivos[par[0]] > efetivos[par[1]]:
            raise ErroCenario(f"{par[0]} maior que {par[1]}")
    n = len(base.pesos)
    for campo in ["pesos_vaaf", "pesos_vaat"]:
        valor = getattr(parametros, campo)
        if valor is not None and len(valor) != n:
            raise ErroCenario(f"{campo} deve ter {n} valores (recebidos {len(valor)})")
        efetivos[campo] = list(valor) if valor is not None else None
    return efetivos


def _pesos(base: Base, efetivos: dict) -> pd.DataFrame:
    p = base.pesos.copy()
    if efetivos["pesos_vaaf"] is not None:
        p["peso_vaaf"] = efetivos["pesos_vaaf"]
    if efetivos["pesos_vaat"] is not None:
        p["peso_vaat"] = efetivos["pesos_vaat"]
    return p


def aplicar_receita(complementar: pd.DataFrame, efetivos: dict, receita: HipoteseReceita) -> tuple[pd.DataFrame, dict]:
    """Aplica a taxa apenas às rubricas aprovadas. Retorna cópias; nunca altera a base."""
    comp = complementar.copy()
    par = dict(efetivos)
    fator = 1.0 + receita.taxa
    for rubrica in receita.rubricas:
        comp[rubrica] = comp[rubrica] * fator
    if receita.complementacoes == "acompanham_taxa":
        for campo in ["complementacao_vaaf", "complementacao_vaat", "complementacao_vaar"]:
            par[campo] = par[campo] * fator
    return comp, par


def _executar(mat: pd.DataFrame, comp: pd.DataFrame, pesos: pd.DataFrame, par: dict,
              modo_ponderador: str) -> pd.DataFrame:
    return simula_fundeb(
        dados_matriculas=mat,
        dados_complementar=comp,
        dados_peso=pesos,
        complementacao_vaaf=par["complementacao_vaaf"],
        complementacao_vaat=par["complementacao_vaat"],
        complementacao_vaar=par["complementacao_vaar"],
        max_nse=par["max_nse"],
        min_nse=par["min_nse"],
        max_nf=par["max_nf"],
        min_nf=par["min_nf"],
        modo_ponderador=modo_ponderador,
    )


def _total_matriculas(mat: pd.DataFrame, base: Base) -> pd.DataFrame:
    """Total de matrículas sem ponderação por ente (guardado no lugar da tabela completa)."""
    return pd.DataFrame({"ibge": mat["ibge"].values, "matriculas_total": mat[base.etapas].sum(axis=1).values})


def _validacao_dict(sim: pd.DataFrame, comp: pd.DataFrame) -> dict:
    v = validar_interno(sim, comp)
    return {"valido": v.valido, "erros": v.erros, "avisos": v.avisos, "n_checagens": len(v.checagens)}


def executar_cenario(req: CenarioRequest, base: Base) -> ResultadoCenario:
    ano_base = base.ano_exercicio
    if req.ano_exercicio is not None and req.ano_exercicio != ano_base:
        raise ErroCenario(
            f"exercício solicitado ({req.ano_exercicio}) difere do exercício da base "
            f"{base.base_id} ({ano_base if ano_base is not None else 'não identificado'})"
        )
    efetivos = resolver_parametros(req.parametros, base)
    modo = base.modo_ponderador
    pesos = _pesos(base, efetivos)
    mat_b, tabela_ajustes = aplicar_ajustes(base.matriculas, req.ajustes, base)

    matriculas = {"A": _total_matriculas(base.matriculas, base), "B": _total_matriculas(mat_b, base)}
    resultados = {
        "A": _executar(base.matriculas, base.complementar, pesos, efetivos, modo),
        "B": _executar(mat_b, base.complementar, pesos, efetivos, modo),
    }
    validacoes = {k: _validacao_dict(v, base.complementar) for k, v in resultados.items()}

    receita = req.receita
    if receita.tipo == "crescimento":
        comp_c, par_c = aplicar_receita(base.complementar, efetivos, receita)
        matriculas.update({"C": matriculas["A"], "D": matriculas["B"]})
        resultados["C"] = _executar(base.matriculas, comp_c, pesos, par_c, modo)
        resultados["D"] = _executar(mat_b, comp_c, pesos, par_c, modo)
        validacoes["C"] = _validacao_dict(resultados["C"], comp_c)
        validacoes["D"] = _validacao_dict(resultados["D"], comp_c)

    return ResultadoCenario(
        cenario_id=uuid.uuid4().hex,
        criado_em=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        base=base.identificacao(),
        versao_motor=VERSAO_MOTOR,
        requisicao=req.model_dump(),
        parametros_efetivos=efetivos,
        receita=receita.model_dump(),
        ajustes=tabela_ajustes,
        resumo_ajustes=resumir_ajustes(tabela_ajustes),
        matriculas_total=matriculas,
        resultados=resultados,
        validacoes=validacoes,
        entes=base.entes.copy(),
        grupos=base.manifesto.get("grupos", {}),
    )


# ---------------------------------------------------------------------------
# Armazenamento mínimo (em memória, retenção limitada)
# ---------------------------------------------------------------------------

class RepositorioCenarios:
    """Guarda os últimos resultados calculados para consulta e exportação. Não persiste entre reinícios."""

    def __init__(self, capacidade: int = 30):
        self.capacidade = capacidade
        self._itens: OrderedDict[str, ResultadoCenario] = OrderedDict()
        self._lock = threading.Lock()

    def guardar(self, resultado: ResultadoCenario) -> None:
        with self._lock:
            self._itens[resultado.cenario_id] = resultado
            while len(self._itens) > self.capacidade:
                self._itens.popitem(last=False)

    def obter(self, cenario_id: str) -> ResultadoCenario | None:
        with self._lock:
            return self._itens.get(cenario_id)


repositorio = RepositorioCenarios()
