import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';

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
  List<Map<String, dynamic>> preferences = [];
  Map<String, dynamic>? selected;
  Map<String, dynamic>? draft;
  Map<String, dynamic>? generation;
  final recipeOverrides = <String, String>{};
  final portionOverrides = <String, String>{};
  final locked = <String>{};
  final removed = <String>{};
  bool busy = true;
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
                        draft = null;
                      }),
                    ),
                  TextButton.icon(
                    onPressed: selected == null ? null : _editPreferences,
                    icon: const Icon(Icons.tune),
                    label: const Text('Einstellungen bearbeiten'),
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
      Text(
        'Basis: Einschätzung ${draft!['assessment']['calculated_at'] ?? draft!['assessment']['id']}',
      ),
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
      Text(draft!['pantry_projection']['notice'].toString()),
      Text(draft!['shopping_projection']['notice'].toString()),
      const SizedBox(height: 16),
      FilledButton.icon(
        key: const Key('apply-automation-draft'),
        onPressed: busy ? null : _apply,
        icon: const Icon(Icons.check),
        label: const Text('Entwurf prüfen und übernehmen'),
      ),
    ];
  }

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
