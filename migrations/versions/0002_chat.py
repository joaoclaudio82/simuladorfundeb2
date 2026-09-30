"""Tabelas do chat de consulta. Não entram no backup das simulações."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    from app.db.chat_schema import metadata

    metadata.create_all(op.get_bind())


def downgrade():
    from app.db.chat_schema import metadata

    metadata.drop_all(op.get_bind())
