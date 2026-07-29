from decimal import Decimal


class IncompatibleUnitError(ValueError):
    pass


def daily_unit(unit: str) -> str:
    return unit.removesuffix("/Tag").strip()


def convert(value: Decimal, source: str, target: str) -> Decimal:
    source, target = daily_unit(source), daily_unit(target)
    if source == target:
        return value
    mass = {"g": Decimal(1), "mg": Decimal("0.001"), "µg": Decimal("0.000001")}
    if source in mass and target in mass:
        return value * mass[source] / mass[target]
    if source == "kcal" and target == "kJ":
        return value * Decimal("4.184")
    if source == "kJ" and target == "kcal":
        return value / Decimal("4.184")
    if source == "ml" and target == "l":
        return value / Decimal(1000)
    if source == "l" and target == "ml":
        return value * Decimal(1000)
    raise IncompatibleUnitError(f"{source} -> {target}")
