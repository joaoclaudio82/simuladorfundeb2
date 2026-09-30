"""Tabelas do chat. Ficam fora do esquema de backup das simulações."""

from sqlalchemy import Column as C, ForeignKey, Index, Integer, MetaData, String, Table, Text

metadata = MetaData()

conversas = Table(
    "chat_conversations",
    metadata,
    C("id", String(32), primary_key=True),
    C("owner_cpf", String(11), nullable=False),
    C("created_at", Text, nullable=False),
    C("updated_at", Text, nullable=False),
    C("context_json", Text, nullable=False),
)
mensagens = Table(
    "chat_messages",
    metadata,
    C("id", String(32), primary_key=True),
    C("conversation_id", ForeignKey("chat_conversations.id"), nullable=False),
    C("role", String(16), nullable=False),
    C("content", Text, nullable=False),
    C("created_at", Text, nullable=False),
)
evidencias = Table(
    "chat_evidence",
    metadata,
    C("id", String(32), primary_key=True),
    C("message_id", ForeignKey("chat_messages.id"), nullable=False),
    C("kind", String(32), nullable=False),
    C("ref_json", Text, nullable=False),
)
chamadas = Table(
    "chat_calls",
    metadata,
    C("id", String(32), primary_key=True),
    C("message_id", ForeignKey("chat_messages.id"), nullable=False),
    C("model", Text, nullable=False),
    C("prompt_tokens", Integer),
    C("completion_tokens", Integer),
    C("duration_ms", Integer, nullable=False),
    C("status", String(32), nullable=False),
    C("error", Text),
)
documentos = Table(
    "chat_documents",
    metadata,
    C("id", String(64), primary_key=True),
    C("path", Text, nullable=False),
    C("title", Text, nullable=False),
    C("version", Text, nullable=False),
    C("source_date", Text),
    C("sha256", String(64), nullable=False),
)
trechos = Table(
    "chat_chunks",
    metadata,
    C("id", String(80), primary_key=True),
    C("document_id", ForeignKey("chat_documents.id"), nullable=False),
    C("position", Integer, nullable=False),
    C("content", Text, nullable=False),
)
Index("ix_chat_messages_conversa", mensagens.c.conversation_id, mensagens.c.created_at)
Index("ix_chat_conversas_owner", conversas.c.owner_cpf, conversas.c.updated_at)
