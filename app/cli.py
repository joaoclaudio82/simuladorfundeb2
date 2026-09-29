"""Operação: python -m app.cli --help. Segredos são lidos do ambiente/terminal."""

import argparse
import getpass
import json
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError


def main():
    parser = argparse.ArgumentParser(description="Persistência e migração do Simulador FUNDEB")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="Aplicar migrações do esquema")
    p = sub.add_parser(
        "import-data", help="Conferir e importar todas as fontes e bases disponíveis"
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--activate",
        action="store_true",
        help="Ativar novas versões explicitamente; mantém anteriores",
    )
    for name in ("import-users", "import-live"):
        p = sub.add_parser(name)
        p.add_argument("path", type=Path)
        p.add_argument("--dry-run", action="store_true")
    for name in ("backup", "verify-backup", "restore"):
        p = sub.add_parser(name)
        p.add_argument("path", type=Path)
    sub.add_parser("create-admin", help="Criar administrador sem senha em argumento de shell")
    args = parser.parse_args()
    from app.db.session import migrate

    if args.command == "migrate":
        migrate()
        result = {"revision": "0001"}
    elif args.command == "import-data":
        from app.ingestion.migrate import import_data

        result = import_data(dry_run=args.dry_run, activate=args.activate)
    elif args.command == "import-users":
        from app.ingestion.migrate import import_users

        result = import_users(args.path, dry_run=args.dry_run)
    elif args.command == "import-live":
        from app.ingestion.live_scenarios import import_live

        result = import_live(args.path, dry_run=args.dry_run)
    elif args.command in ("backup", "verify-backup", "restore"):
        from app.db import backup as b

        function = {"backup": b.backup, "verify-backup": b.verify_backup, "restore": b.restore}[
            args.command
        ]
        result = function(args.path)
    else:
        from app.auth.database import create_user
        from app.auth.models import Role
        from app.auth.security import normalizar_cpf, validar_cpf

        cpf = normalizar_cpf(input("CPF: "))
        if not validar_cpf(cpf):
            raise ValueError("CPF inválido.")
        password = getpass.getpass("Senha (mínimo 12 caracteres): ")
        if len(password) < 12 or password != getpass.getpass("Confirme a senha: "):
            raise ValueError("Senha curta ou confirmação diferente.")
        create_user(cpf, password, Role.admin, input("Nome: "))
        result = {"created": True}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SQLAlchemyError:
        raise SystemExit(
            "Operação de banco falhou. Confira conexão, esquema e conflitos; credenciais não são exibidas."
        )
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        raise SystemExit(str(exc))
