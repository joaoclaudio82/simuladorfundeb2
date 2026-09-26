from copy import deepcopy
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app, gerar_dados_por_uf, gerar_resumo
import routers.cenarios as rotas
from schemas.cenarios import CenarioRequest
from scripts.importar_base import importar
from services.bases import BaseRepository, carregar_base, calibrar, hash_arquivo
from services.cenarios import CenarioService
from services.storage import ScenarioStore
from simulador import simula_fundeb


@pytest.fixture
def client(servico, monkeypatch):
    monkeypatch.setattr(rotas, "service", servico)
    monkeypatch.setattr(rotas, "store", servico.store)
    with TestClient(app) as c:
        yield c


def test_api_criar_recuperar_exportar_e_erro(client):
    response = client.post("/api/cenarios", json={"base_id": "teste", "ano_exercicio": 2026})
    assert response.status_code == 201, response.text
    r = response.json()
    assert "dados" not in r and len(r["comparativos"]["B-A"]["linhas"]) == 4
    assert client.get(f"/api/cenarios/{r['id']}").json() == r
    assert len(client.get(f"/api/cenarios/{r['id']}?completo=true").json()["dados"]["A"]) == 6
    response = client.get(f"/api/cenarios/{r['id']}/exportar?formato=csv")
    assert response.status_code == 200
    assert r["id"] in response.headers["content-disposition"]
    assert client.get(f"/api/cenarios/{r['id']}/exportar?formato=exe").status_code == 422
    assert client.get("/api/cenarios/ausente").status_code == 404


@pytest.mark.parametrize("body", [
    {"base_id": "teste", "ano_exercicio": 2025},
    {"base_id": "teste", "fator_amazonico": True},
    {"base_id": "teste", "recorte": {"tipo": "propag"}},
    {"base_id": "teste", "parametros": {"min_nse": 2, "max_nse": 1}},
    {"base_id": "teste", "parametros": {"complementacao_vaaf": -1}},
    {"base_id": "teste", "parametros": {"pesos_vaaf": {"ausente": 1}}},
    {"base_id": "teste", "receita": {"rubricas": []}},
    {"base_id": "teste", "ajustes": [{"ibge": 23, "etapa": "regular", "valor": True}]},
])
def test_api_rejeita_entradas_invalidas(client, body):
    assert client.post("/api/cenarios", json=body).status_code == 422


def test_nao_finitos_retornam_json_422_sem_erro_de_serializacao(client):
    response = client.post("/api/cenarios", content='{"base_id":"teste","receita":{"taxa_percentual":NaN}}',
                           headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_catalogo_real_e_api_legada_nao_ocultam_rede_inabilitada(client, base_teste):
    assert client.get("/api/bases").json()[0]["ano_exercicio"] is None
    redes = client.get("/api/entes?base_id=legado&tipo=estaduais").json()
    assert len(redes) == 27 and any(x["uf"] == "AP" for x in redes)
    assert client.get("/api/entes/999999999/matriculas").status_code == 404
    assert client.post("/api/simular/municipio", json={"ibge": 999999999}).status_code == 404
    assert client.post("/api/simular/municipio", json={"ibge": 23, "matriculas_ajustadas": {"ausente": 1}}).status_code == 422
    b = base_teste
    r = simula_fundeb(b.tabelas["matriculas"], b.tabelas["complementar"], b.tabelas["pesos"], **b.meta["parametros"], arredondar=False)
    grupos = gerar_dados_por_uf(r)
    assert sum(x["recursos_fundeb"] for x in grupos) == pytest.approx(r.recursos_fundeb.sum(), abs=0.1)
    pi = next(x for x in grupos if x["uf"] == "PI")
    sub = r[r.uf == "PI"]
    assert pi["vaat_medio"] == pytest.approx(sub.recursos_vaat_final.sum() / sub.matriculas_vaat.sum(), abs=0.01)
    referencia = r.copy()
    referencia["nome"] = "Nome alterado"
    assert gerar_resumo(r, referencia)["maior_aumento_abs"] == 0


def arquivos_base(base, root):
    root.mkdir(parents=True, exist_ok=True)
    meta = deepcopy(base.meta)
    meta["arquivos"], meta["hashes"] = {}, {}
    for nome, tabela in base.tabelas.items():
        tabela.to_csv(root / f"{nome}.csv", index=False)
        meta["arquivos"][nome] = f"{nome}.csv"
        meta["hashes"][nome] = hash_arquivo(root / f"{nome}.csv")
    return meta


def test_loader_hash_duplicatas_cobertura_e_booleanos(base_teste, tmp_path):
    meta = arquivos_base(base_teste, tmp_path)
    b = carregar_base(tmp_path, meta)
    assert b.tabelas["complementar"].inabilitados_vaat.sum() == 1
    p = tmp_path / "matriculas.csv"
    p.write_text(p.read_text() + "\n")
    with pytest.raises(ValueError, match="mudou"):
        carregar_base(tmp_path, meta)
    d = pd.read_csv(p)
    pd.concat([d, d.iloc[:1]]).to_csv(p, index=False)
    with pytest.raises(ValueError, match="duplicados"):
        carregar_base(tmp_path, meta, verificar_hash=False)
    d.iloc[1:].to_csv(p, index=False)
    with pytest.raises(ValueError, match="Cobertura"):
        carregar_base(tmp_path, meta, verificar_hash=False)


def test_importacao_preliminar_preserva_versao_e_sinaliza_redes_novas(base_teste, tmp_path):
    original_dir = tmp_path / "dados"
    meta = arquivos_base(base_teste, original_dir)
    catalogo = original_dir / "catalogo.json"
    catalogo.write_text(json.dumps({"schema_version": 1, "bases": [meta]}))
    nova = deepcopy(base_teste)
    nova.meta["id"] = "preliminar-2026-v1"
    for nome in ("matriculas", "complementar", "entes"):
        row = nova.tabelas[nome].iloc[[1]].copy()
        row["ibge"] = 2300029
        nova.tabelas[nome] = pd.concat([nova.tabelas[nome], row], ignore_index=True)
    source = tmp_path / "entrada"
    manifest = arquivos_base(nova, source)
    path = source / "manifesto.json"
    path.write_text(json.dumps(manifest))
    r = importar(path, catalogo)
    assert r["novas_redes"] == [2300029] and not r["registrada"]
    assert len(BaseRepository(catalogo).listar()) == 1
    r = importar(path, catalogo, registrar=True)
    assert r["registrada"]
    assert len(BaseRepository(catalogo).obter("teste").tabelas["entes"]) == 6
    assert len(BaseRepository(catalogo).obter(nova.meta["id"]).tabelas["entes"]) == 7
    with pytest.raises(ValueError, match="já existe"):
        importar(path, catalogo, registrar=True)


def test_calibracao_identifica_ausencias_e_desvio_por_uf_sem_falsa_aprovacao(base_teste):
    b = base_teste
    ref = simula_fundeb(b.tabelas["matriculas"], b.tabelas["complementar"], b.tabelas["pesos"], **b.meta["parametros"], arredondar=False)
    b.tabelas["referencia"] = ref
    assert calibrar(b)["aprovada"]
    b.tabelas["referencia"] = ref.iloc[1:].copy()
    assert not calibrar(b)["aprovada"]
    b.tabelas["referencia"] = ref.copy()
    b.tabelas["referencia"].loc[0, "recursos_fundeb"] *= 2
    r = calibrar(b)
    assert not r["aprovada"]
    assert r["indicadores"][0]["fora_tolerancia"] == 1
    assert r["indicadores"][0]["por_uf"]


def test_snapshot_real_exporta_todas_as_5595_redes(tmp_path):
    from services.exportacao import exportar
    import csv
    service = CenarioService(BaseRepository(), ScenarioStore(tmp_path / "real.sqlite3"))
    r = service.executar(CenarioRequest(recorte={"tipo": "todas"}))
    data, _ = exportar(r, "csv")
    rows = list(csv.DictReader(data.decode("utf-8-sig").splitlines(), delimiter=";"))
    assert len(rows) == 5595
    assert len({x["ibge"] for x in rows}) == 5595
    assert all(float(x["recursos_fundeb_delta"]) == 0 for x in rows)
