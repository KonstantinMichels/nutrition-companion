import '../../core/formatting/german_decimal.dart';

final class RecipeAvailabilitySummary {
  const RecipeAvailabilitySummary({
    required this.recipeId,
    required this.name,
    required this.state,
    required this.maximum,
    required this.missing,
    required this.unresolved,
    required this.archived,
  });
  factory RecipeAvailabilitySummary.fromJson(Map<String, dynamic> json) =>
      RecipeAvailabilitySummary(
        recipeId: json['recipe_id'].toString(),
        name: json['name'].toString(),
        state: json['availability_state'].toString(),
        maximum: GermanDecimal.formatString(json['maximum_possible_portions']),
        missing: (json['missing_ingredient_count'] as num).toInt(),
        unresolved: (json['unresolved_ingredient_count'] as num).toInt(),
        archived: json['is_archived'] == true,
      );
  final String recipeId, name, state, maximum;
  final int missing, unresolved;
  final bool archived;
}

final class RecipeAvailability {
  const RecipeAvailability({
    required this.state,
    required this.portions,
    required this.maximum,
    required this.wholePortions,
    required this.ingredients,
    required this.limiting,
    required this.warnings,
    required this.calculatedAt,
  });
  factory RecipeAvailability.fromJson(Map<String, dynamic> json) =>
      RecipeAvailability(
        state: json['availability_state'].toString(),
        portions: GermanDecimal.formatString(json['requested_portion_count']),
        maximum: GermanDecimal.formatString(json['maximum_possible_portions']),
        wholePortions: (json['maximum_complete_whole_portions'] as num?)
            ?.toInt(),
        ingredients: (json['ingredients'] as List? ?? const [])
            .whereType<Map>()
            .map(
              (e) =>
                  AvailabilityIngredient.fromJson(Map<String, dynamic>.from(e)),
            )
            .toList(),
        limiting: (json['limiting_ingredients'] as List? ?? const [])
            .whereType<Map>()
            .map((e) => e['food_name'].toString())
            .toList(),
        warnings: (json['warnings'] as List? ?? const [])
            .whereType<Map>()
            .map((e) => e['message_de'].toString())
            .toList(),
        calculatedAt: DateTime.parse(json['calculated_at'].toString()),
      );
  final String state, portions, maximum;
  final int? wholePortions;
  final List<AvailabilityIngredient> ingredients;
  final List<String> limiting, warnings;
  final DateTime calculatedAt;
}

final class AvailabilityIngredient {
  const AvailabilityIngredient({
    required this.foodId,
    required this.name,
    required this.required,
    required this.available,
    required this.missing,
    required this.remaining,
    required this.unit,
    required this.state,
    required this.optional,
    required this.estimated,
    required this.archived,
    required this.lots,
  });
  factory AvailabilityIngredient.fromJson(Map<String, dynamic> json) =>
      AvailabilityIngredient(
        foodId: json['food_id'].toString(),
        name: json['food_name'].toString(),
        required: GermanDecimal.formatString(json['required_quantity']),
        available: GermanDecimal.formatString(json['available_quantity']),
        missing: GermanDecimal.formatString(json['missing_quantity']),
        remaining: json['hypothetical_remaining_quantity'] == null
            ? null
            : GermanDecimal.formatString(
                json['hypothetical_remaining_quantity'],
              ),
        unit: json['canonical_unit'].toString(),
        state: json['availability_state'].toString(),
        optional: json['is_optional'] == true,
        estimated: json['conversion_estimated'] == true,
        archived: json['archived_food'] == true,
        lots: (json['lot_contributions'] as List? ?? const [])
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e))
            .toList(),
      );
  final String foodId, name, required, available, missing, unit, state;
  final String? remaining;
  final bool optional, estimated, archived;
  final List<Map<String, dynamic>> lots;
}
