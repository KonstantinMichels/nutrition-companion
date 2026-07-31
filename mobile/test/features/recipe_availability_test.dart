import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/recipes/recipe_availability_models.dart';

void main() {
  test('parses and formats an availability summary', () {
    final summary = RecipeAvailabilitySummary.fromJson({
      'recipe_id': 'recipe-1',
      'name': 'Pizza',
      'availability_state': 'partially_available',
      'maximum_possible_portions': '2.500000000',
      'missing_ingredient_count': 1,
      'unresolved_ingredient_count': 0,
      'is_archived': false,
    });

    expect(summary.maximum, '2,5');
    expect(summary.missing, 1);
    expect(summary.state, 'partially_available');
  });

  test('parses detail quantities, warnings, and contributing lots', () {
    final availability = RecipeAvailability.fromJson({
      'availability_state': 'fully_available',
      'requested_portion_count': '1.500000000',
      'maximum_possible_portions': '3.000000000',
      'maximum_complete_whole_portions': 3,
      'calculated_at': '2026-07-29T10:00:00Z',
      'limiting_ingredients': [
        {'food_name': 'Tomate'},
      ],
      'warnings': [
        {'message_de': 'Archiviertes Lebensmittel.'},
      ],
      'ingredients': [
        {
          'food_id': 'food-1',
          'food_name': 'Tomate',
          'required_quantity': '150.000000000',
          'available_quantity': '300.000000000',
          'missing_quantity': '0.000000000',
          'hypothetical_remaining_quantity': '150.000000000',
          'canonical_unit': 'g',
          'availability_state': 'fully_available',
          'is_optional': false,
          'conversion_estimated': false,
          'archived_food': false,
          'lot_contributions': [
            {
              'stock_lot_id': 'lot-1',
              'location_name': 'Kühlschrank',
              'available_quantity': '300.000000000',
              'canonical_unit': 'g',
              'date_status': 'valid',
            },
          ],
        },
      ],
    });

    expect(availability.portions, '1,5');
    expect(availability.maximum, '3');
    expect(availability.limiting, ['Tomate']);
    expect(availability.ingredients.single.required, '150');
    expect(availability.ingredients.single.remaining, '150');
    expect(
      availability.ingredients.single.lots.single['stock_lot_id'],
      'lot-1',
    );
  });
}
