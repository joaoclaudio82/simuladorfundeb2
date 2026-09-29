from alembic import context
from app.db.schema import metadata
from app.db.session import engine_for
from app.core.config import database_url


def run(connection):
    context.configure(connection=connection, target_metadata=metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if connection is not None:
    run(connection)
else:
    with engine_for(database_url()).connect() as connection:
        run(connection)
