import '../../core/api/api_client.dart';
import 'shopping_list_models.dart';

final class ShoppingListRepository {
  ShoppingListRepository(this._api);
  final ApiClient _api;
  Future<List<ShoppingListSummary>> lists({bool archived = false}) async {
    final raw =
        await _api.get('/api/v1/shopping-lists?include_archived=$archived')
            as Map;
    return (raw['items'] as List)
        .whereType<Map>()
        .map((e) => ShoppingListSummary.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  Future<ShoppingListDetail> detail(String id) async =>
      ShoppingListDetail.fromJson(
        Map<String, dynamic>.from(
          await _api.get('/api/v1/shopping-lists/$id') as Map,
        ),
      );
  Future<ShoppingListDetail> create(String name) async =>
      ShoppingListDetail.fromJson(
        Map<String, dynamic>.from(
          await _api.post('/api/v1/shopping-lists', data: {'name': name})
              as Map,
        ),
      );
  Future<Map<String, dynamic>> preview(Map<String, dynamic> data) async =>
      Map<String, dynamic>.from(
        await _api.post('/api/v1/shopping-lists/generation-preview', data: data)
            as Map,
      );
  Future<ShoppingListDetail> generate(Map<String, dynamic> data) async =>
      ShoppingListDetail.fromJson(
        Map<String, dynamic>.from(
          await _api.post('/api/v1/shopping-lists/generate', data: data) as Map,
        ),
      );
  Future<void> addText(String id, Map<String, dynamic> data) =>
      _api.post('/api/v1/shopping-lists/$id/items', data: data);
  Future<void> setChecked(String id, String itemId, bool checked) => _api.patch(
    '/api/v1/shopping-lists/$id/items/$itemId',
    data: {'is_checked': checked},
  );
  Future<void> remove(String id, String itemId) =>
      _api.delete('/api/v1/shopping-lists/$id/items/$itemId');
  Future<void> state(String id, String action) => action == 'archive'
      ? _api.delete('/api/v1/shopping-lists/$id')
      : _api.post('/api/v1/shopping-lists/$id/$action');
  Future<Map<String, dynamic>> refreshPreview(String id) async =>
      Map<String, dynamic>.from(
        await _api.post('/api/v1/shopping-lists/$id/refresh-preview') as Map,
      );
  Future<void> refresh(String id, int version) => _api.post(
    '/api/v1/shopping-lists/$id/refresh',
    data: {'preview_version': version},
  );
  Future<Map<String, dynamic>> handoffEligibility(String id) async =>
      Map<String, dynamic>.from(
        await _api.get('/api/v1/shopping-lists/$id/pantry-handoff-eligibility')
            as Map,
      );
  Future<Map<String, dynamic>> handoffPreview(
    String id,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.post(
          '/api/v1/shopping-lists/$id/pantry-handoff-preview',
          data: data,
        )
        as Map,
  );
  Future<Map<String, dynamic>> applyHandoff(
    String id,
    Map<String, dynamic> data,
  ) async => Map<String, dynamic>.from(
    await _api.post('/api/v1/shopping-lists/$id/pantry-handoff', data: data)
        as Map,
  );
  Future<List<Map<String, dynamic>>> handoffHistory(String id) async =>
      (await _api.get('/api/v1/shopping-lists/$id/pantry-handoffs') as List)
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
}
