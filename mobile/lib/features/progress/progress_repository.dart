import '../../core/api/api_client.dart';

final class ProgressRepository {
  ProgressRepository(this._api);
  final ApiClient _api;

  Future<Map<String, dynamic>> overview({int window = 7}) async =>
      Map<String, dynamic>.from(
        await _api.get('/api/v1/progress/overview?rolling_window_days=$window')
            as Map,
      );

  Future<Map<String, dynamic>> weights() async => Map<String, dynamic>.from(
    await _api.get('/api/v1/progress/weight-observations?page_size=100') as Map,
  );

  Future<Map<String, dynamic>> saveWeight(
    Map<String, dynamic> data, {
    String? id,
  }) async => Map<String, dynamic>.from(
    id == null
        ? await _api.post('/api/v1/progress/weight-observations', data: data)
        : await _api.patch(
            '/api/v1/progress/weight-observations/$id',
            data: data,
          ),
  );

  Future<void> deleteWeight(String id, int version) => _api.delete(
    '/api/v1/progress/weight-observations/$id?expected_version=$version',
  );

  Future<Map<String, dynamic>> measurements() async =>
      Map<String, dynamic>.from(
        await _api.get('/api/v1/progress/body-measurements?page_size=100')
            as Map,
      );

  Future<void> addMeasurement(Map<String, dynamic> data) =>
      _api.post('/api/v1/progress/body-measurements', data: data);

  Future<Map<String, dynamic>> composition() async => Map<String, dynamic>.from(
    await _api.get('/api/v1/progress/body-composition?page_size=100') as Map,
  );

  Future<void> addComposition(Map<String, dynamic> data) =>
      _api.post('/api/v1/progress/body-composition', data: data);

  Future<List<Map<String, dynamic>>> goals() async =>
      ((await _api.get('/api/v1/progress/goals')) as List)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList();

  Future<void> addGoal(Map<String, dynamic> data) =>
      _api.post('/api/v1/progress/goals', data: data);

  Future<void> completeGoal(String id, int version) => _api.post(
    '/api/v1/progress/goals/$id/complete?expected_version=$version',
  );

  Future<void> cancelGoal(String id, int version) =>
      _api.post('/api/v1/progress/goals/$id/cancel?expected_version=$version');
}
