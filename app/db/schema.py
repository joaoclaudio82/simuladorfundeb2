"""Esquema relacional. Snapshots são a fonte exata; projeções permitem consultas SQL."""

from sqlalchemy import (
    MetaData,
    Table,
    Column as C,
    String,
    Text,
    Integer,
    Float,
    LargeBinary,
    ForeignKey,
    ForeignKeyConstraint,
    CheckConstraint,
    Index,
)

metadata = MetaData()
users = Table(
    "users",
    metadata,
    C("cpf", String(11), primary_key=True),
    C("password_hash", Text, nullable=False),
    C("role", String(16), nullable=False),
    C("nome", Text),
    C("ativo", Integer, nullable=False),
    C("created_at", Text, nullable=False),
    CheckConstraint("role IN ('admin','usuario')"),
    CheckConstraint("ativo IN (0,1)"),
)
source_files = Table(
    "source_files",
    metadata,
    C("sha256", String(64), primary_key=True),
    C("size", Integer, nullable=False),
    C("content", LargeBinary, nullable=False),
)
archives = Table(
    "archives",
    metadata,
    C("id", String(64), primary_key=True),
    C("path", Text, nullable=False),
    C("source_sha256", ForeignKey("source_files.sha256"), nullable=False),
    C("source_commit", String(64), nullable=False),
    C("kind", String(32), nullable=False),
)
base_versions = Table(
    "base_versions",
    metadata,
    C("version_id", String(64), primary_key=True),
    C("base_id", String(100), nullable=False),
    C("year", Integer, nullable=False),
    C("created_at", Text, nullable=False),
    C("manifest", Text, nullable=False),
    C("snapshot", LargeBinary, nullable=False),
    C("snapshot_sha256", String(64), nullable=False),
    C("etl_sha256", String(64), nullable=False),
    C("source_commit", String(64), nullable=False),
)
base_aliases = Table(
    "base_aliases",
    metadata,
    C("base_id", String(100), primary_key=True),
    C("version_id", ForeignKey("base_versions.version_id"), nullable=False),
)
base_sources = Table(
    "base_sources",
    metadata,
    C("version_id", ForeignKey("base_versions.version_id"), primary_key=True),
    C("path", String(500), primary_key=True),
    C("source_sha256", ForeignKey("source_files.sha256"), nullable=False),
)
entities = Table(
    "entities",
    metadata,
    C("version_id", ForeignKey("base_versions.version_id"), primary_key=True),
    C("ibge", Integer, primary_key=True),
    C("position", Integer, nullable=False),
    C("uf", String(2), nullable=False),
    C("name", Text, nullable=False),
    C("network", Text, nullable=False),
)
categories = Table(
    "categories",
    metadata,
    C("version_id", ForeignKey("base_versions.version_id"), primary_key=True),
    C("code", String(200), primary_key=True),
    C("position", Integer, nullable=False),
    C("name", Text, nullable=False),
    C("weight_vaaf", Float(53), nullable=False),
    C("weight_vaat", Float(53), nullable=False),
)
enrollments = Table(
    "enrollments",
    metadata,
    C("version_id", ForeignKey("base_versions.version_id"), primary_key=True),
    C("ibge", Integer, primary_key=True),
    C("category", String(200), primary_key=True),
    C("value", Float(53), nullable=False),
    ForeignKeyConstraint(["version_id", "ibge"], ["entities.version_id", "entities.ibge"]),
    ForeignKeyConstraint(["version_id", "category"], ["categories.version_id", "categories.code"]),
)
financial_inputs = Table(
    "financial_inputs",
    metadata,
    C("version_id", ForeignKey("base_versions.version_id"), primary_key=True),
    C("ibge", Integer, primary_key=True),
    C("values_json", Text, nullable=False),
    ForeignKeyConstraint(["version_id", "ibge"], ["entities.version_id", "entities.ibge"]),
)
scenarios = Table(
    "scenarios",
    metadata,
    C("id", String(64), primary_key=True),
    C("created_at", Text, nullable=False),
    C("owner_cpf", String(11)),
    C("base_id", String(100)),
    C("base_version", ForeignKey("base_versions.version_id")),
    C("engine_version", String(80), nullable=False),
    C("request_json", Text, nullable=False),
    C("snapshot", LargeBinary, nullable=False),
    C("snapshot_sha256", String(64), nullable=False),
    C("response_json", Text),
)
scenario_results = Table(
    "scenario_results",
    metadata,
    C("scenario_id", ForeignKey("scenarios.id"), primary_key=True),
    C("variant", String(8), primary_key=True),
    C("ibge", Integer, primary_key=True),
    C("position", Integer, nullable=False),
    C("values_json", Text, nullable=False),
)
exports = Table(
    "exports",
    metadata,
    C("key", String(64), primary_key=True),
    C("scenario_id", ForeignKey("scenarios.id"), nullable=False),
    C("format", String(16), nullable=False),
    C("selection_json", Text, nullable=False),
    C("content", LargeBinary, nullable=False),
    C("sha256", String(64), nullable=False),
    C("created_at", Text, nullable=False),
)
legacy_runs = Table(
    "legacy_runs",
    metadata,
    C("id", String(64), primary_key=True),
    C("created_at", Text, nullable=False),
    C("owner_cpf", String(11)),
    C("path", Text, nullable=False),
    C("request_json", Text, nullable=False),
    C("response", LargeBinary, nullable=False),
    C("snapshot", LargeBinary, nullable=False),
    C("snapshot_sha256", String(64), nullable=False),
    C("engine_version", String(80), nullable=False),
)
audit_events = Table(
    "audit_events",
    metadata,
    C("id", String(64), primary_key=True),
    C("created_at", Text, nullable=False),
    C("action", String(100), nullable=False),
    C("subject", Text, nullable=False),
    C("details_json", Text, nullable=False),
)
Index("ix_scenarios_owner_date", scenarios.c.owner_cpf, scenarios.c.created_at)
Index("ix_legacy_owner_date", legacy_runs.c.owner_cpf, legacy_runs.c.created_at)
Index("ix_base_id", base_versions.c.base_id)
