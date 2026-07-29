import '../../core/api/api_client.dart';

final class PantryAwareShoppingRepository {
  const PantryAwareShoppingRepository(this._api);
  final ApiClient _api;

  Future<List<Map<String, dynamic>>> eligibleLists() async {
    final raw =
        await _api.get('/api/v1/pantry-aware-shopping/eligible-lists') as Map;
    return (raw['items'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  Future<Map<String, dynamic>> preview(Map<String, dynamic> request) async =>
      Map<String, dynamic>.from(
        await _api.post('/api/v1/pantry-aware-shopping/preview', data: request)
            as Map,
      );

  Future<Map<String, dynamic>> apply(
    Map<String, dynamic> request,
    String previewToken,
    String operationId,
  ) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/pantry-aware-shopping/apply',
          data: {
            'client_operation_id': operationId,
            'preview_token': previewToken,
            'preview': request,
          },
        )
        as Map,
  );
}
