from enum import StrEnum


class GenerationCacheContentTypeEnum(StrEnum):
    TRACK = "track"
    ASSESSMENT = "assessment"


class GenerationCacheStatusEnum(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
