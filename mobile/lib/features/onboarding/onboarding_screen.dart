import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/branding.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../../core/widgets/states.dart';
import '../assessment_history/history_screen.dart';
import '../home/home_controller.dart';
import '../privacy/privacy_repository.dart';
import '../profile/profile_screen.dart';
import 'onboarding_controller.dart';
import 'onboarding_models.dart';

const _stepTitles = <String>[
  'Einführung',
  'Berechnungsdaten',
  'Ziel',
  'Alltagsaktivität',
  'Sport',
  'Ernährungswünsche',
  'Gesundheits-Screening',
  'Datenschutz & Einwilligung',
  'Prüfen',
  'Einschätzung erstellen',
];

final class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({this.fresh = false, super.key});
  final bool fresh;

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

final class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  static const _exitConfirmationWindow = Duration(seconds: 2);
  DateTime? _lastExitBackPress;

  @override
  void initState() {
    super.initState();
    Future.microtask(
      () => ref
          .read(onboardingControllerProvider.notifier)
          .initialize(fresh: widget.fresh),
    );
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(onboardingControllerProvider, (previous, next) {
      final id = next.completedAssessmentId;
      if (id != null && id != previous?.completedAssessmentId) {
        ref.invalidate(homeControllerProvider);
        ref.invalidate(assessmentHistoryProvider);
        ref.invalidate(profileBundleProvider);
        ref.invalidate(consentsProvider);
        context.go('/assessment/$id');
      }
    });
    final state = ref.watch(onboardingControllerProvider);
    final controller = ref.read(onboardingControllerProvider.notifier);
    if (!state.initialized) {
      return const Scaffold(
        body: LoadingState(message: 'Entwurf wird sicher geladen …'),
      );
    }
    final step = state.draft.currentStep;
    return AppScaffold(
      title: _stepTitles[step],
      showNavigation: false,
      onBackPressed: () => _handleSystemBack(state, controller),
      actions: [
        IconButton(
          tooltip: 'Onboarding schließen',
          onPressed: state.submitting ? null : () => _closeOnboarding(step),
          icon: const Icon(Icons.close),
        ),
      ],
      body: Column(
        children: [
          Semantics(
            label: 'Schritt ${step + 1} von 10',
            child: LinearProgressIndicator(value: (step + 1) / 10),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
            child: Row(
              children: [
                Text('Schritt ${step + 1} von 10'),
                const Spacer(),
                const Icon(Icons.lock_outline, size: 16),
                const SizedBox(width: 4),
                const Flexible(
                  child: Text(
                    'Entwurf verschlüsselt gespeichert',
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ContentWidth(
              child: _StepBody(state: state, controller: controller),
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: Row(
                children: [
                  if (step > 0)
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: state.submitting ? null : controller.back,
                        icon: const Icon(Icons.arrow_back),
                        label: const Text('Zurück'),
                      ),
                    ),
                  if (step > 0) const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: step == 9
                        ? FilledButton.icon(
                            key: const Key('submit-assessment'),
                            onPressed: state.submitting
                                ? null
                                : controller.submit,
                            icon: state.submitting
                                ? const SizedBox.square(
                                    dimension: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(Icons.calculate_outlined),
                            label: Text(
                              state.submitting
                                  ? 'Wird erstellt …'
                                  : 'Einschätzung erstellen',
                            ),
                          )
                        : FilledButton.icon(
                            onPressed: controller.next,
                            icon: const Icon(Icons.arrow_forward),
                            label: Text(
                              step == 8 ? 'Zur Erstellung' : 'Weiter',
                            ),
                          ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _handleSystemBack(
    OnboardingState state,
    OnboardingController controller,
  ) {
    if (state.submitting) return;

    if (state.draft.currentStep > 0) {
      _lastExitBackPress = null;
      controller.back();
      return;
    }

    final now = DateTime.now();
    final previousPress = _lastExitBackPress;
    if (previousPress != null &&
        now.difference(previousPress) <= _exitConfirmationWindow) {
      context.go('/home');
      return;
    }

    _lastExitBackPress = now;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        const SnackBar(
          content: Text('Zum Verlassen der Erstellung erneut Zurück drücken'),
          duration: _exitConfirmationWindow,
        ),
      );
  }

  Future<void> _closeOnboarding(int step) async {
    if (step == 0) {
      context.go('/home');
      return;
    }

    final shouldLeave =
        await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Erstellung verlassen?'),
            content: const Text(
              'Möchtest du die Erstellung wirklich verlassen? Dein bisheriger Fortschritt bleibt als verschlüsselter Entwurf gespeichert.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Weiter bearbeiten'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Erstellung verlassen'),
              ),
            ],
          ),
        ) ??
        false;
    if (shouldLeave && mounted) context.go('/home');
  }
}

final class _StepBody extends StatelessWidget {
  const _StepBody({required this.state, required this.controller});
  final OnboardingState state;
  final OnboardingController controller;

  @override
  Widget build(BuildContext context) => switch (state.draft.currentStep) {
    0 => const _IntroductionStep(),
    1 => _PersonalStep(state: state, controller: controller),
    2 => _GoalStep(state: state, controller: controller),
    3 => _ActivityStep(state: state, controller: controller),
    4 => _SportStep(state: state, controller: controller),
    5 => _PreferencesStep(state: state, controller: controller),
    6 => _HealthStep(state: state, controller: controller),
    7 => _ConsentStep(state: state, controller: controller),
    8 => _ReviewStep(state: state, controller: controller),
    _ => _CreationStep(state: state),
  };
}

final class _IntroductionStep extends StatelessWidget {
  const _IntroductionStep();

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Icon(
        Icons.eco_outlined,
        size: 64,
        color: Theme.of(context).colorScheme.primary,
      ),
      const SizedBox(height: 16),
      Text('Worum es geht', style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 8),
      const Text(
        '${AppBranding.productName} berechnet auf Basis deiner Angaben transparente Schätzwerte für Energie, Makro- und Mikronährstoffe. Jede Kennzahl enthält eine Erklärung und Quellenangaben.',
      ),
      const SizedBox(height: 20),
      Text(
        'Für wen der MVP gedacht ist',
        style: Theme.of(context).textTheme.titleMedium,
      ),
      const Text(
        'Für allgemein gesunde Erwachsene von 18 bis 65 Jahren, die nicht schwanger sind oder stillen und keine medizinische Ernährungstherapie benötigen.',
      ),
      const SizedBox(height: 20),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Wichtige Grenze',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              const Text(
                'Die Werte sind Schätzungen. Die App diagnostiziert oder behandelt keine Erkrankungen und ersetzt weder Ärztinnen und Ärzte noch qualifizierte Ernährungsfachkräfte.',
              ),
            ],
          ),
        ),
      ),
      const SizedBox(height: 12),
      const Text(
        'Nicht unterstützte Situationen werden ruhig gekennzeichnet; dein Profil kann dennoch gespeichert werden.',
      ),
    ],
  );
}

final class _GoalStep extends StatelessWidget {
  const _GoalStep({required this.state, required this.controller});
  final OnboardingState state;
  final OnboardingController controller;

  @override
  Widget build(BuildContext context) {
    final draft = state.draft;
    const goals = {
      'maintain_weight': 'Gewicht halten',
      'lose_weight': 'Gewicht reduzieren',
      'gain_weight': 'Gewicht erhöhen',
      'general_health': 'Allgemeine Gesundheit unterstützen',
      'athletic_performance': 'Sportliche Leistung unterstützen',
    };
    final weightChange =
        draft.goalType == 'lose_weight' || draft.goalType == 'gain_weight';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _Lead(
          'Wähle das Ziel, das deine aktuelle Planung am besten beschreibt.',
        ),
        RadioGroup<String>(
          groupValue: draft.goalType.isEmpty ? null : draft.goalType,
          onChanged: (value) => controller.updateField('goal_type', value),
          child: Column(
            children: [
              for (final entry in goals.entries)
                RadioListTile<String>(
                  contentPadding: EdgeInsets.zero,
                  title: Text(entry.value),
                  value: entry.key,
                ),
            ],
          ),
        ),
        _InlineError(state.fieldErrors['goal_type']),
        const SizedBox(height: 12),
        _NumberField(
          label: 'Zielgewicht (optional)',
          suffix: 'kg',
          initialValue: draft.targetWeightKg,
          error: state.fieldErrors['target_weight_kg'],
          onChanged: (value) =>
              controller.updateField('target_weight_kg', value),
        ),
        if (weightChange) ...[
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: draft.desiredIntensity,
            decoration: const InputDecoration(
              labelText: 'Gewünschte Intensität',
            ),
            items: const [
              DropdownMenuItem(value: 'mild', child: Text('Mild')),
              DropdownMenuItem(value: 'moderate', child: Text('Moderat')),
            ],
            onChanged: (value) =>
                controller.updateField('desired_intensity', value),
          ),
          const SizedBox(height: 16),
          _NumberField(
            label: 'Gewünschte Änderung pro Woche (optional)',
            suffix: 'kg/Woche',
            initialValue: draft.requestedWeeklyRateKg,
            error: state.fieldErrors['requested_weekly_rate_kg'],
            onChanged: (value) =>
                controller.updateField('requested_weekly_rate_kg', value),
          ),
          const SizedBox(height: 8),
          const Text(
            'Dies ist ein Planungswunsch, keine Zusage für eine tatsächliche wöchentliche Änderung.',
          ),
        ],
      ],
    );
  }
}

final class _PersonalStep extends StatelessWidget {
  const _PersonalStep({required this.state, required this.controller});
  final OnboardingState state;
  final OnboardingController controller;

  @override
  Widget build(BuildContext context) {
    final draft = state.draft;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _Lead(
          'Diese Angaben werden für Referenzgleichungen und Referenztabellen benötigt.',
        ),
        _DateField(
          label: 'Geburtsdatum',
          isoValue: draft.birthDate,
          error: state.fieldErrors['birth_date'],
          onChanged: (date) =>
              controller.updateField('birth_date', _isoDate(date)),
        ),
        const SizedBox(height: 16),
        _NumberField(
          label: 'Körpergröße',
          suffix: 'cm',
          initialValue: draft.heightCm,
          error: state.fieldErrors['height_cm'],
          onChanged: (value) => controller.updateField('height_cm', value),
        ),
        const SizedBox(height: 16),
        _NumberField(
          label: 'Aktuelles Körpergewicht',
          suffix: 'kg',
          initialValue: draft.weightKg,
          error: state.fieldErrors['weight_kg'],
          onChanged: (value) => controller.updateField('weight_kg', value),
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          initialValue: draft.physiologicalCategory.isEmpty
              ? null
              : draft.physiologicalCategory,
          decoration: InputDecoration(
            labelText: 'Physiologische Referenzkategorie',
            errorText: state.fieldErrors['physiological_category'],
          ),
          items: const [
            DropdownMenuItem(
              value: 'reference_category_a',
              child: Text('Männliche Physiologie'),
            ),
            DropdownMenuItem(
              value: 'reference_category_b',
              child: Text('Weibliche Physiologie'),
            ),
          ],
          onChanged: (value) =>
              controller.updateField('physiological_category', value),
        ),
        const SizedBox(height: 8),
        const Text(
          'Wähle die physiologische Tabellenspalte, die für deine Berechnung verwendet werden soll. Diese Angabe ist keine Aussage über deine Geschlechtsidentität.',
        ),
        const SizedBox(height: 24),
        Text(
          'Optionale Messungen',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 8),
        _MeasurementEditor(
          title: 'Gemessener Ruheenergieverbrauch',
          unit: 'kcal/Tag',
          value: draft.measuredRee,
          error: state.fieldErrors['measured_ree'],
          onChanged: (value) =>
              controller.updateMeasurement('measured_ree', value),
        ),
        _MeasurementEditor(
          title: 'Körperfettanteil',
          unit: '%',
          value: draft.bodyFat,
          error: state.fieldErrors['body_fat'],
          onChanged: (value) => controller.updateMeasurement('body_fat', value),
        ),
        _MeasurementEditor(
          title: 'Taillenumfang',
          unit: 'cm',
          value: draft.waist,
          error: state.fieldErrors['waist'],
          onChanged: (value) => controller.updateMeasurement('waist', value),
        ),
        _MeasurementEditor(
          title: 'Hüftumfang',
          unit: 'cm',
          value: draft.hip,
          error: state.fieldErrors['hip'],
          onChanged: (value) => controller.updateMeasurement('hip', value),
        ),
      ],
    );
  }
}

final class _ActivityStep extends StatelessWidget {
  const _ActivityStep({required this.state, required this.controller});
  final OnboardingState state;
  final OnboardingController controller;

  @override
  Widget build(BuildContext context) {
    final draft = state.draft;
    const options = {
      'mostly_seated': 'Überwiegend sitzend',
      'seated_with_walking': 'Sitzend mit regelmäßigem Gehen oder Stehen',
      'mostly_standing_walking': 'Überwiegend stehend oder gehend',
      'physically_demanding': 'Körperlich anstrengender Alltag',
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _Lead(
          'Beschreibe deinen üblichen Alltag ohne die Sporteinheiten aus dem nächsten Schritt.',
        ),
        DropdownButtonFormField<String>(
          initialValue: draft.occupationalActivity.isEmpty
              ? null
              : draft.occupationalActivity,
          decoration: InputDecoration(
            labelText: 'Übliche Alltagsaktivität',
            errorText: state.fieldErrors['occupational_activity'],
          ),
          isExpanded: true,
          items: options.entries
              .map(
                (entry) => DropdownMenuItem(
                  value: entry.key,
                  child: Text(entry.value),
                ),
              )
              .toList(),
          onChanged: (value) =>
              controller.updateField('occupational_activity', value),
        ),
        const SizedBox(height: 16),
        _NumberField(
          label: 'Durchschnittliche Schritte pro Tag (optional)',
          suffix: 'Schritte',
          decimal: false,
          initialValue: draft.averageSteps,
          error: state.fieldErrors['average_steps'],
          onChanged: (value) => controller.updateField('average_steps', value),
        ),
        const SizedBox(height: 8),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Aktiver Arbeitsweg'),
          subtitle: const Text(
            'Zum Beispiel regelmäßiges Gehen oder Radfahren',
          ),
          value: draft.activeCommuting,
          onChanged: (value) =>
              controller.updateField('active_commuting', value),
        ),
        const SizedBox(height: 8),
        TextFormField(
          initialValue: draft.movementNote,
          maxLength: 500,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Sonstige Bewegung im Alltag (optional)',
          ),
          onChanged: (value) => controller.updateField('movement_note', value),
        ),
        const SizedBox(height: 16),
        ExpansionTile(
          tilePadding: EdgeInsets.zero,
          title: const Text('Erweitert: PAL manuell überschreiben'),
          subtitle: const Text(
            'Nur verwenden, wenn dir ein passender PAL-Wert fachlich bekannt ist.',
          ),
          children: [
            _NumberField(
              label: 'Manueller PAL-Wert',
              initialValue: draft.manualPalOverride,
              error: state.fieldErrors['manual_pal_override'],
              onChanged: (value) =>
                  controller.updateField('manual_pal_override', value),
            ),
          ],
        ),
      ],
    );
  }
}

final class _SportStep extends StatelessWidget {
  const _SportStep({required this.state, required this.controller});
  final OnboardingState state;
  final OnboardingController controller;

  @override
  Widget build(BuildContext context) {
    final draft = state.draft;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const _Lead(
          'Erfasse regelmäßige Sporteinheiten. Wenn du keinen Sport machst, kannst du ohne Eintrag fortfahren.',
        ),
        for (var index = 0; index < draft.sports.length; index++)
          _SportEditor(
            index: index,
            sport: draft.sports[index],
            state: state,
            onChanged: (sport) => controller.updateSport(index, sport),
            onDelete: () => controller.removeSport(index),
          ),
        OutlinedButton.icon(
          onPressed: controller.addSport,
          icon: const Icon(Icons.add),
          label: const Text('Sportart hinzufügen'),
        ),
        const SizedBox(height: 16),
        Text(
          'Gesamtdauer: ${GermanDecimal.format(draft.totalWeeklySportMinutes, decimals: 0)} Minuten pro Woche',
          style: Theme.of(context).textTheme.titleMedium,
        ),
      ],
    );
  }
}

final class _SportEditor extends StatelessWidget {
  const _SportEditor({
    required this.index,
    required this.sport,
    required this.state,
    required this.onChanged,
    required this.onDelete,
  });
  final int index;
  final SportInput sport;
  final OnboardingState state;
  final ValueChanged<SportInput> onChanged;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    const types = {
      'strength_training': 'Krafttraining',
      'cycling': 'Radfahren',
      'running': 'Laufen',
      'swimming': 'Schwimmen',
      'endurance_training': 'Ausdauertraining',
      'team_sport': 'Teamsport',
      'mixed_training': 'Gemischtes Training',
      'mobility_recovery': 'Mobilität oder Regeneration',
      'other': 'Andere',
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Sport ${index + 1}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                IconButton(
                  tooltip: 'Eintrag löschen',
                  onPressed: onDelete,
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
            DropdownButtonFormField<String>(
              initialValue: sport.sportType,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Sportart'),
              items: types.entries
                  .map(
                    (entry) => DropdownMenuItem(
                      value: entry.key,
                      child: Text(entry.value),
                    ),
                  )
                  .toList(),
              onChanged: (value) => onChanged(sport.copyWith(sportType: value)),
            ),
            const SizedBox(height: 12),
            _NumberField(
              label: 'Einheiten pro Woche',
              initialValue: sport.sessionsPerWeek,
              error: state.fieldErrors['sport_${index}_sessions'],
              onChanged: (value) =>
                  onChanged(sport.copyWith(sessionsPerWeek: value)),
            ),
            const SizedBox(height: 12),
            _NumberField(
              label: 'Minuten pro Einheit',
              decimal: false,
              initialValue: sport.minutesPerSession,
              error: state.fieldErrors['sport_${index}_minutes'],
              onChanged: (value) =>
                  onChanged(sport.copyWith(minutesPerSession: value)),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: sport.intensity,
              decoration: const InputDecoration(
                labelText: 'Ungefähre Intensität',
              ),
              items: const [
                DropdownMenuItem(value: 'light', child: Text('Leicht')),
                DropdownMenuItem(value: 'moderate', child: Text('Moderat')),
                DropdownMenuItem(value: 'vigorous', child: Text('Intensiv')),
              ],
              onChanged: (value) => onChanged(sport.copyWith(intensity: value)),
            ),
            const SizedBox(height: 12),
            TextFormField(
              initialValue: sport.note,
              maxLength: 500,
              decoration: const InputDecoration(labelText: 'Notiz (optional)'),
              onChanged: (value) => onChanged(sport.copyWith(note: value)),
            ),
          ],
        ),
      ),
    );
  }
}

final class _PreferencesStep extends StatelessWidget {
  const _PreferencesStep({required this.state, required this.controller});
  final OnboardingState state;
  final OnboardingController controller;

  @override
  Widget build(BuildContext context) {
    final draft = state.draft;
    const diets = {
      'mixed': 'Mischkost',
      'vegetarian': 'Vegetarisch',
      'vegan': 'Vegan',
      'other': 'Andere',
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _Lead(
          'Diese Angaben werden gespeichert, verändern im MVP aber noch keine Rezepte oder Speisepläne.',
        ),
        DropdownButtonFormField<String>(
          initialValue: draft.dietaryPreference.isEmpty
              ? null
              : draft.dietaryPreference,
          decoration: InputDecoration(
            labelText: 'Ernährungsform',
            errorText: state.fieldErrors['dietary_preference'],
          ),
          items: diets.entries
              .map(
                (entry) => DropdownMenuItem(
                  value: entry.key,
                  child: Text(entry.value),
                ),
              )
              .toList(),
          onChanged: (value) =>
              controller.updateField('dietary_preference', value),
        ),
        const SizedBox(height: 16),
        _CommaField(
          label: 'Allergien',
          value: draft.allergies,
          onChanged: (v) => controller.updateField('allergies', v),
        ),
        _CommaField(
          label: 'Unverträglichkeiten',
          value: draft.intolerances,
          onChanged: (v) => controller.updateField('intolerances', v),
        ),
        _CommaField(
          label: 'Ausgeschlossene Lebensmittel',
          value: draft.excludedFoods,
          onChanged: (v) => controller.updateField('excluded_foods', v),
        ),
        _CommaField(
          label: 'Ungern gegessene Lebensmittel',
          value: draft.dislikedFoods,
          onChanged: (v) => controller.updateField('disliked_foods', v),
        ),
        DropdownButtonFormField<String>(
          initialValue: draft.preferredMeals,
          decoration: InputDecoration(
            labelText: 'Bevorzugte Zahl an Mahlzeiten',
            errorText: state.fieldErrors['preferred_meals'],
          ),
          items: List.generate(
            10,
            (index) => DropdownMenuItem(
              value: '${index + 1}',
              child: Text('${index + 1}'),
            ),
          ),
          onChanged: (value) =>
              controller.updateField('preferred_meals', value),
        ),
        const SizedBox(height: 16),
        TextFormField(
          initialValue: draft.mealTiming,
          maxLength: 200,
          decoration: const InputDecoration(
            labelText: 'Bevorzugte Mahlzeitenzeiten (optional)',
          ),
          onChanged: (value) => controller.updateField('meal_timing', value),
        ),
      ],
    );
  }
}

final class _HealthStep extends StatelessWidget {
  const _HealthStep({required this.state, required this.controller});
  final OnboardingState state;
  final OnboardingController controller;

  @override
  Widget build(BuildContext context) {
    const labels = {
      'pregnant': 'Ich bin schwanger.',
      'breastfeeding': 'Ich stille.',
      'diagnosed_eating_disorder':
          'Bei mir wurde eine Essstörung diagnostiziert.',
      'diabetes': 'Bei mir liegt Diabetes vor.',
      'kidney_disease': 'Bei mir liegt eine Nierenerkrankung vor.',
      'liver_disease': 'Bei mir liegt eine Lebererkrankung vor.',
      'medically_prescribed_diet':
          'Ich befolge eine medizinisch verordnete Diät.',
      'serious_metabolic_condition':
          'Bei mir liegt eine ernsthafte Stoffwechselerkrankung vor.',
      'other_professional_nutrition_condition':
          'Eine andere Situation erfordert professionelle Ernährungstherapie.',
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _Lead(
          'Diese kurzen Angaben prüfen nur, ob die automatische Einschätzung für deine Situation vorgesehen ist. Sie stellen keine Diagnose dar.',
        ),
        for (final entry in labels.entries)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            title: Text(entry.value),
            value: state.draft.healthFlags[entry.key] ?? false,
            onChanged: (value) =>
                controller.setHealthFlag(entry.key, value ?? false),
          ),
        const SizedBox(height: 12),
        TextFormField(
          initialValue: state.draft.healthNote,
          maxLength: 1000,
          maxLines: 4,
          decoration: const InputDecoration(
            labelText: 'Optionale Notiz',
            helperText: 'Die Notiz wird nicht medizinisch geprüft.',
          ),
          onChanged: (value) => controller.updateField('health_note', value),
        ),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              'Wenn eine nicht unterstützte Situation vorliegt, erstellt der MVP keine übliche Gewichtsänderungs- oder Sportprotein-Empfehlung und weist auf qualifizierte Beratung hin.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ),
      ],
    );
  }
}

final class _ConsentStep extends StatelessWidget {
  const _ConsentStep({required this.state, required this.controller});
  final OnboardingState state;
  final OnboardingController controller;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const _Lead(
        'Bitte lies diese Informationen, bevor du dich entscheidest.',
      ),
      const _InfoSection(
        title: 'Welche Daten?',
        text:
            'Körper- und Aktivitätsdaten, Ernährungsziele und -wünsche, Screening-Antworten sowie daraus berechnete Einschätzungen.',
      ),
      const _InfoSection(
        title: 'Wofür?',
        text:
            'Zur Speicherung deines Profils und zur Berechnung geschätzter persönlicher Energie- und Nährstoffzielbereiche mit nachvollziehbaren Erklärungen.',
      ),
      const _InfoSection(
        title: 'Wo?',
        text:
            'Der unfertige Entwurf und eine minimale letzte Zusammenfassung werden verschlüsselt auf deinem Gerät gespeichert. Übertragene Daten werden im konfigurierten Backend gespeichert.',
      ),
      const _InfoSection(
        title: 'Deine Kontrolle',
        text:
            'Du kannst Einwilligungen ansehen und widerrufen, Daten exportieren sowie Verlauf, lokale Daten oder dein vollständiges Profil löschen. Widerruf und Löschung sind getrennte Vorgänge.',
      ),
      const _InfoSection(
        title: 'Keine medizinische Leistung',
        text:
            'Die App erstellt allgemeine, wissenschaftlich referenzierte Schätzungen. Sie diagnostiziert oder behandelt keine Erkrankung.',
      ),
      Card(
        color: Theme.of(context).colorScheme.secondaryContainer,
        child: const Padding(
          padding: EdgeInsets.all(16),
          child: Text(
            'Entwurf der Datenschutzinformation – vor öffentlicher Veröffentlichung ist eine professionelle rechtliche und datenschutzrechtliche Prüfung erforderlich.',
          ),
        ),
      ),
      const SizedBox(height: 8),
      CheckboxListTile(
        key: const Key('consent-checkbox'),
        contentPadding: EdgeInsets.zero,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text(
          state.hasActiveConsent
              ? 'Einwilligung bereits wirksam erteilt'
              : 'Ich willige ausdrücklich ein, dass die oben beschriebenen sensiblen Daten für die Erstellung und Speicherung meiner Ernährungseinschätzung verarbeitet werden.',
        ),
        subtitle: Text(
          state.hasActiveConsent
              ? 'Aktiv für Textversion ${state.draft.consentTextVersion}. Ein Widerruf ist unter „Datenschutz & Daten“ möglich.'
              : 'Textversion: ${state.draft.consentTextVersion}',
        ),
        value: state.hasActiveConsent || state.draft.consentAccepted,
        onChanged: state.hasActiveConsent
            ? (_) => ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text(
                    'Die bestehende Einwilligung kannst du unter „Datenschutz & Daten“ widerrufen.',
                  ),
                ),
              )
            : (value) =>
                  controller.updateField('consent_accepted', value ?? false),
      ),
      _InlineError(state.fieldErrors['consent']),
      TextButton.icon(
        onPressed: () => showDialog<void>(
          context: context,
          builder: (context) => const AlertDialog(
            title: Text('Datenschutzinformation (Entwurf)'),
            content: SingleChildScrollView(
              child: Text(
                'Die ausführliche Datenschutzinformation muss vor Veröffentlichung rechtlich geprüft und ergänzt werden. Im MVP werden die für Profil, Berechnung, Verlauf, Einwilligung, Export und Löschung erforderlichen Daten verarbeitet. Es findet kein Tracking und keine Werbung statt.',
              ),
            ),
          ),
        ),
        icon: const Icon(Icons.description_outlined),
        label: const Text('Datenschutzinformation öffnen'),
      ),
    ],
  );
}

final class _ReviewStep extends StatelessWidget {
  const _ReviewStep({required this.state, required this.controller});
  final OnboardingState state;
  final OnboardingController controller;

  @override
  Widget build(BuildContext context) {
    final draft = state.draft;
    final allErrors = state.fieldErrors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const _Lead(
          'Prüfe deine Angaben. Bestehende frühere Einschätzungen werden durch eine neue Berechnung nicht verändert.',
        ),
        if (state.errorMessage != null)
          Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: ListTile(
              leading: const Icon(Icons.error_outline),
              title: Text(state.errorMessage!),
            ),
          ),
        _ReviewCard(
          title: 'Ziel',
          lines: [
            _goalLabel(draft.goalType),
            if (draft.targetWeightKg.isNotEmpty)
              'Zielgewicht: ${draft.targetWeightKg} kg',
            if (draft.goalType == 'lose_weight' ||
                draft.goalType == 'gain_weight')
              'Intensität: ${draft.desiredIntensity == 'moderate' ? 'moderat' : 'mild'}',
            if (draft.requestedWeeklyRateKg.isNotEmpty)
              'Gewünschte Rate: ${draft.requestedWeeklyRateKg} kg/Woche',
          ],
          hasError: _hasAny(allErrors, [
            'goal_type',
            'target_weight_kg',
            'requested_weekly_rate_kg',
          ]),
          onEdit: () => controller.jumpTo(2),
        ),
        _ReviewCard(
          title: 'Berechnungsdaten',
          lines: [
            'Geburtsdatum: ${_formatIsoDate(draft.birthDate)}',
            'Größe: ${draft.heightCm} cm',
            'Gewicht: ${draft.weightKg} kg',
            'Physiologische Referenz: ${draft.physiologicalCategory == 'reference_category_a' ? 'männliche Physiologie' : 'weibliche Physiologie'}',
            if (!draft.measuredRee.isEmpty)
              'Ruheenergie: ${draft.measuredRee.value} kcal/Tag (${_measurementSource(draft.measuredRee.sourceType)}, ${_measurementDate(draft.measuredRee)})',
            if (!draft.bodyFat.isEmpty)
              'Körperfett: ${draft.bodyFat.value} % (${_measurementSource(draft.bodyFat.sourceType)}, ${_measurementDate(draft.bodyFat)})',
            if (!draft.waist.isEmpty)
              'Taille: ${draft.waist.value} cm (${_measurementSource(draft.waist.sourceType)}, ${_measurementDate(draft.waist)})',
            if (!draft.hip.isEmpty)
              'Hüfte: ${draft.hip.value} cm (${_measurementSource(draft.hip.sourceType)}, ${_measurementDate(draft.hip)})',
          ],
          hasError: _hasAny(allErrors, [
            'birth_date',
            'height_cm',
            'weight_kg',
            'physiological_category',
          ]),
          onEdit: () => controller.jumpTo(1),
        ),
        _ReviewCard(
          title: 'Aktivität & Sport',
          lines: [
            'Alltag: ${_activityLabel(draft.occupationalActivity)}',
            if (draft.averageSteps.isNotEmpty)
              'Schritte: ${draft.averageSteps} pro Tag',
            'Aktiver Arbeitsweg: ${draft.activeCommuting ? 'ja' : 'nein'}',
            if (draft.movementNote.isNotEmpty)
              'Sonstige Bewegung: ${draft.movementNote}',
            if (draft.manualPalOverride.isNotEmpty)
              'Manueller PAL: ${draft.manualPalOverride}',
            '${draft.sports.length} Sporteinträge, ${GermanDecimal.format(draft.totalWeeklySportMinutes, decimals: 0)} Min./Woche',
            for (final sport in draft.sports)
              '${_sportLabel(sport.sportType)}: ${sport.sessionsPerWeek} × ${sport.minutesPerSession} Min., ${_intensityLabel(sport.intensity)}${sport.note.isEmpty ? '' : ' – ${sport.note}'}',
          ],
          hasError: allErrors.keys.any(
            (key) => key == 'occupational_activity' || key.startsWith('sport_'),
          ),
          onEdit: () => controller.jumpTo(3),
        ),
        _ReviewCard(
          title: 'Ernährungswünsche',
          lines: [
            'Ernährungsform: ${_dietLabel(draft.dietaryPreference)}',
            '${draft.preferredMeals} Mahlzeiten pro Tag',
            if (draft.mealTiming.isNotEmpty) 'Zeiten: ${draft.mealTiming}',
            if (draft.allergies.isNotEmpty) 'Allergien: ${draft.allergies}',
            if (draft.intolerances.isNotEmpty)
              'Unverträglichkeiten: ${draft.intolerances}',
            if (draft.excludedFoods.isNotEmpty)
              'Ausgeschlossen: ${draft.excludedFoods}',
            if (draft.dislikedFoods.isNotEmpty)
              'Ungern gegessen: ${draft.dislikedFoods}',
          ],
          hasError: _hasAny(allErrors, [
            'dietary_preference',
            'preferred_meals',
          ]),
          onEdit: () => controller.jumpTo(5),
        ),
        _ReviewCard(
          title: 'Screening',
          lines: [
            if (!draft.healthFlags.values.any((value) => value))
              'Keine Screening-Angabe ausgewählt',
            for (final entry in draft.healthFlags.entries)
              if (entry.value) _healthLabel(entry.key),
            if (draft.healthNote.isNotEmpty)
              'Notiz (nicht medizinisch geprüft): ${draft.healthNote}',
          ],
          onEdit: () => controller.jumpTo(6),
        ),
        _ReviewCard(
          title: 'Einwilligung',
          lines: [
            state.hasActiveConsent
                ? 'Bereits aktiv und nicht widerrufen'
                : draft.consentAccepted
                ? 'Erneut ausdrücklich erteilt'
                : 'Nicht erteilt',
            'Textversion: ${draft.consentTextVersion}',
          ],
          hasError: allErrors.containsKey('consent'),
          onEdit: () => controller.jumpTo(7),
        ),
      ],
    );
  }
}

final class _CreationStep extends StatelessWidget {
  const _CreationStep({required this.state});
  final OnboardingState state;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Icon(
        Icons.calculate_outlined,
        size: 72,
        color: Theme.of(context).colorScheme.primary,
      ),
      const SizedBox(height: 16),
      Text(
        'Bereit zur Erstellung',
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      const SizedBox(height: 12),
      const Text(
        'Deine Angaben werden sicher an das Backend gesendet. Dort werden Einwilligung und unterstützter Nutzerbereich geprüft und anschließend die Einschätzung berechnet. Tippe nur einmal – doppelte Übermittlungen werden verhindert.',
        textAlign: TextAlign.center,
      ),
      if (state.submitting) ...[
        const SizedBox(height: 24),
        const LinearProgressIndicator(),
        const SizedBox(height: 8),
        const Text('Profil wird gespeichert und die Einschätzung berechnet …'),
      ],
      if (state.errorMessage != null) ...[
        const SizedBox(height: 20),
        Card(
          color: Theme.of(context).colorScheme.errorContainer,
          child: ListTile(
            leading: const Icon(Icons.cloud_off_outlined),
            title: Text(state.errorMessage!),
            subtitle: const Text(
              'Deine Eingaben bleiben erhalten. Du kannst die Erstellung erneut versuchen.',
            ),
          ),
        ),
      ],
    ],
  );
}

final class _MeasurementEditor extends StatelessWidget {
  const _MeasurementEditor({
    required this.title,
    required this.unit,
    required this.value,
    required this.onChanged,
    this.error,
  });
  final String title;
  final String unit;
  final MeasurementInput value;
  final String? error;
  final ValueChanged<MeasurementInput> onChanged;

  @override
  Widget build(BuildContext context) => Card(
    child: ExpansionTile(
      title: Text(title),
      subtitle: Text(
        value.isEmpty ? 'Nicht angegeben' : '${value.value} $unit',
      ),
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [
        _NumberField(
          label: title,
          suffix: unit,
          initialValue: value.value,
          error: error,
          onChanged: (input) => onChanged(value.copyWith(value: input)),
        ),
        const SizedBox(height: 12),
        _DateField(
          label: 'Messdatum',
          isoValue: value.measuredAt == null ? '' : _isoDate(value.measuredAt!),
          onChanged: (date) => onChanged(value.copyWith(measuredAt: date)),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: value.sourceType,
          decoration: const InputDecoration(labelText: 'Quelle'),
          items: const [
            DropdownMenuItem(value: 'measured', child: Text('Gemessen')),
            DropdownMenuItem(
              value: 'device_estimate',
              child: Text('Geräteschätzung'),
            ),
            DropdownMenuItem(
              value: 'user_estimate',
              child: Text('Eigene Schätzung'),
            ),
          ],
          onChanged: (source) => onChanged(value.copyWith(sourceType: source)),
        ),
      ],
    ),
  );
}

final class _NumberField extends StatelessWidget {
  const _NumberField({
    required this.label,
    required this.initialValue,
    required this.onChanged,
    this.suffix,
    this.error,
    this.decimal = true,
  });
  final String label;
  final String initialValue;
  final ValueChanged<String> onChanged;
  final String? suffix;
  final String? error;
  final bool decimal;

  @override
  Widget build(BuildContext context) => TextFormField(
    initialValue: initialValue,
    keyboardType: TextInputType.numberWithOptions(decimal: decimal),
    inputFormatters: [
      FilteringTextInputFormatter.allow(
        decimal ? RegExp(r'[0-9,.]') : RegExp(r'[0-9]'),
      ),
    ],
    decoration: InputDecoration(
      labelText: label,
      suffixText: suffix,
      errorText: error,
    ),
    onChanged: onChanged,
  );
}

final class _DateField extends StatelessWidget {
  const _DateField({
    required this.label,
    required this.isoValue,
    required this.onChanged,
    this.error,
  });
  final String label;
  final String isoValue;
  final ValueChanged<DateTime> onChanged;
  final String? error;

  @override
  Widget build(BuildContext context) {
    final selected = DateTime.tryParse(isoValue);
    return InkWell(
      onTap: () async {
        final picked = await showDatePicker(
          context: context,
          initialDate: selected ?? DateTime(DateTime.now().year - 30),
          firstDate: DateTime(DateTime.now().year - 120),
          lastDate: DateTime.now().add(const Duration(days: 1)),
          helpText: label,
        );
        if (picked != null) onChanged(picked);
      },
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          errorText: error,
          suffixIcon: const Icon(Icons.calendar_today),
        ),
        child: Text(
          selected == null ? 'Bitte auswählen' : DateFormatters.date(selected),
        ),
      ),
    );
  }
}

final class _CommaField extends StatelessWidget {
  const _CommaField({
    required this.label,
    required this.value,
    required this.onChanged,
  });
  final String label;
  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: TextFormField(
      initialValue: value,
      decoration: InputDecoration(
        labelText: '$label (optional)',
        helperText: 'Mehrere Angaben mit Komma trennen',
      ),
      onChanged: onChanged,
    ),
  );
}

final class _ReviewCard extends StatelessWidget {
  const _ReviewCard({
    required this.title,
    required this.lines,
    required this.onEdit,
    this.hasError = false,
  });
  final String title;
  final List<String> lines;
  final VoidCallback onEdit;
  final bool hasError;

  @override
  Widget build(BuildContext context) => Card(
    color: hasError ? Theme.of(context).colorScheme.errorContainer : null,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                for (final line in lines)
                  Text(line.isEmpty ? 'Nicht angegeben' : line),
                if (hasError)
                  const Text(
                    'Bitte prüfen',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
              ],
            ),
          ),
          TextButton(onPressed: onEdit, child: const Text('Bearbeiten')),
        ],
      ),
    ),
  );
}

final class _InfoSection extends StatelessWidget {
  const _InfoSection({required this.title, required this.text});
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleMedium),
        Text(text),
      ],
    ),
  );
}

final class _Lead extends StatelessWidget {
  const _Lead(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 20),
    child: Text(text, style: Theme.of(context).textTheme.bodyLarge),
  );
}

final class _InlineError extends StatelessWidget {
  const _InlineError(this.message);
  final String? message;

  @override
  Widget build(BuildContext context) => message == null
      ? const SizedBox.shrink()
      : Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            message!,
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        );
}

bool _hasAny(Map<String, String> errors, List<String> keys) =>
    keys.any(errors.containsKey);

String _isoDate(DateTime date) =>
    '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

String _formatIsoDate(String value) {
  final date = DateTime.tryParse(value);
  return date == null ? 'Nicht angegeben' : DateFormatters.date(date);
}

String _goalLabel(String value) => switch (value) {
  'maintain_weight' => 'Gewicht halten',
  'lose_weight' => 'Gewicht reduzieren',
  'gain_weight' => 'Gewicht erhöhen',
  'general_health' => 'Allgemeine Gesundheit unterstützen',
  'athletic_performance' => 'Sportliche Leistung unterstützen',
  _ => 'Nicht angegeben',
};

String _measurementDate(MeasurementInput value) => value.measuredAt == null
    ? 'kein Datum'
    : DateFormatters.date(value.measuredAt!);

String _measurementSource(String value) => switch (value) {
  'measured' => 'gemessen',
  'device_estimate' => 'Geräteschätzung',
  _ => 'eigene Schätzung',
};

String _activityLabel(String value) => switch (value) {
  'mostly_seated' => 'überwiegend sitzend',
  'seated_with_walking' => 'sitzend mit Gehen/Stehen',
  'mostly_standing_walking' => 'überwiegend stehend/gehend',
  'physically_demanding' => 'körperlich anstrengend',
  _ => 'nicht angegeben',
};

String _sportLabel(String value) => switch (value) {
  'strength_training' => 'Krafttraining',
  'cycling' => 'Radfahren',
  'running' => 'Laufen',
  'swimming' => 'Schwimmen',
  'endurance_training' => 'Ausdauertraining',
  'team_sport' => 'Teamsport',
  'mixed_training' => 'Gemischtes Training',
  'mobility_recovery' => 'Mobilität/Regeneration',
  _ => 'Andere Sportart',
};

String _intensityLabel(String value) => switch (value) {
  'light' => 'leicht',
  'vigorous' => 'intensiv',
  _ => 'moderat',
};

String _dietLabel(String value) => switch (value) {
  'mixed' => 'Mischkost',
  'vegetarian' => 'vegetarisch',
  'vegan' => 'vegan',
  'other' => 'andere',
  _ => 'nicht angegeben',
};

String _healthLabel(String value) => switch (value) {
  'pregnant' => 'Schwangerschaft',
  'breastfeeding' => 'Stillzeit',
  'diagnosed_eating_disorder' => 'Diagnostizierte Essstörung',
  'diabetes' => 'Diabetes',
  'kidney_disease' => 'Nierenerkrankung',
  'liver_disease' => 'Lebererkrankung',
  'medically_prescribed_diet' => 'Medizinisch verordnete Diät',
  'serious_metabolic_condition' => 'Ernsthafte Stoffwechselerkrankung',
  'other_professional_nutrition_condition' =>
    'Andere Situation mit professionellem Ernährungsbedarf',
  _ => value,
};
