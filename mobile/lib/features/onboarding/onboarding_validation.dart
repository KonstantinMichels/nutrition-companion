import '../../core/formatting/german_decimal.dart';
import 'onboarding_models.dart';

abstract final class OnboardingValidation {
  static Map<String, String> validateStep(
    OnboardingDraft draft,
    int step, {
    DateTime? now,
    bool hasActiveConsent = false,
  }) {
    final errors = <String, String>{};
    final today = (now ?? DateTime.now()).toLocal();

    void number(
      String key,
      String raw,
      String emptyMessage,
      String invalidMessage,
      double minimum,
      double maximum, {
      bool required = true,
      bool minimumExclusive = false,
    }) {
      if (raw.trim().isEmpty) {
        if (required) errors[key] = emptyMessage;
        return;
      }
      final value = GermanDecimal.tryParse(raw);
      if (value == null ||
          (minimumExclusive ? value <= minimum : value < minimum) ||
          value > maximum) {
        errors[key] = invalidMessage;
      }
    }

    if (step == 2 || step == 8) {
      if (draft.goalType.isEmpty) {
        errors['goal_type'] = 'Bitte wähle ein Ziel aus.';
      }
      number(
        'target_weight_kg',
        draft.targetWeightKg,
        '',
        'Bitte gib ein plausibles Zielgewicht ein.',
        30,
        350,
        required: false,
      );
      number(
        'requested_weekly_rate_kg',
        draft.requestedWeeklyRateKg,
        '',
        'Bitte gib eine plausible gewünschte Rate ein.',
        0,
        2,
        required: false,
        minimumExclusive: true,
      );
    }

    if (step == 1 || step == 8) {
      final birthDate = DateTime.tryParse(draft.birthDate);
      if (birthDate == null) {
        errors['birth_date'] = 'Bitte gib ein gültiges Geburtsdatum ein.';
      } else {
        var age = today.year - birthDate.year;
        if (today.month < birthDate.month ||
            (today.month == birthDate.month && today.day < birthDate.day)) {
          age--;
        }
        if (birthDate.isAfter(today) || age < 13 || age > 120) {
          errors['birth_date'] = 'Bitte gib ein plausibles Geburtsdatum ein.';
        }
      }
      number(
        'height_cm',
        draft.heightCm,
        'Bitte gib deine Körpergröße ein.',
        'Bitte gib eine plausible Körpergröße ein.',
        100.01,
        250,
      );
      number(
        'weight_kg',
        draft.weightKg,
        'Bitte gib dein Körpergewicht ein.',
        'Bitte gib ein plausibles Körpergewicht ein.',
        30,
        350,
      );
      if (draft.physiologicalCategory.isEmpty) {
        errors['physiological_category'] =
            'Bitte wähle eine Referenzkategorie aus.';
      }
      number(
        'measured_ree',
        draft.measuredRee.value,
        '',
        'Bitte gib einen plausiblen Ruheenergieverbrauch ein.',
        500,
        5000,
        required: false,
      );
      number(
        'body_fat',
        draft.bodyFat.value,
        '',
        'Bitte gib einen plausiblen Körperfettanteil ein.',
        2,
        75,
        required: false,
      );
      number(
        'waist',
        draft.waist.value,
        '',
        'Bitte gib einen plausiblen Taillenumfang ein.',
        30,
        250,
        required: false,
      );
      number(
        'hip',
        draft.hip.value,
        '',
        'Bitte gib einen plausiblen Hüftumfang ein.',
        30,
        250,
        required: false,
      );
      for (final entry in <String, MeasurementInput>{
        'measured_ree_date': draft.measuredRee,
        'body_fat_date': draft.bodyFat,
        'waist_date': draft.waist,
        'hip_date': draft.hip,
      }.entries) {
        final date = entry.value.measuredAt;
        if (!entry.value.isEmpty &&
            date != null &&
            date.isAfter(today.add(const Duration(days: 1)))) {
          errors[entry.key] = 'Das Messdatum darf nicht in der Zukunft liegen.';
        }
      }
    }

    if (step == 3 || step == 8) {
      if (draft.occupationalActivity.isEmpty) {
        errors['occupational_activity'] =
            'Bitte wähle deine übliche Aktivität aus.';
      }
      number(
        'average_steps',
        draft.averageSteps,
        '',
        'Bitte gib eine plausible Schrittzahl ein.',
        0,
        100000,
        required: false,
      );
      number(
        'manual_pal_override',
        draft.manualPalOverride,
        '',
        'Der manuelle PAL-Wert muss zwischen 1,2 und 2,4 liegen.',
        1.2,
        2.4,
        required: false,
      );
    }

    if (step == 4 || step == 8) {
      for (var index = 0; index < draft.sports.length; index++) {
        final sport = draft.sports[index];
        number(
          'sport_${index}_sessions',
          sport.sessionsPerWeek,
          'Bitte gib die Häufigkeit ein.',
          'Bitte gib 0 bis 14 Einheiten ein.',
          0,
          14,
        );
        number(
          'sport_${index}_minutes',
          sport.minutesPerSession,
          'Bitte gib die Dauer ein.',
          'Bitte gib 0 bis 600 Minuten ein.',
          0,
          600,
        );
      }
    }

    if (step == 5 || step == 8) {
      if (draft.dietaryPreference.isEmpty) {
        errors['dietary_preference'] = 'Bitte wähle eine Ernährungsform aus.';
      }
      final meals = int.tryParse(draft.preferredMeals);
      if (meals == null || meals < 1 || meals > 10) {
        errors['preferred_meals'] = 'Bitte wähle 1 bis 10 Mahlzeiten.';
      }
    }

    if (step == 7 || step == 8) {
      if (!draft.consentAccepted && !hasActiveConsent) {
        errors['consent'] =
            'Ohne ausdrückliche Einwilligung kann keine Auswertung erstellt werden.';
      }
    }
    return errors;
  }

  static Map<String, String> validateAll(
    OnboardingDraft draft, {
    DateTime? now,
    bool hasActiveConsent = false,
  }) {
    final errors = <String, String>{};
    for (var step = 1; step <= 8; step++) {
      errors.addAll(
        validateStep(draft, step, now: now, hasActiveConsent: hasActiveConsent),
      );
    }
    return errors;
  }
}
