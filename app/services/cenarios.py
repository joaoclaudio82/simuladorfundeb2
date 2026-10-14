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

from app.schemas.cenarios import AVISO_METODOLOGICO, Ajuste, CenarioRequest, HipoteseReceita, ParametrosSimulacao
from app.services.bases import Base
from app.domain.calculo.motor import simula_fundeb
from app.domain.calculo.validacao import validar_interno

_RAIZ = str(__import__("pathlib").Path(__file__).resolve().parents[2])


def _versao_motor() -> str:
    h = hashlib.sha256()
    for nome in ["app/domain/calculo/motor.py", "app/services/cenarios.py"]:
        with open(os.path.join(_RAIZ, nome), "rb") as f:
            h.update(f.read())
    return "sha256:" + h.hexdigest()[:12]


VERSAO_MOTOR = _versao_motor()

NOMES_CENARIOS = {
    "A": "Cenário A — Referência",
    "B": "Cenário B — Simulação 1",
    "C": "Cenário C — Simulação 2",
    "D": "Cenário D — Simulação 3",
}

EXPLICACAO_CENARIO_REFERENCIA = "Matrículas originais da base selecionada."
EXPLICACAO_CENARIO_SIMULACAO = "Ajustes próprios de matrículas, mantendo a mesma receita da referência."

DESCRICAO_CENARIOS_INDEPENDENTES = {
    "A": f"{NOMES_CENARIOS['A']} — {EXPLICACAO_CENARIO_REFERENCIA}",
    "B": f"{NOMES_CENARIOS['B']} — {EXPLICACAO_CENARIO_SIMULACAO}",
    "C": f"{NOMES_CENARIOS['C']} — {EXPLICACAO_CENARIO_SIMULACAO}",
    "D": f"{NOMES_CENARIOS['D']} — {EXPLICACAO_CENARIO_SIMULACAO}",
}

DESCRICAO_CENARIOS_LEGADO = {
    "A": "Matrículas originais, receita original",
    "B": "Matrículas alteradas, receita original",
    "C": "Matrículas originais, receita ampliada",
    "D": "Matrículas alteradas, receita ampliada",
}

DESCRICAO_CENARIOS = DESCRICAO_CENARIOS_INDEPENDENTES


def eh_requisicao_legado_receita(requisicao: dict | None, receita: dict | None = None) -> bool:
    """Identifica se o cenário pertence ao modelo histórico de crescimento de receita."""
    req = requisicao or {}
    modo = req.get("modo_cenarios")
    if modo == "legado_receita":
        return True
    if modo == "matriculas_independentes":
        return False
    rec = receita if receita is not None else (req.get("receita") or {})
    tipo = rec.get("tipo")
    if tipo is not None and tipo != "constante":
        return True
    if float(rec.get("taxa_percentual") or 0.0) != 0.0:
        return True
    return False


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

    @property
    def eh_legado_receita(self) -> bool:
        return eh_requisicao_legado_receita(self.requisicao, self.receita)

    @property
    def modo_cenarios(self) -> str:
        return "legado_receita" if self.eh_legado_receita else "matriculas_independentes"

    def descricoes_cenarios(self) -> dict[str, str]:
        mapa = DESCRICAO_CENARIOS_LEGADO if self.eh_legado_receita else DESCRICAO_CENARIOS_INDEPENDENTES
        return {k: mapa.get(k, f"Cenário {k}") for k in self.cenarios}

    def nomes_cenarios(self) -> dict[str, str]:
        if self.eh_legado_receita:
            return {k: f"Cenário {k} ({DESCRICAO_CENARIOS_LEGADO.get(k, k)})" for k in self.cenarios}
        return {k: NOMES_CENARIOS.get(k, f"Cenário {k}") for k in self.cenarios}

    def metadados(self) -> dict:
        return {
            "cenario_id": self.cenario_id,
            "criado_em": self.criado_em,
            "base": self.base,
            "versao_motor": self.versao_motor,
            "modo_cenarios": self.modo_cenarios,
            "parametros": self.parametros_efetivos,
            "receita": self.receita,
            "cenarios": self.descricoes_cenarios(),
            "nomes_cenarios": self.nomes_cenarios(),
            "resumo_ajustes": self.resumo_ajustes,
            "validacoes": self.validacoes,
            "aviso": self.aviso,
        }


# ---------------------------------------------------------------------------
# Ajustes de matrículas
# ---------------------------------------------------------------------------

_ORDEM_OPERACAO = {"definir": 0, "acrescentar": 1, "converter": 2}
_COLUNAS_TABELA_AJUSTES = [
    "cenario", "ibge", "operacao", "categoria", "categoria_destino",
    "valor_informado", "valor_original", "variacao_total", "convertidas",
]


def validar_ajustes(ajustes: list[Ajuste], base: Base) -> None:
    etapas = set(base.etapas)
    ids = set(base.matriculas["ibge"])
    erros = []
    definidos: dict[tuple[str, int, str], float] = {}
    outras_ops: set[tuple[str, int, str]] = set()
    for i, a in enumerate(ajustes):
        cenario = getattr(a, "cenario", "B") or "B"
        if a.ibge not in ids:
            erros.append(f"ajuste {i}: ente {a.ibge} não existe na base")
        for cat in [a.categoria, a.categoria_destino]:
            if cat is not None and cat not in etapas:
                erros.append(f"ajuste {i}: categoria inexistente '{cat}'")
        chave = (cenario, a.ibge, a.categoria)
        if a.operacao == "definir":
            if chave in definidos and definidos[chave] != a.valor:
                erros.append(f"ajuste {i}: valores conflitantes para {a.ibge}/{a.categoria} no cenário {cenario}")
            definidos[chave] = a.valor
        else:
            outras_ops.add(chave)
            if a.operacao == "converter":
                outras_ops.add((cenario, a.ibge, a.categoria_destino))
    # 'definir' combinado com outra operação na mesma célula do mesmo cenário dependeria da ordem de entrada.
    for chave in sorted(set(definidos) & outras_ops):
        erros.append(f"cenário {chave[0]} ({chave[1]}/{chave[2]}): 'definir' não pode ser combinado com outras operações na mesma categoria")
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
    ordenados = sorted(
        ajustes,
        key=lambda a: (
            getattr(a, "cenario", "B") or "B",
            _ORDEM_OPERACAO[a.operacao],
            a.ibge,
            a.categoria,
            a.categoria_destino or "",
            a.valor,
        ),
    )
    registros = []
    for a in ordenados:
        cenario = getattr(a, "cenario", "B") or "B"
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
            "cenario": cenario, "ibge": a.ibge, "operacao": a.operacao, "categoria": a.categoria,
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

    tabela = pd.DataFrame(registros, columns=_COLUNAS_TABELA_AJUSTES)
    if len(tabela):
        tabela = tabela.merge(base.entes[["ibge", "uf", "nome", "tipo_rede"]], on="ibge", how="left")
        final = [mat.at[pos[r.ibge], r.categoria] for r in tabela.itertuples()]
        tabela["valor_final_categoria"] = final
    return mat, tabela


def _resumo_simples(tabela: pd.DataFrame) -> dict:
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


def resumir_ajustes(tabela: pd.DataFrame) -> dict:
    resumo = _resumo_simples(tabela)
    if "cenario" in tabela.columns and len(tabela) > 0:
        resumo["por_cenario"] = {
            cen: _resumo_simples(tabela.loc[tabela["cenario"] == cen])
            for cen in sorted(tabela["cenario"].unique())
        }
    return resumo


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
    receita = req.receita
    req_dump = req.model_dump()

    if eh_requisicao_legado_receita(req_dump, receita.model_dump()):
        mat_b, tabela_ajustes = aplicar_ajustes(base.matriculas, req.ajustes, base)
        matriculas = {
            "A": _total_matriculas(base.matriculas, base),
            "B": _total_matriculas(mat_b, base),
        }
        resultados = {
            "A": _executar(base.matriculas, base.complementar, pesos, efetivos, modo),
            "B": _executar(mat_b, base.complementar, pesos, efetivos, modo),
        }
        validacoes = {k: _validacao_dict(v, base.complementar) for k, v in resultados.items()}

        if receita.tipo == "crescimento":
            comp_c, par_c = aplicar_receita(base.complementar, efetivos, receita)
            matriculas.update({"C": matriculas["A"], "D": matriculas["B"]})
            resultados["C"] = _executar(base.matriculas, comp_c, pesos, par_c, modo)
            resultados["D"] = _executar(mat_b, comp_c, pesos, par_c, modo)
            validacoes["C"] = _validacao_dict(resultados["C"], comp_c)
            validacoes["D"] = _validacao_dict(resultados["D"], comp_c)
        req_dump["modo_cenarios"] = "legado_receita"
    else:
        cenarios_sim = req.cenarios_simulacao()
        mapa_ajustes = req.mapa_ajustes_por_cenario()
        if req.cenarios_ativos is not None:
            for cen, lista in mapa_ajustes.items():
                if lista and cen not in cenarios_sim:
                    raise ErroCenario(
                        f"não é possível aplicar ajustes ao cenário {cen} porque ele foi excluído"
                    )

        matriculas = {"A": _total_matriculas(base.matriculas, base)}
        resultados = {"A": _executar(base.matriculas, base.complementar, pesos, efetivos, modo)}
        validacoes = {"A": _validacao_dict(resultados["A"], base.complementar)}
        tabelas_ajustes = []

        for cen in cenarios_sim:
            ajustes_cen = [
                aj.model_copy(update={"cenario": cen}) for aj in mapa_ajustes.get(cen, [])
            ]
            # Cada simulação usa uma cópia das matrículas originais e aplica somente seus ajustes.
            mat_cen, tab_cen = aplicar_ajustes(base.matriculas, ajustes_cen, base)
            matriculas[cen] = _total_matriculas(mat_cen, base)
            resultados[cen] = _executar(mat_cen, base.complementar, pesos, efetivos, modo)
            validacoes[cen] = _validacao_dict(resultados[cen], base.complementar)
            if len(tab_cen):
                tabelas_ajustes.append(tab_cen)

        tabela_ajustes = (
            pd.concat(tabelas_ajustes, ignore_index=True)
            if tabelas_ajustes
            else pd.DataFrame(columns=_COLUNAS_TABELA_AJUSTES)
        )
        if req.usa_cenarios_independentes():
            req_dump["modo_cenarios"] = "matriculas_independentes"
            req_dump["cenarios_ativos"] = cenarios_sim

    return ResultadoCenario(
        cenario_id=uuid.uuid4().hex,
        criado_em=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        base=base.identificacao(),
        versao_motor=VERSAO_MOTOR,
        requisicao=req_dump,
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
# Persistência durável. A capacidade antiga permanece aceita por compatibilidade.
# ---------------------------------------------------------------------------
from app.repositories.scenarios import RepositorioCenarios

repositorio = RepositorioCenarios()
