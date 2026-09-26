"""python -m scripts.importar_base manifesto.json [--registrar] [--catalogo caminho]."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from services.bases import DEFAULT_CATALOG, BaseRepository, carregar_base, calibrar


def importar(manifesto, catalogo=DEFAULT_CATALOG, registrar=False):
    manifesto, catalogo = Path(manifesto).resolve(), Path(catalogo).resolve()
    meta = json.loads(manifesto.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", meta.get("id", "")):
        raise ValueError("ID de base inválido.")
    catalogo_bytes = catalogo.read_bytes()
    catalog = json.loads(catalogo_bytes)
    if any(m["id"] == meta["id"] for m in catalog["bases"]):
        raise ValueError("ID já existe. Use outro ID para preservar versões anteriores.")
    base = carregar_base(manifesto.parent, meta, verificar_hash=False)
    comparacao = calibrar(base)
    if meta["status"] == "homologada" and (not comparacao["aprovada"] or not comparacao.get("referencia_oficial")):
        raise ValueError("Base homologada exige calibração aprovada contra referência oficial declarada.")
    anterior = BaseRepository(catalogo).obter(catalog["bases"][-1]["id"])
    atual_ids, anterior_ids = set(base.tabelas["entes"].ibge), set(anterior.tabelas["entes"].ibge)
    relatorio = {"base_id": meta["id"], "registrada": False, "redes": len(atual_ids),
                 "novas_redes": sorted(atual_ids-anterior_ids), "redes_ausentes": sorted(anterior_ids-atual_ids),
                 "novas_categorias": sorted(set(base.etapas)-set(anterior.etapas)),
                 "categorias_ausentes": sorted(set(anterior.etapas)-set(base.etapas)), "calibracao": comparacao}
    if not registrar:
        return relatorio
    # Escrita local de administração, sem endpoint público de upload.
    destino = catalogo.parent / meta["id"]
    if destino.exists():
        raise ValueError("Diretório de destino já existe; não será sobrescrito.")
    lock = catalogo.with_suffix(".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as e:
        raise ValueError("Outra importação está em andamento.") from e
    os.close(fd)
    staging = None
    publicado = False
    movido = False
    try:
        if catalogo.read_bytes() != catalogo_bytes:
            raise ValueError("Catálogo alterado durante a validação; execute novamente.")
        staging = Path(tempfile.mkdtemp(prefix="importacao-", dir=catalogo.parent))
        nova = deepcopy(base.meta)
        nova["arquivos"] = {}
        for nome, relativo in meta["arquivos"].items():
            arquivo = (manifesto.parent / relativo).resolve()
            target_name = nome + arquivo.suffix.lower()
            shutil.copyfile(arquivo, staging / target_name)
            nova["arquivos"][nome] = str(Path(meta["id"]) / target_name)
        # Conferir cópias contra os hashes calculados antes da validação.
        revisao = deepcopy(nova)
        revisao["arquivos"] = {k: Path(v).name for k, v in nova["arquivos"].items()}
        carregar_base(staging, revisao)
        (staging / "relatorio_importacao.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
        staging.rename(destino)
        movido = True
        staging = None
        catalog["bases"].append(nova)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=catalogo.parent, delete=False) as temp:
            json.dump(catalog, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp.name, catalogo)
        publicado = True
        relatorio["registrada"] = True
        return relatorio
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        if movido and not publicado and destino.exists():
            shutil.rmtree(destino)
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifesto")
    parser.add_argument("--catalogo", default=str(DEFAULT_CATALOG))
    parser.add_argument("--registrar", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(importar(args.manifesto, args.catalogo, args.registrar), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as e:
        parser.exit(1, str(e) + "\n")


if __name__ == "__main__":
    main()
