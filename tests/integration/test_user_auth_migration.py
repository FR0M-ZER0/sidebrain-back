import importlib.util
import sys
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "f81a1b2c3d4_user_auth.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "user_auth_migration",
        MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = migration
    spec.loader.exec_module(migration)
    return migration


def test_user_auth_migration_is_reversible_and_follows_latest_revision():
    migration = _load_migration()

    assert migration.revision == "f81a1b2c3d4"
    assert migration.down_revision == "e5f6a7b8c9d0"
    assert callable(migration.upgrade)
    assert callable(migration.downgrade)


def test_migration_audits_legacy_collisions_and_uses_concurrent_index():
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "lower(btrim(usr_email))" in source
    assert "HAVING count(*) > 1" in source
    assert "usr_token_version" in source
    assert "uq_user_usr_email_normalized" in source
    assert "CREATE UNIQUE INDEX CONCURRENTLY" in source
    assert "autocommit_block" in source
    assert "DROP INDEX CONCURRENTLY" in source


def test_migration_preserves_user_rows_and_relationships():
    source = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    assert 'delete from "user"' not in source
    assert 'drop table "user"' not in source
    assert "cascade" not in source
