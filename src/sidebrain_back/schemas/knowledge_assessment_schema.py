from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.enums.step_level_enum import StepLevelEnum

PUBLIC_GENERATION_ERROR_CODES = {
    "generation_failed",
    "invalid_generation_result",
}


def _required_text(value: object, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} é obrigatório.")
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} é obrigatório.")
    return normalized


class KnowledgeAlternative(BaseModel):
    """Legacy SDB-53 provider alternative."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str

    @field_validator("id", "text", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object, info) -> str:
        return _required_text(value, info.field_name)


class KnowledgeQuestion(BaseModel):
    """Legacy SDB-53 provider question."""

    model_config = ConfigDict(extra="forbid")

    id: str
    statement: str
    alternatives: list[KnowledgeAlternative]

    @field_validator("id", "statement", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object, info) -> str:
        return _required_text(value, info.field_name)

    @model_validator(mode="after")
    def validate_question(self) -> Self:
        if len(self.alternatives) != 4:
            raise ValueError(
                "Cada pergunta deve possuir exatamente quatro alternativas."
            )
        alternative_ids = [item.id for item in self.alternatives]
        if len(alternative_ids) != len(set(alternative_ids)):
            raise ValueError("Alternativas repetidas em uma mesma questão.")
        return self


class ProviderQuestion(KnowledgeQuestion):
    """Validated v2 provider question, including the private answer key."""

    correct_alternative_id: str

    @field_validator("correct_alternative_id", mode="before")
    @classmethod
    def normalize_answer_key(cls, value: object) -> str:
        return _required_text(value, "correct_alternative_id")

    @model_validator(mode="after")
    def validate_answer_key(self) -> Self:
        if self.correct_alternative_id not in {
            item.id for item in self.alternatives
        }:
            raise ValueError(
                "correct_alternative_id deve pertencer à própria pergunta."
            )
        return self


class GeneratedAssessmentPayload(BaseModel):
    """Complete provider payload for the persisted v2 flow."""

    model_config = ConfigDict(extra="forbid")

    questions: list[ProviderQuestion]

    @model_validator(mode="after")
    def validate_questions(self) -> Self:
        if len(self.questions) != 5:
            raise ValueError(
                "A avaliação deve possuir exatamente cinco perguntas."
            )
        question_ids = [item.id for item in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("A avaliação possui perguntas repetidas.")
        return self


class AssessmentContext(BaseModel):
    """Legacy v1 task input kept during the compatibility window."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    subject: str | None = None
    objective: str | None = None
    skip: bool = False

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, value: object) -> str:
        user_id = _required_text(value, "user_id")
        try:
            UUID(user_id)
        except ValueError as error:
            raise ValueError("user_id inválido.") from error
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
        if value is not None and len(value) > 255:
            raise ValueError("subject deve ter no máximo 255 caracteres.")
        return value

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 1000:
            raise ValueError("objective deve ter no máximo 1000 caracteres.")
        return value

    @model_validator(mode="after")
    def validate_context(self) -> Self:
        if not self.skip and not self.subject:
            raise ValueError("subject é obrigatório quando skip é falso.")
        return self


class KnowledgeAssessmentResult(BaseModel):
    """Legacy v1 task result kept while queued messages may still exist."""

    model_config = ConfigDict(extra="forbid")

    assessment_id: str = Field(default_factory=lambda: str(uuid4()))
    status: str
    level: str | None = None
    questions: list[KnowledgeQuestion]

    @field_validator("assessment_id", mode="before")
    @classmethod
    def validate_assessment_id(cls, value: object) -> str:
        assessment_id = _required_text(value, "assessment_id")
        try:
            UUID(assessment_id)
        except ValueError as error:
            raise ValueError("assessment_id inválido.") from error
        return assessment_id

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        if self.status == "generated":
            if len(self.questions) != 5:
                raise ValueError(
                    "Resultados gerados devem possuir exatamente "
                    "cinco perguntas."
                )
            if self.level is not None:
                raise ValueError(
                    "Resultados gerados não devem informar level."
                )
            return self
        if self.status == "skipped":
            if self.level != StepLevelEnum.BEGINNER.value:
                raise ValueError(
                    "Resultados pulados devem indicar level='beginner'."
                )
            if self.questions:
                raise ValueError("Resultados pulados não podem ter perguntas.")
            return self
        raise ValueError("status inválido.")


class AssessmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    objective: str | None = None
    skip: bool = False

    @field_validator("subject", mode="before")
    @classmethod
    def normalize_subject(cls, value: object) -> str:
        subject = _required_text(value, "subject")
        if len(subject) > 255:
            raise ValueError("subject deve ter no máximo 255 caracteres.")
        return subject

    @field_validator("objective", mode="before")
    @classmethod
    def normalize_objective(cls, value: object) -> str | None:
        if value is None:
            return None
        objective = _required_text(value, "objective")
        if len(objective) > 1000:
            raise ValueError("objective deve ter no máximo 1000 caracteres.")
        return objective


class AssessmentAcceptedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: UUID
    status: KnowledgeAssessmentStatusEnum


class AssessmentAlternative(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
    )

    id: UUID = Field(validation_alias=AliasChoices("id", "kaa_id"))
    text: str = Field(validation_alias=AliasChoices("text", "kaa_text"))


class AssessmentQuestion(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
    )

    id: UUID = Field(validation_alias=AliasChoices("id", "kaq_id"))
    statement: str = Field(
        validation_alias=AliasChoices("statement", "kaq_statement")
    )
    alternatives: list[AssessmentAlternative]

    @model_validator(mode="after")
    def validate_alternatives(self) -> Self:
        if len(self.alternatives) != 4:
            raise ValueError(
                "Cada pergunta pública deve possuir quatro alternativas."
            )
        return self


class AssessmentAnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    alternative_id: UUID


class AssessmentAnswersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[AssessmentAnswerInput]

    @model_validator(mode="after")
    def validate_answers(self) -> Self:
        if len(self.answers) != 5:
            raise ValueError(
                "Devem ser informadas exatamente cinco respostas."
            )
        question_ids = [item.question_id for item in self.answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("question_id não pode ser repetido.")
        return self


class AssessmentDetail(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
    )

    assessment_id: UUID = Field(
        validation_alias=AliasChoices("assessment_id", "kas_id")
    )
    subject: str = Field(
        validation_alias=AliasChoices("subject", "kas_subject")
    )
    objective: str | None = Field(
        default=None,
        validation_alias=AliasChoices("objective", "kas_objective"),
    )
    skip: bool = Field(validation_alias=AliasChoices("skip", "kas_skip"))
    status: KnowledgeAssessmentStatusEnum = Field(
        validation_alias=AliasChoices("status", "kas_status")
    )
    questions: list[AssessmentQuestion] = Field(default_factory=list)
    score: int | None = Field(
        default=None,
        validation_alias=AliasChoices("score", "kas_score"),
    )
    level: StepLevelEnum | None = Field(
        default=None,
        validation_alias=AliasChoices("level", "kas_level"),
    )
    error_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("error_code", "kas_error_code"),
    )
    created_at: datetime = Field(
        validation_alias=AliasChoices("created_at", "kas_created_at")
    )
    updated_at: datetime = Field(
        validation_alias=AliasChoices("updated_at", "kas_updated_at")
    )
    completed_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("completed_at", "kas_completed_at"),
    )

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.status in {
            KnowledgeAssessmentStatusEnum.PENDING,
            KnowledgeAssessmentStatusEnum.GENERATED,
        }:
            if any(
                value is not None
                for value in (
                    self.score,
                    self.level,
                    self.error_code,
                    self.completed_at,
                )
            ):
                raise ValueError("Estado ativo possui resultado incompatível.")
            expected_questions = (
                5
                if self.status is KnowledgeAssessmentStatusEnum.GENERATED
                else 0
            )
            if len(self.questions) != expected_questions:
                raise ValueError("Quantidade de perguntas incompatível.")
            return self

        if self.status is KnowledgeAssessmentStatusEnum.SKIPPED:
            if (
                not self.skip
                or self.questions
                or self.score is not None
                or self.level is not StepLevelEnum.BEGINNER
                or self.error_code is not None
                or self.completed_at is None
            ):
                raise ValueError("Estado skipped incompatível.")
            return self

        if self.status is KnowledgeAssessmentStatusEnum.FAILED:
            if (
                self.questions
                or self.score is not None
                or self.level is not None
                or self.completed_at is not None
                or self.error_code not in PUBLIC_GENERATION_ERROR_CODES
            ):
                raise ValueError("Estado failed incompatível.")
            return self

        if self.status is KnowledgeAssessmentStatusEnum.COMPLETED:
            if (
                len(self.questions) != 5
                or self.score is None
                or self.level is None
                or self.error_code is not None
                or self.completed_at is None
            ):
                raise ValueError("Estado completed incompatível.")
            expected_level = level_for_score(self.score)
            if self.level is not expected_level:
                raise ValueError("Score e level incompatíveis.")
            return self

        raise ValueError("status inválido.")


def level_for_score(score: int) -> StepLevelEnum:
    if score < 0 or score > 5:
        raise ValueError("score deve estar entre zero e cinco.")
    if score <= 1:
        return StepLevelEnum.BEGINNER
    if score <= 3:
        return StepLevelEnum.INTERMEDIATE
    if score == 4:
        return StepLevelEnum.ADVANCED
    return StepLevelEnum.PRO
