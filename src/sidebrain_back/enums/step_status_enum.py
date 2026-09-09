import enum


class StepStatusEnum(enum.StrEnum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    DONE = "done"
