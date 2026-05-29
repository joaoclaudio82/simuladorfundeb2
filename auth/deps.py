from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status

from auth.database import get_user_record
from auth.models import Role, UserRecord
from auth.security import COOKIE_NAME, decode_access_token


def get_current_user(
    fundeb_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> UserRecord:
    if not fundeb_token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Autenticação necessária",
        )
    payload = decode_access_token(fundeb_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessão inválida ou expirada",
        )
    user = get_user_record(payload["sub"])
    if not user or not user.ativo:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Usuário inativo ou não encontrado",
        )
    return user


def require_admin(user: UserRecord = Depends(get_current_user)) -> UserRecord:
    if user.role != Role.admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Acesso restrito a administradores",
        )
    return user
