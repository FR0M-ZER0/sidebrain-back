import importlib
import sys
from pathlib import Path


def test_generation_migration_is_reversible():
    migration_path = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions"
        / "adiciona_idempotencia_da_geracao_de_trilhas.py"
    )
    spec = importlib.util.spec_from_file_location(
        "generation_migration", migration_path
    )
    migration = importlib.util.module_from_spec(spec)
    sys.modules["generation_migration"] = migration
    spec.loader.exec_module(migration)

    assert migration.down_revision == "16fd0aac0bc2"
    assert callable(migration.upgrade)
    assert callable(migration.downgrade)


def test_track_icon_migration_is_reversible():
    migration_path = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions"
        / "d4e5f6a7b8c9_adiciona_icone_a_track.py"
    )
    spec = importlib.util.spec_from_file_location(
        "track_icon_migration", migration_path
    )
    migration = importlib.util.module_from_spec(spec)
    sys.modules["track_icon_migration"] = migration
    spec.loader.exec_module(migration)

    assert migration.down_revision == "c3d4e5f6a7b8"
    assert callable(migration.upgrade)
    assert callable(migration.downgrade)
