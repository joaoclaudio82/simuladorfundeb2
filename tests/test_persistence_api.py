import json
import pytest
from fastapi.testclient import TestClient
import main
from auth.deps import get_current_user
from auth.models import Role, UserRecord
from app.db.codec import unpack
from app.repositories.scenarios import RepositorioCenarios
from app.db.session import get_engine

ADMIN = UserRecord(cpf="52998224725", role=Role.admin)
USER = UserRecord(cpf="11144477735", role=Role.usuario)


@pytest.fixture
def client():
    main.app.dependency_overrides[get_current_user] = lambda: ADMIN
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_legacy_response_and_complete_frames_survive_restart(client):
    original = client.post("/api/2026/simular", json={})
    assert original.status_code == 200
    ident = original.headers["x-simulation-id"]
    get_engine().dispose()
    restored = client.get(f"/api/historico/legado/{ident}")
    assert restored.content == original.content
    snapshot = client.get(f"/api/historico/legado/{ident}/snapshot")
    calculations = unpack(snapshot.content)
    assert len(calculations) == 1
    assert len(calculations[0]["result"]) == 5596
    assert len(calculations[0]["matriculas"]) == 5596
    assert len(original.json()["dados_tabela"]) == 200
    assert client.get("/api/historico").json()["simulacoes_legadas"][0]["id"] == ident
    main.app.dependency_overrides[get_current_user] = lambda: USER
    assert client.get(f"/api/historico/legado/{ident}").status_code == 404
    assert client.get("/api/historico").json()["simulacoes_legadas"] == []


def test_success_not_returned_when_persistence_fails(client, monkeypatch):
    import app.api.persistence as middleware

    def fail(*_):
        raise RuntimeError("unavailable")

    monkeypatch.setattr(middleware, "save_run", fail)
    response = client.post("/api/simular", json={})
    assert response.status_code == 503
    assert "salvar" in response.json()["detail"]


def test_scenario_original_response_and_exports(client, monkeypatch):
    response = client.post("/api/cenarios", json={"descricao": "Cenário preservado"})
    assert response.status_code == 200
    ident = response.json()["metadados"]["cenario_id"]
    original = client.get(f"/api/cenarios/{ident}/exportar?formato=xlsx").content
    get_engine().dispose()
    assert client.get(f"/api/cenarios/{ident}").json() == response.json()
    assert client.get(f"/api/cenarios/{ident}/exportar?formato=xlsx").content == original
    assert (
        client.get("/api/historico").json()["cenarios"][0]["request_json"]["descricao"]
        == "Cenário preservado"
    )
    main.app.dependency_overrides[get_current_user] = lambda: USER
    assert client.get("/api/historico").json()["cenarios"] == []


def test_production_rejects_insecure_configuration(monkeypatch):
    from app.core.config import validate_configuration

    monkeypatch.setenv("FUNDEB_ENV", "production")
    with pytest.raises(RuntimeError, match="postgresql"):
        validate_configuration()
    monkeypatch.setenv("FUNDEB_DATABASE_URL", "postgresql+psycopg://unused")
    monkeypatch.setenv("FUNDEB_SECRET_KEY", "short")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_configuration()


def test_no_implicit_default_admin(monkeypatch):
    from auth.database import seed_admin_if_empty, list_users

    monkeypatch.delenv("FUNDEB_ADMIN_CPF", raising=False)
    monkeypatch.delenv("FUNDEB_ADMIN_SENHA", raising=False)
    seed_admin_if_empty()
    assert list_users() == []
