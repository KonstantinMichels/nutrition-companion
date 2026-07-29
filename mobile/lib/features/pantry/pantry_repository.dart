import '../../core/api/api_client.dart';
import 'pantry_models.dart';

final class PantryRepository {
  PantryRepository(this._api);
  final ApiClient _api;
  Future<Map<String, dynamic>> summary() async => Map<String, dynamic>.from(
    await _api.get('/api/v1/pantry/summary') as Map,
  );
  Future<List<PantryLocation>> locations({bool archived = false}) async =>
      (await _api.get('/api/v1/pantry/locations?include_archived=$archived')
              as List)
          .whereType<Map>()
          .map(
            (item) => PantryLocation.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList();
  Future<PantryLocation> saveLocation(
    Map<String, dynamic> data, {
    String? id,
  }) async => PantryLocation.fromJson(
    Map<String, dynamic>.from(
      (id == null
              ? await _api.post('/api/v1/pantry/locations', data: data)
              : await _api.patch('/api/v1/pantry/locations/$id', data: data))
          as Map,
    ),
  );
  Future<void> archiveLocation(String id) =>
      _api.delete('/api/v1/pantry/locations/$id');
  Future<void> restoreLocation(String id) =>
      _api.post('/api/v1/pantry/locations/$id/restore');
  Future<List<PantryLot>> lots({
    String query = '',
    bool depleted = false,
    bool archived = false,
    String? status,
    String sort = 'food_name',
  }) async {
    final raw =
        await _api.get(
              '/api/v1/pantry/items?query=${Uri.encodeQueryComponent(query)}&include_depleted=$depleted&include_archived=$archived&sort=$sort${status == null ? '' : '&status=$status'}',
            )
            as Map;
    return (raw['items'] as List)
        .whereType<Map>()
        .map((item) => PantryLot.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  Future<List<PantryAvailability>> availability() async =>
      (await _api.get('/api/v1/pantry/availability') as List)
          .whereType<Map>()
          .map(
            (item) =>
                PantryAvailability.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList();
  Future<PantryLot> detail(String id) async => PantryLot.fromJson(
    Map<String, dynamic>.from(
      await _api.get('/api/v1/pantry/items/$id') as Map,
    ),
  );
  Future<PantryLot> create(Map<String, dynamic> data) async =>
      PantryLot.fromJson(
        Map<String, dynamic>.from(
          await _api.post('/api/v1/pantry/items', data: data) as Map,
        ),
      );
  Future<PantryLot> update(String id, Map<String, dynamic> data) async =>
      PantryLot.fromJson(
        Map<String, dynamic>.from(
          await _api.patch('/api/v1/pantry/items/$id', data: data) as Map,
        ),
      );
  Future<PantryLot> operation(
    String id,
    String operation,
    Map<String, dynamic> data,
  ) async => PantryLot.fromJson(
    Map<String, dynamic>.from(
      await _api.post('/api/v1/pantry/items/$id/$operation', data: data) as Map,
    ),
  );
  Future<void> archive(String id, {required bool confirm}) => _api.delete(
    '/api/v1/pantry/items/$id',
    data: {'confirm_non_depleted': confirm},
  );
  Future<void> restore(String id) =>
      _api.post('/api/v1/pantry/items/$id/restore');
}
