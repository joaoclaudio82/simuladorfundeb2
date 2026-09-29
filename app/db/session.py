"""Uma transação por operação; migrações explícitas em produção."""

from functools import lru_cache
from threading import RLock
from sqlalchemy import create_engine, text
from app.core.config import ROOT, database_url, production, require_postgresql

_LOCK = RLock()
_READY = set()


@lru_cache(maxsize=16)
def engine_for(url):
    require_postgresql(url)
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)


def migrate(engine=None):
    from alembic.config import Config
    from alembic import command

    engine = engine or engine_for(database_url())
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    _READY.add(engine)


def get_engine(url=None):
    engine = engine_for(url or database_url())
    with _LOCK:
        if engine not in _READY:
            if production():
                with engine.connect() as conn:
                    revision = conn.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalar()
                if revision != "0001":
                    raise RuntimeError(
                        "Execute python -m app.cli migrate antes de iniciar a aplicação."
                    )
                _READY.add(engine)
            else:
                migrate(engine)
    return engine
