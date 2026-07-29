import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import 'automation_presentation.dart';

final class AutomationScreen extends ConsumerStatefulWidget {
  const AutomationScreen({
    this.initialScope = 'single_day',
    this.initialDate,
    super.key,
  });
  final String initialScope;
  final DateTime? initialDate;

  @override
  ConsumerState<AutomationScreen> createState() => _AutomationScreenState();
}

final class _AutomationScreenState extends ConsumerState<AutomationScreen> {
  late String scope = widget.initialScope;
  late DateTime date = widget.initialDate ?? DateTime.now();
  String mode = 'empty_meal_slots_only';
  String engine = 'optimizer_strict';
  List<Map<String, dynamic>> preferences = [];
  Map<String, dynamic>? selected;
  Map<String, dynamic>? draft;
  Map<String, dynamic>? generation;
  final recipeOverrides = <String, String>{};
  final portionOverrides = <String, String>{};
  final locked = <String>{};
  final removed = <String>{};
  bool busy = true;
  bool relaxationAccepted = false;
  String? error;

  @override
  void initState() {
    super.initState();
    Future.microtask(_load);
  }

  Future<void> _load() async {
    try {
      final repository = ref.read(automationRepositoryProvider);
      preferences = await repository.preferences();
      if (preferences.isEmpty) {
        preferences = [
          await repository.createPreference({
            'name': 'Standard',
            'is_default': true,
            'slots': [],
          }),
        ];
      }
      selected = preferences.firstWhere(
        (value) => value['is_default'] == true,
        orElse: () => preferences.first,
      );
      engine =
          selected!['default_generation_engine']?.toString() ??
          'optimizer_strict';
    } on AppException catch (value) {
      error = value.message;
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  String _day(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  Map<String, dynamic> _request() => {
    'preferences_id': selected!['id'],
    'scope': scope,
    if (scope == 'single_day')
      'plan_date': _day(date)
    else
      'anchor_date': _day(date),
    'existing_plan_mode': mode,
    'generation_engine': engine,
    'recipe_overrides': recipeOverrides,
    'portion_overrides': portionOverrides,
    'locked_slot_keys': locked.toList(),
    'removed_slot_keys': removed.toList(),
  };

  Future<void> _generate({bool recalculate = false}) async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      generation = _request();
      draft = recalculate
          ? await ref
                .read(automationRepositoryProvider)
                .recalculate(generation!)
          : await ref.read(automationRepositoryProvider).generate(generation!);
    } on AppException catch (value) {
      error = value.message;
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _pickDate() async {
    final value = await showDatePicker(
      context: context,
      initialDate: date,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      locale: const Locale('de'),
    );
    if (value != null) setState(() => date = value);
  }

  Future<void> _editPreferences() async {
    final value = selected!;
    var pantry = value['pantry_preference'] as String;
    var shopping = value['shopping_effort_preference'] as String;
    var maximum = int.tryParse(
      value['maximum_preparation_time_minutes']?.toString() ?? '',
    );
    var optimizerEnabled = value['optimizer_enabled'] == true;
    var dayLimit =
        int.tryParse(value['solver_time_limit_day_seconds'].toString()) ?? 5;
    var weekLimit =
        int.tryParse(value['solver_time_limit_week_seconds'].toString()) ?? 20;
    var strictEnergy = value['strict_energy_target'] == true;
    var strictProtein = value['strict_protein_minimum'] == true;
    var strictFiber = value['strict_fiber_minimum'] == true;
    var relax = value['constraint_relaxation_enabled'] == true;
    var compare = value['compare_with_greedy'] != false;
    final objectiveWeights = <String, double>{
      for (final entry
          in (value['objective_weights'] as Map? ?? const {}).entries)
        entry.key.toString(): double.tryParse(entry.value.toString()) ?? 1,
    };
    const objectiveLabels = {
      'nutrition_fit': 'Nährwertziele',
      'pantry_usage': 'Vorrat',
      'shopping_effort': 'Einkaufsaufwand',
      'preparation_time': 'Zubereitungszeit',
      'variety': 'Abwechslung',
      'meal_prep': 'Meal-Prep',
      'recipe_preference': 'Rezeptpräferenz',
      'data_quality': 'Datenqualität',
    };
    for (final key in objectiveLabels.keys) {
      objectiveWeights.putIfAbsent(key, () => 1);
    }
    final slots = (value['slots'] as List)
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Automatik-Einstellungen'),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Mahlzeiten',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  ...slots.map(
                    (slot) => SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(
                        slot['custom_name']?.toString() ??
                            slot['slot_code'].toString(),
                      ),
                      subtitle: Text(
                        'Portionen ${slot['portion_minimum']}–${slot['portion_maximum']}',
                      ),
                      value: slot['is_enabled'] == true,
                      onChanged: (enabled) =>
                          setDialogState(() => slot['is_enabled'] = enabled),
                    ),
                  ),
                  const Divider(),
                  const Text(
                    'Vorrat und Einkauf',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  DropdownButtonFormField<String>(
                    initialValue: pantry,
                    decoration: const InputDecoration(labelText: 'Vorrat'),
                    items: const [
                      DropdownMenuItem(
                        value: 'ignore',
                        child: Text('Ignorieren'),
                      ),
                      DropdownMenuItem(
                        value: 'prefer_available',
                        child: Text('Vorhandenes bevorzugen'),
                      ),
                      DropdownMenuItem(
                        value: 'require_fully_available',
                        child: Text('Nur vollständig vorhanden'),
                      ),
                    ],
                    onChanged: (v) => setDialogState(() => pantry = v!),
                  ),
                  DropdownButtonFormField<String>(
                    initialValue: shopping,
                    decoration: const InputDecoration(
                      labelText: 'Einkaufsaufwand',
                    ),
                    items: const [
                      DropdownMenuItem(
                        value: 'ignore',
                        child: Text('Ignorieren'),
                      ),
                      DropdownMenuItem(
                        value: 'prefer_fewer_missing_items',
                        child: Text('Weniger fehlende Zutaten'),
                      ),
                      DropdownMenuItem(
                        value: 'prefer_lower_missing_quantity',
                        child: Text('Geringere Fehlmenge'),
                      ),
                    ],
                    onChanged: (v) => setDialogState(() => shopping = v!),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Zubereitungszeit und Abwechslung',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  TextFormField(
                    initialValue: maximum?.toString() ?? '',
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Maximale Zubereitungszeit (Minuten)',
                    ),
                    onChanged: (v) => maximum = int.tryParse(v),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Rezepte · Nährwertschwerpunkte · Bewertungsgewichte',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const Text(
                    'Tags, Zielanteile, Portionsbereiche und Gewichte bleiben in diesem Profil erhalten.',
                  ),
                  const Divider(),
                  const Text(
                    'Optimierungseinstellungen',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: optimizerEnabled,
                    onChanged: (v) =>
                        setDialogState(() => optimizerEnabled = v),
                    title: const Text('Gemeinsame Optimierung aktivieren'),
                  ),
                  DropdownButtonFormField<int>(
                    initialValue: dayLimit,
                    decoration: const InputDecoration(
                      labelText: 'Zeitlimit Tag',
                    ),
                    items: const [3, 5, 10, 15]
                        .map(
                          (v) => DropdownMenuItem(
                            value: v,
                            child: Text('$v Sekunden'),
                          ),
                        )
                        .toList(),
                    onChanged: (v) => setDialogState(() => dayLimit = v!),
                  ),
                  DropdownButtonFormField<int>(
                    initialValue: weekLimit,
                    decoration: const InputDecoration(
                      labelText: 'Zeitlimit Woche',
                    ),
                    items: const [5, 10, 20, 30, 60]
                        .map(
                          (v) => DropdownMenuItem(
                            value: v,
                            child: Text('$v Sekunden'),
                          ),
                        )
                        .toList(),
                    onChanged: (v) => setDialogState(() => weekLimit = v!),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: strictEnergy,
                    onChanged: (v) => setDialogState(() => strictEnergy = v!),
                    title: const Text('Energie-Zielbereich strikt'),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: strictProtein,
                    onChanged: (v) => setDialogState(() => strictProtein = v!),
                    title: const Text('Protein-Mindestwert strikt'),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: strictFiber,
                    onChanged: (v) => setDialogState(() => strictFiber = v!),
                    title: const Text('Ballaststoff-Mindestwert strikt'),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: relax,
                    onChanged: (v) => setDialogState(() => relax = v!),
                    title: const Text('Erklärbare Lockerungen erlauben'),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: compare,
                    onChanged: (v) => setDialogState(() => compare = v!),
                    title: const Text('Mit schnellem Entwurf vergleichen'),
                  ),
                  const Text(
                    'Relative Wichtigkeit',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  ...objectiveLabels.entries.map(
                    (entry) => Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          '${entry.value}: ${objectiveWeights[entry.key]!.round()}',
                        ),
                        Slider(
                          value: objectiveWeights[entry.key]!,
                          min: 0,
                          max: 10,
                          divisions: 10,
                          label: objectiveWeights[entry.key]!
                              .round()
                              .toString(),
                          onChanged: (v) => setDialogState(
                            () => objectiveWeights[entry.key] = v,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Speichern'),
            ),
          ],
        ),
      ),
    );
    if (saved != true) return;
    final payload = Map<String, dynamic>.from(value)
      ..remove('id')
      ..remove('is_archived')
      ..remove('updated_at');
    payload['pantry_preference'] = pantry;
    payload['shopping_effort_preference'] = shopping;
    payload['maximum_preparation_time_minutes'] = maximum;
    payload['optimizer_enabled'] = optimizerEnabled;
    payload['solver_time_limit_day_seconds'] = dayLimit;
    payload['solver_time_limit_week_seconds'] = weekLimit;
    payload['strict_energy_target'] = strictEnergy;
    payload['strict_protein_minimum'] = strictProtein;
    payload['strict_fiber_minimum'] = strictFiber;
    payload['constraint_relaxation_enabled'] = relax;
    payload['compare_with_greedy'] = compare;
    payload['objective_weights'] = objectiveWeights;
    payload['slots'] = slots
        .map((slot) => Map<String, dynamic>.from(slot)..remove('id'))
        .toList();
    selected = await ref
        .read(automationRepositoryProvider)
        .updatePreference(value['id'].toString(), payload);
    setState(() {
      draft = null;
    });
  }

  String _uuid() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }

  Future<void> _apply() async {
    var create = true;
    var applicationMode = 'all_or_nothing';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Entwurf übernehmen?'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Erst mit dieser Bestätigung werden Mahlzeiten gespeichert. Bestehende Mahlzeiten werden nicht überschrieben.',
              ),
              CheckboxListTile(
                value: create,
                onChanged: (v) => setState(() => create = v!),
                title: const Text('Fehlende Tagespläne erstellen'),
              ),
              DropdownButtonFormField<String>(
                initialValue: applicationMode,
                items: const [
                  DropdownMenuItem(
                    value: 'all_or_nothing',
                    child: Text('Alles oder nichts'),
                  ),
                  DropdownMenuItem(
                    value: 'apply_non_conflicting',
                    child: Text('Konfliktfreie Einträge übernehmen'),
                  ),
                ],
                onChanged: (v) => setState(() => applicationMode = v!),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Jetzt speichern'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;
    setState(() => busy = true);
    try {
      await ref.read(automationRepositoryProvider).apply({
        'client_operation_id': _uuid(),
        'preview_token': draft!['preview_token'],
        'generation': generation,
        'selected_slot_keys': <String>[],
        'create_missing_plans': create,
        'application_mode': applicationMode,
        'relaxation_confirmed': relaxationAccepted,
      });
      if (mounted) {
        context.go(
          scope == 'single_day'
              ? '/daily-plan?date=${_day(date)}'
              : '/weekly-plan',
        );
      }
    } on AppException catch (value) {
      if (mounted) setState(() => error = value.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Plan automatisch erstellen',
    body: ContentWidth(
      child: busy && preferences.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Die Automatik erstellt einen erklärbaren Entwurf. Sie speichert nichts ohne deine Bestätigung.',
                  ),
                  const SizedBox(height: 12),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'single_day', label: Text('Tag')),
                      ButtonSegment(
                        value: 'iso_week',
                        label: Text('ISO-Woche'),
                      ),
                    ],
                    selected: {scope},
                    onSelectionChanged: (v) => setState(() {
                      scope = v.first;
                      draft = null;
                    }),
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      scope == 'single_day' ? 'Datum' : 'Woche mit Datum',
                    ),
                    subtitle: Text(_day(date)),
                    trailing: const Icon(Icons.calendar_today),
                    onTap: _pickDate,
                  ),
                  if (selected != null)
                    DropdownButtonFormField<String>(
                      initialValue: selected!['id'].toString(),
                      decoration: const InputDecoration(
                        labelText: 'Einstellungsprofil',
                      ),
                      items: preferences
                          .map(
                            (v) => DropdownMenuItem(
                              value: v['id'].toString(),
                              child: Text(v['name'].toString()),
                            ),
                          )
                          .toList(),
                      onChanged: (id) => setState(() {
                        selected = preferences.firstWhere(
                          (v) => v['id'].toString() == id,
                        );
                        engine =
                            selected!['default_generation_engine']
                                ?.toString() ??
                            'optimizer_strict';
                        draft = null;
                      }),
                    ),
                  TextButton.icon(
                    onPressed: selected == null ? null : _editPreferences,
                    icon: const Icon(Icons.tune),
                    label: const Text('Einstellungen bearbeiten'),
                  ),
                  DropdownButtonFormField<String>(
                    key: const Key('automation-engine-selector'),
                    initialValue: engine,
                    decoration: const InputDecoration(
                      labelText: 'Planungsmethode',
                    ),
                    items: const [
                      DropdownMenuItem(
                        value: 'greedy',
                        child: Text('Schneller regelbasierter Entwurf'),
                      ),
                      DropdownMenuItem(
                        value: 'optimizer_strict',
                        child: Text('Gemeinsame Optimierung'),
                      ),
                      DropdownMenuItem(
                        value: 'optimizer_explainable_relaxation',
                        child: Text('Optimierung mit erklärbarer Lockerung'),
                      ),
                    ],
                    onChanged: (value) => setState(() {
                      engine = value!;
                      draft = null;
                      relaxationAccepted = false;
                    }),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(top: 6, bottom: 12),
                    child: Text(automationEngineDescription(engine)),
                  ),
                  DropdownButtonFormField<String>(
                    initialValue: mode,
                    decoration: const InputDecoration(
                      labelText: 'Bestehende Pläne',
                    ),
                    items: const [
                      DropdownMenuItem(
                        value: 'empty_days_only',
                        child: Text('Nur leere Tage'),
                      ),
                      DropdownMenuItem(
                        value: 'empty_meal_slots_only',
                        child: Text('Nur freie Mahlzeiten'),
                      ),
                      DropdownMenuItem(
                        value: 'draft_all_without_applying',
                        child: Text('Alles als Entwurf anzeigen'),
                      ),
                    ],
                    onChanged: (v) => setState(() => mode = v!),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    key: const Key('generate-automation-draft'),
                    onPressed: busy || selected == null ? null : _generate,
                    icon: const Icon(Icons.auto_awesome),
                    label: const Text('Entwurf erstellen'),
                  ),
                  if (busy)
                    const Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Text(
                        error!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                  if (draft != null) ..._draftWidgets(),
                ],
              ),
            ),
    ),
  );

  List<Widget> _draftWidgets() {
    final days = (draft!['days'] as List).cast<Map>();
    return [
      const Divider(height: 32),
      Text('Entwurf prüfen', style: Theme.of(context).textTheme.titleLarge),
      if (draft!['solver'] is Map)
        _solverSummary(Map.from(draft!['solver'] as Map)),
      Text('Basis: ${automationAssessmentBasis(draft!['assessment'])}'),
      ...days.expand(
        (day) => [
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(
              day['date'].toString(),
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          ...(day['proposed_meals'] as List).cast<Map>().map(_proposal),
          Text(
            'Projizierte Tageswerte: ${(day['projected_totals'] as List).length} Nährwerte',
          ),
        ],
      ),
      ...((draft!['warnings'] as List?) ?? []).map(
        (v) => ListTile(
          leading: const Icon(Icons.info_outline),
          title: Text(v.toString()),
        ),
      ),
      if ((draft!['objective_breakdown'] as List?)?.isNotEmpty == true)
        ExpansionTile(
          title: const Text('Ziele und Gewichtung'),
          children: (draft!['objective_breakdown'] as List)
              .cast<Map>()
              .map(
                (item) => ListTile(
                  title: Text(item['display_name_de'].toString()),
                  subtitle: Text(item['explanation_de'].toString()),
                  trailing: Text(
                    '× ${GermanDecimal.formatString(item['configured_weight'])}',
                  ),
                ),
              )
              .toList(),
        ),
      if (draft!['greedy_comparison'] is Map)
        ListTile(
          leading: const Icon(Icons.compare_arrows),
          title: const Text('Vergleich mit schnellem Entwurf'),
          subtitle: Text(
            '${draft!['greedy_comparison']['changed_slot_count']} geänderte Slots. ${draft!['greedy_comparison']['explanation_de']}',
          ),
        ),
      if ((draft!['infeasibility_reasons'] as List?)?.isNotEmpty == true)
        ..._infeasibilityWidgets(),
      if ((draft!['relaxations'] as List?)?.isNotEmpty == true)
        Card(
          color: Theme.of(context).colorScheme.errorContainer,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Für diesen Entwurf wurden Regeln gelockert',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                ...(draft!['relaxations'] as List).cast<Map>().map(
                  (item) => Text('• ${item['explanation_de']}'),
                ),
                CheckboxListTile(
                  value: relaxationAccepted,
                  onChanged: (value) =>
                      setState(() => relaxationAccepted = value!),
                  title: const Text(
                    'Lockerungen verstanden und Entwurf übernehmen',
                  ),
                ),
              ],
            ),
          ),
        ),
      Text(draft!['pantry_projection']['notice'].toString()),
      Text(draft!['shopping_projection']['notice'].toString()),
      const SizedBox(height: 16),
      FilledButton.icon(
        key: const Key('apply-automation-draft'),
        onPressed:
            busy ||
                ((draft!['relaxations'] as List?)?.isNotEmpty == true &&
                    !relaxationAccepted) ||
                (draft!['solver'] is Map &&
                    !{
                      'optimal',
                      'feasible',
                    }.contains(draft!['solver']['status']))
            ? null
            : _apply,
        icon: const Icon(Icons.check),
        label: const Text('Entwurf prüfen und übernehmen'),
      ),
    ];
  }

  Widget _solverSummary(Map<String, dynamic> solver) {
    final status = solver['status']?.toString();
    final title = optimizerStatusLabel(status);
    return Semantics(
      label: title,
      child: Card(
        child: ListTile(
          leading: const Icon(Icons.calculate_outlined),
          title: Text(title),
          subtitle: Text(
            'Laufzeit ${GermanDecimal.formatString(solver['solve_time_seconds'])} s · '
            'Limit ${GermanDecimal.formatString(solver['time_limit_seconds'])} s'
            '${solver['relative_gap'] == null ? '' : ' · Modelllücke ${GermanDecimal.formatString(solver['relative_gap'])}'}',
          ),
        ),
      ),
    );
  }

  List<Widget> _infeasibilityWidgets() => [
    const ListTile(
      leading: Icon(Icons.warning_amber),
      title: Text('Keine zulässige Kombination gefunden'),
    ),
    ...(draft!['infeasibility_reasons'] as List).cast<Map>().map(
      (item) => ListTile(title: Text(item['explanation_de'].toString())),
    ),
    OutlinedButton(
      onPressed: () => setState(() {
        engine = 'greedy';
        draft = null;
      }),
      child: const Text('Schnellen Entwurf verwenden'),
    ),
  ];

  Widget _proposal(Map proposal) {
    final key = proposal['slot_key'].toString();
    if (proposal['unresolved'] == true) {
      return ListTile(
        leading: const Icon(Icons.warning_amber),
        title: Text(proposal['slot_code'].toString()),
        subtitle: Text(proposal['explanation_de'].toString()),
      );
    }
    final alternatives = (proposal['alternatives'] as List).cast<Map>();
    return Card(
      child: ExpansionTile(
        title: Text(
          '${proposal['custom_name'] ?? proposal['slot_code']}: ${proposal['recipe_name']}',
        ),
        subtitle: Text(
          '${GermanDecimal.formatString(proposal['portion_count'])} Portion(en) · Eignung ${GermanDecimal.formatString(proposal['weighted_score'])}',
        ),
        trailing: IconButton(
          icon: Icon(locked.contains(key) ? Icons.lock : Icons.lock_open),
          onPressed: () => setState(
            () => locked.contains(key) ? locked.remove(key) : locked.add(key),
          ),
        ),
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(proposal['selection_explanation'].toString()),
          ),
          ...((proposal['component_scores'] as List).cast<Map>()).map(
            (c) => ListTile(
              dense: true,
              title: Text(c['code'].toString()),
              subtitle: Text(c['explanation_de'].toString()),
              trailing: Text(GermanDecimal.formatString(c['score'])),
            ),
          ),
          if (alternatives.isNotEmpty)
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(labelText: 'Alternative'),
              initialValue:
                  '${proposal['recipe_id']}|${proposal['portion_count']}',
              items: [proposal, ...alternatives]
                  .map(
                    (a) => DropdownMenuItem(
                      value: '${a['recipe_id']}|${a['portion_count']}',
                      child: Text(
                        '${a['recipe_name']} · ${GermanDecimal.formatString(a['portion_count'])}',
                      ),
                    ),
                  )
                  .toList(),
              onChanged: locked.contains(key)
                  ? null
                  : (selection) {
                      final separator = selection!.lastIndexOf('|');
                      recipeOverrides[key] = selection.substring(0, separator);
                      portionOverrides[key] = selection.substring(
                        separator + 1,
                      );
                      _generate(recalculate: true);
                    },
            ),
          TextButton.icon(
            onPressed: locked.contains(key)
                ? null
                : () {
                    removed.add(key);
                    _generate(recalculate: true);
                  },
            icon: const Icon(Icons.remove_circle_outline),
            label: const Text('Aus Entwurf entfernen'),
          ),
        ],
      ),
    );
  }
}
