import enum


class BadgeCriteriaEnum(enum.StrEnum):
    XP_GAINED = "xp_gained"
    TRACKS_COMPLETED = "tracks_completed"
    LESSONS_COMPLETED = "lessons_completed"
    RIGHT_ANSWERS = "right_answers"
    DAY_STREAK = "day_streak"
    TRACKS_CREATED = "tracks_created"
    MISSIONS_COMPLETED = "missions_completed"
