from sidebrain_back.rag.rag_chunker import (
    RagChunker,
    RagSection,
    approximate_duplicate_groups,
    deduplicate_exact,
)
from sidebrain_back.rag.rag_tokenizer import RagTokenizer


class WhitespaceTokenizer:
    def count(self, text: str) -> int:
        return len(text.split())

    def encode(self, text: str) -> list[str]:
        return text.split()

    def decode(self, tokens: list[str]) -> str:
        return " ".join(tokens)


def test_model_tokenizer_counts_and_roundtrips_python_and_javascript_text():
    tokenizer = RagTokenizer()
    text = "async def run(): return await fetch('/api')"

    encoded = tokenizer.encode(text)

    assert tokenizer.count(text) == len(encoded)
    assert tokenizer.decode(encoded) == text


def _attribution(source_name: str = "python-docs") -> dict:
    return {
        "doc_id": f"doc-{source_name}",
        "source_name": source_name,
        "source_url": f"https://example.invalid/{source_name}",
        "title": "Python Tutorial",
        "language": "python",
        "level": "beginner",
        "content_type": "tutorial",
        "topics": ["lists"],
        "license": "PSF-2.0",
        "license_url": "https://docs.python.org/3/license.html",
        "external_processing_allowed": True,
    }


def test_chunker_prefixes_document_and_section_and_keeps_sections_separate():
    chunker = RagChunker(
        tokenizer=WhitespaceTokenizer(),
        target_tokens=40,
        overlap_ratio=0.1,
    )

    chunks = chunker.chunk_document(
        title="Python Tutorial",
        sections=[
            RagSection("Tutorial > Lists", "A list is a mutable sequence."),
            RagSection("Tutorial > Tuples", "A tuple is immutable."),
        ],
        attribution=_attribution(),
    )

    assert len(chunks) == 2
    assert chunks[0].text.startswith(
        "Document: Python Tutorial\nSection: Tutorial > Lists"
    )
    assert chunks[1].text.startswith(
        "Document: Python Tutorial\nSection: Tutorial > Tuples"
    )


def test_oversized_code_block_is_not_split_and_keeps_its_introduction():
    code = (
        "```python\n"
        + "\n".join(f"print({number})" for number in range(50))
        + "\n```"
    )
    chunker = RagChunker(
        tokenizer=WhitespaceTokenizer(),
        target_tokens=12,
        overlap_ratio=0.12,
    )

    chunks = chunker.chunk_document(
        title="Long example",
        sections=[
            RagSection(
                "Tutorial > Output",
                f"Run this complete example to print the sequence:\n\n{code}",
            )
        ],
        attribution=_attribution(),
    )

    containing_code = [chunk for chunk in chunks if "print(0)" in chunk.text]
    assert len(containing_code) == 1
    assert code in containing_code[0].text
    assert "Run this complete example" in containing_code[0].text
    assert containing_code[0].code_language == "python"
    assert WhitespaceTokenizer().count(containing_code[0].text) > 12


def test_exact_deduplication_merges_attributions_without_losing_sources():
    chunker = RagChunker(
        tokenizer=WhitespaceTokenizer(),
        target_tokens=40,
        overlap_ratio=0.1,
    )
    first = chunker.chunk_document(
        title="Python Tutorial",
        sections=[RagSection("Tutorial > Lists", "Lists preserve order.")],
        attribution=_attribution("python-tutorial"),
    )[0]
    second = chunker.chunk_document(
        title="Python Tutorial",
        sections=[RagSection("Tutorial > Lists", "Lists preserve order.")],
        attribution=_attribution("python-library"),
    )[0]

    deduplicated, removed = deduplicate_exact([first, second])

    assert removed == 1
    assert len(deduplicated) == 1
    assert {item["source_name"] for item in deduplicated[0].attributions} == {
        "python-tutorial",
        "python-library",
    }


def test_approximate_dedup_groups_text_but_not_changed_code():
    chunker = RagChunker(
        tokenizer=WhitespaceTokenizer(),
        target_tokens=100,
        overlap_ratio=0,
    )
    near_first = chunker.chunk_document(
        title="Python Tutorial",
        sections=[
            RagSection(
                "Tutorial > Lists",
                "Python lists store ordered values and allow indexed access.",
            )
        ],
        attribution=_attribution("source-a"),
    )[0]
    near_second = chunker.chunk_document(
        title="Python Tutorial",
        sections=[
            RagSection(
                "Tutorial > Lists",
                (
                    "Python lists often store ordered values and allow "
                    "indexed access."
                ),
            )
        ],
        attribution=_attribution("source-b"),
    )[0]

    assert approximate_duplicate_groups(
        [near_first, near_second], max_hamming_distance=64
    )
    assert (
        approximate_duplicate_groups(
            [near_first, near_second], max_hamming_distance=0
        )
        == []
    )

    code_first = chunker.chunk_document(
        title="Python Tutorial",
        sections=[
            RagSection(
                "Tutorial > Lists", "Example:\n\n```python\nprint(1)\n```"
            )
        ],
        attribution=_attribution("source-c"),
    )[0]
    code_second = chunker.chunk_document(
        title="Python Tutorial",
        sections=[
            RagSection(
                "Tutorial > Lists", "Example:\n\n```python\nprint(2)\n```"
            )
        ],
        attribution=_attribution("source-d"),
    )[0]
    assert (
        approximate_duplicate_groups(
            [code_first, code_second], max_hamming_distance=64
        )
        == []
    )
