import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_models.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_validation.dart';

void main() {
  OnboardingDraft validDraft() {
    var draft = OnboardingDraft.initial(DateTime.utc(2026, 7, 1));
    final values = <String, Object?>{
      'goal_type': 'maintain_weight',
      'birth_date': '1990-05-20',
      'height_cm': '178',
      'weight_kg': '82,5',
      'physiological_category': 'reference_category_a',
      'occupational_activity': 'mostly_seated',
      'dietary_preference': 'mixed',
      'preferred_meals': '3',
      'consent_accepted': true,
    };
    for (final entry in values.entries) {
      draft = draft.withField(entry.key, entry.value, DateTime.utc(2026, 7, 1));
    }
    return draft;
  }

  test('accepts German decimal input in a complete supported draft', () {
    expect(
      OnboardingValidation.validateAll(
        validDraft(),
        now: DateTime.utc(2026, 7, 28),
      ),
      isEmpty,
    );
  });

  test('does not preselect or waive required consent', () {
    final draft = validDraft().withField(
      'consent_accepted',
      false,
      DateTime.utc(2026, 7, 1),
    );
    expect(
      OnboardingValidation.validateStep(draft, 7)['consent'],
      contains('ausdrückliche Einwilligung'),
    );
  });

  test('accepts a matching active consent without a new checkbox action', () {
    final draft = validDraft().withField(
      'consent_accepted',
      false,
      DateTime.utc(2026, 7, 29),
    );

    final errors = OnboardingValidation.validateAll(
      draft,
      now: DateTime.utc(2026, 7, 29),
      hasActiveConsent: true,
    );

    expect(errors, isNot(contains('consent')));
  });

  test('rejects malformed decimals instead of clamping', () {
    final draft = validDraft().withField(
      'weight_kg',
      'NaN',
      DateTime.utc(2026, 7, 1),
    );
    final errors = OnboardingValidation.validateStep(draft, 1);
    expect(errors['weight_kg'], contains('plausibles Körpergewicht'));
    expect(draft.weightKg, 'NaN');
  });

  test('accepts an older adult but leaves scope decision to backend', () {
    final draft = validDraft().withField(
      'birth_date',
      '1950-01-01',
      DateTime.utc(2026, 7, 1),
    );
    expect(
      OnboardingValidation.validateStep(
        draft,
        2,
        now: DateTime.utc(2026, 7, 28),
      ),
      isEmpty,
    );
  });
}
