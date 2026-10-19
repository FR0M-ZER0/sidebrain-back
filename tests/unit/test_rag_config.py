from pathlib import Path

import pytest

from sidebrain_back.rag.rag_config import RagConfigError, load_rag_config


def test_default_rag_config_has_scoped_initial_sources():
    config = load_rag_config()
    sources = {source.name: source for source in config.sources}

    assert set(sources) == {
        "python-tutorial",
        "python-library",
        "mdn-javascript",
    }
    assert sources["python-tutorial"].type == "url"
    assert sources["python-tutorial"].language == "python"
    assert sources["python-tutorial"].level == "beginner"
    assert "/3/tutorial/**" in sources["python-tutorial"].include_paths
    assert sources["python-library"].language == "python"
    assert "/3/library/**" in sources["python-library"].include_paths
    assert sources["mdn-javascript"].language == "javascript"
    assert "/en-US/docs/Web/JavaScript/**" in sources[
        "mdn-javascript"
    ].include_paths
    mdn_code_license = sources["mdn-javascript"].content_licenses[
        "code_example"
    ].license
    assert mdn_code_license == "unknown"


def test_rag_config_rejects_unknown_source_type(tmp_path: Path):
    config_path = tmp_path / "invalid-rag.yml"
    config_path.write_text(
        """
version: 1
defaults: {}
sources:
  - name: invalid
    type: database
    url: https://example.invalid/docs
    language: python
    level: beginner
    license: unknown
    license_url: null
    include_paths: [/**]
    exclude_paths: []
    version_strategy: fixed
    connector: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(RagConfigError, match="type"):
        load_rag_config(config_path)


def test_rag_config_requires_source_provenance_and_valid_chunk_defaults(
    tmp_path: Path,
):
    config_path = tmp_path / "invalid-rag.yml"
    config_path.write_text(
        """
version: 1
defaults:
  chunking:
    target_tokens: 500
    overlap_ratio: 1.2
sources:
  - name: invalid
    type: local
    path: /tmp/docs
    language: python
    level: beginner
    include_paths: [.md]
    exclude_paths: []
    version_strategy: content_hash
    connector: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(RagConfigError):
        load_rag_config(config_path)
