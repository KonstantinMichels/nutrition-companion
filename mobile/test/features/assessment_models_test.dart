import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/nutrition_assessment/assessment_models.dart';

void main() {
  test('parses backend report and derives summary cards from metrics', () {
    final report = AssessmentReport.fromJson({
      'id': '4a9dcf84-2ec6-4fea-91c6-a6c32c23db84',
      'calculated_at': '2026-07-28T10:00:00Z',
      'supported_scope_status': 'supported',
      'reference_set_identifier': 'verified-reference-set',
      'reference_set_version': '1',
      'application_rule_set_identifier': 'nutrition_companion_mvp_v1',
      'application_rule_set_version': '1',
      'engine_version': '1',
      'summary': {
        'goal_type': 'maintain_weight',
        'energy_target': {
          'available': true,
          'lower': 2100,
          'midpoint': 2250,
          'upper': 2400,
          'unit': 'kcal/day',
        },
        'micronutrients': {
          'available_codes': ['fiber'],
          'unavailable_codes': ['vitamin_d'],
        },
        'food_groups': [
          {
            'code': 'vegetables',
            'display_name_de': 'Gemüse',
            'recommendation_de': 'Allgemeine Empfehlung',
          },
        ],
      },
      'metrics': [
        {
          'metric_code': 'energy.maintenance',
          'raw_value': 2250,
          'lower_value': 2100,
          'upper_value': 2400,
          'display_value': '2.100–2.400',
          'unit': 'kcal/day',
          'method_code': 'ree_x_pal',
          'explanation_de': 'Test explanation',
          'limitations_de': 'Test limitation',
          'calculation_inputs': {},
          'source_metadata': {},
          'application_rule_identifier': null,
          'confidence_type': 'estimated',
        },
        {
          'metric_code': 'macros.protein_grams',
          'raw_value': 66,
          'display_value': '66',
          'lower_value': null,
          'upper_value': null,
          'unit': 'g/day',
          'method_code': 'protein_base',
          'explanation_de': 'Test',
          'limitations_de': 'Test',
          'calculation_inputs': {},
          'source_metadata': {},
          'application_rule_identifier': null,
          'confidence_type': 'reference_target',
        },
      ],
      'safety_flags': [],
    });

    expect(report.summary.maintenanceEnergy.lower, 2100);
    expect(report.summary.targetEnergy.upper, 2400);
    expect(report.summary.macros['protein'], contains('66'));
    expect(report.unavailableMicronutrients, ['vitamin_d']);
    expect(report.foodGroups.single['code'], 'vegetables');
  });

  test('history parsing retains server-provided energy summary', () {
    final item = AssessmentSummary.fromHistoryJson({
      'id': 'id',
      'calculated_at': '2026-07-28T10:00:00Z',
      'supported_scope_status': 'supported',
      'goal_type': 'general_health',
      'energy_target_summary': '2.100–2.400 kcal/Tag',
      'warning_codes': ['INFO'],
    });
    expect(item.energyTargetLabel, '2.100–2.400 kcal/Tag');
    expect(item.warnings.single.code, 'INFO');
  });

  test('latest-summary cache becomes stale after 24 hours', () {
    final summary = AssessmentSummary.fromHistoryJson({
      'id': 'id',
      'calculated_at': '2026-07-27T08:00:00Z',
      'supported_scope_status': 'supported',
      'goal_type': 'maintain_weight',
      'warning_codes': <String>[],
    });
    final cached = CachedAssessment(
      summary: summary,
      cachedAt: DateTime.utc(2026, 7, 27, 8),
    );
    expect(cached.isStale(DateTime.utc(2026, 7, 28, 7, 59)), isFalse);
    expect(cached.isStale(DateTime.utc(2026, 7, 28, 8, 1)), isTrue);
  });
}
