import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/core/widgets/app_scaffold.dart';
import 'package:nutrition_companion/features/weekly_plans/weekly_plan_models.dart';

void main() {
  test(
    'weekly model preserves Monday-to-Sunday order and planned-day average',
    () {
      final week = WeeklyPlan.fromJson({
        'week_start': '2026-07-27',
        'week_end': '2026-08-02',
        'iso_week_number': 31,
        'iso_week_year': 2026,
        'days': List.generate(
          7,
          (index) => {
            'date': DateTime(
              2026,
              7,
              27 + index,
            ).toIso8601String().substring(0, 10),
            'weekday': const [
              'monday',
              'tuesday',
              'wednesday',
              'thursday',
              'friday',
              'saturday',
              'sunday',
            ][index],
            'state': index == 0 ? 'planned' : 'no_plan',
            'plan': index == 0 ? {'id': 'plan-1'} : null,
            'summary': {
              'meal_count': index == 0 ? 1 : 0,
              'entry_count': index == 0 ? 1 : 0,
            },
            'warnings': <Object>[],
            'meals': <Object>[],
          },
        ),
        'day_counts': {'planned_days': 1, 'missing_plan_days': 6},
        'weekly_totals': [
          {
            'nutrient_code': 'energy_kcal',
            'display_name_de': 'Energie',
            'category': 'energy',
            'amount': '2400.000000',
            'average_per_planned_day': '2400.000000',
            'unit': 'kcal',
            'is_complete': true,
            'coverage_ratio': '1',
          },
        ],
        'weekly_target_comparison': <Object>[],
        'quality': {
          'quality_level': 'partial_week',
          'mixed_assessment_basis': false,
        },
        'warnings': <Object>[],
      });
      expect(week.weekNumber, 31);
      expect(week.days.first.weekday, 'monday');
      expect(week.days.last.weekday, 'sunday');
      expect(week.nutrient('energy_kcal')?.average, '2400.000000');
      expect(week.counts['planned_days'], 1);
    },
  );

  testWidgets(
    'navigation exposes weekly planning without automatic planning or score',
    (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: AppScaffold(title: 'Test', body: SizedBox.shrink()),
        ),
      );
      await tester.tap(find.byTooltip('Open navigation menu'));
      await tester.pumpAndSettle();
      expect(find.text('Wochenplan'), findsOneWidget);
      expect(find.textContaining('Health Score'), findsNothing);
      expect(find.textContaining('automatisch'), findsNothing);
    },
  );
}
