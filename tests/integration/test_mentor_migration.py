import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "sdb110_cria_mentoria.py"
)
PRIVACY_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "sdb110_motivo_bloqueio.py"
)
RETRY_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "sdb110_retry_origem.py"
)
CONTEXT_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "f3a4b5c6d7e8_mentor_contexto_por_mensagem.py"
)


def _load_migration(path=MIGRATION_PATH):
    assert path.is_file()
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_mentor_migration_has_upgrade_and_downgrade():
    migration = _load_migration()

    assert migration.revision
    assert migration.down_revision == "a92b8c9d0e1f"
    assert callable(migration.upgrade)
    assert callable(migration.downgrade)


@pytest.mark.anyio
async def test_mentor_migration_creates_tables_and_foreign_keys(db_session):
    connection = await db_session.connection()

    def inspect_schema(sync_connection):
        inspector = inspect(sync_connection)
        tables = set(inspector.get_table_names())
        expected = {
            "mentor_consent",
            "mentor_conversation",
            "mentor_message",
            "mentor_generation",
            "mentor_dispatch",
            "mentor_send_reservation",
            "mentor_privacy_block",
        }
        assert expected <= tables
        for table in expected:
            assert inspector.get_pk_constraint(table)["constrained_columns"]
        for table in expected - {"mentor_privacy_block"}:
            assert inspector.get_foreign_keys(table)
        message_uniques = inspector.get_unique_constraints("mentor_message")
        assert {"conversation_id", "sequence"} in [
            set(item["column_names"]) for item in message_uniques
        ]
        generation_indexes = inspector.get_indexes("mentor_generation")
        assert any(
            item["name"] == "uq_mentor_generation_active" and item["unique"]
            for item in generation_indexes
        )

    await connection.run_sync(inspect_schema)


@pytest.mark.anyio
async def test_mentor_migration_upgrade_downgrade_in_isolated_schema(
    db_session,
):
    migration = _load_migration()
    privacy_migration = _load_migration(PRIVACY_MIGRATION_PATH)
    retry_migration = _load_migration(RETRY_MIGRATION_PATH)
    context_migration = _load_migration(CONTEXT_MIGRATION_PATH)
    assert privacy_migration.down_revision == migration.revision
    assert retry_migration.down_revision == privacy_migration.revision
    schema = f"mentor_test_{uuid4().hex}"
    connection = await db_session.connection()
    await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    await connection.execute(
        text('CREATE TABLE "user" (usr_id uuid PRIMARY KEY)')
    )
    await connection.execute(
        text("CREATE TABLE track (trk_id uuid PRIMARY KEY)")
    )

    def run_migration(sync_connection):
        context = MigrationContext.configure(sync_connection)
        with Operations.context(context):
            migration.upgrade()
            privacy_migration.upgrade()
            retry_migration.upgrade()
            context_migration.upgrade()
            tables = inspect(sync_connection).get_table_names(schema=schema)
            assert "mentor_message" in tables
            columns = inspect(sync_connection).get_columns(
                "mentor_privacy_block", schema=schema
            )
            assert "reason" in {column["name"] for column in columns}
            message_columns = inspect(sync_connection).get_columns(
                "mentor_message", schema=schema
            )
            assert "context" in {column["name"] for column in message_columns}
            context_migration.downgrade()
            retry_migration.downgrade()
            privacy_migration.downgrade()
            migration.downgrade()
        tables = inspect(sync_connection).get_table_names(schema=schema)
        assert set(tables) == {"user", "track"}

    await connection.run_sync(run_migration)
