"""Typed immutable output models shared by all engine calculation modules."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, StrEnum
from types import MappingProxyType
from typing import Any, cast


class ConfidenceType(StrEnum):
    MEASURED = "measured"
    DERIVED = "derived"
    ESTIMATED = "estimated"
    REFERENCE_TARGET = "reference_target"


class SafetySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class SupportedScopeStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class FieldIssue:
    field: str
    code: str
    message_de: str


class EngineInputError(ValueError):
    def __init__(self, issues: tuple[FieldIssue, ...]) -> None:
        self.issues = issues
        super().__init__("; ".join(f"{item.field}: {item.code}" for item in issues))


@dataclass(frozen=True, slots=True)
class SafetyFlag:
    code: str
    severity: SafetySeverity
    explanation_de: str
    recommended_action_de: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "explanation_de": self.explanation_de,
            "recommended_action_de": self.recommended_action_de,
        }


@dataclass(frozen=True, slots=True)
class MetricResult:
    metric_code: str
    raw_value: Decimal | None
    display_value: str
    lower_value: Decimal | None
    upper_value: Decimal | None
    unit: str
    method_code: str
    explanation_de: str
    limitations_de: str
    calculation_inputs: Mapping[str, Any]
    source_metadata: Mapping[str, Any]
    application_rule_identifier: str | None
    confidence_type: ConfidenceType
    calculated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "calculation_inputs", MappingProxyType(dict(self.calculation_inputs))
        )
        object.__setattr__(self, "source_metadata", MappingProxyType(dict(self.source_metadata)))

    def to_persistence_dict(self) -> dict[str, Any]:
        """Shape accepted by ``AssessmentMetric`` (timestamp lives on Assessment)."""

        return {
            "metric_code": self.metric_code,
            "raw_value": self.raw_value,
            "display_value": self.display_value,
            "lower_value": self.lower_value,
            "upper_value": self.upper_value,
            "unit": self.unit,
            "method_code": self.method_code,
            "explanation_de": self.explanation_de,
            "limitations_de": self.limitations_de,
            "calculation_inputs": _json_safe(dict(self.calculation_inputs)),
            "source_metadata": _json_safe(dict(self.source_metadata)),
            "application_rule_identifier": self.application_rule_identifier,
            "confidence_type": self.confidence_type.value,
        }


@dataclass(frozen=True, slots=True)
class FoodGroupRecommendation:
    code: str
    display_name_de: str
    recommendation_de: str
    amount: Decimal | None
    unit: str | None
    frequency: str
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    combined_group_code: str | None = None
    source_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_metadata", MappingProxyType(dict(self.source_metadata)))

    def to_dict(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            _json_safe(
                {
                    "code": self.code,
                    "display_name_de": self.display_name_de,
                    "recommendation_de": self.recommendation_de,
                    "amount": self.amount,
                    "unit": self.unit,
                    "frequency": self.frequency,
                    "minimum": self.minimum,
                    "maximum": self.maximum,
                    "combined_group_code": self.combined_group_code,
                    "source_metadata": dict(self.source_metadata),
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    supported_scope_status: SupportedScopeStatus
    reference_set_identifier: str
    reference_set_version: str
    application_rule_set_identifier: str
    application_rule_set_version: str
    engine_version: str
    calculated_at: datetime
    input_snapshot: Mapping[str, Any]
    summary: Mapping[str, Any]
    metrics: tuple[MetricResult, ...]
    safety_flags: tuple[SafetyFlag, ...]
    food_groups: tuple[FoodGroupRecommendation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_snapshot", MappingProxyType(dict(self.input_snapshot)))
        object.__setattr__(self, "summary", MappingProxyType(dict(self.summary)))

    def metric(self, code: str) -> MetricResult:
        for metric in self.metrics:
            if metric.metric_code == code:
                return metric
        raise KeyError(code)

    def to_dict(self) -> dict[str, Any]:
        return {
            "supported_scope_status": self.supported_scope_status.value,
            "reference_set_identifier": self.reference_set_identifier,
            "reference_set_version": self.reference_set_version,
            "application_rule_set_identifier": self.application_rule_set_identifier,
            "application_rule_set_version": self.application_rule_set_version,
            "engine_version": self.engine_version,
            "calculated_at": self.calculated_at.isoformat(),
            "input_snapshot": _json_safe(dict(self.input_snapshot)),
            "summary": _json_safe(dict(self.summary)),
            "metrics": [_json_safe(metric.to_persistence_dict()) for metric in self.metrics],
            "safety_flags": [flag.to_dict() for flag in self.safety_flags],
            "food_groups": [item.to_dict() for item in self.food_groups],
        }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value
