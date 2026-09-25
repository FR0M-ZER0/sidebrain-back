import enum


class KnowledgeAssessmentStatusEnum(enum.StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    SKIPPED = "skipped"
    COMPLETED = "completed"
    FAILED = "failed"
