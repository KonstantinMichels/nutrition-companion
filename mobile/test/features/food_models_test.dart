import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/foods/food_models.dart';

void main() {
  test('unknown nutrients remain absent and zero remains explicit', () {
    final food = FoodItem.fromJson({
      'id': 'food-1',
      'name': 'Test',
      'brand': null,
      'category_code': null,
      'reference_unit': 'g',
      'source_type': 'user_entered',
      'source_name': null,
      'is_archived': false,
      'quality': {'quality_level': 'incomplete'},
      'nutrients': [
        {
          'nutrient_code': 'fat',
          'display_name_de': 'Fett',
          'amount': '0',
          'unit': 'g',
          'is_derived': false,
        },
      ],
    });
    expect(food.nutrients.single.amount, '0');
    expect(food.nutrients.where((value) => value.code == 'protein'), isEmpty);
  });

  test('barcode preview preserves source and absent nutrients', () {
    final preview = BarcodePreview.fromJson({
      'barcode': '12345678',
      'name': 'Testprodukt',
      'brand': 'Testmarke',
      'quantity_label': '500 g',
      'reference_unit': 'g',
      'nutrients': [
        {'nutrient_code': 'fat', 'amount': '0', 'unit': 'g'},
      ],
      'image_url': null,
      'source_name': 'Open Food Facts',
      'source_version': '1234',
      'warnings': ['Bitte prüfen.'],
    });
    expect(preview.sourceName, 'Open Food Facts');
    expect(preview.nutrients.single['amount'], '0');
    expect(
      preview.nutrients.where((value) => value['nutrient_code'] == 'protein'),
      isEmpty,
    );
  });
}
