import enum


class StepLevelEnum(enum.StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PRO = "pro"


STEP_LEVEL_RANK = {
    StepLevelEnum.BEGINNER: 0,
    StepLevelEnum.INTERMEDIATE: 1,
    StepLevelEnum.ADVANCED: 2,
    StepLevelEnum.PRO: 3,
}
