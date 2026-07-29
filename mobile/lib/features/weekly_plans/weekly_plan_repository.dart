import '../../core/api/api_client.dart';
import '../daily_plans/daily_plan_models.dart' show apiDate;
import 'weekly_plan_models.dart';

final class WeeklyPlanRepository {
  WeeklyPlanRepository(this._api);
  final ApiClient _api;

  Future<WeeklyPlan> overview(DateTime anchor) async => WeeklyPlan.fromJson(
    Map<String, dynamic>.from(
      await _api.get('/api/v1/weekly-meal-plans?anchor_date=${apiDate(anchor)}')
          as Map,
    ),
  );

  Future<void> transfer({
    required bool move,
    required String sourcePlanId,
    required String sourceMealId,
    required DateTime targetDate,
    required String copyMode,
    String? targetMealId,
    String assessmentMode = 'source',
  }) => _api.post(
    '/api/v1/weekly-meal-plans/actions/${move ? 'move' : 'copy'}-meal',
    data: {
      'source_plan_id': sourcePlanId,
      'source_meal_id': sourceMealId,
      'target_date': apiDate(targetDate),
      'copy_mode': copyMode,
      'target_meal_id': targetMealId,
      'assessment_copy_mode': assessmentMode,
    },
  );
}
