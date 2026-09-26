from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import numpy as np

from schemas.cenarios import AjusteMatricula
from simulador import simula_fundeb
from validacao import validar_interno
from .comparacao import METRICAS, comparar, registros, selecionar_ids, totais

AVISO = ("Os resultados representam cenários hipotéticos condicionados aos dados, parâmetros e regras "
         "informados. Não constituem previsão de repasses futuros.")
NOTA_MATRICULAS = ("Matrículas representam a soma das categorias informadas na base, não alunos únicos. "
                   "Categorias de AEE e outras classificações podem se sobrepor.")


def arredondar_contagem(valor):
    return int(Decimal(str(valor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def versao_motor():
    root = Path(__file__).resolve().parents[1]
    arquivos = [root / "simulador.py", root / "validacao.py"]
    for pasta in ("services", "schemas"):
        arquivos += sorted((root / pasta).glob("*.py"))
    return sha256(b"".join(p.name.encode() + p.read_bytes() for p in arquivos)).hexdigest()


def aplicar_ajustes(base, ajustes):
    mat = base.tabelas["matriculas"].copy(deep=True).set_index("ibge")
    usados, log = set(), []
    for ajuste in sorted(ajustes, key=lambda a: (a.ibge, a.etapa)):
        if ajuste.ibge not in mat.index or ajuste.etapa not in base.etapas:
            raise ValueError("Rede ou categoria de matrícula desconhecida.")
        campos = [ajuste.etapa]
        if ajuste.operacao == "converter":
            if ajuste.destino not in base.etapas:
                raise ValueError("Categoria de destino desconhecida.")
            campos.append(ajuste.destino)
        celulas = {(ajuste.ibge, c) for c in campos}
        if usados & celulas:
            raise ValueError("Há ajustes conflitantes para a mesma rede e categoria.")
        usados |= celulas
        antes = {c: float(mat.at[ajuste.ibge, c]) for c in campos}
        atual = antes[ajuste.etapa]
        valor = ajuste.valor
        if ajuste.operacao == "definir":
            novo = valor
        elif ajuste.operacao == "adicionar":
            novo = atual + valor
        elif ajuste.operacao == "percentual":
            incremento = arredondar_contagem(Decimal(str(atual)) * Decimal(str(valor)) / 100)
            novo = atual + incremento
        else:
            if valor > atual:
                raise ValueError(f"Conversão de {ajuste.ibge}: quantidade superior à categoria de origem.")
            novo = atual - valor
            mat.at[ajuste.ibge, ajuste.destino] += valor
        if novo > 1e9:
            raise ValueError("Quantidade final acima do limite de matrículas por categoria.")
        mat.at[ajuste.ibge, ajuste.etapa] = novo
        depois = {c: float(mat.at[ajuste.ibge, c]) for c in campos}
        log.append({**ajuste.model_dump(), "antes": antes, "depois": depois,
                    "delta_total": sum(depois.values()) - sum(antes.values()),
                    "arredondamento": "Incremento percentual arredondado à unidade, metade para cima."})
    return mat.reset_index(), log


def resolver_parametros(base, request):
    p = deepcopy(base.meta["parametros"])
    p.update(request.parametros.model_dump(exclude_none=True, exclude={"pesos_vaaf", "pesos_vaat"}))
    p.pop("pesos_vaaf", None)
    p.pop("pesos_vaat", None)
    if p["min_nse"] > p["max_nse"] or p["min_nf"] > p["max_nf"]:
        raise ValueError("Mínimos NSE/NF não podem ser maiores que os máximos.")
    pesos = base.tabelas["pesos"].copy(deep=True).set_index("etapa")
    for modalidade in ("vaaf", "vaat"):
        substituicoes = getattr(request.parametros, f"pesos_{modalidade}")
        if not set(substituicoes) <= set(pesos.index):
            raise ValueError("Ponderação informada para categoria desconhecida.")
        for etapa, valor in substituicoes.items():
            pesos.at[etapa, f"peso_{modalidade}"] = valor
    return p, pesos.reset_index()


def fatores_amazonicos(base, habilitado):
    if not habilitado:
        return None
    regra = base.meta.get("amazonico", {})
    ano = base.meta.get("ano_exercicio")
    if regra.get("status") != "validado" or not regra.get("norma") or not regra.get("responsavel_validacao"):
        raise ValueError("Fator amazônico depende de norma e especificação validadas para esta base.")
    if regra.get("incidencia") != "matriculas_ponderadas_por_ente":
        raise ValueError("Incidência do fator não suportada; requer implementação da regra específica.")
    if ano is None or not regra.get("ano_inicio", 9999) <= ano <= regra.get("ano_fim", ano):
        raise ValueError("Fator fora da vigência ou exercício não identificado.")
    fatores = base.tabelas.get("fatores_amazonicos")
    if fatores is None or fatores.ibge.duplicated().any() or set(fatores.ibge) != set(base.tabelas["entes"].ibge):
        raise ValueError("Tabela de fatores deve cobrir todos os entes, com fator 1 para não abrangidos.")
    return fatores[["ibge", "fator_vaaf", "fator_vaat"]].copy()


def validar_resultado(sim, comp, parametros):
    v = validar_interno(sim, comp)
    for modalidade in ("vaaf", "vaat", "vaar"):
        distribuido = sim[f"complemento_{modalidade}"].sum()
        esperado = parametros[f"complementacao_{modalidade}"]
        if not np.isclose(distribuido, esperado, atol=0.01, rtol=1e-10):
            v.erros.append(f"Total {modalidade.upper()} distribuído difere do parâmetro do cenário.")
        else:
            v.checagens.append(f"Total {modalidade.upper()} distribuído confere com o parâmetro.")
    if len(sim) != len(comp) or set(sim.ibge) != set(comp.ibge):
        v.erros.append("Cobertura de redes mudou durante o cálculo.")
    financeiros = [c for c in sim if c.startswith("recursos_") or c.startswith("complemento_")]
    if not np.isfinite(sim[financeiros].to_numpy()).all() or (sim[financeiros] < -0.01).any().any():
        v.erros.append("Resultados financeiros negativos ou não finitos.")
    mask = sim.matriculas_vaat > 0
    if not np.allclose(sim.loc[mask, "vaat_final"], sim.loc[mask, "recursos_vaat_final"] / sim.loc[mask, "matriculas_vaat"]):
        v.erros.append("VAAT inconsistente com seu numerador e denominador.")
    v.valido = not v.erros
    if not v.valido:
        raise ValueError("Validação do cenário falhou: " + "; ".join(v.erros))
    return {"valido": v.valido, "erros": v.erros, "avisos": v.avisos, "checagens": v.checagens}


def publico(resultado):
    return {k: v for k, v in resultado.items() if k != "dados"}


class CenarioService:
    def __init__(self, bases, store):
        self.bases, self.store = bases, store

    def executar(self, request, persistir=True, base=None):
        base = base or self.bases.obter(request.base_id)
        if request.ano_exercicio is not None and request.ano_exercicio != base.meta.get("ano_exercicio"):
            raise ValueError("Exercício solicitado não corresponde ao exercício identificado da base.")
        mat_b, ajustes = aplicar_ajustes(base, request.ajustes)
        ids, universo, denominador = selecionar_ids(base, request.recorte, request.ajustes)
        parametros, pesos = resolver_parametros(base, request)
        fatores = fatores_amazonicos(base, request.fator_amazonico)
        receita = request.receita
        permitidas = {"recursos_vaaf", "recursos_vaat"} if base.meta["modo_vaat"] == "fixo" else {"recursos_vaaf", "outras_receitas_vaat"}
        if not set(receita.rubricas) <= permitidas:
            raise ValueError("Rubricas de crescimento incompatíveis com a composição VAAT desta base.")
        comp_a = base.tabelas["complementar"].copy(deep=True)
        comp_c = comp_a.copy(deep=True)
        taxa = receita.taxa()
        comp_c[receita.rubricas] *= 1 + taxa / 100
        parametros_c = deepcopy(parametros)
        if receita.complementacoes == "proporcionais":
            for tipo in ("vaaf", "vaat", "vaar"):
                parametros_c[f"complementacao_{tipo}"] *= 1 + taxa / 100
        resultados, validacoes = {}, {}
        definicoes = [("A", base.tabelas["matriculas"], comp_a, parametros),
                      ("B", mat_b, comp_a, parametros),
                      ("C", base.tabelas["matriculas"], comp_c, parametros_c),
                      ("D", mat_b, comp_c, parametros_c)]
        for nome, mat, comp, p in definicoes:
            sim = simula_fundeb(mat, comp, pesos, **p, modo_vaat=base.meta["modo_vaat"],
                                fatores_matriculas=fatores, arredondar=False)
            validacoes[nome] = validar_resultado(sim, comp, p)
            brutas = mat.set_index("ibge")[base.etapas].sum(axis=1)
            ept = mat.set_index("ibge")[base.meta.get("etapas_ept", [])].sum(axis=1)
            sim["matriculas_brutas"] = sim.ibge.map(brutas)
            sim["matriculas_ept"] = sim.ibge.map(ept)
            sim = sim.merge(base.tabelas["entes"][["ibge", "tipo"]], on="ibge", validate="one_to_one")
            resultados[nome] = sim
        comparativos = {f"{b}-{a}": comparar(resultados[a], resultados[b], ids, universo)
                       for a, b in (("A", "B"), ("A", "C"), ("A", "D"), ("C", "D"))}
        avisos = list(base.meta.get("pendencias", []))
        if base.meta["status"] != "homologada":
            avisos.insert(0, "Base não homologada: resultados exploratórios, sem validação oficial do exercício.")
        if base.meta["modo_vaat"] == "fixo":
            avisos.append("Modelo legado: receita VAAT do snapshot permanece independente da redistribuição VAAF. "
                          "Crescimento só afeta as rubricas selecionadas; composição VAAT precisa de validação.")
        resultado = {"id": uuid4().hex, "tipo": "cenario", "nome": request.nome,
                     "criado_em": datetime.now(timezone.utc).isoformat(), "aviso": AVISO,
                     "nota_matriculas": NOTA_MATRICULAS, "avisos": avisos,
                     "entrada": request.model_dump(), "base": base.resumo(), "motor_sha256": versao_motor(),
                     "parametros_efetivos": {"A_B": parametros, "C_D": parametros_c,
                                              "taxa_receita_percentual": taxa, "pesos": registros(pesos)},
                     "recorte": {**request.recorte.model_dump(), "redes": len(ids), "denominador": denominador},
                     "ajustes": ajustes, "metricas": METRICAS, "comparativos": comparativos,
                     "resumos_nacionais": {k: totais(v) for k, v in resultados.items()},
                     "validacao": validacoes, "dados": {k: registros(v) for k, v in resultados.items()}}
        if persistir:
            self.store.salvar(resultado)
        return resultado

    def trajetoria(self, request):
        base = self.bases.obter(request.cenario.base_id)
        if request.etapa not in base.meta.get("etapas_ept", []):
            raise ValueError("Categoria não pertence ao recorte EPT declarado na base.")
        mat = base.tabelas["matriculas"].set_index("ibge")
        if not set(request.entes) <= set(mat.index):
            raise ValueError("Trajetória contém rede desconhecida.")
        if base.meta.get("ano_exercicio") is not None and request.ano_inicial != base.meta["ano_exercicio"]:
            raise ValueError("Ano inicial deve coincidir com o exercício da base.")
        prazo = request.ano_final - request.ano_inicial
        taxa_anual = request.cenario.receita.taxa()
        series = []
        for passo in range(prazo + 1):
            c = request.cenario.model_copy(deep=True)
            ajustes = []
            for ibge in request.entes:
                valor = arredondar_contagem(Decimal(str(mat.at[ibge, request.etapa])) *
                                           Decimal(str(request.aumento_total_percentual)) * passo / prazo / 100)
                ajustes.append(AjusteMatricula(ibge=ibge, etapa=request.origem if request.operacao == "converter" else request.etapa,
                                               operacao=request.operacao, destino=request.etapa if request.operacao == "converter" else None,
                                               valor=valor))
            c.ajustes = ajustes
            c.receita = c.receita.model_copy(update={"metodo": "informada", "pib": [],
                "taxa_percentual": 100*((1+taxa_anual/100)**passo-1)})
            # Validar limites após a composição anual, pois model_copy não revalida.
            c = type(c).model_validate(c.model_dump())
            resultado = self.executar(c, persistir=False, base=base)
            series.append({"ano": request.ano_inicial + passo, "incremento_ept": sum(a.valor for a in ajustes),
                           "taxa_receita_acumulada": c.receita.taxa_percentual,
                           "comparativos": resultado["comparativos"], "resumos_nacionais": resultado["resumos_nacionais"]})
        retorno = {"id": uuid4().hex, "tipo": "trajetoria", "nome": "Trajetória EPT — " + request.cenario.nome,
                   "criado_em": datetime.now(timezone.utc).isoformat(), "aviso": AVISO, "entrada": request.model_dump(),
                   "nota_matriculas": NOTA_MATRICULAS, "base": base.resumo(), "motor_sha256": versao_motor(),
                   "avisos": resultado["avisos"] + ["Trajetória linear de EPT; receita composta anualmente. Pesos, elegibilidade e regras congelados.",
                       "Ano inicial é hipótese temporal do usuário quando o exercício da base não está identificado."],
                   "recorte": resultado["recorte"], "metricas": METRICAS, "series": series}
        self.store.salvar(retorno)
        return retorno
