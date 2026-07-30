from decimal import Decimal

RULE_IDENTIFIER = "training-day-planning-heuristics"
RULE_VERSION = "1.0"
MIN_DURATION = 5
MAX_DURATION = 720
INTENSITY_FACTORS = {
    "very_easy": Decimal("0.5"),
    "easy": Decimal("0.75"),
    "moderate": Decimal("1"),
    "hard": Decimal("1.35"),
    "very_hard": Decimal("1.65"),
}
TYPE_FACTORS = {
    "recovery": Decimal("0.5"),
    "technique": Decimal("0.7"),
    "easy_endurance": Decimal("0.85"),
    "moderate_endurance": Decimal("1"),
    "hard_endurance": Decimal("1.25"),
    "interval": Decimal("1.4"),
    "strength": Decimal("1"),
    "mixed": Decimal("1.1"),
    "competition": Decimal("1.6"),
    "long_session": Decimal("1.25"),
    "other": Decimal("1"),
}
WEIGHTS = {
    "rest": Decimal("0.82"),
    "recovery": Decimal("0.9"),
    "light": Decimal("0.96"),
    "moderate": Decimal("1.04"),
    "high": Decimal("1.12"),
    "very_high": Decimal("1.18"),
    "mixed_uncertain": Decimal("1"),
}
ADDITIVE_RANGES = {
    "rest": (Decimal(0), Decimal(0)),
    "recovery": (Decimal(0), Decimal("50")),
    "light": (Decimal("50"), Decimal("100")),
    "moderate": (Decimal("75"), Decimal("175")),
    "high": (Decimal("125"), Decimal("250")),
    "very_high": (Decimal("150"), Decimal("300")),
    "mixed_uncertain": (Decimal(0), Decimal(0)),
}
CARB_RANGES = {
    "rest": (Decimal(0), Decimal(0)),
    "recovery": (Decimal(0), Decimal("10")),
    "light": (Decimal("5"), Decimal("20")),
    "moderate": (Decimal("15"), Decimal("35")),
    "high": (Decimal("25"), Decimal("55")),
    "very_high": (Decimal("35"), Decimal("75")),
    "mixed_uncertain": (Decimal(0), Decimal(0)),
}
RULE_POSITIVE_CAP = Decimal("300")
RULE_NEGATIVE_CAP = Decimal("250")
RULE_RELATIVE_CAP = Decimal("0.15")
MINIMUM_RELATIVE_TARGET = Decimal("0.80")
