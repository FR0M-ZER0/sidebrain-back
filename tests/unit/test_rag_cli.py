import pytest

from sidebrain_back.rag.rag_cli import build_argument_parser, main


def test_index_cli_requires_exactly_one_source_selection():
    parser = build_argument_parser()

    assert parser.parse_args(["index", "--all"]).all is True
    source_args = parser.parse_args(["index", "--source", "python-tutorial"])
    assert source_args.source == "python-tutorial"
    with pytest.raises(SystemExit):
        parser.parse_args(["index"])
    with pytest.raises(SystemExit):
        parser.parse_args(["index", "--all", "--source", "python-tutorial"])


def test_reindex_cli_requires_full_rebuild_flag():
    parser = build_argument_parser()

    args = parser.parse_args(["reindex", "--full"])
    assert args.full is True
    assert args.source is None
    with pytest.raises(SystemExit):
        parser.parse_args(["reindex"])


def test_query_cli_validates_top_k_and_accepts_retrieval_filters():
    parser = build_argument_parser()
    args = parser.parse_args(
        [
            "query",
            "async await",
            "--language",
            "javascript",
            "--level",
            "advanced",
            "--content-type",
            "code_example",
            "--top-k",
            "8",
        ]
    )

    assert args.language == "javascript"
    assert args.level == "advanced"
    assert args.content_type == "code_example"
    assert args.top_k == 8
    with pytest.raises(SystemExit):
        parser.parse_args(["query", "python", "--top-k", "0"])


def test_fixture_evaluation_cli_runs_without_external_services(capsys):
    exit_code = main(["evaluate", "--fixtures", "--k", "8"])

    assert exit_code == 0
    assert '"mean_recall_at_k": 1.0' in capsys.readouterr().out
