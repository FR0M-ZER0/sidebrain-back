import importlib.util
import sys
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "a2b3c4d5e6f7_cria_indice_rag.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "rag_index_migration",
        MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = migration
    spec.loader.exec_module(migration)
    return migration


def test_rag_migration_follows_pgvector_and_is_reversible():
    migration = _load_migration()

    assert migration.revision == "a2b3c4d5e6f7"
    assert migration.down_revision == "f6a7b8c9d0e1"
    assert callable(migration.upgrade)
    assert callable(migration.downgrade)


def test_rag_migration_declares_persistence_and_search_indexes():
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    for table in (
        "rag_document",
        "rag_chunk",
        "rag_chunk_attribution",
        "rag_chunk_embedding",
    ):
        assert f'"{table}"' in source

    assert "Vector(1536)" in source
    assert "vector_cosine_ops" in source
    assert 'postgresql_using="hnsw"' in source
    assert "TSVECTOR" in source
    assert 'postgresql_using="gin"' in source
    assert '"language"' in source
    assert '"level"' in source
    assert '"content_type"' in source
    assert '"topics"' in source


def test_rag_downgrade_removes_only_feature_objects_and_preserves_extension():
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    downgrade = source.split("def downgrade()", maxsplit=1)[1]

    positions = [
        downgrade.index(f'op.drop_table("{table}")')
        for table in (
            "rag_chunk_embedding",
            "rag_chunk_attribution",
            "rag_chunk",
            "rag_document",
        )
    ]
    assert positions == sorted(positions)
    assert "DROP EXTENSION" not in downgrade.upper()
