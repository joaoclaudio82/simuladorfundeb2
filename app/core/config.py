"""Configuração central. Valores secretos nunca entram em logs ou relatórios."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def production():
    return os.getenv("FUNDEB_ENV", "development") == "production"


def database_url():
    value = os.getenv("FUNDEB_DATABASE_URL")
    if value:
        return value
    if os.getenv("FUNDEB_DB_HOST"):
        from sqlalchemy.engine import URL

        return URL.create(
            "postgresql+psycopg",
            username=os.getenv("FUNDEB_DB_USER", "fundeb"),
            password=os.getenv("FUNDEB_DB_PASSWORD", ""),
            host=os.environ["FUNDEB_DB_HOST"],
            port=int(os.getenv("FUNDEB_DB_PORT", "5432")),
            database=os.getenv("FUNDEB_DB_NAME", "fundeb"),
        ).render_as_string(hide_password=False)
    return "sqlite:///" + os.getenv("FUNDEB_USERS_DB", str(ROOT / "data/fundeb.db"))


def database_source():
    return os.getenv("FUNDEB_DATA_SOURCE", "database" if production() else "files") == "database"


def validate_configuration():
    if production():
        if not database_url().startswith("postgresql+psycopg://"):
            raise RuntimeError("Produção exige FUNDEB_DATABASE_URL com postgresql+psycopg.")
        secret = os.getenv("FUNDEB_SECRET_KEY", "")
        if len(secret) < 32 or secret.startswith("dev-fundeb"):
            raise RuntimeError(
                "Produção exige FUNDEB_SECRET_KEY aleatória com pelo menos 32 caracteres."
            )
        if not database_source():
            raise RuntimeError("Produção exige FUNDEB_DATA_SOURCE=database.")


def cookie_secure():
    return production() or os.getenv("FUNDEB_COOKIE_SECURE", "false").lower() == "true"
