import '../../core/api/api_client.dart';
import '../../core/errors/app_exception.dart';

final class ConsumptionRepository {
  ConsumptionRepository(this._api);
  final ApiClient _api;

  Future<Map<String, dynamic>?> byDate(String date) async {
    try {
      return Map<String, dynamic>.from(
        await _api.get('/api/v1/consumption-days/by-date/$date') as Map,
      );
    } on AppException catch (error) {
      if (error.code == 'CONSUMPTION_DAY_NOT_FOUND') return null;
      rethrow;
    }
  }

  Future<Map<String, dynamic>> detail(String dayId) async =>
      Map<String, dynamic>.from(
        await _api.get('/api/v1/consumption-days/$dayId') as Map,
      );

  Future<Map<String, dynamic>> create(String date) async =>
      Map<String, dynamic>.from(
        await _api.post(
              '/api/v1/consumption-days',
              data: {
                'consumption_date': date,
                'target_basis_source': 'latest_usable_assessment',
              },
            )
            as Map,
      );

  Future<Map<String, dynamic>> fromPlan(String planId) async =>
      Map<String, dynamic>.from(
        await _api.post(
              '/api/v1/consumption-days/from-daily-plan',
              data: {'daily_plan_id': planId},
            )
            as Map,
      );

  Future<Map<String, dynamic>> linkPlan(
    String dayId,
    String planId,
    int version, {
    bool confirmConflicts = false,
  }) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/consumption-days/$dayId/link-daily-plan',
          data: {
            'daily_plan_id': planId,
            'expected_version': version,
            'confirm_conflicts': confirmConflicts,
          },
        )
        as Map,
  );

  Future<Map<String, dynamic>?> planByDate(String date) async {
    try {
      return Map<String, dynamic>.from(
        await _api.get('/api/v1/daily-meal-plans/by-date/$date') as Map,
      );
    } on AppException catch (error) {
      if (error.code == 'DAILY_PLAN_NOT_FOUND') return null;
      rethrow;
    }
  }

  Future<Map<String, dynamic>> addMeal(
    String dayId,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.post('/api/v1/consumption-days/$dayId/meals', data: data) as Map,
  );

  Future<Map<String, dynamic>> updateMeal(
    String dayId,
    String mealId,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.patch(
          '/api/v1/consumption-days/$dayId/meals/$mealId',
          data: data,
        )
        as Map,
  );

  Future<void> deleteMeal(
    String dayId,
    String mealId, {
    bool confirm = false,
  }) => _api.delete(
    '/api/v1/consumption-days/$dayId/meals/$mealId?confirm=$confirm',
  );

  Future<Map<String, dynamic>> addEntry(
    String dayId,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.post('/api/v1/consumption-days/$dayId/entries', data: data)
        as Map,
  );

  Future<Map<String, dynamic>> previewEntry(
    String dayId,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/consumption-days/$dayId/entries/preview',
          data: data,
        )
        as Map,
  );

  Future<Map<String, dynamic>> updateEntry(
    String dayId,
    String entryId,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.patch(
          '/api/v1/consumption-days/$dayId/entries/$entryId',
          data: data,
        )
        as Map,
  );

  Future<Map<String, dynamic>> reorderMeals(
    String dayId,
    List<String> mealIds,
    int version,
  ) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/consumption-days/$dayId/meals/reorder',
          data: {'meal_ids': mealIds, 'expected_version': version},
        )
        as Map,
  );

  Future<Map<String, dynamic>> outcome(
    String dayId,
    String planEntryId,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.put(
          '/api/v1/consumption-days/$dayId/planned-entry-outcomes/$planEntryId',
          data: data,
        )
        as Map,
  );

  Future<Map<String, dynamic>> confirmWholeMeal(
    String dayId,
    String planMealId,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/consumption-days/$dayId/plan-meals/$planMealId/confirm',
          data: data,
        )
        as Map,
  );

  Future<Map<String, dynamic>> finalize(
    String dayId,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.post('/api/v1/consumption-days/$dayId/finalize', data: data)
        as Map,
  );

  Future<Map<String, dynamic>> reopen(String dayId) async =>
      Map<String, dynamic>.from(
        await _api.post('/api/v1/consumption-days/$dayId/reopen') as Map,
      );

  Future<void> deleteDay(String dayId) =>
      _api.delete('/api/v1/consumption-days/$dayId');

  Future<void> deleteEntry(String dayId, String entryId) =>
      _api.delete('/api/v1/consumption-days/$dayId/entries/$entryId');

  Future<Map<String, dynamic>> history({
    String? status,
    String? completeness,
    bool? unresolved,
  }) async {
    final query = <String>[
      if (status != null) 'status=${Uri.encodeQueryComponent(status)}',
      if (completeness != null)
        'completeness_attestation=${Uri.encodeQueryComponent(completeness)}',
      if (unresolved != null) 'has_unresolved_entries=$unresolved',
    ];
    return Map<String, dynamic>.from(
      await _api.get(
            '/api/v1/consumption/history${query.isEmpty ? '' : '?${query.join('&')}'}',
          )
          as Map,
    );
  }

  Future<Map<String, dynamic>> weekly(String date) async =>
      Map<String, dynamic>.from(
        await _api.get('/api/v1/consumption/weekly-summary?week_start=$date')
            as Map,
      );
}
