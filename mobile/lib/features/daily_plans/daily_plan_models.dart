import '../../core/formatting/german_decimal.dart';

final class DailyNutrient {
  const DailyNutrient({
    required this.code,
    required this.name,
    required this.amount,
    required this.unit,
    required this.complete,
    required this.coverage,
  });
  factory DailyNutrient.fromJson(Map<String, dynamic> json) => DailyNutrient(
    code: json['nutrient_code'].toString(),
    name: json['display_name_de'].toString(),
    amount: json['amount'] == null
        ? null
        : GermanDecimal.formatString(json['amount']),
    unit: json['unit'].toString(),
    complete: json['is_complete'] == true,
    coverage: json['coverage_ratio'] == null
        ? null
        : GermanDecimal.format(
            (num.tryParse(json['coverage_ratio'].toString()) ?? 0) * 100,
          ),
  );
  final String code, name, unit;
  final String? amount, coverage;
  final bool complete;
}

final class DailyComparison {
  const DailyComparison({
    required this.code,
    required this.name,
    required this.amount,
    required this.unit,
    required this.kind,
    required this.relation,
    required this.explanation,
    required this.remaining,
    required this.remainingStatus,
    required this.targetMinimum,
    required this.targetValue,
    required this.targetMaximum,
  });
  factory DailyComparison.fromJson(Map<String, dynamic> json) =>
      DailyComparison(
        code: json['nutrient_code'].toString(),
        name: json['display_name_de'].toString(),
        amount: json['amount'] == null
            ? null
            : GermanDecimal.formatString(json['amount']),
        unit: json['unit'].toString().replaceAll('/Tag', ''),
        kind: json['target_kind'].toString(),
        relation: json['relation'].toString(),
        explanation: json['explanation_de'].toString(),
        remaining: json['remaining_amount'] == null
            ? null
            : GermanDecimal.formatString(json['remaining_amount']),
        remainingStatus: json['remaining_status']?.toString(),
        targetMinimum: json['target_minimum'] == null
            ? null
            : GermanDecimal.formatString(json['target_minimum']),
        targetValue: json['target_value'] == null
            ? null
            : GermanDecimal.formatString(json['target_value']),
        targetMaximum: json['target_maximum'] == null
            ? null
            : GermanDecimal.formatString(json['target_maximum']),
      );
  final String code, name, unit, kind, relation, explanation;
  final String? amount, remaining, remainingStatus;
  final String? targetMinimum, targetValue, targetMaximum;
}

final class DailyEntry {
  const DailyEntry({
    required this.id,
    required this.type,
    required this.sourceId,
    required this.name,
    required this.archived,
    required this.portions,
    required this.quantity,
    required this.unitCode,
    required this.measureId,
    required this.estimated,
    required this.note,
  });
  factory DailyEntry.fromJson(Map<String, dynamic> json) => DailyEntry(
    id: json['id']?.toString(),
    type: json['entry_type'].toString(),
    sourceId: json['source_id'].toString(),
    name: json['source_name'].toString(),
    archived: json['is_archived'] == true,
    portions: json['recipe_portion_count'] == null
        ? null
        : GermanDecimal.formatString(json['recipe_portion_count']),
    quantity: json['food_quantity'] == null
        ? null
        : GermanDecimal.formatString(json['food_quantity']),
    unitCode: json['food_unit_code']?.toString(),
    measureId: json['food_measure_id']?.toString(),
    estimated: json['conversion_is_estimated'] == true,
    note: json['note']?.toString(),
  );
  final String? id, portions, quantity, unitCode, measureId, note;
  final String type, sourceId, name;
  final bool archived, estimated;
  Map<String, dynamic> toPayload() => {
    'entry_type': type,
    if (type == 'recipe') 'recipe_id': sourceId else 'food_id': sourceId,
    'recipe_portion_count': portions?.replaceAll(',', '.'),
    'food_quantity': quantity?.replaceAll(',', '.'),
    'food_unit_code': unitCode,
    'food_measure_id': measureId,
    'note': note,
  };
}

final class DailyMeal {
  const DailyMeal({
    required this.id,
    required this.type,
    required this.name,
    required this.customName,
    required this.time,
    required this.notes,
    required this.entries,
    required this.nutrients,
  });
  factory DailyMeal.fromJson(Map<String, dynamic> json) => DailyMeal(
    id: json['id']?.toString(),
    type: json['meal_type'].toString(),
    name: json['meal_name'].toString(),
    customName:
        json['meal_name']?.toString() ==
            _mealLabel(json['meal_type'].toString())
        ? null
        : json['meal_name']?.toString(),
    time: json['planned_time']?.toString().substring(0, 5),
    notes: json['notes']?.toString(),
    entries: (json['entries'] as List)
        .whereType<Map>()
        .map((item) => DailyEntry.fromJson(Map<String, dynamic>.from(item)))
        .toList(),
    nutrients: (json['nutrient_totals'] as List)
        .whereType<Map>()
        .map((item) => DailyNutrient.fromJson(Map<String, dynamic>.from(item)))
        .toList(),
  );
  final String? id, customName, time, notes;
  final String type, name;
  final List<DailyEntry> entries;
  final List<DailyNutrient> nutrients;
  Map<String, dynamic> toPayload() => {
    'meal_type': type,
    'custom_name': customName,
    'planned_time': time,
    'notes': notes,
    'entries': entries.map((item) => item.toPayload()).toList(),
  };
}

final class DailyPlan {
  const DailyPlan({
    required this.id,
    required this.date,
    required this.name,
    required this.notes,
    required this.archived,
    required this.assessmentId,
    required this.meals,
    required this.nutrients,
    required this.comparisons,
    required this.warnings,
    required this.quality,
    required this.targetBasis,
  });
  factory DailyPlan.fromJson(Map<String, dynamic> json) {
    final plan = Map<String, dynamic>.from(json['plan'] as Map);
    final assessment = json['assessment'] as Map?;
    return DailyPlan(
      id: plan['id']?.toString(),
      date: DateTime.parse(plan['plan_date'].toString()),
      name: plan['name']?.toString(),
      notes: plan['notes']?.toString(),
      archived: plan['is_archived'] == true,
      assessmentId: assessment?['id']?.toString(),
      meals: (json['meals'] as List)
          .whereType<Map>()
          .map((item) => DailyMeal.fromJson(Map<String, dynamic>.from(item)))
          .toList(),
      nutrients: (json['daily_totals'] as List)
          .whereType<Map>()
          .map(
            (item) => DailyNutrient.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList(),
      comparisons: (json['target_comparison'] as List)
          .whereType<Map>()
          .map(
            (item) => DailyComparison.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList(),
      warnings: (json['warnings'] as List)
          .whereType<Map>()
          .map((item) => item['explanation_de'].toString())
          .toList(),
      quality: (json['quality'] as Map)['quality_level'].toString(),
      targetBasis: Map<String, dynamic>.from(
        (json['target_basis'] as Map?) ?? const {},
      ),
    );
  }
  final String? id, name, notes, assessmentId;
  final DateTime date;
  final bool archived;
  final List<DailyMeal> meals;
  final List<DailyNutrient> nutrients;
  final List<DailyComparison> comparisons;
  final List<String> warnings;
  final String quality;
  final Map<String, dynamic> targetBasis;
  int get entryCount => meals.fold(0, (sum, meal) => sum + meal.entries.length);
}

String apiDate(DateTime date) =>
    '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

String _mealLabel(String code) =>
    const {
      'breakfast': 'Frühstück',
      'morning_snack': 'Vormittagssnack',
      'lunch': 'Mittagessen',
      'afternoon_snack': 'Nachmittagssnack',
      'dinner': 'Abendessen',
      'evening_snack': 'Abendsnack',
      'other': 'Andere Mahlzeit',
    }[code] ??
    'Andere Mahlzeit';
