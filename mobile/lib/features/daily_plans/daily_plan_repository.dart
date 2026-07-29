import '../../core/api/api_client.dart';
import '../../core/errors/app_exception.dart';
import 'daily_plan_models.dart';

final class DailyPlanRepository {
  const DailyPlanRepository(this._api);
  final ApiClient _api;

  Future<DailyPlan?> byDate(DateTime date) async {
    try {
      return DailyPlan.fromJson(
        Map<String, dynamic>.from(
          await _api.get('/api/v1/daily-meal-plans/by-date/${apiDate(date)}')
              as Map,
        ),
      );
    } on ApiException catch (error) {
      if (error.code == 'DAILY_PLAN_NOT_FOUND') return null;
      rethrow;
    }
  }

  Future<DailyPlan?> archivedByDate(DateTime date) async {
    final day = apiDate(date);
    final raw = Map<String, dynamic>.from(
      await _api.get(
            '/api/v1/daily-meal-plans?date_from=$day&date_to=$day&include_archived=true',
          )
          as Map,
    );
    final items = (raw['items'] as List).whereType<Map>().where(
      (item) => item['is_archived'] == true,
    );
    if (items.isEmpty) return null;
    return detail(items.first['id'].toString());
  }

  Future<DailyPlan> detail(String id) async => DailyPlan.fromJson(
    Map<String, dynamic>.from(
      await _api.get('/api/v1/daily-meal-plans/$id') as Map,
    ),
  );

  Future<DailyPlan> preview(Map<String, dynamic> payload) async =>
      DailyPlan.fromJson(
        Map<String, dynamic>.from(
          await _api.post('/api/v1/daily-meal-plans/preview', data: payload)
              as Map,
        ),
      );

  Future<DailyPlan> save(Map<String, dynamic> payload, {String? id}) async =>
      DailyPlan.fromJson(
        Map<String, dynamic>.from(
          (id == null
                  ? await _api.post('/api/v1/daily-meal-plans', data: payload)
                  : await _api.put(
                      '/api/v1/daily-meal-plans/$id',
                      data: payload,
                    ))
              as Map,
        ),
      );

  Future<void> archive(String id) =>
      _api.delete('/api/v1/daily-meal-plans/$id');
  Future<DailyPlan> restore(String id) async => DailyPlan.fromJson(
    Map<String, dynamic>.from(
      await _api.post('/api/v1/daily-meal-plans/$id/restore') as Map,
    ),
  );
  Future<DailyPlan> duplicate(
    String id,
    DateTime target, {
    required bool copyAssessment,
  }) async => DailyPlan.fromJson(
    Map<String, dynamic>.from(
      await _api.post(
            '/api/v1/daily-meal-plans/$id/duplicate',
            data: {
              'target_date': apiDate(target),
              'copy_assessment': copyAssessment,
            },
          )
          as Map,
    ),
  );
}
