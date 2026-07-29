import '../../core/api/api_client.dart';

final class AutomationRepository {
  AutomationRepository(this._api);
  final ApiClient _api;

  Future<List<Map<String, dynamic>>> preferences() async =>
      ((await _api.get('/api/v1/meal-plan-automation/preferences')) as List)
          .map((value) => Map<String, dynamic>.from(value as Map))
          .toList();

  Future<Map<String, dynamic>> createPreference(
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.post('/api/v1/meal-plan-automation/preferences', data: data)
        as Map,
  );

  Future<Map<String, dynamic>> updatePreference(
    String id,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.patch('/api/v1/meal-plan-automation/preferences/$id', data: data)
        as Map,
  );

  Future<Map<String, dynamic>> generate(Map<String, dynamic> data) async =>
      Map<String, dynamic>.from(
        await _api.post('/api/v1/meal-plan-automation/generate', data: data)
            as Map,
      );

  Future<Map<String, dynamic>> recalculate(Map<String, dynamic> data) async =>
      Map<String, dynamic>.from(
        await _api.post('/api/v1/meal-plan-automation/recalculate', data: data)
            as Map,
      );

  Future<Map<String, dynamic>> apply(Map<String, dynamic> data) async =>
      Map<String, dynamic>.from(
        await _api.post('/api/v1/meal-plan-automation/apply', data: data)
            as Map,
      );
}
