from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from auth.models import Role, UserRecord
from auth.security import hash_password

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.environ.get("FUNDEB_USERS_DB", os.path.join(DATA_DIR, "usuarios.db"))


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                cpf TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'usuario')),
                nome TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _row_to_user(row: sqlite3.Row) -> UserRecord:
    return UserRecord(
        cpf=row["cpf"],
        role=Role(row["role"]),
        nome=row["nome"],
        ativo=bool(row["ativo"]),
    )


def get_user(cpf: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE cpf = ?", (cpf,)).fetchone()
        return dict(row) if row else None


def get_user_record(cpf: str) -> Optional[UserRecord]:
    row = get_user(cpf)
    if not row:
        return None
    return UserRecord(
        cpf=row["cpf"],
        role=Role(row["role"]),
        nome=row["nome"],
        ativo=bool(row["ativo"]),
    )


def verify_user_password(cpf: str, senha: str) -> Optional[UserRecord]:
    row = get_user(cpf)
    if not row or not row["ativo"]:
        return None
    from auth.security import verify_password

    if not verify_password(senha, row["password_hash"]):
        return None
    return _row_to_user(row)  # type: ignore[arg-type]


def create_user(
    cpf: str,
    senha: str,
    role: Role = Role.usuario,
    nome: Optional[str] = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (cpf, password_hash, role, nome, ativo, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (cpf, hash_password(senha), role.value, nome, now),
        )
        conn.commit()
    row = get_user(cpf)
    assert row is not None
    return row


def list_users() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT cpf, role, nome, ativo, created_at FROM users ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def update_user(cpf: str, **fields) -> Optional[dict]:
    allowed = {"nome", "role", "ativo", "password_hash"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_user(cpf)
    sets = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [cpf]
    with _connect() as conn:
        conn.execute(f"UPDATE users SET {sets} WHERE cpf = ?", vals)
        conn.commit()
    return get_user(cpf)


def delete_user(cpf: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM users WHERE cpf = ?", (cpf,))
        conn.commit()
        return cur.rowcount > 0


def count_admins() -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE role = 'admin' AND ativo = 1"
        ).fetchone()
        return int(row["n"]) if row else 0


def seed_admin_if_empty() -> None:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        if row and int(row["n"]) > 0:
            return

    cpf = os.environ.get("FUNDEB_ADMIN_CPF", "52998224725")
    senha = os.environ.get("FUNDEB_ADMIN_SENHA", "admin123")
    from auth.security import normalizar_cpf, validar_cpf

    cpf = normalizar_cpf(cpf)
    if not validar_cpf(cpf):
        cpf = "52998224725"
    create_user(cpf, senha, Role.admin, nome="Administrador")
    print(f"Admin inicial criado (CPF {cpf}). Altere a senha após o primeiro login.")
