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


def _alembic_config():
    from alembic.config import Config

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


@lru_cache(maxsize=1)
def head_revision():
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(_alembic_config()).get_current_head()


def migrate(engine=None):
    from alembic import command

    engine = engine or engine_for(database_url())
    config = _alembic_config()
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
                if revision != head_revision():
                    raise RuntimeError(
                        "Execute python -m app.cli migrate antes de iniciar a aplicação."
                    )
                _READY.add(engine)
            else:
                migrate(engine)
    return engine
