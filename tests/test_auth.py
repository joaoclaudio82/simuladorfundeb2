"""
Testes de autenticação, perfis e restrição de pesos customizados.
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.database import create_user, init_db
from auth.models import Role
from auth.routes import router as auth_router
from auth.security import COOKIE_NAME, normalizar_cpf
from api_simulacao import SimulacaoRequest, preparar_pesos


ADMIN_CPF = "52998224725"
USER_CPF = "11144477735"
ADMIN_PASS = "admin123"
USER_PASS = "userpass"


@pytest.fixture()
def auth_client(tmp_path, monkeypatch):
    db_path = tmp_path / "usuarios_test.db"
    monkeypatch.setenv("FUNDEB_USERS_DB", str(db_path))
    monkeypatch.setenv("FUNDEB_SECRET_KEY", "test-secret-key")

    import auth.database as db_mod
    import auth.security as sec_mod

    monkeypatch.setattr(db_mod, "DB_PATH", str(db_path))
    monkeypatch.setattr(sec_mod, "SECRET_KEY", "test-secret-key")

    init_db()
    create_user(ADMIN_CPF, ADMIN_PASS, Role.admin, "Admin Teste")
    create_user(USER_CPF, USER_PASS, Role.usuario, "Usuario Teste")

    app = FastAPI()
    app.include_router(auth_router, prefix="/api")
    return TestClient(app)


def _login(client: TestClient, cpf: str, senha: str) -> None:
    res = client.post("/api/auth/login", json={"cpf": cpf, "senha": senha})
    assert res.status_code == 200, res.text


def test_login_ok(auth_client):
    res = auth_client.post(
        "/api/auth/login",
        json={"cpf": ADMIN_CPF, "senha": ADMIN_PASS},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "admin"
    assert COOKIE_NAME in res.cookies


def test_login_senha_errada(auth_client):
    res = auth_client.post(
        "/api/auth/login",
        json={"cpf": ADMIN_CPF, "senha": "errada"},
    )
    assert res.status_code == 401


def test_login_cpf_invalido(auth_client):
    res = auth_client.post(
        "/api/auth/login",
        json={"cpf": "123", "senha": "qualquer"},
    )
    assert res.status_code == 422


def test_usuario_nao_acessa_admin(auth_client):
    _login(auth_client, USER_CPF, USER_PASS)
    res = auth_client.get("/api/admin/usuarios")
    assert res.status_code == 403


def test_admin_lista_usuarios(auth_client):
    _login(auth_client, ADMIN_CPF, ADMIN_PASS)
    res = auth_client.get("/api/admin/usuarios")
    assert res.status_code == 200
    assert len(res.json()) >= 2


def test_usuario_inativo_login_403(auth_client, tmp_path, monkeypatch):
    from auth.database import update_user

    update_user(USER_CPF, ativo=0)
    res = auth_client.post(
        "/api/auth/login",
        json={"cpf": USER_CPF, "senha": USER_PASS},
    )
    assert res.status_code == 403


def test_preparar_pesos_admin_aplica_custom():
    pesos_df = pd.DataFrame({
        "etapa": ["e1", "e2"],
        "nome": ["E1", "E2"],
        "peso_vaaf": [1.0, 2.0],
        "peso_vaat": [1.5, 2.5],
    })

    class FakeDs:
        pesos = pesos_df

    req = SimulacaoRequest(pesos_vaaf=[3.0, 4.0], pesos_vaat=[5.0, 6.0])
    from auth.models import UserRecord

    admin = UserRecord(cpf=ADMIN_CPF, role=Role.admin)
    p = preparar_pesos(req, FakeDs(), admin)
    assert list(p["peso_vaaf"]) == [3.0, 4.0]
    assert list(p["peso_vaat"]) == [5.0, 6.0]


def test_preparar_pesos_usuario_ignora_custom():
    pesos_df = pd.DataFrame({
        "etapa": ["e1", "e2"],
        "nome": ["E1", "E2"],
        "peso_vaaf": [1.0, 2.0],
        "peso_vaat": [1.5, 2.5],
    })

    class FakeDs:
        pesos = pesos_df

    req = SimulacaoRequest(pesos_vaaf=[9.0, 9.0], pesos_vaat=[8.0, 8.0])
    from auth.models import UserRecord

    user = UserRecord(cpf=USER_CPF, role=Role.usuario)
    p = preparar_pesos(req, FakeDs(), user)
    assert list(p["peso_vaaf"]) == [1.0, 2.0]
    assert list(p["peso_vaat"]) == [1.5, 2.5]


def test_normalizar_cpf():
    assert normalizar_cpf("529.982.247-25") == ADMIN_CPF
