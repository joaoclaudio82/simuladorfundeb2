"""Consultas que o chat pode pedir. Os argumentos são validados aqui."""

from __future__ import annotations

import difflib
import json
import unicodedata

from sqlalchemy import func, select

from app.auth.models import Role, UserRecord
from app.db.schema import (
    base_aliases,
    base_sources,
    base_versions,
    categories,
    entities,
    financial_inputs,
    scenario_results,
    scenarios,
)
from app.db.session import get_engine
from app.repositories.chat import buscar_trechos
from app.services.bases import PERIODOS_EXIBICAO

CHAVES = (
    "matriculas_total",
    "matriculas_vaaf",
    "matriculas_vaat",
    "recursos_fundeb",
    "complemento_vaaf",
    "complemento_vaat",
    "complemento_vaar",
    "complemento_uniao",
    "vaaf_final",
    "vaat_final",
    "recursos_vaaf",
    "recursos_vaat",
    "nse",
    "nf",
    "drec",
)
PROIBIDOS = {"cpf", "senha", "password", "password_hash", "secret", "token", "api_key", "owner_cpf"}


def limpar(valor):
    if isinstance(valor, dict):
        return {k: limpar(v) for k, v in valor.items() if k.lower() not in PROIBIDOS}
    if isinstance(valor, list):
        return [limpar(v) for v in valor[:40]]
    if isinstance(valor, float):
        return round(valor, 4)
    return valor


def _numeros(dados: dict) -> dict:
    saida = {}
    for chave in CHAVES:
        valor = dados.get(chave)
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            saida[chave] = round(float(valor), 4)
    return saida


def _inteiro(valor):
    if valor is None or valor == "":
        return None
    return int(valor)


def _bases_ativas(engine=None) -> list[dict]:
    motor = engine or get_engine()
    with motor.connect() as conn:
        rows = conn.execute(
            select(
                base_versions.c.base_id,
                base_versions.c.year,
                base_versions.c.version_id,
                base_versions.c.manifest,
            ).join(base_aliases, base_aliases.c.version_id == base_versions.c.version_id)
        ).mappings()
        linhas = list(rows)
    saida = []
    for row in linhas:
        try:
            manifesto = json.loads(row["manifest"] or "{}")
        except json.JSONDecodeError:
            manifesto = {}
        if not isinstance(manifesto, dict):
            manifesto = {}
        saida.append({
            "base_id": manifesto.get("base_id") or row["base_id"],
            "ano_exercicio": manifesto.get("ano_exercicio", row["year"]),
            "situacao": manifesto.get("situacao"),
            "homologada": bool(manifesto.get("homologada")),
            "periodo_exibicao": PERIODOS_EXIBICAO.get(manifesto.get("base_id") or row["base_id"]),
            "version_id": row["version_id"],
        })
    return saida


def _base_escolhida(ano, base_id: str | None, *, engine=None) -> dict | None:
    try:
        ano = _inteiro(ano)
    except (TypeError, ValueError):
        return {"erro": "O exercício informado não é um número."}
    if base_id:
        achadas = [b for b in _bases_ativas(engine) if b["base_id"] == base_id]
    elif ano is not None:
        achadas = [b for b in _bases_ativas(engine) if b.get("ano_exercicio") == ano]
    else:
        return None
    if len(achadas) > 1:
        return {"erro": "ambiguo", "candidatos": [b["base_id"] for b in achadas]}
    return achadas[0] if achadas else None


def consultar_base(argumentos: dict, _usuario: UserRecord, *, engine=None) -> dict:
    base = _base_escolhida(argumentos.get("ano"), argumentos.get("base_id"), engine=engine)
    if not base or "version_id" not in base:
        return {
            "encontrado": False,
            "motivo": (base or {}).get("erro") or "Informe o exercício ou o identificador da base.",
            "candidatos": (base or {}).get("candidatos"),
        }
    versao = base["version_id"]
    motor = engine or get_engine()
    with motor.connect() as conn:
        entes = conn.execute(
            select(func.count()).select_from(entities).where(entities.c.version_id == versao)
        ).scalar()
        fontes = list(conn.execute(
            select(base_sources.c.path, base_sources.c.source_sha256).where(
                base_sources.c.version_id == versao
            )
        ).mappings())
        meta = conn.execute(
            select(base_versions.c.snapshot_sha256, base_versions.c.source_commit, base_versions.c.created_at).where(
                base_versions.c.version_id == versao
            )
        ).mappings().first()
    return limpar({
        "encontrado": True,
        "tipo_dado": "oficial_importado",
        "base_id": base["base_id"],
        "ano_exercicio": base.get("ano_exercicio"),
        "situacao": base.get("situacao"),
        "homologada": base.get("homologada"),
        "periodo_exibicao": base.get("periodo_exibicao"),
        "version_id": versao,
        "snapshot_sha256": meta["snapshot_sha256"] if meta else None,
        "source_commit": meta["source_commit"] if meta else None,
        "criada_em": meta["created_at"] if meta else None,
        "quantidade_entes": entes,
        "fontes": [
            {"caminho": f["path"], "sha256": f["source_sha256"][:12]}
            for f in fontes
        ],
    })


_ROTULOS_TELA = (
    ("matriculas_vaaf", "Matrículas VAAF (ponderadas)", False),
    ("matriculas_vaat", "Matrículas VAAT (ponderadas)", False),
    ("vaaf_final", "VAAF por aluno", False),
    ("recursos_vaaf_final", "Recursos VAAF totais", True),
    ("complemento_vaaf", "Complementação VAAF", True),
    ("vaat_final", "VAAT por aluno", False),
    ("recursos_vaat_final", "Recursos VAAT totais", True),
    ("complemento_vaat", "Complementação VAAT", True),
    ("complemento_vaar", "Complementação VAAR", True),
    ("complemento_uniao", "Total Complementação da União", True),
    ("recursos_vaaf", "Receita da contribuição de estados e municípios ao Fundeb", True),
    ("recursos_fundeb", "Receita Total do Fundeb", True),
)


def _exibir_como_tela(valor: float, dinheiro: bool) -> str:
    if dinheiro:
        texto = f"{int(round(valor)):,}".replace(",", ".")
        return f"R$ {texto}"
    numero = round(float(valor), 2)
    inteiro, frac = f"{numero:.2f}".split(".")
    sinal = "-" if inteiro.startswith("-") else ""
    inteiro = f"{abs(int(inteiro)):,}".replace(",", ".")
    if frac == "00":
        return f"{sinal}{inteiro}"
    return f"{sinal}{inteiro},{frac}"


def _resultado_da_tela(ano, ibge: int, dataset) -> dict | None:
    if dataset is None:
        from app.ingestion.fundeb_dataset import carregar_dataset

        dataset = carregar_dataset(int(ano))
    tabela = getattr(dataset, "cenario_atual", None)
    if tabela is None or not len(tabela) or "ibge" not in getattr(tabela, "columns", []):
        return None
    linha = tabela.loc[tabela["ibge"] == int(ibge)]
    if linha.empty:
        return None
    registro = linha.iloc[0]
    indicadores = {}
    for chave, rotulo, dinheiro in _ROTULOS_TELA:
        if chave not in tabela.columns or registro.get(chave) is None:
            continue
        valor = float(registro[chave])
        indicadores[chave] = {
            "rotulo": rotulo,
            "valor": round(valor, 2),
            "exibicao": _exibir_como_tela(valor, dinheiro),
        }
    if not indicadores:
        return None
    return {
        "tipo_dado": "resultado_simulador",
        "sem_alteracao_de_matriculas": True,
        "indicadores": indicadores,
        "leitura": (
            "Estes são os números da tela municipal no botão Simular, sem alterar matrículas. "
            "Matrículas VAAF (ponderadas) é matriculas_vaaf. "
            "VAAF por aluno é vaaf_final. "
            "Recursos VAAF totais é recursos_vaaf_final. "
            "VAAT por aluno é vaat_final. Recursos VAAT totais é recursos_vaat_final. "
            "Complementação VAAT é complemento_vaat. "
            "valores_oficiais.recursos_vaaf é a receita de contribuição do ente e não é esse total."
        ),
    }


def consultar_municipio(argumentos: dict, _usuario: UserRecord, *, engine=None, dataset=None) -> dict:
    nome = (argumentos.get("nome") or argumentos.get("municipio") or "").strip()
    ano = argumentos.get("ano")
    if not nome or ano is None:
        return {"encontrado": False, "motivo": "Informe o município e o exercício."}
    motor = engine or get_engine()
    base = _base_escolhida(ano, argumentos.get("base_id"), engine=motor)
    if not base or "version_id" not in base:
        return {
            "encontrado": False,
            "motivo": (base or {}).get("erro") or f"Não há base para o exercício {ano}.",
            "candidatos": (base or {}).get("candidatos"),
        }
    versao = base["version_id"]
    seguro = nome.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with motor.connect() as conn:
        consulta = select(
            entities.c.ibge, entities.c.uf, entities.c.name, entities.c.network
        ).where(entities.c.version_id == versao)
        if argumentos.get("uf"):
            consulta = consulta.where(entities.c.uf == str(argumentos["uf"]).upper())
        if argumentos.get("ibge"):
            consulta = consulta.where(entities.c.ibge == int(argumentos["ibge"]))
        exatas = list(conn.execute(
            consulta.where(entities.c.name.ilike(seguro, escape="\\")).limit(8)
        ).mappings())
        parciais = [] if exatas else list(conn.execute(
            consulta.where(entities.c.name.ilike(f"%{seguro}%", escape="\\")).limit(8)
        ).mappings())
        linhas = exatas or parciais or _candidatos_sem_acento(conn, consulta, nome)
        if len(linhas) != 1:
            return {
                "encontrado": False,
                "motivo": "ambiguo" if len(linhas) > 1 else "nao_encontrado",
                "candidatos": [dict(l) for l in linhas],
                "ano_exercicio": ano,
                "base_id": base["base_id"],
            }
        ente = dict(linhas[0])
        financeiro = conn.execute(
            select(financial_inputs.c.values_json).where(
                financial_inputs.c.version_id == versao,
                financial_inputs.c.ibge == ente["ibge"],
            )
        ).scalar()
    valores = json.loads(financeiro) if financeiro else {}
    tela = None
    if dataset is not None or engine is None:
        try:
            tela = _resultado_da_tela(ano, ente["ibge"], dataset)
        except Exception:
            tela = None
    resposta = {
        "encontrado": True,
        "tipo_dado": "oficial_importado",
        "ano_exercicio": ano,
        "base_id": base["base_id"],
        "ente": ente,
        "valores_oficiais": _numeros(valores),
    }
    if base.get("periodo_exibicao"):
        resposta["periodo_exibicao"] = base["periodo_exibicao"]
    else:
        resposta["homologada"] = base.get("homologada")
        resposta["situacao"] = base.get("situacao")
    if tela:
        resposta["resultado_tela"] = tela
    return limpar(resposta)


def _cenario_visivel(conn, cenario_id: str, usuario: UserRecord):
    row = conn.execute(select(scenarios).where(scenarios.c.id == cenario_id)).mappings().first()
    if not row:
        return None
    if usuario.role != Role.admin and row["owner_cpf"] != usuario.cpf:
        return None
    return row


def _interpretar_cenarios_pedido(pedido: dict) -> tuple[str, dict[str, str]]:
    from app.services.cenarios import (
        DESCRICAO_CENARIOS_INDEPENDENTES,
        DESCRICAO_CENARIOS_LEGADO,
        eh_requisicao_legado_receita,
    )

    if eh_requisicao_legado_receita(pedido):
        return "legado_receita", dict(DESCRICAO_CENARIOS_LEGADO)
    return "matriculas_independentes", dict(DESCRICAO_CENARIOS_INDEPENDENTES)


def consultar_simulacao(argumentos: dict, usuario: UserRecord, *, engine=None) -> dict:
    cenario_id = (argumentos.get("cenario_id") or "").strip()
    if not cenario_id:
        return {"encontrado": False, "motivo": "Informe o identificador da simulação."}
    motor = engine or get_engine()
    with motor.connect() as conn:
        row = _cenario_visivel(conn, cenario_id, usuario)
        if not row:
            return {"encontrado": False, "motivo": "nao_encontrado"}
        consulta = select(
            scenario_results.c.variant, scenario_results.c.ibge, scenario_results.c.values_json
        ).where(scenario_results.c.scenario_id == cenario_id)
        if argumentos.get("ibge"):
            consulta = consulta.where(scenario_results.c.ibge == int(argumentos["ibge"]))
        linhas = list(conn.execute(consulta.limit(12)).mappings())
    pedido = json.loads(row["request_json"]) if row["request_json"] else {}
    modo_cenarios, descricoes = _interpretar_cenarios_pedido(pedido)
    variantes_presentes = sorted({l["variant"] for l in linhas})
    return limpar({
        "encontrado": True,
        "tipo_dado": "resultado_simulado",
        "cenario_id": cenario_id,
        "base_id": row["base_id"],
        "base_version": row["base_version"],
        "criado_em": row["created_at"],
        "modo_cenarios": modo_cenarios,
        "cenarios_descricao": {
            k: descricoes.get(k, f"Cenário {k}")
            for k in (variantes_presentes or list(descricoes.keys()))
        },
        "parametros": pedido,
        "resultados": [
            {
                "variante": l["variant"],
                "descricao_cenario": descricoes.get(l["variant"], f"Cenário {l['variant']}"),
                "ibge": l["ibge"],
                "valores": _numeros(json.loads(l["values_json"])),
            }
            for l in linhas
        ],
        "causa_demonstravel": False,
    })


def comparar_simulacoes(argumentos: dict, usuario: UserRecord, *, engine=None) -> dict:
    cenario_id = (argumentos.get("cenario_id") or "").strip()
    ibge = argumentos.get("ibge")
    variante_a = argumentos.get("variante_a") or "A"
    variante_b = argumentos.get("variante_b") or "B"
    if not cenario_id or ibge is None:
        return {
            "encontrado": False,
            "motivo": "Informe a simulação e o código IBGE da rede antes de comparar.",
        }
    motor = engine or get_engine()
    with motor.connect() as conn:
        row = _cenario_visivel(conn, cenario_id, usuario)
        if not row:
            return {"encontrado": False, "motivo": "nao_encontrado"}
        pares = {}
        for variante in (variante_a, variante_b):
            bruto = conn.execute(
                select(scenario_results.c.values_json).where(
                    scenario_results.c.scenario_id == cenario_id,
                    scenario_results.c.variant == variante,
                    scenario_results.c.ibge == int(ibge),
                )
            ).scalar()
            if bruto:
                pares[variante] = _numeros(json.loads(bruto))
    if len(pares) < 2:
        return {"encontrado": False, "motivo": "Uma das variantes não está gravada para essa rede."}
    pedido = json.loads(row["request_json"]) if row["request_json"] else {}
    modo_cenarios, descricoes = _interpretar_cenarios_pedido(pedido)
    diferencas = {}
    for chave in CHAVES:
        if chave in pares[variante_a] and chave in pares[variante_b]:
            diferencas[chave] = {
                variante_a: pares[variante_a][chave],
                variante_b: pares[variante_b][chave],
                "diferenca_observada": round(pares[variante_b][chave] - pares[variante_a][chave], 4),
            }
    return limpar({
        "encontrado": True,
        "tipo_dado": "resultado_simulado",
        "cenario_id": cenario_id,
        "base_id": row["base_id"],
        "base_version": row["base_version"],
        "modo_cenarios": modo_cenarios,
        "cenarios_comparados": {
            variante_a: descricoes.get(variante_a, f"Cenário {variante_a}"),
            variante_b: descricoes.get(variante_b, f"Cenário {variante_b}"),
        },
        "ibge": int(ibge),
        "diferencas": diferencas,
        "causa_demonstravel": False,
        "leitura": "A diferença foi calculada nos resultados gravados. Ela não demonstra sozinha a causa da mudança.",
    })


def _candidatos_sem_acento(conn, consulta, nome: str) -> list:
    alvo = _sem_acento(nome)
    if len(alvo) < 3:
        return []
    linhas = list(conn.execute(consulta).mappings())
    exatas = [linha for linha in linhas if _sem_acento(linha["name"]) == alvo]
    if exatas:
        return exatas[:8]
    contidas = [linha for linha in linhas if alvo in _sem_acento(linha["name"])]
    if contidas:
        return contidas[:8]
    compacto = _compacto(nome)
    if len(compacto) < 6:
        return []
    juntas = [linha for linha in linhas if _compacto(linha["name"]) == compacto]
    if juntas:
        return juntas[:8]
    por_nome = {}
    for linha in linhas:
        por_nome.setdefault(_compacto(linha["name"]), []).append(linha)
    parecidos = difflib.get_close_matches(compacto, list(por_nome), n=3, cutoff=0.88)
    return [linha for chave in parecidos for linha in por_nome[chave]][:8]


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )


def _compacto(texto: str) -> str:
    """Sem acento, espaço nem pontuação: 'Alta Floresta D'Oeste' vira 'altaflorestadoeste'."""
    return "".join(c for c in _sem_acento(texto) if c.isalnum())


def consultar_ponderacoes(argumentos: dict, _usuario: UserRecord, *, engine=None) -> dict:
    termos = argumentos.get("etapas") or argumentos.get("termos") or argumentos.get("etapa") or []
    if isinstance(termos, str):
        termos = [termos]
    termos = [str(t).strip() for t in termos if str(t).strip()][:4]
    if argumentos.get("ano") is None or not termos:
        return {
            "encontrado": False,
            "motivo": "Informe o exercício e as etapas que serão comparadas, por exemplo EJA e educação profissional.",
        }
    motor = engine or get_engine()
    base = _base_escolhida(argumentos.get("ano"), argumentos.get("base_id"), engine=motor)
    if not base or "version_id" not in base:
        return {
            "encontrado": False,
            "motivo": (base or {}).get("erro") or "Não há base para o exercício informado.",
        }
    with motor.connect() as conn:
        linhas = list(conn.execute(
            select(categories.c.name, categories.c.weight_vaaf, categories.c.weight_vaat).where(
                categories.c.version_id == base["version_id"]
            )
        ).mappings())
    grupos = []
    for termo in termos:
        tokens = [p for p in _sem_acento(termo).split() if len(p) >= 3]
        if not tokens:
            continue
        candidatas = []
        for linha in linhas:
            nome = _sem_acento(linha["name"])
            acertos = sum(1 for token in tokens if token in nome)
            if not acertos:
                continue
            penalidade = 0
            for extra in ("especial", "indigena", "quilombola", "campo", "surdo", "conveniada", "alternancia"):
                if extra in nome and extra not in _sem_acento(termo):
                    penalidade += 10
            if nome.startswith(tokens[0]):
                penalidade -= 5
            candidatas.append((acertos, penalidade, len(linha["name"]), linha))
        candidatas.sort(key=lambda item: (-item[0], item[1], item[2]))
        grupos.append({
            "termo": termo,
            "quantidade": len(candidatas),
            "etapas": [
                {
                    "nome": item[3]["name"],
                    "peso_vaaf": round(float(item[3]["weight_vaaf"]), 4),
                    "peso_vaat": round(float(item[3]["weight_vaat"]), 4),
                }
                for item in candidatas[:6]
            ],
        })
    return limpar({
        "encontrado": any(grupo["etapas"] for grupo in grupos),
        "tipo_dado": "oficial_importado",
        "ano_exercicio": base.get("ano_exercicio"),
        "base_id": base["base_id"],
        "version_id": base["version_id"],
        "homologada": base.get("homologada"),
        "grupos": grupos,
        "causa_demonstravel": False,
        "leitura": (
            "Um peso maior aumenta a matrícula ponderada dessa etapa. "
            "Isso pode mudar a participação da rede no fundo, mas não demonstra sozinho que o repasse aumenta. "
            "Esta consulta não executa uma simulação nova."
        ),
    })


_EXTRAS_ETAPA = (
    "campo", "indigena", "quilombola", "especial", "eja", "aee",
    "bilingue", "surdos", "conveniada", "alternancia", "concomitante",
    "itinerario", "sistema",
)
_SINONIMOS_ETAPA = {
    "tecnico": ("tecnico", "tecnica", "profissional"),
    "tecnica": ("tecnico", "tecnica", "profissional"),
    "profissional": ("tecnico", "tecnica", "profissional"),
}
_METRICAS_TRANSFERENCIA = (
    "vaaf_final",
    "matriculas_vaaf",
    "recursos_vaaf",
    "recursos_vaaf_final",
    "complemento_vaaf",
    "recursos_fundeb",
)


def _grupos_termo(termo: str) -> list[set[str]]:
    grupos = []
    for palavra in _sem_acento(termo).split():
        if len(palavra) < 3:
            continue
        grupos.append(set(_SINONIMOS_ETAPA.get(palavra, (palavra,))))
    return grupos


def escolher_etapa(termo: str, opcoes: list[dict]) -> dict | None:
    """Escolhe a etapa real mais próxima. 'Médio' sem o adjetivo integral fica no parcial."""
    grupos = _grupos_termo(termo)
    if not grupos:
        return None
    consulta = " ".join(palavra for grupo in grupos for palavra in grupo)
    melhor = None
    for opcao in opcoes:
        nome = _sem_acento(opcao["nome"])
        acertos = sum(1 for grupo in grupos if any(token in nome for token in grupo))
        if not acertos:
            continue
        penalidade = 0
        for extra in _EXTRAS_ETAPA:
            if extra in nome and extra not in consulta:
                penalidade += 8
        if "integral" in nome and "integral" not in consulta:
            penalidade += 12
        if "parcial" in nome and "integral" in consulta and "parcial" not in consulta:
            penalidade += 12
        chave = (acertos, -penalidade, float(opcao.get("alunos") or 0))
        if melhor is None or chave > melhor[0]:
            melhor = (chave, opcao)
    return dict(melhor[1]) if melhor else None


def _opcoes_com_estoque(ds, ibge: int) -> list[dict]:
    linha = ds.matriculas.loc[ds.matriculas["ibge"] == ibge]
    if linha.empty:
        return []
    registro = linha.iloc[0]
    pesos = ds.pesos.set_index("etapa")
    opcoes = []
    for etapa in ds.etapas:
        if etapa not in ds.matriculas.columns:
            continue
        alunos = float(registro.get(etapa) or 0)
        if alunos <= 0:
            continue
        peso = pesos.loc[etapa] if etapa in pesos.index else None
        opcoes.append({
            "codigo": etapa,
            "nome": ds.etapas_nomes.get(etapa, etapa),
            "alunos": alunos,
            "peso_vaaf": None if peso is None else round(float(peso["peso_vaaf"]), 4),
            "peso_vaat": None if peso is None else round(float(peso["peso_vaat"]), 4),
        })
    return opcoes


def _entes_por_nome(ds, nome: str, uf: str | None, ibge):
    tabela = ds.complementar
    if ibge:
        return tabela[tabela["ibge"] == int(ibge)]
    alvo = _sem_acento(nome)
    nomes = tabela["nome"].map(lambda valor: _sem_acento(str(valor)))
    achados = tabela[nomes == alvo]
    if uf:
        achados = achados[achados["uf"].astype(str).str.upper() == str(uf).upper()]
    return achados


def _ente_estadual(ds, uf: str):
    tabela = ds.complementar
    estaduais = tabela[(tabela["uf"] == uf) & (tabela["ibge"] < 100)]
    if estaduais.empty:
        return None
    return estaduais.iloc[0]


def _simular_matriz(ds, matriculas, simulador):
    if simulador is not None:
        return simulador(matriculas)
    from app.domain.calculo.motor import simula_fundeb

    padroes = ds.defaults_complementacao or {}
    return simula_fundeb(
        dados_matriculas=matriculas,
        dados_complementar=ds.complementar,
        dados_peso=ds.pesos,
        complementacao_vaaf=float(padroes.get("vaaf") or 0),
        complementacao_vaat=float(padroes.get("vaat") or 0),
        complementacao_vaar=float(padroes.get("vaar") or 0),
        max_nse=1.1,
        min_nse=1.0,
        max_nf=1.0,
        min_nf=1.0,
        modo_ponderador=ds.modo_ponderador,
    )


def _recortar(resultado, ibge: int) -> dict:
    linha = resultado.loc[resultado["ibge"] == ibge]
    if linha.empty:
        return {}
    registro = linha.iloc[0]
    return {
        chave: round(float(registro[chave]), 2)
        for chave in _METRICAS_TRANSFERENCIA
        if chave in resultado.columns and registro.get(chave) is not None
    }


def simular_transferencia(argumentos: dict, _usuario: UserRecord, *, engine=None, dataset=None, simulador=None) -> dict:
    nome = (argumentos.get("nome") or argumentos.get("municipio") or "").strip()
    origem_termo = (argumentos.get("origem") or "").strip()
    destino_termo = (argumentos.get("destino") or "").strip()
    try:
        ano = _inteiro(argumentos.get("ano"))
        alunos = float(argumentos.get("alunos"))
    except (TypeError, ValueError):
        ano, alunos = None, 0
    if not nome or ano is None or not origem_termo or not destino_termo or alunos <= 0:
        return {
            "encontrado": False,
            "motivo": "Informe o município, o exercício, a etapa de origem, a etapa de destino e a quantidade de alunos.",
        }
    if dataset is None:
        from app.ingestion.fundeb_dataset import carregar_dataset

        try:
            dataset = carregar_dataset(ano)
        except ValueError as exc:
            return {"encontrado": False, "motivo": str(exc)}
    if not getattr(dataset, "simulacao_habilitada", True):
        return {"encontrado": False, "motivo": f"A simulação de {ano} não está habilitada nesta base."}
    entes = _entes_por_nome(dataset, nome, argumentos.get("uf"), argumentos.get("ibge"))
    if len(entes) != 1:
        return {
            "encontrado": False,
            "motivo": "ambiguo" if len(entes) > 1 else "nao_encontrado",
            "candidatos": [
                {"ibge": int(linha.ibge), "uf": linha.uf, "nome": linha.nome}
                for linha in entes.head(8).itertuples()
            ],
        }
    pedido = entes.iloc[0]
    aviso = None
    ente = pedido
    origem = escolher_etapa(origem_termo, _opcoes_com_estoque(dataset, int(pedido.ibge)))
    destino = escolher_etapa(destino_termo, _opcoes_com_estoque(dataset, int(pedido.ibge)))
    if origem is None or destino is None or origem["codigo"] == destino["codigo"]:
        estadual = _ente_estadual(dataset, str(pedido.uf))
        if estadual is not None and int(estadual.ibge) != int(pedido.ibge):
            origem_estado = escolher_etapa(origem_termo, _opcoes_com_estoque(dataset, int(estadual.ibge)))
            destino_estado = escolher_etapa(destino_termo, _opcoes_com_estoque(dataset, int(estadual.ibge)))
            if origem_estado and destino_estado and origem_estado["codigo"] != destino_estado["codigo"]:
                aviso = (
                    f"A rede de {pedido.nome} (IBGE {int(pedido.ibge)}) não tem matrícula suficiente "
                    f"em '{origem_termo}' e '{destino_termo}' em {ano}. "
                    f"O cálculo usou a rede estadual de {estadual.nome} (IBGE {int(estadual.ibge)}), "
                    "onde essas etapas estão registradas."
                )
                ente = estadual
                origem, destino = origem_estado, destino_estado
    if origem is None or destino is None or origem["codigo"] == destino["codigo"]:
        return {
            "encontrado": False,
            "motivo": "nao_encontrado",
            "ano_exercicio": ano,
            "ente": {"ibge": int(pedido.ibge), "uf": pedido.uf, "nome": pedido.nome},
            "leitura": "Nenhuma etapa com matrícula corresponde à origem e ao destino informados.",
        }
    movimentar = min(float(alunos), float(origem["alunos"]))
    base = dataset.matriculas.copy()
    etapas = [c for c in dataset.etapas if c in base.columns]
    base[etapas] = base[etapas].astype("float64")
    ajustada = base.copy()
    indice = ajustada.index[ajustada["ibge"] == int(ente.ibge)][0]
    ajustada.at[indice, origem["codigo"]] -= movimentar
    ajustada.at[indice, destino["codigo"]] += movimentar
    antes = _recortar(_simular_matriz(dataset, base, simulador), int(ente.ibge))
    depois = _recortar(_simular_matriz(dataset, ajustada, simulador), int(ente.ibge))
    variacao = {
        chave: round(depois[chave] - antes[chave], 2)
        for chave in antes
        if chave in depois
    }
    return limpar({
        "encontrado": True,
        "tipo_dado": "resultado_simulado",
        "causa_demonstravel": True,
        "ano_exercicio": ano,
        "aviso": aviso,
        "ente": {"ibge": int(ente.ibge), "uf": ente.uf, "nome": ente.nome},
        "origem": origem,
        "destino": destino,
        "alunos_pedidos": alunos,
        "alunos_movidos": movimentar,
        "total_de_alunos_conservado": True,
        "antes": antes,
        "depois": depois,
        "variacao": variacao,
        "leitura": (
            "O motor completo foi reexecutado depois de mover os alunos, com o total da rede constante. "
            "vaaf_final é o valor aluno-ano. recursos_vaaf é a receita do fundo antes do complemento da União. "
            "recursos_fundeb é o total da rede."
        ),
    })


def executar(nome: str, argumentos: dict, usuario: UserRecord, *, engine=None) -> dict:
    if nome == "consultar_base":
        resultado = consultar_base(argumentos or {}, usuario, engine=engine)
    elif nome == "consultar_municipio":
        resultado = consultar_municipio(argumentos or {}, usuario, engine=engine)
    elif nome == "consultar_simulacao":
        resultado = consultar_simulacao(argumentos or {}, usuario, engine=engine)
    elif nome == "comparar_simulacoes":
        resultado = comparar_simulacoes(argumentos or {}, usuario, engine=engine)
    elif nome == "consultar_ponderacoes":
        resultado = consultar_ponderacoes(argumentos or {}, usuario, engine=engine)
    elif nome == "simular_transferencia":
        resultado = simular_transferencia(argumentos or {}, usuario, engine=engine)
    elif nome == "buscar_documentacao":
        consulta = (argumentos or {}).get("consulta") or ""
        if len(consulta.strip()) < 3:
            resultado = {"encontrado": False, "motivo": "Informe o assunto da busca."}
        else:
            trechos = buscar_trechos(consulta, engine=engine)
            resultado = {
                "encontrado": bool(trechos),
                "tipo_dado": "documentacao",
                "trechos": [
                    {
                        "titulo": t["title"],
                        "caminho": t["path"],
                        "versao": t["version"],
                        "texto": t["content"][:900],
                    }
                    for t in trechos
                ],
            }
    else:
        resultado = {"encontrado": False, "motivo": "Ferramenta não permitida."}
    return limpar(resultado)


FERRAMENTAS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_base",
            "description": "Exercício, versão ativa, homologação, cobertura e arquivos de origem de uma base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ano": {"type": "integer"},
                    "base_id": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_municipio",
            "description": (
                "Ente e rede numa base. resultado_tela traz os mesmos números do botão Simular "
                "sem alterar matrículas: matrículas VAAF e VAAT ponderadas, VAAF por aluno, recursos VAAF totais, "
                "VAAT por aluno, recursos VAAT totais e complementações VAAF, VAAT e VAAR. "
                "valores_oficiais são insumos importados e não substituem resultado_tela. "
                "Chame com o nome do município e, se souber, a UF, antes de perguntar a rede: "
                "nome de município já é a rede municipal. Se houver mais de uma rede, devolve ambiguo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string"},
                    "ano": {"type": "integer"},
                    "uf": {"type": "string"},
                    "ibge": {"type": "integer"},
                },
                "required": ["nome", "ano"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_simulacao",
            "description": "Parâmetros e resultados gravados de uma simulação visível ao usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cenario_id": {"type": "string"},
                    "ibge": {"type": "integer"},
                },
                "required": ["cenario_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "comparar_simulacoes",
            "description": "Diferença observada entre duas variantes gravadas da mesma simulação, para uma rede.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cenario_id": {"type": "string"},
                    "ibge": {"type": "integer"},
                    "variante_a": {"type": "string"},
                    "variante_b": {"type": "string"},
                },
                "required": ["cenario_id", "ibge"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_ponderacoes",
            "description": "Pesos oficiais de etapas de ensino. Use uma vez para comparar uma transferência de matrículas, como EJA para educação profissional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ano": {"type": "integer"},
                    "etapas": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["ano", "etapas"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simular_transferencia",
            "description": (
                "Move alunos de uma etapa para outra na base real e recalcula o FUNDEB. "
                "Use para dizer quanto muda o VAAF ou o repasse. "
                "Exemplo: 100 alunos de Fortaleza, do médio para o técnico, em 2025."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string"},
                    "uf": {"type": "string"},
                    "ano": {"type": "integer"},
                    "origem": {"type": "string"},
                    "destino": {"type": "string"},
                    "alunos": {"type": "number"},
                },
                "required": ["nome", "ano", "origem", "destino", "alunos"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_documentacao",
            "description": "Trechos da documentação indexada sobre VAAF, VAAT, VAAR e o simulador.",
            "parameters": {
                "type": "object",
                "properties": {"consulta": {"type": "string"}},
                "required": ["consulta"],
            },
        },
    },
]
