import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/shopping_lists/shopping_list_models.dart';

void main() {
  test('shopping-list detail accepts API decimal strings', () {
    final detail = ShoppingListDetail.fromJson({
      'id': 'list-1',
      'name': 'Tagesplan',
      'status': 'open',
      'source_type': 'daily_plan',
      'active_item_count': 1,
      'checked_item_count': 0,
      'is_archived': false,
      'version': 1,
      'pantry_considered': true,
      'items': [
        {
          'id': 'item-1',
          'name': 'Haferflocken',
          'category_code': 'other',
          'origin_type': 'generated',
          'is_checked': false,
          'purchase_quantity': '250.000000000000000',
          'required_quantity': '300.000000000000000',
          'pantry_available_quantity': '50.000000000000000',
          'suggested_purchase_quantity': '250.000000000000000',
          'purchase_unit_code': 'g',
        },
      ],
    });

    expect(detail.items.single.quantity, 250);
    expect(detail.items.single.required, 300);
    expect(detail.items.single.available, 50);
    expect(detail.items.single.suggested, 250);
  });

  test('shopping-list model also tolerates localized decimal strings', () {
    final item = ShoppingItem.fromJson({
      'id': 'item-1',
      'name': 'Äpfel',
      'is_checked': false,
      'manual_quantity': '2,5',
    });

    expect(item.quantity, 2.5);
  });

  test(
    'shopping-list model keeps Pantry handoff state separate from checked state',
    () {
      final item = ShoppingItem.fromJson({
        'id': 'item-1',
        'name': 'Kartoffeln',
        'is_checked': false,
        'pantry_handoff_state': 'partial',
        'pantry_transferred_quantity': '800.000000000000000',
      });

      expect(item.checked, isFalse);
      expect(item.pantryHandoffState, 'partial');
      expect(item.pantryTransferred, 800);
    },
  );
}
