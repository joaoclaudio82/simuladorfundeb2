"""Configuração central. Valores secretos nunca entram em logs ou relatórios."""

import os
from pathlib import Path
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]


def production():
    return os.getenv("FUNDEB_ENV", "development") == "production"


def database_url():
    value = os.getenv("FUNDEB_DATABASE_URL")
    if value:
        return require_postgresql(value)
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
    raise RuntimeError(
        "Configure FUNDEB_DATABASE_URL (postgresql+psycopg) ou FUNDEB_DB_HOST. PostgreSQL é obrigatório."
    )


def require_postgresql(url):
    try:
        driver = make_url(url).drivername
    except Exception:
        raise ValueError("URL de banco inválida; use postgresql+psycopg.") from None
    if driver != "postgresql+psycopg":
        raise ValueError("Use postgresql+psycopg: PostgreSQL é o único banco da aplicação.")
    return url


def validate_configuration():
    database_url()
    if os.getenv("FUNDEB_DATA_SOURCE", "database") != "database":
        raise RuntimeError(
            "A aplicação consulta somente PostgreSQL; use import-data para carregar arquivos."
        )
    if production():
        secret = os.getenv("FUNDEB_SECRET_KEY", "")
        if len(secret) < 32 or secret.startswith("dev-fundeb"):
            raise RuntimeError(
                "Produção exige FUNDEB_SECRET_KEY aleatória com pelo menos 32 caracteres."
            )


def cookie_secure():
    return production() or os.getenv("FUNDEB_COOKIE_SECURE", "false").lower() == "true"
