import '../../core/api/api_client.dart';

final class TrainingRepository {
  TrainingRepository(this._api);
  final ApiClient _api;

  Future<List<Map<String, dynamic>>> sessions({bool cancelled = true}) async =>
      ((await _api.get(
                '/api/v1/training-sessions?include_cancelled=$cancelled',
              ))
              as List)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList();
  Future<Map<String, dynamic>> saveSession(
    Map<String, dynamic> data, {
    String? id,
  }) async => Map<String, dynamic>.from(
    id == null
        ? await _api.post('/api/v1/training-sessions', data: data) as Map
        : await _api.patch('/api/v1/training-sessions/$id', data: data) as Map,
  );
  Future<Map<String, dynamic>> sessionStatus(String id, String action) async =>
      Map<String, dynamic>.from(
        await _api.post('/api/v1/training-sessions/$id/$action') as Map,
      );
  Future<void> deleteSession(String id) =>
      _api.delete('/api/v1/training-sessions/$id');
  Future<List<Map<String, dynamic>>> preferences() async =>
      ((await _api.get('/api/v1/training-day-adjustment-preferences')) as List)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList();
  Future<Map<String, dynamic>> preview(Map<String, dynamic> data) async =>
      Map<String, dynamic>.from(
        await _api.post('/api/v1/training-day-adjustments/preview', data: data)
            as Map,
      );
  Future<Map<String, dynamic>> apply(
    Map<String, dynamic> request,
    String token,
    String operationId, {
    List<String> replace = const [],
    List<String> link = const [],
    List<String> create = const [],
  }) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/training-day-adjustments/apply',
          data: {
            'preview_token': token,
            'client_operation_id': operationId,
            'preview': request,
            'replacement_confirmation_ids': replace,
            'link_to_daily_plan_dates': link,
            'create_missing_plan_dates': create,
          },
        )
        as Map,
  );
  Future<List<Map<String, dynamic>>> adjustments() async =>
      (((await _api.get('/api/v1/training-day-adjustments')) as Map)['items']
              as List)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList();
}
