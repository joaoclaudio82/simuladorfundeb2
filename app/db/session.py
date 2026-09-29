"""Uma transação por operação; migrações explícitas em produção."""

from functools import lru_cache
from threading import RLock
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from app.core.config import ROOT, database_url, production

_LOCK = RLock()
_READY = set()


@lru_cache(maxsize=16)
def engine_for(url):
    parsed = make_url(url)
    kwargs = {"pool_pre_ping": True, "hide_parameters": True}
    if parsed.get_backend_name() == "sqlite":
        if parsed.database and parsed.database != ":memory:":
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        if not parsed.database or parsed.database == ":memory:":
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def pragmas(dbapi, _record):
            dbapi.execute("PRAGMA foreign_keys=ON")
            dbapi.execute("PRAGMA busy_timeout=30000")

    return engine


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
