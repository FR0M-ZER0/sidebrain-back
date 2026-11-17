import asyncio
from types import SimpleNamespace

from sidebrain_back.rag.rag_evaluation import (
    load_evaluation_questions,
    recall_at_k,
    run_fixture_evaluation,
)


def test_local_evaluation_set_has_twenty_python_and_javascript_queries():
    questions = load_evaluation_questions()

    assert len(questions) == 20
    assert {question.language for question in questions} == {
        "python",
        "javascript",
    }
    assert {question.level for question in questions} == {
        "beginner",
        "intermediate",
        "advanced",
    }
    assert all(question.expected for question in questions)


def test_recall_at_k_matches_expected_source_and_section():
    expected = [
        {
            "source_name": "python-library",
            "section_path": "Python > asyncio",
        },
        {
            "source_name": "python-tutorial",
            "section_path": "Tutorial > Lists",
        },
    ]
    retrieved = [
        SimpleNamespace(
            source_name="python-library",
            section_path="Python > asyncio",
            attributions=[],
        ),
        SimpleNamespace(
            source_name="python-library",
            section_path="Python > Context Managers",
            attributions=[],
        ),
    ]

    assert recall_at_k(retrieved, expected, k=1) == 0.5
    assert recall_at_k(retrieved, expected, k=2) == 0.5
    assert recall_at_k(retrieved, expected, k=3) == 0.5


def test_fixture_evaluation_runs_offline_for_all_twenty_questions():
    report = asyncio.run(run_fixture_evaluation(k=8))

    assert len(report.questions) == 20
    assert report.mean_recall_at_k == 1.0
    assert report.model_id is None
    assert report.dimensions is None
