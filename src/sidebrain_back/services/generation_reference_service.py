import re

from sidebrain_back.schemas.generation_schema import (
    MAX_LESSON_TEXT_LENGTH,
    MIN_LESSON_TEXT_LENGTH,
)
from sidebrain_back.schemas.rag_schema import RagReferenceSchema


class GenerationReferenceService:
    CITATION_PATTERN = re.compile(r"\[Fonte\s+(\d+)\]")

    @staticmethod
    def build_prompt_references(
        references: list[RagReferenceSchema],
    ) -> list[dict]:
        return [
            {
                "reference_id": index,
                "source": reference.source_name,
                "url": reference.source_url,
                "title": reference.title,
                "section": reference.section_path,
                "license": reference.license,
                "text": reference.text,
                "attributions": [
                    attribution.model_dump()
                    for attribution in reference.attributions
                ],
            }
            for index, reference in enumerate(references, start=1)
        ]

    @classmethod
    def add_references_to_text(
        cls, text: str, references: list[RagReferenceSchema]
    ) -> str:
        if not references:
            return cls._validate_final_text(text)

        citation_ids = sorted(
            {int(match) for match in cls.CITATION_PATTERN.findall(text)}
        )
        if not citation_ids:
            raise ValueError(
                "cada lição com contexto RAG deve citar ao menos uma fonte"
            )
        if any(
            citation_id < 1 or citation_id > len(references)
            for citation_id in citation_ids
        ):
            raise ValueError("a lição citou uma fonte RAG inexistente")

        bibliography = "\n\nReferências:\n" + "\n".join(
            cls._format_reference(citation_id, references[citation_id - 1])
            for citation_id in citation_ids
        )
        content_limit = MAX_LESSON_TEXT_LENGTH - len(bibliography)
        if content_limit < MIN_LESSON_TEXT_LENGTH:
            raise ValueError(
                "as referências excedem o limite de caracteres da lição"
            )

        content = text.strip()
        if len(content) > content_limit:
            content = content[:content_limit].rstrip()
            if len(content) >= MIN_LESSON_TEXT_LENGTH:
                last_space = content.rfind(" ")
                if last_space >= MIN_LESSON_TEXT_LENGTH:
                    content = content[:last_space].rstrip()
            if not cls.CITATION_PATTERN.search(content):
                marker = f"[Fonte {citation_ids[0]}]"
                content_limit -= len(marker) + 1
                if content_limit < MIN_LESSON_TEXT_LENGTH:
                    raise ValueError(
                        "as referências excedem o limite de caracteres "
                        "da lição"
                    )
                content = f"{marker} {text.strip()[:content_limit].rstrip()}"

        return cls._validate_final_text(content + bibliography)

    @staticmethod
    def _format_reference(
        citation_id: int, reference: RagReferenceSchema
    ) -> str:
        return (
            f"[Fonte {citation_id}] {reference.title} — "
            f"{reference.source_url}"
        )

    @staticmethod
    def _validate_final_text(text: str) -> str:
        normalized = text.strip()
        if not MIN_LESSON_TEXT_LENGTH <= len(
            normalized
        ) <= MAX_LESSON_TEXT_LENGTH:
            raise ValueError(
                "o texto final da lição deve ter entre "
                f"{MIN_LESSON_TEXT_LENGTH} e "
                f"{MAX_LESSON_TEXT_LENGTH} caracteres"
            )
        return normalized
