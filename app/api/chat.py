"""Endpoints autenticados do chat."""

import json

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import get_current_user
from app.auth.models import Role, UserRecord
from app.integrations.openrouter import ErroChat
from app.repositories import chat as repositorio
from app.schemas.chat import PedidoChat
from app.services.chat import responder

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
def enviar(pedido: PedidoChat, usuario: UserRecord = Depends(get_current_user)):
    try:
        return responder(usuario, pedido)
    except ErroChat as exc:
        codigo = 404 if exc.situacao == "nao_encontrado" else 503
        raise HTTPException(codigo, exc.mensagem) from exc


@router.get("/conversas")
def conversas(usuario: UserRecord = Depends(get_current_user)):
    repositorio.garantir_tabelas()
    return {
        "conversas": repositorio.listar_conversas(
            usuario.cpf, admin=usuario.role == Role.admin
        )
    }


@router.get("/conversas/{conversa_id}")
def conversa(conversa_id: str, usuario: UserRecord = Depends(get_current_user)):
    repositorio.garantir_tabelas()
    row = repositorio.conversa_do_usuario(
        conversa_id, usuario.cpf, admin=usuario.role == Role.admin
    )
    if not row:
        raise HTTPException(404, "Conversa não encontrada.")
    return {
        "id": row["id"],
        "contexto": json.loads(row["context_json"]),
        "mensagens": repositorio.listar_mensagens(conversa_id, limite=50),
    }
