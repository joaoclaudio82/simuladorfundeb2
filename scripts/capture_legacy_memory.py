"""Executar DENTRO do processo antigo, antes de reiniciá-lo. Ver docs/MIGRACAO.md.

Um novo processo Python não enxerga os cenários na memória do servidor anterior.
Esta função recebe a instância viva do repositório; não importa/reinicia o servidor.
"""

from dataclasses import fields
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import zipfile


def capturar(repositorio_vivo, destino):
    codec_path = Path(__file__).resolve().parents[1] / "app/db/codec.py"
    spec = importlib.util.spec_from_file_location("fundeb_capture_codec", codec_path)
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    if not hasattr(repositorio_vivo, "_itens") or not hasattr(repositorio_vivo, "_lock"):
        raise ValueError("Passe a instância em memória do repositório antigo.")
    fd = os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    manifest = {"format": "fundeb-live-scenarios-v1", "scenarios": []}
    try:
        with (
            os.fdopen(fd, "wb") as file,
            zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED) as archive,
        ):
            with repositorio_vivo._lock:
                for ident, result in repositorio_vivo._itens.items():
                    body = codec.pack({f.name: getattr(result, f.name) for f in fields(result)})
                    name = f"{len(manifest['scenarios'])}.zip"
                    archive.writestr(name, body)
                    manifest["scenarios"].append(
                        {"id": ident, "file": name, "sha256": hashlib.sha256(body).hexdigest()}
                    )
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
    except BaseException:
        Path(destino).unlink(missing_ok=True)
        raise
    return {"captured": len(manifest["scenarios"]), "path": str(destino)}


if __name__ == "__main__":
    raise SystemExit(
        "A captura exige a instância viva no processo antigo. Leia docs/MIGRACAO.md; não reinicie o servidor."
    )
