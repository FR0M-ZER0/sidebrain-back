import importlib.util
import sys
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "c3d4e5f6a7b8_cria_avaliacoes_de_conhecimento.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "knowledge_assessment_migration",
        MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = migration
    spec.loader.exec_module(migration)
    return migration


def test_knowledge_assessment_migration_is_reversible():
    migration = _load_migration()

    assert migration.revision == "c3d4e5f6a7b8"
    assert migration.down_revision == "b2c3d4e5f6a7"
    assert callable(migration.upgrade)
    assert callable(migration.downgrade)


def test_migration_declares_tables_constraints_and_partial_indexes():
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    for table in (
        "knowledge_assessment",
        "knowledge_assessment_question",
        "knowledge_assessment_alternative",
        "knowledge_assessment_answer",
    ):
        assert f'"{table}"' in source

    assert 'name="knowledge_assessment_status"' in source
    assert 'name="step_level"' in source
    assert "create_type=False" in source
    assert "postgresql_where" in source
    assert "kas_status IN ('pending', 'generated')" in source
    assert "kaa_is_correct IS true" in source
    assert "ForeignKeyConstraint" in source
    assert "CheckConstraint" in source


def test_downgrade_drops_children_before_parent_and_preserves_step_level():
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    downgrade = source.split("def downgrade()", maxsplit=1)[1]

    positions = [
        downgrade.index(f'op.drop_table("{table}")')
        for table in (
            "knowledge_assessment_answer",
            "knowledge_assessment_alternative",
            "knowledge_assessment_question",
            "knowledge_assessment",
        )
    ]
    assert positions == sorted(positions)
    assert 'ENUM(name="knowledge_assessment_status")' in downgrade
    assert 'ENUM(name="step_level")' not in downgrade
