import '../../core/formatting/german_decimal.dart';

final class ComparableAssessmentItem {
  const ComparableAssessmentItem({
    required this.id,
    required this.calculatedAt,
    required this.goalType,
    required this.energyTarget,
    required this.usable,
    required this.reason,
  });
  factory ComparableAssessmentItem.fromJson(Map<String, dynamic> json) =>
      ComparableAssessmentItem(
        id: json['id'].toString(),
        calculatedAt: DateTime.parse(json['calculated_at'].toString()),
        goalType: json['goal_type'].toString(),
        energyTarget: json['energy_target_summary']?.toString(),
        usable: json['usable_for_comparison'] == true,
        reason: json['unavailable_reason_de']?.toString(),
      );
  final String id, goalType;
  final DateTime calculatedAt;
  final String? energyTarget, reason;
  final bool usable;
}

final class ComparisonItem {
  const ComparisonItem({
    required this.code,
    required this.name,
    required this.selectedAmount,
    required this.unit,
    required this.targetKind,
    required this.targetMinimum,
    required this.targetValue,
    required this.targetMaximum,
    required this.status,
    required this.relation,
    required this.coverage,
    required this.explanation,
    required this.formula,
    required this.amountPerServing,
  });
  factory ComparisonItem.fromJson(Map<String, dynamic> json) => ComparisonItem(
    code: json['nutrient_code'].toString(),
    name: json['display_name_de'].toString(),
    selectedAmount: json['selected_amount'] == null
        ? null
        : GermanDecimal.formatString(json['selected_amount']),
    amountPerServing: json['amount_per_serving'] == null
        ? null
        : GermanDecimal.formatString(json['amount_per_serving']),
    unit: json['unit'].toString().replaceAll('/Tag', ''),
    targetKind: json['target_kind'].toString(),
    targetMinimum: _number(json['target_minimum']),
    targetValue: _number(json['target_value']),
    targetMaximum: _number(json['target_maximum']),
    status: json['comparison_status'].toString(),
    relation: json['relation'].toString(),
    coverage: GermanDecimal.formatString(
      (num.tryParse(json['coverage_ratio'].toString()) ?? 0) * 100,
    ),
    explanation: json['explanation'].toString(),
    formula: json['formula_de']?.toString(),
  );
  static String? _number(Object? value) =>
      value == null ? null : GermanDecimal.formatString(value);
  final String code,
      name,
      unit,
      targetKind,
      status,
      relation,
      coverage,
      explanation;
  final String? selectedAmount,
      amountPerServing,
      targetMinimum,
      targetValue,
      targetMaximum,
      formula;
}

final class ComparisonGroup {
  const ComparisonGroup({required this.name, required this.items});
  factory ComparisonGroup.fromJson(Map<String, dynamic> json) =>
      ComparisonGroup(
        name: json['display_name_de'].toString(),
        items: (json['items'] as List)
            .whereType<Map>()
            .map(
              (item) =>
                  ComparisonItem.fromJson(Map<String, dynamic>.from(item)),
            )
            .toList(),
      );
  final String name;
  final List<ComparisonItem> items;
}

final class RecipeComparison {
  const RecipeComparison({
    required this.assessmentId,
    required this.assessmentDate,
    required this.goalType,
    required this.referenceVersion,
    required this.ruleVersion,
    required this.portionCount,
    required this.baseServings,
    required this.recipeUpdatedAt,
    required this.groups,
    required this.notices,
  });
  factory RecipeComparison.fromJson(Map<String, dynamic> json) {
    final assessment = Map<String, dynamic>.from(json['assessment'] as Map);
    final recipe = Map<String, dynamic>.from(json['recipe'] as Map);
    return RecipeComparison(
      assessmentId: assessment['id'].toString(),
      assessmentDate: DateTime.parse(assessment['calculated_at'].toString()),
      goalType: assessment['goal_type'].toString(),
      referenceVersion: assessment['reference_set_version'].toString(),
      ruleVersion: assessment['application_rule_set_version'].toString(),
      portionCount: GermanDecimal.formatString(json['portion_count']),
      baseServings: GermanDecimal.formatString(recipe['base_servings']),
      recipeUpdatedAt: DateTime.parse(recipe['updated_at'].toString()),
      groups: (json['groups'] as List)
          .whereType<Map>()
          .map(
            (item) => ComparisonGroup.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList(),
      notices: (json['notices'] as List)
          .map((item) => item.toString())
          .toList(),
    );
  }
  final String assessmentId,
      goalType,
      referenceVersion,
      ruleVersion,
      portionCount,
      baseServings;
  final DateTime assessmentDate, recipeUpdatedAt;
  final List<ComparisonGroup> groups;
  final List<String> notices;
  List<ComparisonItem> get items =>
      groups.expand((group) => group.items).toList();
}
