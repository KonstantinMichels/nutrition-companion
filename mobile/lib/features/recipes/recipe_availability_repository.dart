import '../../core/api/api_client.dart';
import 'recipe_availability_models.dart';

final class RecipeAvailabilityRepository {
  const RecipeAvailabilityRepository(this._api);
  final ApiClient _api;
  Future<RecipeAvailability> detail(
    String id, {
    required String portions,
    bool optional = false,
    String dateMode = 'include_all',
  }) async => RecipeAvailability.fromJson(
    Map<String, dynamic>.from(
      await _api.get(
            '/api/v1/recipes/$id/pantry-availability?portion_count=${Uri.encodeQueryComponent(portions)}&include_optional_ingredients=$optional&date_handling_mode=$dateMode',
          )
          as Map,
    ),
  );
  Future<List<RecipeAvailabilitySummary>> summaries({
    String query = '',
    String? state,
    bool archived = false,
  }) async {
    final raw =
        await _api.get(
              '/api/v1/recipes/pantry-availability?query=${Uri.encodeQueryComponent(query)}&include_archived=$archived${state == null ? '' : '&availability_state=$state'}',
            )
            as Map;
    return (raw['items'] as List)
        .whereType<Map>()
        .map(
          (e) =>
              RecipeAvailabilitySummary.fromJson(Map<String, dynamic>.from(e)),
        )
        .toList();
  }
}
