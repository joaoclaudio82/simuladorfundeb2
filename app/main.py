"""Composição da API; rotas históricas conservam seu contrato."""
from __future__ import annotations
import os
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query
from app.core.config import validate_configuration, production
from app.api.persistence import PersistLegacyMiddleware
from app.db.session import get_engine
validate_configuration()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from app.auth.database import init_db, seed_admin_if_empty
from app.auth.routes import router as auth_router
from app.ingestion.fundeb_dataset import ESTADOS_REGIOES, carregar_dataset, listar_entes_por_uf
from app.auth.deps import get_current_user
from app.auth.models import Role, UserRecord
from app.schemas.cenarios import AVISO_METODOLOGICO, CenarioRequest, Recorte
from app.services.bases import ErroBase, carregar_base, listar_bases, resolver_base_id
from app.services.calibracao import comparar_com_oficial
from app.services.cenarios import ErroCenario, executar_cenario, repositorio
from app.services.comparacao import ErroRecorte, montar_comparacao
from app.services.exportacao import EXPORTADORES, nome_arquivo
from app.api.legacy import (
    SimulacaoRequest,
    SimulacaoMunicipioRequest,
    _resposta_simular,
    executar_simulacao,
    extrair_detalhes_municipio,
    registrar_rotas_ano,
    sanitize_for_json,
)

print("Carregando dados 2024...")
_DS2024 = carregar_dataset(2024)
pesos = _DS2024.pesos
matriculas = _DS2024.matriculas
complementar = _DS2024.complementar
cenario_atual = _DS2024.cenario_atual
cenario_atual_agregada = _DS2024.cenario_atual_agregada
cenario_ufs_atual = _DS2024.cenario_ufs_atual
ETAPAS_NOMES = _DS2024.etapas_nomes
print("Dados 2024 carregados.")

# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app):
    init_db()
    seed_admin_if_empty()
    if production():
        # Refuse partial deployments: every supported exercise must already be imported.
        for year in (2024, 2025, 2026):
            carregar_dataset(year)
    yield


app = FastAPI(title="Simulador FUNDEB v2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("FUNDEB_ALLOWED_ORIGINS", "").split(",") if x.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.add_middleware(PersistLegacyMiddleware)
app.include_router(auth_router, prefix="/api")


# ---------------------------------------------------------------------------
# Rotas de dados
# ---------------------------------------------------------------------------

@app.get("/api/estados")
def listar_estados(_user: UserRecord = Depends(get_current_user)):
    ufs = sorted(complementar["uf"].unique().tolist())
    return {"estados": ufs, "regioes": ESTADOS_REGIOES}


@app.get("/api/municipios")
def listar_municipios(uf: str, _user: UserRecord = Depends(get_current_user)):
    df = listar_entes_por_uf(complementar, uf)
    return sanitize_for_json(df.to_dict(orient="records"))


@app.get("/api/pesos")
def obter_pesos(_user: UserRecord = Depends(get_current_user)):
    from app.ingestion.fundeb_dataset import familia_segmento

    out = pesos.to_dict(orient="records")
    for row in out:
        row["familia"] = familia_segmento(row["nome"])
    return sanitize_for_json(out)


@app.get("/api/etapas")
def obter_etapas(_user: UserRecord = Depends(get_current_user)):
    """Retorna as etapas de matrícula com nomes amigáveis."""
    return ETAPAS_NOMES


@app.get("/api/municipio/{ibge}/matriculas")
def obter_matriculas_municipio(ibge: int, _user: UserRecord = Depends(get_current_user)):
    row = matriculas[matriculas["ibge"] == ibge]
    if len(row) == 0:
        raise HTTPException(404, "Município não encontrado")
    etapas = pesos["etapa"].tolist()
    row_dict = row.iloc[0].to_dict()
    mat = {e: row_dict.get(e, 0) for e in etapas}
    info = complementar[complementar["ibge"] == ibge].iloc[0].to_dict()
    return sanitize_for_json({
        "ibge": ibge,
        "nome": info.get("nome", ""),
        "uf": info.get("uf", ""),
        "matriculas": mat,
        "recursos_vaaf": info.get("recursos_vaaf", 0),
        "recursos_vaat": info.get("recursos_vaat", 0),
        "nse": info.get("nse", 1),
        "nf": info.get("nf", 1),
        "peso_vaar": info.get("peso_vaar", 0),
        "inabilitados_vaat": bool(info.get("inabilitados_vaat", False)),
    })


@app.get("/api/cenario-atual/resumo")
def resumo_cenario_atual(_user: UserRecord = Depends(get_current_user)):
    """Retorna dados do cenário atual para comparação."""
    ufs = cenario_ufs_atual.to_dict(orient="records") if cenario_ufs_atual is not None else []
    agregada = cenario_atual_agregada.to_dict(orient="records") if cenario_atual_agregada is not None else []
    return sanitize_for_json({"ufs": ufs, "agregada": agregada})


# ---------------------------------------------------------------------------
# Rotas de simulação
# ---------------------------------------------------------------------------

@app.post("/api/simular")
def simular(req: SimulacaoRequest, user: UserRecord = Depends(get_current_user)):
    try:
        return _resposta_simular(req, 2024, user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/simular/completo")
def simular_completo(req: SimulacaoRequest, user: UserRecord = Depends(get_current_user)):
    try:
        sim = executar_simulacao(req, _DS2024, user=user)
        sim["inabilitados_vaat"] = sim["inabilitados_vaat"].apply(
            lambda x: "Verdadeiro" if x else "Falso"
        )
        return sanitize_for_json(sim.fillna(0).to_dict(orient="records"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/simular/municipio")
def simular_municipio(req: SimulacaoMunicipioRequest, user: UserRecord = Depends(get_current_user)):
    try:
        mat = matriculas.copy()
        if req.matriculas_ajustadas:
            idx = mat.index[mat["ibge"] == req.ibge]
            if len(idx) == 0:
                raise HTTPException(404, "Município não encontrado")
            for etapa, valor in req.matriculas_ajustadas.items():
                if etapa in mat.columns:
                    mat.loc[idx, etapa] = valor
        sim_original = executar_simulacao(req, _DS2024, matriculas, user=user)
        sim_ajustada = executar_simulacao(req, _DS2024, mat, user=user)
        mun_original = extrair_detalhes_municipio(sim_original, req.ibge, matriculas)
        mun_ajustado = extrair_detalhes_municipio(sim_ajustada, req.ibge, mat)
        uf = mun_original["uf"]
        return sanitize_for_json({
            "municipio_original": mun_original,
            "municipio_ajustado": mun_ajustado,
            "estado_original": sim_original[sim_original["uf"] == uf].to_dict(orient="records"),
            "estado_ajustado": sim_ajustada[sim_ajustada["uf"] == uf].to_dict(orient="records"),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# Rotas por exercício (2025 e 2026)
registrar_rotas_ano(app, 2025)
registrar_rotas_ano(app, 2026)


# ---------------------------------------------------------------------------
# Rotas de cenários (FND-03, FND-04, FND-05, FND-07, FND-08, FND-11)
# ---------------------------------------------------------------------------

def _base_ou_erro(base_id: Optional[str], ano_exercicio: Optional[int] = None):
    try:
        return carregar_base(resolver_base_id(base_id, ano_exercicio))
    except ErroBase as e:
        texto = str(e)
        codigo = 404 if ("desconhecido" in texto or "nenhuma base" in texto) else 422 if "informe base_id" in texto else 503
        raise HTTPException(codigo, texto)


def _cenario_ou_404(cenario_id: str):
    res = repositorio.obter(cenario_id)
    if res is None:
        raise HTTPException(404, "Cenário não encontrado")
    return res


def _ler_selecionadas(selecionadas: Optional[str], res) -> list[int]:
    if selecionadas is None:
        return res.requisicao.get("selecionadas", [])
    try:
        return [int(x) for x in selecionadas.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(422, "selecionadas deve ser uma lista de códigos separados por vírgula")


def _resposta_cenario(res, recorte, selecionadas):
    try:
        comparacao = montar_comparacao(res, recorte, selecionadas)
    except ErroRecorte as e:
        raise HTTPException(422, str(e))
    return sanitize_for_json({
        "metadados": res.metadados(),
        "ajustes": res.ajustes.to_dict(orient="records"),
        "comparacao": comparacao,
    })


@app.get("/api/bases")
def api_listar_bases(_user: UserRecord = Depends(get_current_user)):
    return {"bases": listar_bases(), "aviso": AVISO_METODOLOGICO}


@app.get("/api/bases/{base_id}")
def api_obter_base(base_id: str, _user: UserRecord = Depends(get_current_user)):
    base = _base_ou_erro(base_id)
    return sanitize_for_json({
        **base.identificacao(),
        "pendencias": base.manifesto.get("pendencias", []),
        "parametros_referencia": base.parametros_referencia,
        "quantidade_entes": int(len(base.entes)),
        "quantidade_categorias": len(base.etapas),
        "avisos": base.avisos,
    })


@app.get("/api/bases/{base_id}/calibracao")
def api_calibracao(base_id: str, _user: UserRecord = Depends(get_current_user)):
    return sanitize_for_json(comparar_com_oficial(_base_ou_erro(base_id)))


@app.get("/api/entes")
def api_listar_entes(base_id: Optional[str] = None, uf: Optional[str] = None, tipo: Optional[str] = None,
                     _user: UserRecord = Depends(get_current_user)):
    base = _base_ou_erro(base_id)
    ent = base.entes
    if uf:
        ent = ent[ent["uf"] == uf.upper()]
    if tipo:
        ent = ent[ent["tipo_rede"] == tipo]
    return {"base_id": base.base_id, "entes": ent.to_dict(orient="records")}


@app.get("/api/entes/{ibge}/matriculas")
def api_matriculas_ente(ibge: int, base_id: Optional[str] = None, _user: UserRecord = Depends(get_current_user)):
    base = _base_ou_erro(base_id)
    linha = base.matriculas[base.matriculas["ibge"] == ibge]
    if len(linha) == 0:
        raise HTTPException(404, "Ente não encontrado na base")
    ente = base.entes[base.entes["ibge"] == ibge].iloc[0].to_dict()
    mat = linha.iloc[0]
    return sanitize_for_json({
        **ente,
        "base_id": base.base_id,
        "matriculas": {e: float(mat[e]) for e in base.etapas},
        "nomes_categorias": dict(zip(base.pesos["etapa"], base.pesos["nome"])),
    })


@app.post("/api/cenarios")
def api_criar_cenario(req: CenarioRequest, user: UserRecord = Depends(get_current_user)):
    if (req.parametros.pesos_vaaf is not None or req.parametros.pesos_vaat is not None) and user.role != Role.admin:
        raise HTTPException(403, "Somente administradores podem simular com pesos alterados")
    base = _base_ou_erro(req.base_id, req.ano_exercicio)
    from app.repositories.bases import ensure_file_base
    ensure_file_base(base)
    try:
        res = executar_cenario(req, base)
    except ErroCenario as e:
        raise HTTPException(422, str(e))
    resposta = _resposta_cenario(res, req.recorte, req.selecionadas)
    repositorio.guardar(res, owner_cpf=user.cpf, base_version=getattr(base, "version_id", None), resposta=resposta)
    return resposta


@app.get("/api/cenarios/{cenario_id}")
def api_obter_cenario(cenario_id: str, recorte: Optional[Recorte] = None, selecionadas: Optional[str] = None,
                      _user: UserRecord = Depends(get_current_user)):
    res = _cenario_ou_404(cenario_id)
    if recorte is None and selecionadas is None:
        original = repositorio.resposta_original(cenario_id)
        if original is not None:
            return original
    return _resposta_cenario(res, recorte or res.requisicao["recorte"], _ler_selecionadas(selecionadas, res))


@app.get("/api/cenarios/{cenario_id}/exportar")
def api_exportar_cenario(cenario_id: str, formato: str = "csv", recorte: Optional[Recorte] = None,
                         selecionadas: Optional[str] = None, _user: UserRecord = Depends(get_current_user)):
    res = _cenario_ou_404(cenario_id)
    if formato not in EXPORTADORES:
        raise HTTPException(422, f"formato deve ser um de {sorted(EXPORTADORES)}")
    funcao, mime = EXPORTADORES[formato]
    try:
        conteudo = repositorio.exportar(res, formato, recorte or res.requisicao["recorte"], _ler_selecionadas(selecionadas, res), funcao)
    except ErroRecorte as e:
        raise HTTPException(422, str(e))
    return Response(
        content=conteudo,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo(res, formato)}"'},
    )


# ---------------------------------------------------------------------------
# Histórico persistente
# ---------------------------------------------------------------------------

@app.get("/api/historico")
def historico(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
              user: UserRecord = Depends(get_current_user)):
    from app.repositories.legacy import list_runs
    admin = user.role == Role.admin
    return {"cenarios": repositorio.listar(user.cpf, admin=admin, limit=limit, offset=offset),
            "simulacoes_legadas": list_runs(user.cpf, admin=admin, limit=limit, offset=offset),
            "limit": limit, "offset": offset}


@app.get("/api/historico/legado/{ident}")
def historico_legado(ident: str, user: UserRecord = Depends(get_current_user)):
    from app.repositories.legacy import get_run
    row = get_run(ident, user)
    if row is None:
        raise HTTPException(404, "Simulação não encontrada")
    return Response(content=row["response"], media_type="application/json")


@app.get("/api/historico/legado/{ident}/snapshot")
def snapshot_legado(ident: str, user: UserRecord = Depends(get_current_user)):
    from app.repositories.legacy import get_run
    row = get_run(ident, user)
    if row is None:
        raise HTTPException(404, "Simulação não encontrada")
    return Response(content=row["snapshot"], media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="simulacao-{ident}.zip"'})


@app.get("/health/ready")
def health_ready():
    from sqlalchemy import text
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Servir frontend
# ---------------------------------------------------------------------------

STATIC_DIR = str(Path(__file__).resolve().parents[1] / "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/login.html")
def serve_login():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))


@app.get("/historico.html")
def serve_historico():
    return FileResponse(os.path.join(STATIC_DIR, "historico.html"))


@app.get("/admin.html")
def serve_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import uvicorn
    # reload=False evita reinícios em loop no Windows ao salvar arquivos do projeto
    reload = os.environ.get("FUNDEB_RELOAD", "").lower() in ("1", "true", "yes")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload)
