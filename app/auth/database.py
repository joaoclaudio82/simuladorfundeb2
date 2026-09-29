"""Usuários no mesmo banco da aplicação, preservando os hashes bcrypt existentes."""

import os
from sqlalchemy import select, func
from app.core.config import ROOT, database_url, production
from app.db.session import get_engine
from app.db.schema import users
from app.repositories.common import now, audit
from app.auth.models import Role, UserRecord
from app.auth.security import hash_password


def _engine():
    return get_engine()


def init_db():
    _engine()


def _row_to_user(row):
    return UserRecord(
        cpf=row["cpf"], role=Role(row["role"]), nome=row["nome"], ativo=bool(row["ativo"])
    )


def get_user(cpf):
    with _engine().connect() as conn:
        row = conn.execute(select(users).where(users.c.cpf == cpf)).mappings().first()
        return dict(row) if row else None


def get_user_record(cpf):
    row = get_user(cpf)
    return _row_to_user(row) if row else None


def verify_user_password(cpf, senha):
    from app.auth.security import verify_password

    row = get_user(cpf)
    if row and row["ativo"] and verify_password(senha, row["password_hash"]):
        return _row_to_user(row)
    return None


def create_user(cpf, senha, role=Role.usuario, nome=None):
    with _engine().begin() as conn:
        conn.execute(
            users.insert().values(
                cpf=cpf,
                password_hash=hash_password(senha),
                role=role.value,
                nome=nome,
                ativo=1,
                created_at=now(),
            )
        )
        audit(conn, "user.create", cpf)
    return get_user(cpf)


def list_users():
    with _engine().connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                select(
                    users.c.cpf, users.c.role, users.c.nome, users.c.ativo, users.c.created_at
                ).order_by(users.c.created_at)
            ).mappings()
        ]


def update_user(cpf, **fields):
    updates = {
        k: v
        for k, v in fields.items()
        if k in {"nome", "role", "ativo", "password_hash"} and v is not None
    }
    if updates:
        with _engine().begin() as conn:
            conn.execute(users.update().where(users.c.cpf == cpf).values(**updates))
            audit(conn, "user.update", cpf, {"fields": sorted(updates)})
    return get_user(cpf)


def delete_user(cpf):
    with _engine().begin() as conn:
        result = conn.execute(users.delete().where(users.c.cpf == cpf))
        audit(conn, "user.delete", cpf)
        return result.rowcount > 0


def count_admins():
    with _engine().connect() as conn:
        return conn.execute(
            select(func.count())
            .select_from(users)
            .where(users.c.role == "admin", users.c.ativo == 1)
        ).scalar_one()


def seed_admin_if_empty():
    """Only explicit bootstrap credentials; no known default password or CPF."""
    init_db()
    with _engine().connect() as conn:
        if conn.execute(select(func.count()).select_from(users)).scalar_one():
            return
    if (ROOT / "data/usuarios.db").exists():
        raise RuntimeError("Usuários legados encontrados. Execute import-users antes de iniciar.")
    cpf, senha = os.getenv("FUNDEB_ADMIN_CPF"), os.getenv("FUNDEB_ADMIN_SENHA")
    if not cpf and not senha:
        return
    from app.auth.security import normalizar_cpf, validar_cpf

    cpf = normalizar_cpf(cpf)
    if not validar_cpf(cpf) or not senha or len(senha) < 12:
        raise RuntimeError("Bootstrap exige CPF válido e senha de pelo menos 12 caracteres.")
    create_user(cpf, senha, Role.admin, "Administrador")
