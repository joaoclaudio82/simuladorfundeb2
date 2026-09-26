"""Rotas de bases, entes, cenários e exportação (integração com a base de 2026)."""
import pytest
from fastapi.testclient import TestClient

import main
from auth.deps import get_current_user
from auth.models import Role, UserRecord

ADMIN = UserRecord(cpf="52998224725", role=Role.admin, nome="Admin")
USUARIO = UserRecord(cpf="11144477735", role=Role.usuario, nome="Usuário")


@pytest.fixture
def client():
    main.app.dependency_overrides[get_current_user] = lambda: ADMIN
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_rotas_exigem_autenticacao():
    anonimo = TestClient(main.app)
    assert anonimo.get("/api/bases").status_code == 401
    assert anonimo.post("/api/cenarios", json={}).status_code == 401


def test_listar_bases(client):
    bases = client.get("/api/bases").json()["bases"]
    assert {b["base_id"] for b in bases} == {"fundeb-2024", "fundeb-2025", "fundeb-2026"}
    assert next(b for b in bases if b["padrao"])["ano_exercicio"] == 2026


def test_listar_entes_por_uf_e_tipo(client):
    entes = client.get("/api/entes", params={"uf": "CE", "tipo": "rede estadual"}).json()["entes"]
    assert [e["ibge"] for e in entes] == [23]


def test_matriculas_de_rede_estadual(client):
    r = client.get("/api/entes/22/matriculas")
    assert r.status_code == 200
    assert r.json()["tipo_rede"] == "rede estadual"
    assert len(r.json()["matriculas"]) >= 300


CAT = "ensino_medio_integral"


def _cenario(client, **kw):
    corpo = {"ajustes": [
        {"ibge": 22, "categoria": CAT, "operacao": "acrescentar", "valor": 5000},
        {"ibge": 21, "categoria": "ensino_medio_parcial", "operacao": "converter",
         "valor": 3000, "categoria_destino": CAT},
    ]}
    corpo.update(kw)
    r = client.post("/api/cenarios", json=corpo)
    assert r.status_code == 200, r.text
    return r.json()


def test_cenario_conjunto_estaduais(client):
    dados = _cenario(client)
    comp = dados["comparacao"]
    assert comp["recorte"]["quantidade_redes"] == 27
    assert dados["metadados"]["resumo_ajustes"]["matriculas_convertidas"] == 3000
    assert dados["metadados"]["base"]["ano_exercicio"] == 2026
    assert dados["metadados"]["base"]["homologada"] is False


def test_cenario_ajuste_unico_compativel_com_rota_anterior(client):
    """Mesma entrada: a nova rota reproduz /api/2026/simular/municipio."""
    from services.bases import carregar_base
    base = carregar_base("fundeb-2026")
    par = base.parametros_referencia
    original = base.matriculas.loc[base.matriculas.ibge == 23, CAT].iloc[0]
    antigo = client.post("/api/2026/simular/municipio", json={
        "ibge": 23, "complementacao_vaaf": par["complementacao_vaaf"],
        "complementacao_vaat": par["complementacao_vaat"], "complementacao_vaar": par["complementacao_vaar"],
        "matriculas_ajustadas": {CAT: original + 1000}}).json()
    novo = client.post("/api/cenarios", json={
        "ajustes": [{"ibge": 23, "categoria": CAT, "operacao": "acrescentar", "valor": 1000}]}).json()
    linha = next(x for x in novo["comparacao"]["linhas"] if x["ibge"] == 23)
    assert linha["recursos_fundeb_B"] == pytest.approx(antigo["municipio_ajustado"]["recursos_fundeb"], abs=0.01)
    assert linha["recursos_fundeb_A"] == pytest.approx(antigo["municipio_original"]["recursos_fundeb"], abs=0.01)


def test_cenario_por_exercicio(client):
    dados = client.post("/api/cenarios", json={"ano_exercicio": 2025}).json()
    assert dados["metadados"]["base"]["base_id"] == "fundeb-2025"
    r = client.post("/api/cenarios", json={"base_id": "fundeb-2026", "ano_exercicio": 2025})
    assert r.status_code == 422 and "exercício" in r.json()["detail"]


def test_cenario_invalido_retorna_422(client):
    r = client.post("/api/cenarios", json={"ajustes": [{"ibge": 1, "categoria": "x", "valor": 1}]})
    assert r.status_code == 422
    r = client.post("/api/cenarios", json={"recorte": "propag"})
    assert r.status_code == 422 and "Propag" in r.json()["detail"]


def test_pesos_alterados_so_para_admin(client):
    from services.bases import carregar_base
    n = len(carregar_base("fundeb-2026").pesos)
    corpo = {"parametros": {"pesos_vaaf": [1.0] * n}}
    assert client.post("/api/cenarios", json=corpo).status_code == 200
    main.app.dependency_overrides[get_current_user] = lambda: USUARIO
    assert client.post("/api/cenarios", json=corpo).status_code == 403


def test_obter_e_exportar_mesmo_cenario(client):
    dados = _cenario(client, receita={"tipo": "crescimento", "taxa": 0.04})
    cid = dados["metadados"]["cenario_id"]
    r = client.get(f"/api/cenarios/{cid}", params={"recorte": "selecionadas"})
    assert r.status_code == 200
    assert {x["ibge"] for x in r.json()["comparacao"]["linhas"]} == {21, 22}
    for formato, assinatura in [("csv", b"\xef\xbb\xbf"), ("xlsx", b"PK"), ("pdf", b"%PDF")]:
        r = client.get(f"/api/cenarios/{cid}/exportar", params={"formato": formato})
        assert r.status_code == 200, (formato, r.text[:200])
        assert r.content.startswith(assinatura)
        assert cid[:8] in r.headers["content-disposition"]
    assert client.get(f"/api/cenarios/{cid}/exportar", params={"formato": "doc"}).status_code == 422
    assert client.get("/api/cenarios/inexistente").status_code == 404


def test_calibracao_endpoint(client):
    r = client.get("/api/bases/fundeb-2026/calibracao")
    assert r.status_code == 200 and r.json()["disponivel"]


def test_dados_por_uf_nao_excluem_inabilitados_dos_totais():
    from api_simulacao import SimulacaoRequest, executar_simulacao, gerar_dados_por_uf
    from dados.fundeb_dataset import carregar_dataset
    ds = carregar_dataset(2026)
    sim = executar_simulacao(SimulacaoRequest(**{f"complementacao_{k}": v for k, v in ds.defaults_complementacao.items()}), ds)
    por_uf = {d["uf"]: d for d in gerar_dados_por_uf(sim)}
    assert len(por_uf) == 27
    assert sum(d["recursos_fundeb"] for d in por_uf.values()) == pytest.approx(sim["recursos_fundeb"].sum(), rel=1e-9)
