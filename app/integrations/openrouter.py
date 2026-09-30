"""Chamada ao OpenRouter. A chave fica só no cabeçalho, nunca no corpo nem na resposta."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

URL = "https://openrouter.ai/api/v1/chat/completions"


class ErroChat(Exception):
    def __init__(self, situacao: str, mensagem: str):
        super().__init__(mensagem)
        self.situacao = situacao
        self.mensagem = mensagem


def completar(mensagens: list[dict], ferramentas: list[dict] | None = None, *, modelo: str, chave: str, escolha: str = "auto") -> dict:
    payload = {"model": modelo, "messages": mensagens}
    if ferramentas:
        payload["tools"] = ferramentas
        payload["tool_choice"] = escolha
    corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    pedido = urllib.request.Request(
        URL,
        data=corpo,
        method="POST",
        headers={
            "Authorization": f"Bearer {chave}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://127.0.0.1:8000",
            "X-Title": "Simulador FUNDEB",
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=60) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code in (402, 429):
            raise ErroChat("cota", "A cota do modelo gratuito se esgotou ou o serviço limitou o pedido.") from exc
        if exc.code in (502, 503, 504):
            raise ErroChat("indisponivel", "O modelo gratuito está indisponível agora.") from exc
        raise ErroChat("falha", "O provedor recusou o pedido.") from exc
    except urllib.error.URLError as exc:
        raise ErroChat("indisponivel", "Não foi possível falar com o OpenRouter.") from exc
    if chave and chave in json.dumps(dados):
        raise ErroChat("falha", "A resposta do provedor foi descartada.")
    escolha = (dados.get("choices") or [{}])[0].get("message") or {}
    uso = dados.get("usage") or {}
    return {
        "mensagem": escolha,
        "modelo": dados.get("model") or modelo,
        "prompt_tokens": uso.get("prompt_tokens"),
        "completion_tokens": uso.get("completion_tokens"),
    }
