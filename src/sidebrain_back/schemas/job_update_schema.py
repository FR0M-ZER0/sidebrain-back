from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

JobChannel = Literal[
    "track_generation", "assessment", "step_preparation", "step_summary"
]


class PublicJobModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", from_attributes=True, populate_by_name=True
    )


class JobScope(PublicJobModel):
    channel: JobChannel
    resource_id: str = Field(min_length=1, max_length=511)

    @field_validator("resource_id")
    @classmethod
    def validate_resource_id(cls, value: str, info) -> str:
        value = value.strip()
        channel = info.data.get("channel")
        if channel in {"track_generation", "assessment"}:
            value = str(UUID(value))
        elif channel == "step_summary":
            parts = value.split(":")
            if len(parts) != 2:
                raise ValueError("resource_id de sumário inválido.")
            value = f"{UUID(parts[0])}:{UUID(parts[1])}"
        if not value:
            raise ValueError("resource_id não pode ser vazio.")
        return value


class WsTicketRequest(JobScope):
    pass


class WsTicketResponse(PublicJobModel):
    ticket: str


class JobSubscribe(JobScope):
    type: Literal["subscribe"]


class TrackGenerationPayload(PublicJobModel):
    request_id: UUID
    status: Literal["pending", "succeeded", "failed"]
    track_id: UUID | None = None
    error_code: str | None = None

    @model_validator(mode="after")
    def validate_terminal_fields(self):
        if self.status == "succeeded" and self.track_id is None:
            raise ValueError("track_id é obrigatório no sucesso.")
        if self.status != "succeeded" and self.track_id is not None:
            raise ValueError("track_id só pode existir no sucesso.")
        if self.status == "failed" and self.error_code is None:
            raise ValueError("error_code é obrigatório na falha.")
        if self.status != "failed" and self.error_code is not None:
            raise ValueError("error_code só pode existir na falha.")
        return self


class AssessmentAlternativePayload(PublicJobModel):
    id: UUID
    text: str


class AssessmentQuestionPayload(PublicJobModel):
    id: UUID
    statement: str
    alternatives: list[AssessmentAlternativePayload]


class AssessmentPayload(PublicJobModel):
    assessment_id: UUID
    status: Literal["pending", "completed", "failed"]
    questions: list[AssessmentQuestionPayload] = Field(default_factory=list)
    error_code: (
        Literal["generation_failed", "invalid_generation_result"] | None
    ) = None

    @model_validator(mode="after")
    def validate_failure(self):
        if self.status == "failed" and self.error_code is None:
            raise ValueError("error_code é obrigatório na falha.")
        if self.status != "failed" and self.error_code is not None:
            raise ValueError("error_code só pode existir na falha.")
        if self.status != "completed" and self.questions:
            raise ValueError("questions só pode existir no sucesso.")
        return self


class StepPreparationPayload(PublicJobModel):
    task_id: str
    status: Literal["pending", "completed", "failed"]


class StepSummaryPayload(PublicJobModel):
    step_id: UUID
    status: Literal["pending", "completed", "failed"]
    summary: str | None = None
    error: str | None = None

    @model_validator(mode="after")
    def validate_result(self):
        if self.status == "completed" and self.summary is None:
            raise ValueError("summary é obrigatório no sucesso.")
        if self.status != "completed" and self.summary is not None:
            raise ValueError("summary só pode existir no sucesso.")
        if self.status == "failed" and self.error is None:
            raise ValueError("error é obrigatório na falha.")
        if self.status != "failed" and self.error is not None:
            raise ValueError("error só pode existir na falha.")
        return self


JobPayload = Annotated[
    TrackGenerationPayload
    | AssessmentPayload
    | StepPreparationPayload
    | StepSummaryPayload,
    Field(union_mode="left_to_right"),
]


class JobUpdated(PublicJobModel):
    type: Literal["job.updated"] = "job.updated"
    channel: JobChannel
    resource_id: str
    payload: JobPayload


class JobError(PublicJobModel):
    type: Literal["job.error"] = "job.error"
    channel: JobChannel
    resource_id: str
    message: str
