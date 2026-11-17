from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RagLanguage = Literal["python", "javascript"]
RagLevel = Literal["beginner", "intermediate", "advanced"]
RagContentType = Literal[
    "concept",
    "code_example",
    "reference",
    "tutorial",
    "exercise",
]


class RagClassificationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    use_rag: bool
    language: RagLanguage | None
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_language_decision(self):
        if self.use_rag and self.language is None:
            raise ValueError("language is required when use_rag is true")
        if not self.use_rag and self.language is not None:
            raise ValueError("language must be null when use_rag is false")
        return self


class RagReferenceAttributionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str
    source_url: str
    title: str
    section_path: str
    language: RagLanguage
    level: RagLevel
    content_type: RagContentType
    topics: list[str] = Field(default_factory=list)
    license: str
    license_url: str | None = None
    external_processing_allowed: bool = False


class RagReferenceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    text: str
    source_name: str
    source_url: str
    title: str
    section_path: str
    language: RagLanguage
    level: RagLevel
    content_type: RagContentType
    topics: list[str] = Field(default_factory=list)
    license: str
    license_url: str | None = None
    external_processing_allowed: bool = False
    attributions: list[RagReferenceAttributionSchema] = Field(
        default_factory=list
    )
    score: float | None = None


class RagIndexingReportSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources_processed: int = 0
    documents_found: int = 0
    documents_processed: int = 0
    documents_unchanged: int = 0
    chunks_generated: int = 0
    exact_duplicates_removed: int = 0
    approximate_duplicates_grouped: int = 0
    license_excluded: int = 0
    failures: list[str] = Field(default_factory=list)
    duration_seconds: float = 0
    estimated_cost: float | None = None
