import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/meal_plan_automation/automation_presentation.dart';

void main() {
  test('all planning methods have explicit German labels and explanations', () {
    expect(automationEngines.keys, {
      'greedy',
      'optimizer_strict',
      'optimizer_explainable_relaxation',
    });
    expect(
      automationEngineDescription('greedy'),
      contains('nicht global optimiert'),
    );
    expect(
      automationEngineDescription('optimizer_strict'),
      contains('strikten Regeln'),
    );
    expect(
      automationEngineDescription('optimizer_explainable_relaxation'),
      contains('Lockerungen'),
    );
  });

  test('optimal and merely feasible solver results are worded differently', () {
    expect(optimizerStatusLabel('optimal'), contains('Optimale Lösung'));
    expect(
      optimizerStatusLabel('feasible'),
      contains('innerhalb des Zeitlimits'),
    );
    expect(optimizerStatusLabel('feasible'), isNot(contains('Optimal')));
    expect(optimizerStatusLabel('infeasible'), contains('Keine zulässige'));
    expect(
      optimizerStatusLabel('time_limit_without_solution'),
      contains('keine Lösung'),
    );
  });

  test('presentation never claims medical or health-score optimality', () {
    final text = [
      ...automationEngines.values,
      for (final engine in automationEngines.keys)
        automationEngineDescription(engine),
      for (final status in ['optimal', 'feasible', 'infeasible'])
        optimizerStatusLabel(status),
    ].join(' ').toLowerCase();
    expect(text, isNot(contains('medizinisch optimal')));
    expect(text, isNot(contains('health score')));
    expect(text, isNot(contains('gesündester')));
  });

  test('missing assessment in an infeasible response is rendered safely', () {
    expect(automationAssessmentBasis(null), 'Keine Einschätzung verfügbar');
    expect(
      automationAssessmentBasis({'id': 'assessment-id'}),
      'Einschätzung assessment-id',
    );
    expect(
      automationAssessmentBasis({
        'id': 'assessment-id',
        'calculated_at': '2026-07-29T20:00:00Z',
      }),
      'Einschätzung 2026-07-29T20:00:00Z',
    );
  });
}
