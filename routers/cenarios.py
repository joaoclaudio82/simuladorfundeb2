import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from schemas.cenarios import CenarioRequest, TrajetoriaRequest
from services.bases import BaseRepository, DEFAULT_CATALOG, calibrar
from services.cenarios import CenarioService, publico
from services.exportacao import exportar
from services.storage import ScenarioStore

router = APIRouter(prefix="/api", tags=["Cenários nacionais"])
bases = BaseRepository(os.environ.get("FUNDEB_CATALOGO", DEFAULT_CATALOG))
store = ScenarioStore(os.environ.get("FUNDEB_CENARIOS_DB", Path(__file__).resolve().parents[1] / ".runtime/cenarios.sqlite3"),
                      limite=int(os.environ.get("FUNDEB_MAX_CENARIOS", "1000")))
service = CenarioService(bases, store)


def entrada_invalida(e):
    return HTTPException(status_code=422, detail=str(e))


@router.get("/bases")
def listar_bases():
    return [{k: v for k, v in m.items() if k not in {"arquivos", "hashes"}} for m in bases.listar()]


@router.get("/bases/{base_id}")
def detalhes_base(base_id: str):
    try:
        return bases.obter(base_id).resumo()
    except ValueError as e:
        raise entrada_invalida(e) from e


@router.get("/bases/{base_id}/auditoria")
def auditar_base(base_id: str):
    try:
        base = bases.obter(base_id)
        return {"base": base.resumo(), "calibracao": calibrar(base)}
    except ValueError as e:
        raise entrada_invalida(e) from e


@router.get("/entes")
def listar_entes(base_id: str = "legado", uf: str | None = None, tipo: str | None = None):
    try:
        df = bases.obter(base_id).tabelas["entes"]
        if uf:
            if uf not in set(df.uf):
                raise ValueError("UF desconhecida.")
            df = df[df.uf == uf]
        if tipo:
            if tipo not in {"estadual", "municipal", "distrital", "estaduais"}:
                raise ValueError("Tipo de rede inválido.")
            df = df[df.tipo.isin(["estadual", "distrital"])] if tipo == "estaduais" else df[df.tipo == tipo]
        return df.sort_values(["uf", "tipo", "nome"]).to_dict("records")
    except ValueError as e:
        raise entrada_invalida(e) from e


@router.get("/entes/{ibge}/matriculas")
def matriculas_ente(ibge: int, base_id: str = "legado"):
    try:
        base = bases.obter(base_id)
        cadastro = base.tabelas["entes"].set_index("ibge")
        if ibge not in cadastro.index:
            raise HTTPException(404, "Ente federado não encontrado.")
        mat = base.tabelas["matriculas"].set_index("ibge").loc[ibge, base.etapas]
        return {"ibge": ibge, **cadastro.loc[ibge].to_dict(), "matriculas": mat.to_dict()}
    except ValueError as e:
        raise entrada_invalida(e) from e


@router.post("/cenarios", status_code=201)
def criar_cenario(req: CenarioRequest):
    try:
        return publico(service.executar(req))
    except ValueError as e:
        raise entrada_invalida(e) from e


@router.post("/trajetorias", status_code=201)
def criar_trajetoria(req: TrajetoriaRequest):
    try:
        return service.trajetoria(req)
    except ValueError as e:
        raise entrada_invalida(e) from e


@router.get("/cenarios/{cenario_id}")
def obter_cenario(cenario_id: str, completo: bool = False):
    try:
        r = store.obter(cenario_id)
        return r if completo else publico(r)
    except KeyError as e:
        raise HTTPException(404, "Cenário não encontrado.") from e


@router.get("/cenarios/{cenario_id}/exportar")
def exportar_cenario(cenario_id: str, formato: str = "csv", comparacao: str = "B-A", indicador: str = "recursos_fundeb"):
    try:
        resultado = store.obter(cenario_id)
        data, tipo = exportar(resultado, formato, comparacao, indicador)
        return Response(data, media_type=tipo, headers={"Content-Disposition":
            f'attachment; filename="fundeb_{cenario_id}_{comparacao}.{formato}"'})
    except KeyError as e:
        raise HTTPException(404, "Cenário não encontrado.") from e
    except ValueError as e:
        raise entrada_invalida(e) from e
