import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:nutrition_companion/core/secure_storage/sensitive_store.dart';
import 'package:nutrition_companion/core/widgets/app_scaffold.dart';
import 'package:nutrition_companion/core/widgets/content_width.dart';
import 'package:nutrition_companion/features/daily_plans/daily_plan_draft_repository.dart';
import 'package:nutrition_companion/features/daily_plans/daily_plan_models.dart';

import '../helpers/fake_sensitive_store.dart';

void main() {
  test(
    'daily plan preserves unavailable nutrients and uncertain remaining values',
    () {
      final plan = DailyPlan.fromJson({
        'plan': {
          'id': 'plan-1',
          'plan_date': '2026-07-29',
          'name': null,
          'notes': null,
          'is_archived': false,
        },
        'assessment': {'id': 'assessment-1'},
        'meals': <Object>[],
        'daily_totals': [
          {
            'nutrient_code': 'fiber',
            'display_name_de': 'Ballaststoffe',
            'amount': null,
            'unit': 'g',
            'is_complete': false,
            'coverage_ratio': '0',
          },
        ],
        'target_comparison': [
          {
            'nutrient_code': 'protein',
            'display_name_de': 'Eiweiß',
            'amount': '42.000000',
            'unit': 'g/Tag',
            'target_kind': 'minimum',
            'relation': 'indeterminate',
            'explanation_de': 'Abstand ungewiss.',
            'remaining_amount': '8.000000',
            'remaining_status': 'upper_bound_only',
          },
        ],
        'warnings': <Object>[],
        'quality': {'quality_level': 'incomplete'},
      });
      expect(plan.nutrients.single.amount, isNull);
      expect(plan.comparisons.single.amount, '42');
      expect(plan.comparisons.single.remaining, '8');
      expect(plan.comparisons.single.remainingStatus, 'upper_bound_only');
    },
  );

  test(
    'daily draft uses the sensitive store and is removed with app data',
    () async {
      final store = FakeSensitiveStore();
      final repository = DailyPlanDraftRepository(store);
      await repository.write('2026-07-29', {
        'plan_date': '2026-07-29',
        'meals': <Object>[],
      });
      expect(store.values, contains(SensitiveKeys.dailyPlanDrafts));
      expect((await repository.read('2026-07-29'))?['plan_date'], '2026-07-29');
      await store.clearAppData();
      expect(await repository.read('2026-07-29'), isNull);
    },
  );

  testWidgets(
    'top-level navigation contains manual daily planning without scores',
    (tester) async {
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
      expect(find.text('Plan'), findsOneWidget);
      expect(find.textContaining('Health Score'), findsNothing);
      expect(find.textContaining('Empfehlung'), findsNothing);
    },
  );

  testWidgets('daily planner content has one scrolling viewport', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ContentWidth(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [Text('Tagesplan'), Text('Tagesbilanz')],
            ),
          ),
        ),
      ),
    );
    expect(tester.takeException(), isNull);
    expect(find.text('Tagesplan'), findsOneWidget);
  });
}
