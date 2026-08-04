from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from auth.database import (
    count_admins,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
    verify_user_password,
)
from auth.deps import get_current_user, require_admin
from auth.models import LoginRequest, Role, UserCreate, UserPublic, UserUpdate
from auth.security import (
    COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_HOURS,
    create_access_token,
    formatar_cpf,
    hash_password,
)

router = APIRouter(tags=["auth"])


def _public_user(row: dict) -> UserPublic:
    return UserPublic(
        cpf=row["cpf"],
        role=Role(row["role"]),
        nome=row.get("nome"),
        ativo=bool(row["ativo"]),
        created_at=row["created_at"],
    )


@router.post("/auth/login")
def login(req: LoginRequest, response: Response):
    from auth.security import normalizar_cpf

    cpf = normalizar_cpf(req.cpf)
    row = get_user(cpf)
    if row and not row["ativo"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Usuário inativo. Contate o administrador.",
        )
    user = verify_user_password(cpf, req.senha)
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "CPF ou senha incorretos, ou usuário inativo",
        )
    token = create_access_token(user.cpf, user.role.value)
    max_age = ACCESS_TOKEN_EXPIRE_HOURS * 3600
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    return {
        "cpf": user.cpf,
        "cpf_formatado": formatar_cpf(user.cpf),
        "role": user.role.value,
        "nome": user.nome,
    }


@router.post("/auth/logout")
def logout(response: Response, _user=Depends(get_current_user)):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(user=Depends(get_current_user)):
    return {
        "cpf": user.cpf,
        "cpf_formatado": formatar_cpf(user.cpf),
        "role": user.role.value,
        "nome": user.nome,
    }


@router.get("/admin/usuarios")
def admin_listar(_admin=Depends(require_admin)):
    return [_public_user(r) for r in list_users()]


@router.post("/admin/usuarios", status_code=201)
def admin_criar(req: UserCreate, _admin=Depends(require_admin)):
    if get_user(req.cpf):
        raise HTTPException(409, "CPF já cadastrado")
    row = create_user(req.cpf, req.senha, req.role, req.nome)
    return _public_user(row)


@router.patch("/admin/usuarios/{cpf}")
def admin_atualizar(cpf: str, req: UserUpdate, admin=Depends(require_admin)):
    from auth.security import normalizar_cpf

    cpf = normalizar_cpf(cpf)
    row = get_user(cpf)
    if not row:
        raise HTTPException(404, "Usuário não encontrado")

    updates = {}
    if req.nome is not None:
        updates["nome"] = req.nome
    if req.role is not None:
        if row["role"] == "admin" and req.role != Role.admin and count_admins() <= 1:
            raise HTTPException(400, "Não é possível remover o último administrador")
        updates["role"] = req.role.value
    if req.ativo is not None:
        if cpf == admin.cpf and not req.ativo:
            raise HTTPException(400, "Não é possível desativar o próprio usuário")
        if row["role"] == "admin" and not req.ativo and count_admins() <= 1:
            raise HTTPException(400, "Não é possível desativar o último administrador")
        updates["ativo"] = 1 if req.ativo else 0
    if req.senha is not None:
        updates["password_hash"] = hash_password(req.senha)

    updated = update_user(cpf, **updates)
    return _public_user(updated)


@router.delete("/admin/usuarios/{cpf}")
def admin_excluir(cpf: str, admin=Depends(require_admin)):
    from auth.security import normalizar_cpf

    cpf = normalizar_cpf(cpf)
    row = get_user(cpf)
    if not row:
        raise HTTPException(404, "Usuário não encontrado")
    if cpf == admin.cpf:
        raise HTTPException(400, "Não é possível excluir o próprio usuário")
    if row["role"] == "admin" and count_admins() <= 1:
        raise HTTPException(400, "Não é possível excluir o último administrador")
    delete_user(cpf)
    return {"ok": True}
