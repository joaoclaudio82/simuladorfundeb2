"""Consultas que o chat pode pedir. Os argumentos são validados aqui."""

from __future__ import annotations

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


def consultar_municipio(argumentos: dict, _usuario: UserRecord, *, engine=None) -> dict:
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
        linhas = exatas or list(conn.execute(
            consulta.where(entities.c.name.ilike(f"%{seguro}%", escape="\\")).limit(8)
        ).mappings())
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
    return limpar({
        "encontrado": True,
        "tipo_dado": "oficial_importado",
        "ano_exercicio": ano,
        "base_id": base["base_id"],
        "homologada": base.get("homologada"),
        "situacao": base.get("situacao"),
        "ente": ente,
        "valores_oficiais": _numeros(valores),
    })


def _cenario_visivel(conn, cenario_id: str, usuario: UserRecord):
    row = conn.execute(select(scenarios).where(scenarios.c.id == cenario_id)).mappings().first()
    if not row:
        return None
    if usuario.role != Role.admin and row["owner_cpf"] != usuario.cpf:
        return None
    return row


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
    return limpar({
        "encontrado": True,
        "tipo_dado": "resultado_simulado",
        "cenario_id": cenario_id,
        "base_id": row["base_id"],
        "base_version": row["base_version"],
        "criado_em": row["created_at"],
        "parametros": pedido,
        "resultados": [
            {"variante": l["variant"], "ibge": l["ibge"], "valores": _numeros(json.loads(l["values_json"]))}
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
        "ibge": int(ibge),
        "diferencas": diferencas,
        "causa_demonstravel": False,
        "leitura": "A diferença foi calculada nos resultados gravados. Ela não demonstra sozinha a causa da mudança.",
    })


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )


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
            "description": "Ente e rede numa base, com valores oficiais importados. Não escolhe sozinho se houver mais de uma rede.",
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
