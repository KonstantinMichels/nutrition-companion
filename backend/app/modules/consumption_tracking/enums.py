from enum import StrEnum


class DayStatus(StrEnum):
    OPEN = "open"
    FINALIZED = "finalized"


class Completeness(StrEnum):
    NOT_DECLARED = "not_declared"
    COMPLETE = "complete_to_best_knowledge"
    PARTIAL = "partial"
    UNCERTAIN = "uncertain"


class TargetBasisSource(StrEnum):
    DAILY_PLAN = "daily_plan_snapshot"
    LATEST = "latest_usable_assessment"
    EXPLICIT = "explicit_assessment"
    NONE = "none"


class EntryType(StrEnum):
    FOOD = "food"
    RECIPE = "recipe"
    MANUAL = "manual_unresolved"


class OriginType(StrEnum):
    PLANNED = "planned"
    UNPLANNED = "unplanned"
    REPLACEMENT = "replacement"


class OutcomeType(StrEnum):
    AS_PLANNED = "consumed_as_planned"
    MODIFIED = "consumed_modified"
    PARTIAL = "partially_consumed"
    SKIPPED = "skipped"
    REPLACED = "replaced"


class SnapshotState(StrEnum):
    KNOWN = "known"
    TRUE_ZERO = "true_zero"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
