"""Controles do chat. A chave nunca sai deste módulo para o cliente."""

import os

MODELO_PADRAO = "openrouter/free"


def chat_habilitado() -> bool:
    return os.getenv("FUNDEB_CHAT_ENABLED", "true").lower() in ("1", "true", "yes")


def somente_gratuito() -> bool:
    return os.getenv("FUNDEB_CHAT_FREE_ONLY", "true").lower() in ("1", "true", "yes")


def chave_openrouter() -> str:
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def modelo_configurado() -> str:
    return os.getenv("OPENROUTER_MODEL", MODELO_PADRAO).strip() or MODELO_PADRAO


def modelo_permitido(modelo: str) -> bool:
    if not somente_gratuito():
        return True
    nome = (modelo or "").strip()
    return nome == MODELO_PADRAO or nome.endswith(":free")
