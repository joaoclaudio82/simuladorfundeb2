"""Só confirma uma simulação legada ao cliente depois do commit do resultado completo."""

import re
import logging
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from app.services.capture import current_capture
from app.repositories.legacy import save_run

logger = logging.getLogger(__name__)


class PersistLegacyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or not re.fullmatch(
                r"/api/(?:\d{4}/)?simular(?:/(?:completo|municipio))?", scope["path"]
            )
        ):
            return await self.app(scope, receive, send)
        request_parts, messages = [], []
        capture = {"owner_cpf": None, "calculations": []}
        token = current_capture.set(capture)

        async def receive_copy():
            message = await receive()
            if message["type"] == "http.request":
                request_parts.append(message.get("body", b""))
            return message

        async def collect(message):
            messages.append(message)

        try:
            await self.app(scope, receive_copy, collect)
            start = next(m for m in messages if m["type"] == "http.response.start")
            if 200 <= start["status"] < 300 and capture["calculations"]:
                body = b"".join(
                    m.get("body", b"") for m in messages if m["type"] == "http.response.body"
                )
                try:
                    ident = await run_in_threadpool(
                        save_run, scope["path"], b"".join(request_parts), body, capture
                    )
                except Exception:
                    # Never log a request, CPF, password, SQL values or connection URL.
                    logger.error("Falha ao persistir simulação; resposta de sucesso retida.")
                    return await JSONResponse(
                        {"detail": "Não foi possível salvar a simulação. Tente novamente."},
                        status_code=503,
                    )(scope, receive, send)
                start["headers"] = list(start.get("headers", [])) + [
                    (b"x-simulation-id", ident.encode())
                ]
            for message in messages:
                await send(message)
        finally:
            current_capture.reset(token)
