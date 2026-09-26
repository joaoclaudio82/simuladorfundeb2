"""Auditoria reproduzível, sem alterar dados ou marcar homologação."""
import argparse
import json
from services.bases import BaseRepository, DEFAULT_CATALOG, calibrar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_id", nargs="?", default="legado")
    parser.add_argument("--catalogo", default=str(DEFAULT_CATALOG))
    args = parser.parse_args()
    base = BaseRepository(args.catalogo).obter(args.base_id)
    print(json.dumps({"base": base.resumo(), "calibracao": calibrar(base)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
