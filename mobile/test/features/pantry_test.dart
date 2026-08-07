import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:nutrition_companion/core/widgets/app_scaffold.dart';
import 'package:nutrition_companion/features/pantry/pantry_add_screen.dart';
import 'package:nutrition_companion/features/pantry/pantry_models.dart';
import 'package:nutrition_companion/features/pantry/pantry_screen.dart';

void main() {
  test(
    'pantry lot preserves decimal quantities, separate dates and movement history',
    () {
      final lot = PantryLot.fromJson({
        'id': 'lot-1',
        'food': {
          'id': 'food-1',
          'name': 'Milch',
          'brand': null,
          'is_archived': false,
        },
        'location': {'id': 'location-1', 'name': 'Kühlschrank'},
        'current_quantity': '750.000000000',
        'normalized_unit': 'ml',
        'initial_entered_quantity': '0.750000000',
        'initial_entered_unit_code': 'l',
        'initial_conversion_estimated': false,
        'purchase_date': '2026-07-28',
        'opened_date': '2026-07-29',
        'best_before_date': '2026-08-01',
        'use_by_date': '2026-08-02',
        'date_status': 'expiring_soon',
        'is_depleted': false,
        'is_archived': false,
        'warnings': <Object>[],
        'movements': [
          {
            'movement_type': 'initial_stock',
            'quantity_delta': '750.000000000',
            'normalized_unit': 'ml',
            'balance_before': '0',
            'balance_after': '750.000000000',
            'conversion_estimated': false,
            'created_at': '2026-07-29T12:00:00Z',
          },
        ],
      });
      expect(lot.quantity, '750');
      expect(lot.initialQuantity, '0,75');
      expect(lot.bestBeforeDate, isNotNull);
      expect(lot.useByDate, isNotNull);
      expect(lot.movements.single.after, '750');
    },
  );

  test('operation identifiers are UUID v4 values and differ', () {
    final first = pantryOperationId();
    final second = pantryOperationId();
    expect(
      first,
      matches(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ),
      ),
    );
    expect(second, isNot(first));
  });

  test('date states use neutral German wording', () {
    expect(
      pantryDateStatus('past_best_before'),
      'Mindesthaltbarkeitsdatum überschritten',
    );
    expect(pantryDateStatus('past_use_by'), 'Verbrauchsdatum überschritten');
    expect(pantryDateStatus('date_today'), 'Heute datiert');
  });

  testWidgets('navigation exposes Pantry without shopping automation', (
    tester,
  ) async {
    final router = GoRouter(
      initialLocation: '/home',
      routes: [
        GoRoute(
          path: '/home',
          builder: (_, _) => const AppScaffold(
            title: 'Test',
            body: SizedBox.shrink(),
          ),
        ),
      ],
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();
    expect(find.text('Vorrat'), findsOneWidget);
    expect(find.textContaining('Einkaufsliste'), findsNothing);
    expect(find.textContaining('automatisch abziehen'), findsNothing);
  });
}
