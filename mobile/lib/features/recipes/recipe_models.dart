import '../../core/formatting/german_decimal.dart';

final class RecipeIngredient {
  const RecipeIngredient({
    required this.id,
    required this.foodId,
    required this.foodName,
    required this.quantity,
    required this.unitCode,
    required this.unitName,
    required this.unitType,
    required this.equivalentQuantity,
    required this.equivalentUnit,
    required this.archived,
    required this.estimated,
    required this.note,
  });
  factory RecipeIngredient.fromJson(Map<String, dynamic> json) =>
      RecipeIngredient(
        id: json['id'].toString(),
        foodId: json['food_id'].toString(),
        foodName: json['food_name'].toString(),
        quantity: GermanDecimal.formatString(json['quantity']),
        unitCode: json['unit_code'].toString(),
        unitName: json['unit_name'].toString(),
        unitType: json['unit_type'].toString(),
        equivalentQuantity: json['equivalent_quantity'] == null
            ? null
            : GermanDecimal.formatString(json['equivalent_quantity']),
        equivalentUnit: json['equivalent_unit']?.toString(),
        archived: json['food_is_archived'] == true,
        estimated: json['conversion_is_estimated'] == true,
        note: json['preparation_note']?.toString(),
      );
  final String id, foodId, foodName, quantity, unitCode, unitName, unitType;
  final String? equivalentQuantity, equivalentUnit;
  final String? note;
  final bool archived, estimated;
}

final class RecipeNutrient {
  const RecipeNutrient({
    required this.code,
    required this.name,
    required this.total,
    required this.perServing,
    required this.per100g,
    required this.unit,
    required this.complete,
  });
  factory RecipeNutrient.fromJson(Map<String, dynamic> json) => RecipeNutrient(
    code: json['nutrient_code'].toString(),
    name: json['display_name_de'].toString(),
    total: GermanDecimal.formatString(json['amount_total']),
    perServing: GermanDecimal.formatString(json['amount_per_serving']),
    per100g: json['amount_per_100g'] == null
        ? null
        : GermanDecimal.formatString(json['amount_per_100g']),
    unit: json['unit'].toString(),
    complete: json['is_complete'] == true,
  );
  final String code, name, total, perServing, unit;
  final String? per100g;
  final bool complete;
}

final class RecipeStepItem {
  const RecipeStepItem({required this.instruction, required this.duration});
  factory RecipeStepItem.fromJson(Map<String, dynamic> json) => RecipeStepItem(
    instruction: json['instruction'].toString(),
    duration: json['optional_duration_minutes'] as int?,
  );
  final String instruction;
  final int? duration;
}

final class RecipeItem {
  const RecipeItem({
    required this.id,
    required this.name,
    required this.description,
    required this.servings,
    required this.tags,
    required this.archived,
    required this.ingredients,
    required this.steps,
    required this.nutrients,
    required this.quality,
    required this.warnings,
    required this.weightStatus,
  });
  factory RecipeItem.fromJson(Map<String, dynamic> json) => RecipeItem(
    id: json['id'].toString(),
    name: json['name'].toString(),
    description: json['description']?.toString(),
    servings: GermanDecimal.formatString(json['servings']),
    tags: (json['tag_labels'] as List).map((e) => e.toString()).toList(),
    archived: json['is_archived'] == true,
    ingredients: (json['ingredients'] as List)
        .whereType<Map>()
        .map((e) => RecipeIngredient.fromJson(Map<String, dynamic>.from(e)))
        .toList(),
    steps: (json['steps'] as List)
        .whereType<Map>()
        .map((e) => RecipeStepItem.fromJson(Map<String, dynamic>.from(e)))
        .toList(),
    nutrients: (json['nutrients'] as List)
        .whereType<Map>()
        .map((e) => RecipeNutrient.fromJson(Map<String, dynamic>.from(e)))
        .toList(),
    quality: (json['quality'] as Map)['quality_level'].toString(),
    warnings: ((json['quality'] as Map)['warnings'] as List)
        .map((e) => e.toString())
        .toList(),
    weightStatus: (json['weight'] as Map)['status'].toString(),
  );
  final String id, name, servings, quality, weightStatus;
  final String? description;
  final bool archived;
  final List<String> tags, warnings;
  final List<RecipeIngredient> ingredients;
  final List<RecipeStepItem> steps;
  final List<RecipeNutrient> nutrients;
}
