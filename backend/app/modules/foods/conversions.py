from decimal import Decimal

KJ_PER_KCAL = Decimal("4.184")
SALT_PER_SODIUM = Decimal("2.5")


def kcal_to_kj(value: Decimal) -> Decimal:
    return value * KJ_PER_KCAL


def salt_to_sodium(value: Decimal) -> Decimal:
    return value / SALT_PER_SODIUM


def sodium_to_salt(value: Decimal) -> Decimal:
    return value * SALT_PER_SODIUM
