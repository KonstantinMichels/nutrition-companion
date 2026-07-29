import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/recipes/recipe_comparison_models.dart';
import 'package:nutrition_companion/features/recipes/recipe_comparison_section.dart';

void main() {
  test('comparison model preserves unavailable and partial values', () {
    final result = RecipeComparison.fromJson({
      'recipe': {
        'base_servings': '4.000000',
        'updated_at': '2026-08-20T12:00:00Z',
      },
      'assessment': {
        'id': 'assessment-1',
        'calculated_at': '2026-08-15T08:00:00Z',
        'goal_type': 'maintain_weight',
        'reference_set_version': 'reference-v1',
        'application_rule_set_version': 'rules-v1',
      },
      'portion_count': '1.500000',
      'groups': [
        {
          'display_name_de': 'Makronährstoffe',
          'items': [
            {
              'nutrient_code': 'protein',
              'display_name_de': 'Eiweiß',
              'selected_amount': '42.000000',
              'amount_per_serving': '28.000000',
              'unit': 'g/Tag',
              'target_kind': 'range',
              'target_minimum': '100',
              'target_value': '130',
              'target_maximum': '160',
              'comparison_status': 'partial',
              'relation': 'unknown_due_to_incomplete_data',
              'coverage_ratio': '0.6',
              'explanation': 'Bekannter Beitrag.',
              'formula_de': '42 / 100 mal 100',
            },
          ],
        },
      ],
      'notices': ['Nur eine Rezeptmenge.'],
    });
    expect(result.portionCount, '1,5');
    expect(result.items.single.selectedAmount, '42');
    expect(result.items.single.coverage, '60');
    expect(result.items.single.status, 'partial');
  });

  testWidgets('personal comparison section is lazy and has no overall score', (
    tester,
  ) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(body: RecipeComparisonSection(recipeId: 'recipe-1')),
        ),
      ),
    );
    expect(find.text('Persönlicher Vergleich'), findsOneWidget);
    expect(find.textContaining('Health Score'), findsNothing);
    expect(find.textContaining('Recipe Score'), findsNothing);
  });
}
