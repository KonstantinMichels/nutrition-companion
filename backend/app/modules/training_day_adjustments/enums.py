from enum import StrEnum


class SportType(StrEnum):
    STRENGTH_TRAINING = "strength_training"
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    TRIATHLON = "triathlon"
    TEAM_SPORT = "team_sport"
    AMERICAN_FOOTBALL = "american_football"
    COMBAT_SPORT = "combat_sport"
    RACQUET_SPORT = "racquet_sport"
    ROWING = "rowing"
    HIKING = "hiking"
    MOBILITY = "mobility"
    RECOVERY = "recovery"
    OTHER = "other"


class SessionType(StrEnum):
    RECOVERY = "recovery"
    TECHNIQUE = "technique"
    EASY_ENDURANCE = "easy_endurance"
    MODERATE_ENDURANCE = "moderate_endurance"
    HARD_ENDURANCE = "hard_endurance"
    INTERVAL = "interval"
    STRENGTH = "strength"
    MIXED = "mixed"
    COMPETITION = "competition"
    LONG_SESSION = "long_session"
    OTHER = "other"


class Intensity(StrEnum):
    VERY_EASY = "very_easy"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    VERY_HARD = "very_hard"


class BaselineInclusion(StrEnum):
    INCLUDED = "included_in_baseline"
    ADDITIONAL = "additional_to_baseline"
    PARTIAL = "partially_included"
    UNKNOWN = "unknown"


class Strategy(StrEnum):
    REDISTRIBUTION = "weekly_redistribution"
    ADDITIVE = "bounded_additive"
    MANUAL = "custom_manual"
    NONE = "none"
