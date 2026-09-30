"""Mensagens e filtros do chat."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ContextoChat(BaseModel):
    ano: Optional[int] = None
    municipio: Optional[str] = None
    ibge: Optional[int] = None
    cenario_id: Optional[str] = None


class PedidoChat(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    conversa_id: Optional[str] = None
    contexto: ContextoChat = Field(default_factory=ContextoChat)


class ReferenciaChat(BaseModel):
    tipo: Literal["base", "municipio", "simulacao", "comparacao", "documento"]
    descricao: str
    referencia: dict
