from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class KnowledgeAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str

    @field_validator("id", "text", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object) -> str:
        if value is None:
            raise ValueError("Campo obrigatório.")
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("Campo obrigatório.")
        return normalized


class KnowledgeQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    statement: str
    alternatives: list[KnowledgeAlternative]

    @field_validator("id", "statement", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object) -> str:
        if value is None:
            raise ValueError("Campo obrigatório.")
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("Campo obrigatório.")
        return normalized

    @model_validator(mode="after")
    def validate_question(self) -> KnowledgeQuestion:
        if len(self.alternatives) != 4:
            raise ValueError(
                "Cada pergunta deve possuir exatamente quatro alternativas."
            )

        alternative_ids = [alternative.id for alternative in self.alternatives]
        if len(alternative_ids) != len(set(alternative_ids)):
            raise ValueError("Alternativas repetidas em uma mesma questão.")
        return self


class AssessmentContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    subject: str | None = None
    objective: str | None = None
    skip: bool = False

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, value: object) -> str:
        if value is None:
            raise ValueError("user_id é obrigatório.")
        user_id = str(value).strip()
        if not user_id:
            raise ValueError("user_id é obrigatório.")
        try:
            UUID(user_id)
        except ValueError as exc:
            raise ValueError("user_id inválido.") from exc
        return user_id

    @field_validator("subject", "objective", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) > 255:
            raise ValueError("subject deve ter no máximo 255 caracteres.")
        return value

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) > 1000:
            raise ValueError("objective deve ter no máximo 1000 caracteres.")
        return value

    @model_validator(mode="after")
    def validate_context(self) -> AssessmentContext:
        if self.skip:
            return self
        if not self.subject:
            raise ValueError("subject é obrigatório quando skip é falso.")
        return self


class KnowledgeAssessmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: str = Field(default_factory=lambda: str(uuid4()))
    status: str
    level: str | None = None
    questions: list[KnowledgeQuestion]

    @field_validator("assessment_id", mode="before")
    @classmethod
    def validate_assessment_id(cls, value: object) -> str:
        if value is None:
            raise ValueError("assessment_id é obrigatório.")
        assessment_id = str(value).strip()
        if not assessment_id:
            raise ValueError("assessment_id é obrigatório.")
        try:
            UUID(assessment_id)
        except ValueError as exc:
            raise ValueError("assessment_id inválido.") from exc
        return assessment_id

    @model_validator(mode="after")
    def validate_result(self) -> KnowledgeAssessmentResult:
        if self.status == "generated":
            if len(self.questions) != 5:
                raise ValueError(
                    "Resultados gerados devem possuir exatamente cinco "
                    "perguntas."
                )
            if self.level is not None:
                raise ValueError(
                    "Resultados gerados não devem informar level."
                )
            return self

        if self.status == "skipped":
            if self.level != "beginner":
                raise ValueError(
                    "Resultados pulados devem indicar level='beginner'."
                )
            if self.questions:
                raise ValueError("Resultados pulados não podem ter perguntas.")
            return self

        raise ValueError("status inválido.")
