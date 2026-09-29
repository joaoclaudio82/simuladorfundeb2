import uuid
from sqlalchemy import select
from app.db import schema as s
from app.db.session import get_engine
from app.db.codec import pack, sha256, unpack
from app.repositories.common import now, audit


def save_run(path, request_body, response_body, capture):
    from app.services.cenarios import VERSAO_MOTOR

    engine = get_engine()
    ident = uuid.uuid4().hex
    snapshot = pack(capture["calculations"])
    with engine.begin() as conn:
        conn.execute(
            s.legacy_runs.insert().values(
                id=ident,
                created_at=now(),
                owner_cpf=capture["owner_cpf"],
                path=path,
                request_json=request_body.decode("utf-8"),
                response=response_body,
                snapshot=snapshot,
                snapshot_sha256=sha256(snapshot),
                engine_version=VERSAO_MOTOR,
            )
        )
        audit(conn, "legacy.save", ident, {"calculations": len(capture["calculations"])})
    return ident


def list_runs(owner_cpf, *, admin=False, limit=50, offset=0):
    query = select(
        s.legacy_runs.c.id,
        s.legacy_runs.c.created_at,
        s.legacy_runs.c.path,
        s.legacy_runs.c.engine_version,
    )
    if not admin:
        query = query.where(s.legacy_runs.c.owner_cpf == owner_cpf)
    with get_engine().connect() as conn:
        return [
            dict(r)
            for r in conn.execute(
                query.order_by(s.legacy_runs.c.created_at.desc(), s.legacy_runs.c.id)
                .limit(limit)
                .offset(offset)
            ).mappings()
        ]


def get_run(ident, user):
    query = select(s.legacy_runs).where(s.legacy_runs.c.id == ident)
    if user.role.value != "admin":
        query = query.where(s.legacy_runs.c.owner_cpf == user.cpf)
    with get_engine().connect() as conn:
        row = conn.execute(query).mappings().first()
    if row and sha256(row["snapshot"]) != row["snapshot_sha256"]:
        raise ValueError("Snapshot corrompido.")
    return row
