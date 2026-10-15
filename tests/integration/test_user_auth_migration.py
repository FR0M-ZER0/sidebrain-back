import importlib.util
import sys
from contextlib import contextmanager
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


def test_migration_repairs_partial_state_before_retry(monkeypatch):
    migration = _load_migration()

    class ResultDouble:
        def __init__(self, *, rows=None, scalar=None):
            self.rows = rows
            self.scalar = scalar

        def fetchall(self):
            return self.rows

        def scalar_one(self):
            return self.scalar

        def scalar_one_or_none(self):
            return self.scalar

    class ConnectionDouble:
        def __init__(self):
            self.results = iter(
                (
                    ResultDouble(rows=[]),
                    ResultDouble(scalar=True),
                    ResultDouble(scalar=False),
                )
            )

        def execute(self, *_args, **_kwargs):
            return next(self.results)

    @contextmanager
    def autocommit_block():
        yield

    added_columns = []
    statements = []
    monkeypatch.setattr(migration.op, "get_bind", ConnectionDouble)
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda *args: added_columns.append(args),
    )
    monkeypatch.setattr(migration.op, "execute", statements.append)
    monkeypatch.setattr(
        migration.op,
        "get_context",
        lambda: type(
            "ContextDouble",
            (),
            {"autocommit_block": staticmethod(autocommit_block)},
        )(),
    )

    migration.upgrade()

    assert added_columns == []
    assert statements == [
        f'DROP INDEX CONCURRENTLY IF EXISTS "{migration.INDEX_NAME}"',
        f'CREATE UNIQUE INDEX CONCURRENTLY "{migration.INDEX_NAME}" '
        'ON "user" (lower(btrim(usr_email)))',
    ]
