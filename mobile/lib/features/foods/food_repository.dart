import '../../core/api/api_client.dart';
import 'food_models.dart';

final class FoodRepository {
  FoodRepository(this._api);
  final ApiClient _api;
  Future<List<FoodItem>> list({
    String query = '',
    bool archived = false,
  }) async {
    final data =
        await _api.get(
              '/api/v1/foods?query=${Uri.encodeQueryComponent(query)}&include_archived=$archived',
            )
            as Map;
    return (data['items'] as List)
        .whereType<Map>()
        .map((e) => FoodItem.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  Future<FoodItem> detail(String id) async => FoodItem.fromJson(
    Map<String, dynamic>.from(await _api.get('/api/v1/foods/$id') as Map),
  );
  Future<FoodItem> save(Map<String, dynamic> data, {String? id}) async =>
      FoodItem.fromJson(
        Map<String, dynamic>.from(
          (id == null
                  ? await _api.post('/api/v1/foods', data: data)
                  : await _api.put('/api/v1/foods/$id', data: data))
              as Map,
        ),
      );
  Future<void> archive(String id) async {
    await _api.delete('/api/v1/foods/$id');
  }

  Future<void> restore(String id) async {
    await _api.post('/api/v1/foods/$id/restore');
  }

  Future<void> permanentlyDelete(String id) async {
    await _api.delete('/api/v1/foods/$id/permanent');
  }

  Future<BarcodePreview> lookupBarcode(String barcode) async =>
      BarcodePreview.fromJson(
        Map<String, dynamic>.from(
          await _api.get('/api/v1/foods/barcode/$barcode') as Map,
        ),
      );

  Future<FoodItem> importBarcode(
    BarcodePreview preview, {
    bool confirmIncomplete = false,
    bool confirmDuplicate = false,
  }) async => FoodItem.fromJson(
    Map<String, dynamic>.from(
      await _api.post(
            '/api/v1/foods/barcode/${preview.barcode}/import',
            data: {
              'preview': preview.toJson(),
              'confirm_incomplete': confirmIncomplete,
              'confirm_duplicate': confirmDuplicate,
            },
          )
          as Map,
    ),
  );
}
