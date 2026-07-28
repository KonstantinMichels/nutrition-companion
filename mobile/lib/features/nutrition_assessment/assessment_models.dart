import '../../core/formatting/german_decimal.dart';

Map<String, dynamic> _map(Object? value) =>
    value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};

double? _number(Object? value) {
  if (value is num) return value.toDouble();
  return GermanDecimal.tryParse(value?.toString());
}

final class EnergyRange {
  const EnergyRange({
    this.lower,
    this.midpoint,
    this.upper,
    this.unit = 'kcal/Tag',
  });

  final double? lower;
  final double? midpoint;
  final double? upper;
  final String unit;

  bool get isAvailable => lower != null || midpoint != null || upper != null;

  String get display {
    if (lower != null && upper != null) {
      return '${GermanDecimal.format(lower!, decimals: 0)}–${GermanDecimal.format(upper!, decimals: 0)} $unit';
    }
    if (midpoint != null) {
      return '${GermanDecimal.format(midpoint!, decimals: 0)} $unit';
    }
    return 'Nicht verfügbar';
  }

  Map<String, dynamic> toJson() => {
    'lower': lower,
    'midpoint': midpoint,
    'upper': upper,
    'unit': unit,
  };

  factory EnergyRange.fromJson(Object? raw) {
    final json = _map(raw);
    return EnergyRange(
      lower: _number(json['lower'] ?? json['lower_value'] ?? json['minimum']),
      midpoint: _number(json['midpoint'] ?? json['value'] ?? json['default']),
      upper: _number(json['upper'] ?? json['upper_value'] ?? json['maximum']),
      unit: json['unit']?.toString() ?? 'kcal/Tag',
    );
  }
}

final class SafetyFlag {
  const SafetyFlag({
    required this.code,
    required this.severity,
    required this.explanation,
    required this.recommendedAction,
  });

  final String code;
  final String severity;
  final String explanation;
  final String recommendedAction;

  factory SafetyFlag.fromJson(Object? raw) {
    final json = _map(raw);
    return SafetyFlag(
      code: json['code']?.toString() ?? 'UNSPECIFIED',
      severity: json['severity']?.toString() ?? 'information',
      explanation:
          (json['explanation_de'] ?? json['explanation'])?.toString() ??
          'Für diese Auswertung liegt ein Hinweis vor.',
      recommendedAction:
          (json['recommended_action_de'] ?? json['recommended_action'])
              ?.toString() ??
          '',
    );
  }

  Map<String, dynamic> toJson() => {
    'code': code,
    'severity': severity,
    'explanation_de': explanation,
    'recommended_action_de': recommendedAction,
  };
}

final class AssessmentMetric {
  const AssessmentMetric({
    required this.code,
    required this.displayValue,
    required this.unit,
    required this.methodCode,
    required this.explanation,
    required this.limitations,
    required this.calculationInputs,
    required this.sourceMetadata,
    required this.confidenceType,
    this.rawValue,
    this.lowerValue,
    this.upperValue,
    this.applicationRuleIdentifier,
  });

  final String code;
  final double? rawValue;
  final String displayValue;
  final double? lowerValue;
  final double? upperValue;
  final String unit;
  final String methodCode;
  final String explanation;
  final String limitations;
  final Map<String, dynamic> calculationInputs;
  final Map<String, dynamic> sourceMetadata;
  final String? applicationRuleIdentifier;
  final String confidenceType;

  factory AssessmentMetric.fromJson(Object? raw, {String? fallbackCode}) {
    final json = _map(raw);
    return AssessmentMetric(
      code:
          (json['metric_code'] ?? json['code'] ?? fallbackCode)?.toString() ??
          'metric',
      rawValue: _number(json['raw_value'] ?? json['value']),
      displayValue:
          (json['display_value'] ?? json['display'])?.toString() ??
          _number(json['raw_value'] ?? json['value'])?.toString() ??
          'Nicht verfügbar',
      lowerValue: _number(json['lower_value'] ?? json['lower']),
      upperValue: _number(json['upper_value'] ?? json['upper']),
      unit: json['unit']?.toString() ?? '',
      methodCode:
          (json['method_code'] ?? json['formula_identifier'] ?? json['method'])
              ?.toString() ??
          'nicht angegeben',
      explanation:
          (json['explanation_de'] ?? json['explanation'])?.toString() ??
          'Für diese Kennzahl wurde keine zusätzliche Erklärung bereitgestellt.',
      limitations:
          (json['limitations_de'] ?? json['limitations'])?.toString() ??
          'Schätzwerte können vom individuellen Bedarf abweichen.',
      calculationInputs: _map(json['calculation_inputs'] ?? json['inputs']),
      sourceMetadata: _map(json['source_metadata'] ?? json['source']),
      applicationRuleIdentifier:
          (json['application_rule_identifier'] ?? json['application_rule_id'])
              ?.toString(),
      confidenceType: json['confidence_type']?.toString() ?? 'estimated',
    );
  }

  Map<String, dynamic> toJson() => {
    'metric_code': code,
    'raw_value': rawValue,
    'display_value': displayValue,
    'lower_value': lowerValue,
    'upper_value': upperValue,
    'unit': unit,
    'method_code': methodCode,
    'explanation_de': explanation,
    'limitations_de': limitations,
    'calculation_inputs': calculationInputs,
    'source_metadata': sourceMetadata,
    'application_rule_identifier': applicationRuleIdentifier,
    'confidence_type': confidenceType,
  };
}

final class AssessmentSummary {
  const AssessmentSummary({
    required this.id,
    required this.calculatedAt,
    required this.supportedScopeStatus,
    required this.goalType,
    required this.maintenanceEnergy,
    required this.targetEnergy,
    required this.macros,
    required this.warnings,
    this.energyTargetLabel,
  });

  final String id;
  final DateTime calculatedAt;
  final String supportedScopeStatus;
  final String goalType;
  final EnergyRange maintenanceEnergy;
  final EnergyRange targetEnergy;
  final Map<String, String> macros;
  final List<SafetyFlag> warnings;
  final String? energyTargetLabel;

  factory AssessmentSummary.fromJson(Map<String, dynamic> json) {
    final nestedSummary = _map(json['summary']);
    final summary = nestedSummary.isEmpty ? json : nestedSummary;
    final metrics = _metricList(json['metrics']);
    AssessmentMetric? metric(String code) {
      for (final item in metrics) {
        if (item.code == code) return item;
      }
      return null;
    }

    EnergyRange rangeFromMetric(String code) {
      final item = metric(code);
      if (item == null) return const EnergyRange();
      return EnergyRange(
        lower: item.lowerValue,
        midpoint: item.rawValue,
        upper: item.upperValue,
        unit: item.unit.isEmpty ? 'kcal/Tag' : item.unit,
      );
    }

    String metricDisplay(String code) {
      final item = metric(code);
      if (item == null) return 'Nicht verfügbar';
      return '${item.displayValue}${item.unit.isEmpty ? '' : ' ${item.unit}'}';
    }

    final rawWarnings = json['safety_flags'] ?? summary['warnings'];
    final macrosJson = _map(summary['macros']);
    final goal =
        (summary['goal_type'] ?? json['goal_type'])?.toString() ?? 'unknown';
    return AssessmentSummary(
      id: (json['id'] ?? json['assessment_id'])?.toString() ?? '',
      calculatedAt:
          DateTime.tryParse(
            (json['calculated_at'] ?? json['created_at'])?.toString() ?? '',
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      supportedScopeStatus:
          json['supported_scope_status']?.toString() ??
          summary['supported_scope_status']?.toString() ??
          'unknown',
      goalType: goal,
      maintenanceEnergy:
          EnergyRange.fromJson(
            summary['maintenance_energy'] ??
                summary['maintenance_energy_range'],
          ).isAvailable
          ? EnergyRange.fromJson(
              summary['maintenance_energy'] ??
                  summary['maintenance_energy_range'],
            )
          : rangeFromMetric('energy.maintenance'),
      targetEnergy:
          EnergyRange.fromJson(
            summary['energy_target'] ??
                summary['target_energy'] ??
                summary['target_energy_range'],
          ).isAvailable
          ? EnergyRange.fromJson(
              summary['energy_target'] ??
                  summary['target_energy'] ??
                  summary['target_energy_range'],
            )
          : rangeFromMetric('energy.goal_target'),
      macros: macrosJson.isNotEmpty
          ? macrosJson.map((key, value) => MapEntry(key, value.toString()))
          : {
              'protein': metricDisplay('macros.protein_grams'),
              'fat': metricDisplay('macros.fat_grams'),
              'carbohydrates': metricDisplay('macros.carbohydrate_grams'),
            },
      warnings: rawWarnings is List
          ? rawWarnings.map(SafetyFlag.fromJson).toList(growable: false)
          : const [],
      energyTargetLabel: summary['energy_target_summary']?.toString(),
    );
  }

  factory AssessmentSummary.fromHistoryJson(Map<String, dynamic> json) {
    final warningCodes = json['warning_codes'];
    return AssessmentSummary(
      id: json['id']?.toString() ?? '',
      calculatedAt:
          DateTime.tryParse(json['calculated_at']?.toString() ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      supportedScopeStatus:
          json['supported_scope_status']?.toString() ?? 'unknown',
      goalType: json['goal_type']?.toString() ?? 'unknown',
      maintenanceEnergy: const EnergyRange(),
      targetEnergy: EnergyRange(midpoint: _number(json['energy_target'])),
      macros: const {},
      warnings: warningCodes is List
          ? warningCodes
                .map(
                  (code) => SafetyFlag(
                    code: code.toString(),
                    severity: 'warning',
                    explanation: code.toString(),
                    recommendedAction: '',
                  ),
                )
                .toList(growable: false)
          : const [],
      energyTargetLabel: json['energy_target_summary']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'calculated_at': calculatedAt.toUtc().toIso8601String(),
    'supported_scope_status': supportedScopeStatus,
    'goal_type': goalType,
    'maintenance_energy': maintenanceEnergy.toJson(),
    'target_energy': targetEnergy.toJson(),
    'macros': macros,
    'safety_flags': warnings.map((warning) => warning.toJson()).toList(),
    if (energyTargetLabel != null) 'energy_target_summary': energyTargetLabel,
  };
}

final class AssessmentReport {
  const AssessmentReport({
    required this.summary,
    required this.referenceSetIdentifier,
    required this.referenceSetVersion,
    required this.applicationRuleSetIdentifier,
    required this.applicationRuleSetVersion,
    required this.engineVersion,
    required this.metrics,
    required this.foodGroups,
    required this.unavailableMicronutrients,
  });

  final AssessmentSummary summary;
  final String referenceSetIdentifier;
  final String referenceSetVersion;
  final String applicationRuleSetIdentifier;
  final String applicationRuleSetVersion;
  final String engineVersion;
  final List<AssessmentMetric> metrics;
  final List<Map<String, dynamic>> foodGroups;
  final List<String> unavailableMicronutrients;

  factory AssessmentReport.fromJson(Map<String, dynamic> json) {
    final summary = _map(json['summary']);
    final rawFoodGroups = summary['food_groups'];
    final micronutrients = _map(summary['micronutrients']);
    final rawUnavailable =
        micronutrients['unavailable_codes'] ??
        summary['unavailable_micronutrient_codes'] ??
        summary['unavailable_micronutrients'];
    return AssessmentReport(
      summary: AssessmentSummary.fromJson(json),
      referenceSetIdentifier:
          json['reference_set_identifier']?.toString() ?? 'nicht angegeben',
      referenceSetVersion:
          json['reference_set_version']?.toString() ?? 'nicht angegeben',
      applicationRuleSetIdentifier:
          json['application_rule_set_identifier']?.toString() ??
          'nicht angegeben',
      applicationRuleSetVersion:
          json['application_rule_set_version']?.toString() ?? 'nicht angegeben',
      engineVersion: json['engine_version']?.toString() ?? 'nicht angegeben',
      metrics: _metricList(json['metrics']),
      foodGroups: rawFoodGroups is List
          ? rawFoodGroups
                .whereType<Map>()
                .map((item) => Map<String, dynamic>.from(item))
                .toList(growable: false)
          : const [],
      unavailableMicronutrients: rawUnavailable is List
          ? rawUnavailable
                .map((item) => item.toString())
                .toList(growable: false)
          : const [],
    );
  }
}

List<AssessmentMetric> _metricList(Object? raw) {
  if (raw is List) {
    return raw.map(AssessmentMetric.fromJson).toList(growable: false);
  }
  if (raw is Map) {
    return raw.entries
        .map(
          (entry) => AssessmentMetric.fromJson(
            entry.value,
            fallbackCode: entry.key.toString(),
          ),
        )
        .toList(growable: false);
  }
  return const [];
}

final class CachedAssessment {
  const CachedAssessment({required this.summary, required this.cachedAt});
  final AssessmentSummary summary;
  final DateTime cachedAt;

  bool isStale(DateTime now, {Duration maxAge = const Duration(hours: 24)}) =>
      now.toUtc().difference(cachedAt.toUtc()) > maxAge;
}
