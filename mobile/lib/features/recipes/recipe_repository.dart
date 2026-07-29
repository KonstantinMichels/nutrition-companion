import '../../core/api/api_client.dart';
import 'recipe_models.dart';

final class RecipeRepository {
  RecipeRepository(this._api);
  final ApiClient _api;
  Future<List<RecipeItem>> list({
    String query = '',
    bool archived = false,
  }) async {
    final data =
        await _api.get(
              '/api/v1/recipes?query=${Uri.encodeQueryComponent(query)}&include_archived=$archived',
            )
            as Map;
    return (data['items'] as List)
        .whereType<Map>()
        .map((e) => RecipeItem.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  Future<RecipeItem> detail(String id) async => RecipeItem.fromJson(
    Map<String, dynamic>.from(await _api.get('/api/v1/recipes/$id') as Map),
  );
  Future<RecipeItem> save(Map<String, dynamic> data, {String? id}) async =>
      RecipeItem.fromJson(
        Map<String, dynamic>.from(
          (id == null
                  ? await _api.post('/api/v1/recipes', data: data)
                  : await _api.put('/api/v1/recipes/$id', data: data))
              as Map,
        ),
      );
  Future<RecipeItem> duplicate(String id) async => RecipeItem.fromJson(
    Map<String, dynamic>.from(
      await _api.post('/api/v1/recipes/$id/duplicate') as Map,
    ),
  );
  Future<Map<String, dynamic>> scale(
    String id,
    String servings,
  ) async => Map<String, dynamic>.from(
    await _api.get(
          '/api/v1/recipes/$id/scale?servings=${Uri.encodeQueryComponent(servings)}',
        )
        as Map,
  );
  Future<void> archive(String id) async {
    await _api.delete('/api/v1/recipes/$id');
  }

  Future<void> restore(String id) async {
    await _api.post('/api/v1/recipes/$id/restore');
  }

  Future<void> permanentlyDelete(String id) async {
    await _api.delete('/api/v1/recipes/$id/permanent');
  }
}
