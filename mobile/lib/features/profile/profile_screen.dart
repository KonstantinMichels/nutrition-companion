import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../../core/widgets/states.dart';
import '../assessment_history/history_screen.dart';
import '../home/home_controller.dart';
import '../onboarding/onboarding_controller.dart';
import '../privacy/privacy_repository.dart';
import 'profile_repository.dart';

final profileBundleProvider = FutureProvider<ProfileBundle?>(
  (ref) => ref.watch(profileRepositoryProvider).load(),
);

final class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(profileBundleProvider);
    return AppScaffold(
      title: 'Profil bearbeiten',
      body: profile.when(
        loading: () => const LoadingState(),
        error: (error, _) => ErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(profileBundleProvider),
        ),
        data: (bundle) => ContentWidth(
          child: bundle == null
              ? const _EmptyProfile()
              : _ProfileForm(
                  initial: bundle,
                  onSaved: () => ref.invalidate(profileBundleProvider),
                ),
        ),
      ),
    );
  }
}

final class _EmptyProfile extends StatelessWidget {
  const _EmptyProfile();

  @override
  Widget build(BuildContext context) => Column(
    children: [
      const SizedBox(height: 48),
      const Icon(Icons.person_add_alt, size: 64),
      const SizedBox(height: 16),
      Text(
        'Noch kein Profil vorhanden',
        style: Theme.of(context).textTheme.titleLarge,
      ),
      const SizedBox(height: 16),
      FilledButton(
        onPressed: () => context.go('/onboarding?new=true'),
        child: const Text('Profil anlegen'),
      ),
    ],
  );
}

final class _ProfileForm extends ConsumerStatefulWidget {
  const _ProfileForm({required this.initial, required this.onSaved});
  final ProfileBundle initial;
  final VoidCallback onSaved;

  @override
  ConsumerState<_ProfileForm> createState() => _ProfileFormState();
}

final class _ProfileFormState extends ConsumerState<_ProfileForm> {
  late final Map<String, dynamic> profile;
  late final Map<String, dynamic> activity;
  late final Map<String, dynamic> goal;
  late final Map<String, dynamic> health;
  late final Map<String, TextEditingController> fields;
  bool saving = false;
  bool deleting = false;
  String? message;

  @override
  void initState() {
    super.initState();
    profile = Map<String, dynamic>.from(widget.initial.profile);
    activity = Map<String, dynamic>.from(widget.initial.activity);
    final rawSports = activity['sports'];
    activity['sports'] = rawSports is List
        ? rawSports
              .whereType<Map>()
              .map((item) => Map<String, dynamic>.from(item))
              .toList()
        : <Map<String, dynamic>>[];
    goal = Map<String, dynamic>.from(widget.initial.goal);
    health = Map<String, dynamic>.from(widget.initial.health);
    String restrictions(String type) => widget.initial.restrictions
        .where((item) => item['restriction_type'] == type)
        .map((item) => item['value'].toString())
        .join(', ');
    fields = {
      'birth_date': _controller(profile['birth_date']),
      'height_cm': _controller(profile['height_cm']),
      'current_weight_kg': _controller(profile['current_weight_kg']),
      'preferred_meals_per_day': _controller(
        profile['preferred_meals_per_day'],
      ),
      'preferred_meal_timing': _controller(profile['preferred_meal_timing']),
      'target_weight_kg': _controller(goal['target_weight_kg']),
      'requested_weekly_rate_kg': _controller(goal['requested_weekly_rate_kg']),
      'average_daily_steps': _controller(activity['average_daily_steps']),
      'movement_notes': _controller(activity['movement_notes']),
      'manual_pal_override': _controller(activity['manual_pal_override']),
      'user_note': _controller(health['user_note']),
      'allergy': TextEditingController(text: restrictions('allergy')),
      'intolerance': TextEditingController(text: restrictions('intolerance')),
      'excluded_food': TextEditingController(
        text: restrictions('excluded_food'),
      ),
      'disliked_food': TextEditingController(
        text: restrictions('disliked_food'),
      ),
    };
  }

  TextEditingController _controller(Object? value) =>
      TextEditingController(text: value?.toString() ?? '');

  @override
  void dispose() {
    for (final controller in fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const healthLabels = {
      'pregnant': 'Schwangerschaft',
      'breastfeeding': 'Stillzeit',
      'diagnosed_eating_disorder': 'Diagnostizierte Essstörung',
      'diabetes': 'Diabetes',
      'kidney_disease': 'Nierenerkrankung',
      'liver_disease': 'Lebererkrankung',
      'medically_prescribed_diet': 'Medizinisch verordnete Diät',
      'serious_metabolic_condition': 'Ernsthafte Stoffwechselerkrankung',
      'other_professional_nutrition_condition':
          'Andere Situation mit professionellem Ernährungsbedarf',
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          color: Theme.of(context).colorScheme.secondaryContainer,
          child: const Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              'Bestehende Einschätzungen bleiben unverändert. Erstelle nach dem Speichern eine neue Einschätzung, um die Änderungen anzuwenden.',
            ),
          ),
        ),
        if (message != null)
          Card(
            color: message == 'Gespeichert.'
                ? Theme.of(context).colorScheme.primaryContainer
                : Theme.of(context).colorScheme.errorContainer,
            child: ListTile(title: Text(message!)),
          ),
        _heading('Persönliche Berechnungsdaten'),
        _text('Geburtsdatum (JJJJ-MM-TT)', 'birth_date'),
        _text('Körpergröße (cm)', 'height_cm', numeric: true),
        _text('Aktuelles Gewicht (kg)', 'current_weight_kg', numeric: true),
        _dropdown(
          label: 'Physiologische Referenzkategorie',
          value: profile['physiological_category']?.toString(),
          values: const {
            'reference_category_a': 'Männliche Physiologie',
            'reference_category_b': 'Weibliche Physiologie',
          },
          onChanged: (value) =>
              setState(() => profile['physiological_category'] = value),
        ),
        const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text(
            'Diese Auswahl bestimmt die physiologische Spalte der Energiegleichung und Nährstofftabellen. Sie ist keine Aussage über die Geschlechtsidentität.',
          ),
        ),
        _dropdown(
          label: 'Ernährungsform',
          value: profile['dietary_preference']?.toString(),
          values: const {
            'mixed': 'Mischkost',
            'vegetarian': 'Vegetarisch',
            'vegan': 'Vegan',
            'other': 'Andere',
          },
          onChanged: (value) =>
              setState(() => profile['dietary_preference'] = value),
        ),
        _text('Mahlzeiten pro Tag', 'preferred_meals_per_day', numeric: true),
        _text('Bevorzugte Mahlzeitenzeiten', 'preferred_meal_timing'),
        Card(
          child: ExpansionTile(
            title: Text(
              'Optionale Messungen (${(profile['measurements'] as List?)?.length ?? 0})',
            ),
            subtitle: const Text(
              'Quelle und Messdatum der gespeicherten Werte',
            ),
            children: [
              for (final raw in (profile['measurements'] as List? ?? const []))
                if (raw is Map)
                  ListTile(
                    title: Text(
                      _measurementLabel(
                        raw['measurement_type']?.toString() ?? '',
                      ),
                    ),
                    subtitle: Text(
                      '${raw['value'] ?? '–'} ${raw['unit'] ?? ''}\n'
                      'Datum: ${raw['measured_at'] ?? 'nicht angegeben'}, Quelle: ${_measurementSource(raw['source_type']?.toString() ?? '')}',
                    ),
                  ),
            ],
          ),
        ),
        _heading('Ziel'),
        _dropdown(
          label: 'Ziel',
          value: goal['goal_type']?.toString(),
          values: const {
            'maintain_weight': 'Gewicht halten',
            'lose_weight': 'Gewicht reduzieren',
            'gain_weight': 'Gewicht erhöhen',
            'general_health': 'Allgemeine Gesundheit',
            'athletic_performance': 'Sportliche Leistung',
          },
          onChanged: (value) => setState(() => goal['goal_type'] = value),
        ),
        _text('Zielgewicht (kg, optional)', 'target_weight_kg', numeric: true),
        if (goal['goal_type'] == 'lose_weight' ||
            goal['goal_type'] == 'gain_weight')
          _dropdown(
            label: 'Intensität',
            value: goal['desired_intensity']?.toString() ?? 'mild',
            values: const {'mild': 'Mild', 'moderate': 'Moderat'},
            onChanged: (value) =>
                setState(() => goal['desired_intensity'] = value),
          ),
        _text(
          'Gewünschte Änderung (kg/Woche, optional)',
          'requested_weekly_rate_kg',
          numeric: true,
        ),
        _heading('Aktivität'),
        _dropdown(
          label: 'Alltagsaktivität',
          value: activity['occupational_activity_category']?.toString(),
          values: const {
            'mostly_seated': 'Überwiegend sitzend',
            'seated_with_walking': 'Sitzend mit Gehen/Stehen',
            'mostly_standing_walking': 'Überwiegend stehend/gehend',
            'physically_demanding': 'Körperlich anstrengend',
          },
          onChanged: (value) => setState(
            () => activity['occupational_activity_category'] = value,
          ),
        ),
        _text(
          'Schritte pro Tag (optional)',
          'average_daily_steps',
          numeric: true,
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Aktiver Arbeitsweg'),
          value: activity['active_commuting'] == true,
          onChanged: (value) =>
              setState(() => activity['active_commuting'] = value),
        ),
        _text('Alltagsbewegung (optional)', 'movement_notes'),
        _text('Manueller PAL (optional)', 'manual_pal_override', numeric: true),
        _heading('Sport'),
        for (var index = 0; index < _sports.length; index++)
          _sportEditor(index, _sports[index]),
        OutlinedButton.icon(
          onPressed: () => setState(() {
            _sports.add({
              'sport_type': 'other',
              'sessions_per_week': 1,
              'minutes_per_session': 30,
              'intensity': 'moderate',
              'note': null,
            });
          }),
          icon: const Icon(Icons.add),
          label: const Text('Sportart hinzufügen'),
        ),
        _heading('Einschränkungen und Vorlieben'),
        _text('Allergien (kommagetrennt)', 'allergy'),
        _text('Unverträglichkeiten (kommagetrennt)', 'intolerance'),
        _text('Ausgeschlossene Lebensmittel', 'excluded_food'),
        _text('Ungern gegessene Lebensmittel', 'disliked_food'),
        _heading('Gesundheits-Screening'),
        for (final entry in healthLabels.entries)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            title: Text(entry.value),
            value: health[entry.key] == true,
            onChanged: (value) =>
                setState(() => health[entry.key] = value ?? false),
          ),
        _text(
          'Optionale, nicht medizinisch geprüfte Notiz',
          'user_note',
          lines: 3,
        ),
        const SizedBox(height: 20),
        FilledButton.icon(
          onPressed: saving ? null : _save,
          icon: saving
              ? const SizedBox.square(
                  dimension: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.save_outlined),
          label: Text(saving ? 'Wird gespeichert …' : 'Profil speichern'),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: saving || deleting
              ? null
              : () => context.go('/onboarding?new=true'),
          icon: const Icon(Icons.calculate_outlined),
          label: const Text('Neue Einschätzung erstellen'),
        ),
        _heading('Profil löschen'),
        Card(
          color: Theme.of(context).colorScheme.errorContainer,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Löscht das vollständige Profil, alle Einschätzungen, Einwilligungen und lokalen App-Daten dauerhaft.',
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  key: const Key('delete-complete-profile'),
                  style: FilledButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.error,
                  ),
                  onPressed: saving || deleting ? null : _deleteProfile,
                  icon: deleting
                      ? const SizedBox.square(
                          dimension: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.delete_forever_outlined),
                  label: Text(
                    deleting
                        ? 'Profil wird gelöscht …'
                        : 'Profil vollständig löschen',
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 32),
      ],
    );
  }

  Future<void> _deleteProfile() async {
    final confirmed =
        await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Vollständiges Profil endgültig löschen?'),
            content: const Text(
              'Alle Profildaten, Messungen, Aktivitäten, Ziele, Einschränkungen, Screening-Antworten, Einschätzungen, Sicherheitsmarkierungen, Einwilligungen und lokalen App-Daten werden dauerhaft gelöscht. Dies kann nicht rückgängig gemacht werden.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Abbrechen'),
              ),
              FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: Theme.of(context).colorScheme.error,
                ),
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Alles endgültig löschen'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed || !mounted) return;

    setState(() {
      deleting = true;
      message = null;
    });
    try {
      await ref.read(privacyRepositoryProvider).deleteProfile();
      ref.invalidate(profileBundleProvider);
      ref.invalidate(assessmentHistoryProvider);
      ref.invalidate(homeControllerProvider);
      ref.invalidate(onboardingControllerProvider);
      ref.invalidate(consentsProvider);
      if (mounted) context.go('/home');
    } catch (error) {
      if (mounted) setState(() => message = 'Löschen fehlgeschlagen: $error');
    } finally {
      if (mounted) setState(() => deleting = false);
    }
  }

  Widget _heading(String text) => Padding(
    padding: const EdgeInsets.only(top: 24, bottom: 12),
    child: Text(text, style: Theme.of(context).textTheme.titleLarge),
  );

  Widget _text(
    String label,
    String key, {
    bool numeric = false,
    int lines = 1,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextField(
      controller: fields[key],
      keyboardType: numeric
          ? const TextInputType.numberWithOptions(decimal: true)
          : TextInputType.text,
      maxLines: lines,
      decoration: InputDecoration(labelText: label),
    ),
  );

  Widget _dropdown({
    required String label,
    required String? value,
    required Map<String, String> values,
    required ValueChanged<String?> onChanged,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: DropdownButtonFormField<String>(
      initialValue: values.containsKey(value) ? value : null,
      isExpanded: true,
      decoration: InputDecoration(labelText: label),
      items: values.entries
          .map(
            (entry) =>
                DropdownMenuItem(value: entry.key, child: Text(entry.value)),
          )
          .toList(),
      onChanged: onChanged,
    ),
  );

  List<Map<String, dynamic>> get _sports =>
      (activity['sports'] as List).cast<Map<String, dynamic>>();

  Widget _sportEditor(int index, Map<String, dynamic> sport) {
    const types = {
      'strength_training': 'Krafttraining',
      'cycling': 'Radfahren',
      'running': 'Laufen',
      'swimming': 'Schwimmen',
      'endurance_training': 'Ausdauertraining',
      'team_sport': 'Teamsport',
      'mixed_training': 'Gemischtes Training',
      'mobility_recovery': 'Mobilität/Regeneration',
      'other': 'Andere',
    };
    return Card(
      key: ValueKey(sport['id'] ?? index),
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
                  tooltip: 'Sportart löschen',
                  onPressed: () => setState(() => _sports.removeAt(index)),
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
            DropdownButtonFormField<String>(
              initialValue: types.containsKey(sport['sport_type'])
                  ? sport['sport_type'].toString()
                  : 'other',
              decoration: const InputDecoration(labelText: 'Sportart'),
              isExpanded: true,
              items: types.entries
                  .map(
                    (entry) => DropdownMenuItem(
                      value: entry.key,
                      child: Text(entry.value),
                    ),
                  )
                  .toList(),
              onChanged: (value) => sport['sport_type'] = value,
            ),
            const SizedBox(height: 12),
            TextFormField(
              initialValue: sport['sessions_per_week']?.toString() ?? '1',
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(
                labelText: 'Einheiten pro Woche',
              ),
              onChanged: (value) => sport['sessions_per_week'] = value,
            ),
            const SizedBox(height: 12),
            TextFormField(
              initialValue: sport['minutes_per_session']?.toString() ?? '30',
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Minuten pro Einheit',
              ),
              onChanged: (value) =>
                  sport['minutes_per_session'] = int.tryParse(value),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: sport['intensity']?.toString() ?? 'moderate',
              decoration: const InputDecoration(labelText: 'Intensität'),
              items: const [
                DropdownMenuItem(value: 'light', child: Text('Leicht')),
                DropdownMenuItem(value: 'moderate', child: Text('Moderat')),
                DropdownMenuItem(value: 'vigorous', child: Text('Intensiv')),
              ],
              onChanged: (value) => sport['intensity'] = value,
            ),
            const SizedBox(height: 12),
            TextFormField(
              initialValue: sport['note']?.toString() ?? '',
              maxLength: 500,
              decoration: const InputDecoration(labelText: 'Notiz (optional)'),
              onChanged: (value) =>
                  sport['note'] = value.trim().isEmpty ? null : value.trim(),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _save() async {
    String? optional(String key) {
      final value = fields[key]!.text.trim();
      return value.isEmpty ? null : value;
    }

    final birthDate = DateTime.tryParse(fields['birth_date']!.text.trim());
    final height = GermanDecimal.tryParse(fields['height_cm']!.text);
    final weight = GermanDecimal.tryParse(fields['current_weight_kg']!.text);
    final today = DateTime.now();
    final age = birthDate == null
        ? null
        : today.year -
              birthDate.year -
              ((today.month < birthDate.month ||
                      (today.month == birthDate.month &&
                          today.day < birthDate.day))
                  ? 1
                  : 0);
    final meals = int.tryParse(fields['preferred_meals_per_day']!.text);
    final stepsText = fields['average_daily_steps']!.text.trim();
    final steps = stepsText.isEmpty ? null : int.tryParse(stepsText);
    final palText = fields['manual_pal_override']!.text.trim();
    final pal = palText.isEmpty ? null : GermanDecimal.tryParse(palText);
    final targetText = fields['target_weight_kg']!.text.trim();
    final target = targetText.isEmpty
        ? null
        : GermanDecimal.tryParse(targetText);
    final rateText = fields['requested_weekly_rate_kg']!.text.trim();
    final rate = rateText.isEmpty ? null : GermanDecimal.tryParse(rateText);
    final weightChange =
        goal['goal_type'] == 'lose_weight' ||
        goal['goal_type'] == 'gain_weight';
    final invalidSport = _sports.any((sport) {
      final sessions = GermanDecimal.tryParse(
        sport['sessions_per_week']?.toString(),
      );
      final minutes = int.tryParse(
        sport['minutes_per_session']?.toString() ?? '',
      );
      return sessions == null ||
          sessions < 0 ||
          sessions > 14 ||
          minutes == null ||
          minutes < 0 ||
          minutes > 600;
    });
    if (birthDate == null ||
        age == null ||
        age < 13 ||
        age > 120 ||
        height == null ||
        height <= 100 ||
        height > 250 ||
        weight == null ||
        weight <= 25 ||
        weight > 350 ||
        meals == null ||
        meals < 1 ||
        meals > 12 ||
        (stepsText.isNotEmpty &&
            (steps == null || steps < 0 || steps > 100000)) ||
        (palText.isNotEmpty && (pal == null || pal < 1.2 || pal > 2.4)) ||
        (targetText.isNotEmpty &&
            (target == null || target <= 25 || target > 350)) ||
        (weightChange &&
            rateText.isNotEmpty &&
            (rate == null || rate <= 0 || rate > 2)) ||
        invalidSport) {
      setState(() {
        message =
            'Bitte prüfe die plausiblen Bereiche für Geburtsdatum, Körperdaten, Mahlzeiten, Aktivität, Ziel und Sport.';
      });
      return;
    }
    profile.addAll({
      'birth_date': fields['birth_date']!.text.trim(),
      'height_cm': GermanDecimal.parse(fields['height_cm']!.text),
      'current_weight_kg': GermanDecimal.parse(
        fields['current_weight_kg']!.text,
      ),
      'preferred_meals_per_day': meals,
      'preferred_meal_timing': optional('preferred_meal_timing'),
    });
    goal.addAll({
      'target_weight_kg': optional('target_weight_kg'),
      'requested_weekly_rate_kg': optional('requested_weekly_rate_kg'),
    });
    if (weightChange) {
      goal['desired_intensity'] ??= 'mild';
    } else {
      goal.remove('desired_intensity');
      goal.remove('requested_weekly_rate_kg');
    }
    activity.addAll({
      'average_daily_steps': steps,
      'movement_notes': optional('movement_notes'),
      'manual_pal_override': optional('manual_pal_override'),
    });
    health['user_note'] = optional('user_note');
    List<Map<String, dynamic>> restrictions(String type, bool hard) =>
        fields[type]!.text
            .split(',')
            .map((value) => value.trim())
            .where((value) => value.isNotEmpty)
            .map(
              (value) => {
                'restriction_type': type,
                'value': value,
                'hard_exclusion': hard,
              },
            )
            .toList();
    final bundle = ProfileBundle(
      profile: profile,
      activity: activity,
      goal: goal,
      restrictions: [
        ...restrictions('allergy', true),
        ...restrictions('intolerance', true),
        ...restrictions('excluded_food', true),
        ...restrictions('disliked_food', false),
      ],
      health: health,
    );
    setState(() {
      saving = true;
      message = null;
    });
    try {
      await ref.read(profileRepositoryProvider).save(bundle);
      if (!mounted) return;
      setState(() {
        saving = false;
        message = 'Gespeichert.';
      });
      widget.onSaved();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        saving = false;
        message = error.toString();
      });
    }
  }
}

String _measurementLabel(String value) => switch (value) {
  'weight' => 'Gewicht',
  'body_fat_percentage' => 'Körperfettanteil',
  'waist_circumference' => 'Taillenumfang',
  'hip_circumference' => 'Hüftumfang',
  'measured_resting_energy_expenditure' => 'Gemessener Ruheenergieverbrauch',
  _ => value,
};

String _measurementSource(String value) => switch (value) {
  'measured' => 'gemessen',
  'device_estimate' => 'Geräteschätzung',
  'user_estimate' => 'eigene Schätzung',
  _ => value,
};
