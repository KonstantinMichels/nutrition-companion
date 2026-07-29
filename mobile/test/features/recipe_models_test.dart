import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/recipes/recipe_models.dart';

void main() {
  test('recipe model preserves known zero and unavailable per-100-g value', () {
    final recipe = RecipeItem.fromJson({
      'id': 'recipe-1',
      'name': 'Testgericht',
      'description': null,
      'servings': '2.5',
      'tag_labels': ['Fertiggericht'],
      'is_archived': false,
      'ingredients': <Object>[],
      'steps': <Object>[],
      'nutrients': [
        {
          'nutrient_code': 'protein',
          'display_name_de': 'Protein',
          'amount_total': '0',
          'amount_per_serving': '0',
          'amount_per_100g': null,
          'unit': 'g',
          'is_complete': true,
        },
      ],
      'quality': {
        'quality_level': 'basic_complete',
        'warnings': <Object>[],
      },
      'weight': {'status': 'unavailable'},
    });

    expect(recipe.servings, '2,5');
    expect(recipe.nutrients.single.total, '0');
    expect(recipe.nutrients.single.per100g, isNull);
    expect(recipe.weightStatus, 'unavailable');
  });
}
