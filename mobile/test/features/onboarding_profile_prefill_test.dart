import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/onboarding/onboarding_models.dart';

void main() {
  test('prefills a new draft from the stored profile without consent', () {
    final draft = OnboardingDraft.fromStoredProfile(
      profile: {
        'birth_date': '1990-05-04',
        'physiological_category': 'reference_category_a',
        'height_cm': '182',
        'current_weight_kg': '81.5',
        'dietary_preference': 'mixed',
        'preferred_meals_per_day': 4,
        'preferred_meal_timing': 'morgens, mittags, abends',
        'measurements': [
          {
            'measurement_type': 'waist_circumference',
            'value': '88',
            'measured_at': '2026-07-28',
            'source_type': 'measured',
          },
        ],
      },
      activity: {
        'occupational_activity_category': 'seated_with_walking',
        'average_daily_steps': 7500,
        'active_commuting': true,
        'movement_notes': 'Tägliche Spaziergänge',
        'sports': [
          {
            'sport_type': 'strength_training',
            'sessions_per_week': '3',
            'minutes_per_session': 60,
            'intensity': 'moderate',
          },
        ],
      },
      goal: {'goal_type': 'maintain_weight', 'desired_intensity': 'mild'},
      restrictions: [
        {
          'restriction_type': 'allergy',
          'value': 'Erdnuss',
          'hard_exclusion': true,
        },
      ],
      health: {'diabetes': false, 'user_note': 'Keine Besonderheiten'},
      now: DateTime.utc(2026, 7, 28),
    );

    expect(draft.currentStep, 0);
    expect(draft.birthDate, '1990-05-04');
    expect(draft.heightCm, '182');
    expect(draft.weightKg, '81.5');
    expect(draft.occupationalActivity, 'seated_with_walking');
    expect(draft.averageSteps, '7500');
    expect(draft.sports, hasLength(1));
    expect(draft.allergies, 'Erdnuss');
    expect(draft.waist.value, '88');
    expect(draft.consentAccepted, isFalse);
  });
}
