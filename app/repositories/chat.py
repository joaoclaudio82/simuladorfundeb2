"""Conversas, evidências e trechos de documentação do chat."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from sqlalchemy import delete, select, text

from app.core.config import ROOT
from app.db.chat_schema import chamadas, conversas, documentos, evidencias, mensagens, metadata, trechos
from app.db.session import get_engine
from app.repositories.common import now

GLOSSARIO = (
    "glossario-fundeb",
    "Glossário FUNDEB",
    """
VAAF é o Valor Anual por Aluno do Fundeb. A complementação VAAF busca um valor mínimo por aluno no fundo estadual.
VAAT é o Valor Anual por Aluno Total. A complementação VAAT considera a receita vinculada à educação do ente e vai a quem fica abaixo do mínimo nacional.
VAAR é o Valor Aluno Ano Resultado. A complementação VAAR depende de indicadores de atendimento e aprendizagem, não só de matrícula.
No exercício 2024 o ponderador fiscal do VAAF é o NF, que pode ser reescalonado. Em 2025 e 2026 o ponderador fiscal é o DREC oficial, usado como valor fixo.
Uma base não homologada não autoriza tratar o número como repasse oficial. Resultado simulado é o que o motor gravou. Valor oficial importado é o que veio do arquivo de origem da base.
Simulação não é previsão de repasse futuro.
""".strip(),
)
ARQUIVOS = (
    "docs/DADOS_E_COMPATIBILIDADE.md",
    "docs/BANCO.md",
    "docs/ARQUITETURA.md",
)
_PRONTO = False


def garantir_tabelas(engine=None) -> None:
    global _PRONTO
    motor = engine or get_engine()
    if _PRONTO:
        return
    metadata.create_all(motor)
    _PRONTO = True


def nova_conversa(owner_cpf: str, contexto: dict, *, engine=None) -> str:
    ident = uuid.uuid4().hex
    instante = now()
    with (engine or get_engine()).begin() as conn:
        conn.execute(
            conversas.insert().values(
                id=ident,
                owner_cpf=owner_cpf,
                created_at=instante,
                updated_at=instante,
                context_json=json.dumps(contexto, ensure_ascii=False),
            )
        )
    return ident


def conversa_do_usuario(conversa_id: str, owner_cpf: str, *, admin: bool, engine=None) -> dict | None:
    with (engine or get_engine()).connect() as conn:
        row = conn.execute(select(conversas).where(conversas.c.id == conversa_id)).mappings().first()
    if not row:
        return None
    if not admin and row["owner_cpf"] != owner_cpf:
        return None
    return dict(row)


def atualizar_contexto(conversa_id: str, contexto: dict, *, engine=None) -> None:
    with (engine or get_engine()).begin() as conn:
        conn.execute(
            conversas.update()
            .where(conversas.c.id == conversa_id)
            .values(context_json=json.dumps(contexto, ensure_ascii=False), updated_at=now())
        )


def acrescentar_mensagem(conversa_id: str, role: str, content: str, *, engine=None) -> str:
    ident = uuid.uuid4().hex
    with (engine or get_engine()).begin() as conn:
        conn.execute(
            mensagens.insert().values(
                id=ident,
                conversation_id=conversa_id,
                role=role,
                content=content,
                created_at=now(),
            )
        )
        conn.execute(
            conversas.update().where(conversas.c.id == conversa_id).values(updated_at=now())
        )
    return ident


def listar_mensagens(conversa_id: str, *, limite: int = 10, engine=None) -> list[dict]:
    with (engine or get_engine()).connect() as conn:
        rows = conn.execute(
            select(mensagens.c.role, mensagens.c.content)
            .where(mensagens.c.conversation_id == conversa_id)
            .order_by(mensagens.c.created_at.desc())
            .limit(limite)
        ).mappings()
    return list(reversed([dict(r) for r in rows]))


def listar_conversas(owner_cpf: str, *, admin: bool, engine=None) -> list[dict]:
    consulta = select(
        conversas.c.id, conversas.c.updated_at, conversas.c.context_json
    ).order_by(conversas.c.updated_at.desc()).limit(30)
    if not admin:
        consulta = consulta.where(conversas.c.owner_cpf == owner_cpf)
    with (engine or get_engine()).connect() as conn:
        rows = conn.execute(consulta).mappings()
    saida = []
    for row in rows:
        item = dict(row)
        item["contexto"] = json.loads(item.pop("context_json"))
        saida.append(item)
    return saida


def registrar_evidencias(mensagem_id: str, itens: list[dict], *, engine=None) -> None:
    if not itens:
        return
    with (engine or get_engine()).begin() as conn:
        conn.execute(
            evidencias.insert(),
            [
                {
                    "id": uuid.uuid4().hex,
                    "message_id": mensagem_id,
                    "kind": item["tipo"],
                    "ref_json": json.dumps(item, ensure_ascii=False),
                }
                for item in itens
            ],
        )


def registrar_chamada(mensagem_id: str, *, modelo: str, uso: dict, duracao_ms: int, situacao: str, erro: str | None, engine=None) -> None:
    with (engine or get_engine()).begin() as conn:
        conn.execute(
            chamadas.insert().values(
                id=uuid.uuid4().hex,
                message_id=mensagem_id,
                model=modelo,
                prompt_tokens=uso.get("prompt_tokens"),
                completion_tokens=uso.get("completion_tokens"),
                duration_ms=duracao_ms,
                status=situacao,
                error=erro,
            )
        )


def _fatiar(texto: str, tamanho: int = 1200) -> list[str]:
    partes, atual = [], ""
    for bloco in texto.split("\n\n"):
        if len(atual) + len(bloco) + 2 > tamanho and atual:
            partes.append(atual.strip())
            atual = bloco
        else:
            atual = f"{atual}\n\n{bloco}".strip()
    if atual.strip():
        partes.append(atual.strip())
    return partes


def indexar_documentos(*, engine=None) -> None:
    motor = engine or get_engine()
    fontes = [(GLOSSARIO[0], GLOSSARIO[1], "glossario", None, GLOSSARIO[2])]
    for relativo in ARQUIVOS:
        caminho = Path(ROOT) / relativo
        if caminho.is_file():
            fontes.append((relativo, caminho.name, "arquivo", None, caminho.read_text(encoding="utf-8")))
    with motor.begin() as conn:
        for ident, titulo, versao, data, conteudo in fontes:
            digest = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
            existente = conn.execute(
                select(documentos.c.sha256).where(documentos.c.id == ident)
            ).scalar()
            if existente == digest:
                continue
            conn.execute(delete(trechos).where(trechos.c.document_id == ident))
            conn.execute(delete(documentos).where(documentos.c.id == ident))
            conn.execute(
                documentos.insert().values(
                    id=ident,
                    path=ident,
                    title=titulo,
                    version=versao,
                    source_date=data,
                    sha256=digest,
                )
            )
            fatias = _fatiar(conteudo)
            if fatias:
                conn.execute(
                    trechos.insert(),
                    [
                        {
                            "id": f"{ident}:{i}",
                            "document_id": ident,
                            "position": i,
                            "content": fatia,
                        }
                        for i, fatia in enumerate(fatias)
                    ],
                )


def buscar_trechos(consulta: str, *, limite: int = 4, engine=None) -> list[dict]:
    sql = text(
        """
        SELECT d.title, d.path, d.version, c.content
        FROM chat_chunks c
        JOIN chat_documents d ON d.id = c.document_id
        WHERE to_tsvector('portuguese', c.content) @@ plainto_tsquery('portuguese', :consulta)
        ORDER BY c.position
        LIMIT :limite
        """
    )
    try:
        with (engine or get_engine()).connect() as conn:
            rows = conn.execute(sql, {"consulta": consulta, "limite": limite}).mappings()
            achados = [dict(r) for r in rows]
    except Exception:
        achados = []
    if achados:
        return achados
    termos = [p for p in consulta.lower().split() if len(p) >= 4][:4]
    if not termos:
        return []
    filtro = " AND ".join(f"lower(c.content) LIKE :t{i}" for i in range(len(termos)))
    params = {f"t{i}": f"%{termo}%" for i, termo in enumerate(termos)}
    params["limite"] = limite
    with (engine or get_engine()).connect() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT d.title, d.path, d.version, c.content
                FROM chat_chunks c
                JOIN chat_documents d ON d.id = c.document_id
                WHERE {filtro}
                LIMIT :limite
                """
            ),
            params,
        ).mappings()
    return [dict(r) for r in rows]
