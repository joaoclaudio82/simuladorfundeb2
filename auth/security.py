from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

SECRET_KEY = os.environ.get(
    "FUNDEB_SECRET_KEY",
    "dev-fundeb-secret-altere-em-producao",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("FUNDEB_TOKEN_HOURS", "12"))
COOKIE_NAME = "fundeb_token"


def normalizar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", str(cpf or ""))


def validar_cpf(cpf: str) -> bool:
    cpf = normalizar_cpf(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for j in (9, 10):
        soma = sum(int(cpf[i]) * ((j + 1) - i) for i in range(j))
        dig = (soma * 10 % 11) % 10
        if int(cpf[j]) != dig:
            return False
    return True


def formatar_cpf(cpf: str) -> str:
    c = normalizar_cpf(cpf)
    if len(c) != 11:
        return cpf
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"


def hash_password(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(senha: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(cpf: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": cpf, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
