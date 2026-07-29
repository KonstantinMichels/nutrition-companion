final class WeeklyPlan {
  const WeeklyPlan({
    required this.weekStart,
    required this.weekEnd,
    required this.weekNumber,
    required this.weekYear,
    required this.days,
    required this.counts,
    required this.totals,
    required this.comparisons,
    required this.quality,
    required this.warnings,
  });

  factory WeeklyPlan.fromJson(Map<String, dynamic> json) => WeeklyPlan(
    weekStart: DateTime.parse(json['week_start'].toString()),
    weekEnd: DateTime.parse(json['week_end'].toString()),
    weekNumber: json['iso_week_number'] as int,
    weekYear: json['iso_week_year'] as int,
    days: (json['days'] as List)
        .map(
          (item) => WeeklyDay.fromJson(Map<String, dynamic>.from(item as Map)),
        )
        .toList(),
    counts: Map<String, dynamic>.from(json['day_counts'] as Map),
    totals: (json['weekly_totals'] as List)
        .map(
          (item) =>
              WeeklyNutrient.fromJson(Map<String, dynamic>.from(item as Map)),
        )
        .toList(),
    comparisons: (json['weekly_target_comparison'] as List)
        .map(
          (item) =>
              WeeklyComparison.fromJson(Map<String, dynamic>.from(item as Map)),
        )
        .toList(),
    quality: Map<String, dynamic>.from(json['quality'] as Map),
    warnings: (json['warnings'] as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList(),
  );

  final DateTime weekStart, weekEnd;
  final int weekNumber, weekYear;
  final List<WeeklyDay> days;
  final Map<String, dynamic> counts, quality;
  final List<WeeklyNutrient> totals;
  final List<WeeklyComparison> comparisons;
  final List<Map<String, dynamic>> warnings;

  WeeklyNutrient? nutrient(String code) =>
      totals.where((item) => item.code == code).firstOrNull;
}

final class WeeklyDay {
  const WeeklyDay({
    required this.date,
    required this.weekday,
    required this.state,
    required this.plan,
    required this.summary,
    required this.warnings,
    required this.meals,
  });
  factory WeeklyDay.fromJson(Map<String, dynamic> json) => WeeklyDay(
    date: DateTime.parse(json['date'].toString()),
    weekday: json['weekday'].toString(),
    state: json['state'].toString(),
    plan: json['plan'] == null
        ? null
        : Map<String, dynamic>.from(json['plan'] as Map),
    summary: Map<String, dynamic>.from(json['summary'] as Map),
    warnings: (json['warnings'] as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList(),
    meals: (json['meals'] as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList(),
  );
  final DateTime date;
  final String weekday, state;
  final Map<String, dynamic>? plan;
  final Map<String, dynamic> summary;
  final List<Map<String, dynamic>> warnings, meals;
}

final class WeeklyNutrient {
  const WeeklyNutrient({
    required this.code,
    required this.name,
    required this.category,
    required this.amount,
    required this.average,
    required this.unit,
    required this.complete,
    required this.coverage,
  });
  factory WeeklyNutrient.fromJson(Map<String, dynamic> json) => WeeklyNutrient(
    code: json['nutrient_code'].toString(),
    name: json['display_name_de'].toString(),
    category: json['category'].toString(),
    amount: json['amount']?.toString(),
    average: json['average_per_planned_day']?.toString(),
    unit: json['unit'].toString(),
    complete: json['is_complete'] as bool,
    coverage: json['coverage_ratio']?.toString(),
  );
  final String code, name, category, unit;
  final String? amount, average, coverage;
  final bool complete;
}

final class WeeklyComparison {
  const WeeklyComparison({
    required this.code,
    required this.name,
    required this.category,
    required this.kind,
    required this.amount,
    required this.average,
    required this.unit,
    required this.minimum,
    required this.value,
    required this.maximum,
    required this.targetDays,
    required this.relation,
    required this.basis,
    required this.explanation,
    required this.coverage,
  });
  factory WeeklyComparison.fromJson(Map<String, dynamic> json) =>
      WeeklyComparison(
        code: json['nutrient_code'].toString(),
        name: json['display_name_de'].toString(),
        category: json['category'].toString(),
        kind: json['target_kind']?.toString(),
        amount: json['amount']?.toString(),
        average: json['average_per_planned_day']?.toString(),
        unit: json['unit'].toString(),
        minimum: json['target_minimum']?.toString(),
        value: json['target_value']?.toString(),
        maximum: json['target_maximum']?.toString(),
        targetDays: json['target_day_count'] as int,
        relation: json['relation'].toString(),
        basis: json['target_basis_status'].toString(),
        explanation: json['explanation_de'].toString(),
        coverage: json['coverage_ratio']?.toString(),
      );
  final String code, name, category, unit, relation, basis, explanation;
  final String? kind, amount, average, minimum, value, maximum, coverage;
  final int targetDays;
}
