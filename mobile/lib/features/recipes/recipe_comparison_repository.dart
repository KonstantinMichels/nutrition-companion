import '../../core/api/api_client.dart';
import 'recipe_comparison_models.dart';

final class RecipeComparisonRepository {
  const RecipeComparisonRepository(this._api);
  final ApiClient _api;

  Future<({List<ComparableAssessmentItem> items, String? latestId})>
  assessments() async {
    final raw = Map<String, dynamic>.from(
      await _api.get('/api/v1/assessments/comparable') as Map,
    );
    return (
      items: (raw['items'] as List)
          .whereType<Map>()
          .map(
            (item) => ComparableAssessmentItem.fromJson(
              Map<String, dynamic>.from(item),
            ),
          )
          .toList(),
      latestId: raw['latest_usable_assessment_id']?.toString(),
    );
  }

  Future<RecipeComparison> compare(
    String recipeId, {
    String? assessmentId,
    required String portionCount,
  }) async {
    final query = <String, String>{'portion_count': portionCount};
    if (assessmentId != null) query['assessment_id'] = assessmentId;
    final uri = Uri(
      path: '/api/v1/recipes/$recipeId/target-comparison',
      queryParameters: query,
    );
    return RecipeComparison.fromJson(
      Map<String, dynamic>.from(await _api.get(uri.toString()) as Map),
    );
  }
}
