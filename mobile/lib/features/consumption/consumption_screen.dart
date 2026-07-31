import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../foods/food_models.dart';
import '../recipes/recipe_models.dart';
import 'consumption_repository.dart';

final class ConsumptionScreen extends ConsumerStatefulWidget {
  const ConsumptionScreen({this.initialDate, super.key});
  final DateTime? initialDate;

  @override
  ConsumerState<ConsumptionScreen> createState() => _ConsumptionScreenState();
}

final class _ConsumptionScreenState extends ConsumerState<ConsumptionScreen> {
  late DateTime selected = _dateOnly(widget.initialDate ?? DateTime.now());
  bool loading = true;
  String? error;
  Map<String, dynamic>? day;
  Map<String, dynamic>? plan;
  Map<String, dynamic>? weekly;
  bool mutating = false;

  ConsumptionRepository get repository =>
      ref.read(consumptionRepositoryProvider);
  String get date => _iso(selected);
  bool get editable => day?['status'] != 'finalized';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final values = await Future.wait([
        repository.byDate(date),
        repository.planByDate(date),
        repository.weekly(date),
      ]);
      if (!mounted) return;
      setState(() {
        day = values[0];
        plan = values[1];
        weekly = values[2];
        loading = false;
      });
    } catch (exception) {
      if (!mounted) return;
      setState(() {
        error = exception.toString();
        loading = false;
      });
    }
  }

  Future<void> _move(int days) async {
    selected = selected.add(Duration(days: days));
    await _load();
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Verzehr',
    actions: [
      IconButton(
        tooltip: 'Wochenübersicht',
        onPressed: mutating ? null : () => _guard(_weeklyOverview),
        icon: const Icon(Icons.view_week_outlined),
      ),
      IconButton(
        tooltip: 'Verlauf',
        onPressed: mutating ? null : () => _guard(_history),
        icon: const Icon(Icons.history),
      ),
      IconButton(
        tooltip: 'Aktualisieren',
        onPressed: _load,
        icon: const Icon(Icons.refresh),
      ),
    ],
    body: ContentWidth(
      child: loading
          ? const Center(child: CircularProgressIndicator())
          : error != null
          ? _error()
          : Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _dateNavigation(),
                const SizedBox(height: 12),
                if (day == null) _empty() else _content(),
                const SizedBox(height: 32),
              ],
            ),
    ),
  );

  Widget _dateNavigation() => Row(
    children: [
      IconButton(
        tooltip: 'Vorheriger Tag',
        onPressed: () => _move(-1),
        icon: const Icon(Icons.chevron_left),
      ),
      Expanded(
        child: OutlinedButton.icon(
          onPressed: _pickDate,
          icon: const Icon(Icons.calendar_today),
          label: Text('${selected.day}.${selected.month}.${selected.year}'),
        ),
      ),
      IconButton(
        tooltip: 'Nächster Tag',
        onPressed: selected.isBefore(_dateOnly(DateTime.now()))
            ? () => _move(1)
            : null,
        icon: const Icon(Icons.chevron_right),
      ),
      TextButton(
        onPressed: () {
          selected = _dateOnly(DateTime.now());
          _load();
        },
        child: const Text('Heute'),
      ),
    ],
  );

  Widget _empty() => Card(
    key: const Key('consumption-no-day'),
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Icon(Icons.restaurant_outlined, size: 48),
          const SizedBox(height: 12),
          Text(
            'Für diesen Tag wurde noch kein Verzehr erfasst.',
            style: Theme.of(context).textTheme.titleMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          FilledButton(
            key: const Key('create-empty-consumption-day'),
            onPressed: mutating ? null : () => _guard(_createEmpty),
            child: const Text('Leeren Tag anlegen'),
          ),
          if (plan != null) ...[
            const SizedBox(height: 8),
            OutlinedButton(
              key: const Key('initialize-consumption-from-plan'),
              onPressed: mutating ? null : () => _guard(_fromPlan),
              child: const Text('Aus Tagesplan übernehmen'),
            ),
            const SizedBox(height: 8),
            const Text(
              'Dabei werden Planeinträge nur als offen angezeigt – nichts wird automatisch als konsumiert markiert.',
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    ),
  );

  Widget _content() {
    final current = day!;
    final summary = Map<String, dynamic>.from(current['summary'] as Map);
    final quality = Map<String, dynamic>.from(summary['quality'] as Map);
    final totals = (summary['actual_totals'] as List).whereType<Map>();
    String value(String code) {
      final item = totals
          .cast<Map>()
          .where((e) => e['nutrient_code'] == code)
          .firstOrNull;
      if (item == null || item['amount'] == null) return 'unbekannt';
      return '${GermanDecimal.formatString(item['amount'])} ${item['unit']}';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      editable ? Icons.edit_note : Icons.lock_outline,
                      semanticLabel: editable
                          ? 'Offener Tag'
                          : 'Abgeschlossener Tag',
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        editable
                            ? 'Aufzeichnung offen'
                            : 'Aufzeichnung abgeschlossen',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                  ],
                ),
                Text(
                  consumptionAttestationLabel(
                    current['completeness_attestation']?.toString(),
                  ),
                ),
                const Divider(),
                Text('Energie: ${value('energy_kcal')}'),
                Text('Protein: ${value('protein')}'),
                Text('Kohlenhydrate: ${value('carbohydrate')}'),
                Text('Fett: ${value('fat')}'),
                const SizedBox(height: 8),
                Text(
                  current['training_day_adjustment_id'] == null
                      ? 'Zielbasis: unveränderte Einschätzung'
                      : 'Zielbasis: einschließlich verknüpfter Trainingstag-Anpassung',
                ),
                if (current['target_basis_snapshot']
                    case final Map snapshot) ...[
                  Text(
                    'Basisziel Energie: ${_valueOrUnknown(snapshot['baseline_energy_target_kcal'], 'kcal')}',
                  ),
                  Text(
                    'Trainingstag-Anpassung: ${_valueOrUnknown(snapshot['energy_delta_kcal'], 'kcal')}',
                  ),
                  Text(
                    'Effektives Energieziel: ${_valueOrUnknown(snapshot['effective_energy_target_kcal'], 'kcal')}',
                  ),
                ],
                if (!editable && current['finalized_at'] != null)
                  Text(
                    'Abgeschlossen am ${_dateTimeLabel(current['finalized_at'])}',
                  ),
              ],
            ),
          ),
        ),
        _comparisonCard(current, summary),
        if (editable && plan != null && current['source_daily_plan_id'] == null)
          OutlinedButton.icon(
            key: const Key('link-existing-consumption-to-plan'),
            onPressed: mutating ? null : () => _guard(_linkPlan),
            icon: const Icon(Icons.link),
            label: const Text('Vorhandenen Tagesplan verknüpfen'),
          ),
        if ((current['planned_entries'] as List).isNotEmpty) _planned(current),
        for (final indexed
            in (current['meals'] as List).whereType<Map>().indexed)
          _mealCard(
            Map<String, dynamic>.from(indexed.$2),
            indexed.$1,
            (current['meals'] as List).length,
          ),
        if (editable)
          OutlinedButton.icon(
            key: const Key('add-consumption-meal'),
            onPressed: mutating ? null : () => _guard(_addMeal),
            icon: const Icon(Icons.add),
            label: const Text('Mahlzeit hinzufügen'),
          ),
        const SizedBox(height: 12),
        _qualityCard(quality),
        const SizedBox(height: 8),
        const Card(
          child: ListTile(
            leading: Icon(Icons.inventory_2_outlined),
            title: Text('Vorrat bleibt unverändert'),
            subtitle: Text(
              'Verzehreinträge verändern den Vorrat nicht automatisch.',
            ),
          ),
        ),
        const SizedBox(height: 8),
        if (editable)
          FilledButton.icon(
            key: const Key('finalize-consumption-day'),
            onPressed: mutating ? null : () => _guard(_finalize),
            icon: const Icon(Icons.check_circle_outline),
            label: const Text('Tag prüfen und abschließen'),
          )
        else
          OutlinedButton(
            key: const Key('reopen-consumption-day'),
            onPressed: mutating ? null : () => _guard(_reopen),
            child: const Text('Tag wieder öffnen'),
          ),
        TextButton.icon(
          onPressed: mutating ? null : () => _guard(_deleteDay),
          icon: const Icon(Icons.delete_forever),
          label: const Text('Verzehrtag dauerhaft löschen'),
        ),
        if (weekly != null)
          Text(
            'Diese Woche: ${weekly!['recorded_day_count']} erfasste Tage, '
            '${weekly!['missing_day_count']} Tage ohne Aufzeichnung. Fehlende Tage zählen nicht als null.',
          ),
      ],
    );
  }

  Widget _planned(Map<String, dynamic> current) => Card(
    key: const Key('pending-planned-entries'),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Geplant', style: Theme.of(context).textTheme.titleMedium),
          const Text(
            'Ein Tagesplan ist kein Nachweis für tatsächlichen Verzehr.',
          ),
          for (final mealId
              in (current['planned_entries'] as List)
                  .whereType<Map>()
                  .where((item) => item['status'] == 'pending')
                  .map((item) => item['meal_id'].toString())
                  .toSet())
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                key: Key('confirm-whole-meal-$mealId'),
                onPressed: editable && !mutating
                    ? () => _guard(() => _confirmWholeMeal(mealId))
                    : null,
                icon: const Icon(Icons.done_all),
                label: const Text('Gesamte Mahlzeit wie geplant übernehmen'),
              ),
            ),
          for (final raw
              in (current['planned_entries'] as List).whereType<Map>())
            Builder(
              builder: (context) {
                final item = Map<String, dynamic>.from(raw);
                final pending = item['status'] == 'pending';
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(item['display_name'].toString()),
                  subtitle: Text(
                    '${_plannedAmount(item)}\n'
                    'Aktueller Status: ${consumptionOutcomeLabel(item['status'].toString())}\n'
                    'Tatsächliche Menge: ${_actualOutcomeAmount(item)}'
                    '${item['source_unavailable'] == true ? '\nQuelle nicht mehr verfügbar – historischer Stand bleibt erhalten.' : ''}',
                  ),
                  isThreeLine: true,
                  trailing: pending && editable
                      ? PopupMenuButton<String>(
                          tooltip: 'Tatsächlichen Ausgang erfassen',
                          onSelected: (value) =>
                              _guard(() => _simpleOutcome(item, value)),
                          itemBuilder: (_) => const [
                            PopupMenuItem(
                              value: 'consumed_as_planned',
                              child: Text('Wie geplant konsumiert'),
                            ),
                            PopupMenuItem(
                              value: 'skipped',
                              child: Text('Übersprungen'),
                            ),
                            PopupMenuItem(
                              value: 'consumed_modified',
                              child: Text('Menge anpassen'),
                            ),
                            PopupMenuItem(
                              value: 'partially_consumed',
                              child: Text('Teilweise konsumiert'),
                            ),
                            PopupMenuItem(
                              value: 'replaced',
                              child: Text('Ersetzt'),
                            ),
                          ],
                        )
                      : null,
                );
              },
            ),
        ],
      ),
    ),
  );

  Widget _mealCard(Map<String, dynamic> meal, int index, int mealCount) {
    final entries = (meal['entries'] as List).whereType<Map>().toList();
    final nutrients = (meal['nutrient_totals'] as List? ?? const [])
        .whereType<Map>();
    String nutrient(String code) {
      final item = nutrients
          .cast<Map>()
          .where((candidate) => candidate['nutrient_code'] == code)
          .firstOrNull;
      if (item == null || item['amount'] == null) return 'unbekannt';
      return '${GermanDecimal.formatString(item['amount'])} ${item['unit']}';
    }

    return Card(
      child: ExpansionTile(
        initiallyExpanded: true,
        title: Row(
          children: [
            Expanded(child: Text(meal['meal_name'].toString())),
            if (editable) ...[
              IconButton(
                tooltip: 'Mahlzeit bearbeiten',
                onPressed: mutating
                    ? null
                    : () => _guard(() => _editMeal(meal)),
                icon: const Icon(Icons.edit_outlined, size: 18),
              ),
              IconButton(
                tooltip: 'Mahlzeit löschen',
                onPressed: mutating
                    ? null
                    : () => _guard(() => _deleteMeal(meal)),
                icon: const Icon(Icons.delete_outline, size: 18),
              ),
              IconButton(
                tooltip: 'Nach oben',
                onPressed: index == 0 || mutating
                    ? null
                    : () => _guard(() => _moveMeal(index, -1)),
                icon: const Icon(Icons.arrow_upward, size: 18),
              ),
              IconButton(
                tooltip: 'Nach unten',
                onPressed: index == mealCount - 1 || mutating
                    ? null
                    : () => _guard(() => _moveMeal(index, 1)),
                icon: const Icon(Icons.arrow_downward, size: 18),
              ),
            ],
          ],
        ),
        subtitle: Text(
          '${meal['consumed_time'] == null ? '' : '${meal['consumed_time'].toString().substring(0, 5)} Uhr · '}'
          '${entries.length} tatsächlich erfasste Einträge · '
          '${nutrient('energy_kcal')} · Protein ${nutrient('protein')}\n'
          '${meal['unresolved_entry_count']} ungeklärt · '
          '${(meal['planned_outcome_summary'] as Map?)?['resolved'] ?? 0} Planentscheidungen',
        ),
        children: [
          for (final raw in entries)
            ListTile(
              title: Text(raw['source_display_name_snapshot'].toString()),
              subtitle: Text(
                '${_entryAmount(raw)} · normalisiert: '
                '${_normalizedAmount(raw)}\n'
                '${raw['nutrient_snapshot_status'] == 'complete' ? 'Nährwertdaten vollständig' : 'Teilweise unbekannte Nährwerte'}',
              ),
              isThreeLine: true,
              onTap: () => _snapshotDetails(Map<String, dynamic>.from(raw)),
              trailing: editable
                  ? Wrap(
                      children: [
                        IconButton(
                          tooltip: raw['entry_type'] == 'manual_unresolved'
                              ? 'Mit Lebensmittel oder Rezept klären'
                              : 'Menge bearbeiten',
                          onPressed: mutating
                              ? null
                              : () => _guard(
                                  () => raw['entry_type'] == 'manual_unresolved'
                                      ? _resolveManualEntry(
                                          Map<String, dynamic>.from(raw),
                                        )
                                      : _editEntry(
                                          Map<String, dynamic>.from(raw),
                                        ),
                                ),
                          icon: const Icon(Icons.edit_outlined),
                        ),
                        IconButton(
                          tooltip: 'Eintrag dauerhaft löschen',
                          onPressed: mutating
                              ? null
                              : () => _guard(
                                  () => _deleteEntry(raw['id'].toString()),
                                ),
                          icon: const Icon(Icons.delete_outline),
                        ),
                      ],
                    )
                  : null,
            ),
          if (editable)
            Padding(
              padding: const EdgeInsets.all(8),
              child: FilledButton.tonalIcon(
                onPressed: mutating
                    ? null
                    : () => _guard(() => _addEntry(meal)),
                icon: const Icon(Icons.add),
                label: const Text('Tatsächlichen Verzehr hinzufügen'),
              ),
            ),
        ],
      ),
    );
  }

  Widget _qualityCard(Map<String, dynamic> quality) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Datenqualität', style: Theme.of(context).textTheme.titleMedium),
          Text('Offene Planeinträge: ${quality['pending_plan_entry_count']}'),
          Text('Ungeklärte Einträge: ${quality['unresolved_entry_count']}'),
          Text(
            quality['basic_nutrition_complete'] == true
                ? 'Nährwertdaten vollständig'
                : 'Teilweise unbekannte Nährwerte',
          ),
          for (final raw in (quality['warnings'] as List).whereType<Map>())
            Text('• ${raw['explanation_de']}'),
        ],
      ),
    ),
  );

  Widget _comparisonCard(
    Map<String, dynamic> current,
    Map<String, dynamic> summary,
  ) {
    final comparison = Map<String, dynamic>.from(
      current['planned_vs_actual'] as Map? ?? const {},
    );
    final differences = (comparison['differences'] as List? ?? const [])
        .whereType<Map>();
    final energy = differences
        .cast<Map>()
        .where((item) => item['nutrient_code'] == 'energy_kcal')
        .firstOrNull;
    final targets = (summary['target_comparison'] as List? ?? const [])
        .whereType<Map>();
    final targetEnergy = targets
        .cast<Map>()
        .where((item) => item['nutrient_code'] == 'energy_kcal')
        .firstOrNull;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Vergleich: geplant und erfasst',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (current['source_daily_plan_id'] == null)
              const Text('Für diesen Tag ist kein Tagesplan verknüpft.')
            else if (energy == null || energy['relation'] == 'indeterminate')
              const Text(
                'Der Energievergleich ist wegen unvollständiger Daten unbestimmt.',
              )
            else ...[
              Text(
                'Geplant: ${GermanDecimal.formatString(energy['planned_amount'])} ${energy['unit']}',
              ),
              Text(
                'Erfasst: ${GermanDecimal.formatString(energy['actual_amount'])} ${energy['unit']}',
              ),
              Text(
                'Differenz: ${GermanDecimal.formatString(energy['difference'])} ${energy['unit']}',
              ),
            ],
            const Divider(),
            Text(
              'Zielvergleich',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(
              targetEnergy == null
                  ? 'Keine persönliche Zielbasis verfügbar.'
                  : targetEnergy['explanation_de'].toString(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _error() => Center(
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Die Verzehrdaten konnten nicht geladen werden.'),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: _load,
              child: const Text('Erneut versuchen'),
            ),
          ],
        ),
      ),
    ),
  );

  Future<void> _createEmpty() async {
    await repository.create(date);
    await _load();
  }

  Future<void> _fromPlan() async {
    await repository.fromPlan((plan!['plan'] as Map)['id'].toString());
    await _load();
  }

  Future<void> _linkPlan() async {
    await repository.linkPlan(
      day!['id'].toString(),
      (plan!['plan'] as Map)['id'].toString(),
      day!['version'] as int,
    );
    await _load();
  }

  Future<void> _addMeal() async {
    final name = TextEditingController();
    String type = 'other';
    TimeOfDay? consumedTime;
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Mahlzeit hinzufügen'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: type,
                decoration: const InputDecoration(labelText: 'Art'),
                items: _mealTypes.entries
                    .map(
                      (e) =>
                          DropdownMenuItem(value: e.key, child: Text(e.value)),
                    )
                    .toList(),
                onChanged: (value) => setDialogState(() => type = value!),
              ),
              TextField(
                controller: name,
                decoration: const InputDecoration(labelText: 'Optionaler Name'),
              ),
              TextButton.icon(
                onPressed: () async {
                  final picked = await showTimePicker(
                    context: context,
                    initialTime: consumedTime ?? TimeOfDay.now(),
                  );
                  if (picked != null) {
                    setDialogState(() => consumedTime = picked);
                  }
                },
                icon: const Icon(Icons.schedule),
                label: Text(
                  consumedTime == null
                      ? 'Verzehrzeit hinzufügen'
                      : consumedTime!.format(context),
                ),
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
              child: const Text('Anlegen'),
            ),
          ],
        ),
      ),
    );
    if (accepted != true) return;
    await repository.addMeal(day!['id'].toString(), {
      'meal_type': type,
      'custom_name': name.text.trim().isEmpty ? null : name.text.trim(),
      'consumed_time': consumedTime == null
          ? null
          : '${consumedTime!.hour.toString().padLeft(2, '0')}:${consumedTime!.minute.toString().padLeft(2, '0')}:00',
    });
    await _load();
  }

  Future<void> _moveMeal(int index, int delta) async {
    final ids = (day!['meals'] as List)
        .whereType<Map>()
        .map((meal) => meal['id'].toString())
        .toList();
    final target = index + delta;
    final item = ids.removeAt(index);
    ids.insert(target, item);
    await repository.reorderMeals(
      day!['id'].toString(),
      ids,
      day!['version'] as int,
    );
    await _load();
  }

  Future<void> _editMeal(Map<String, dynamic> meal) async {
    final name = TextEditingController(text: meal['custom_name']?.toString());
    String type = meal['meal_type'].toString();
    TimeOfDay? consumedTime;
    final rawTime = meal['consumed_time']?.toString();
    if (rawTime != null) {
      final parts = rawTime.split(':');
      consumedTime = TimeOfDay(
        hour: int.parse(parts[0]),
        minute: int.parse(parts[1]),
      );
    }
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Mahlzeit bearbeiten'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: type,
                decoration: const InputDecoration(labelText: 'Art'),
                items: _mealTypes.entries
                    .map(
                      (item) => DropdownMenuItem(
                        value: item.key,
                        child: Text(item.value),
                      ),
                    )
                    .toList(),
                onChanged: (value) => setDialogState(() => type = value!),
              ),
              TextField(
                controller: name,
                decoration: const InputDecoration(labelText: 'Optionaler Name'),
              ),
              TextButton.icon(
                onPressed: () async {
                  final picked = await showTimePicker(
                    context: context,
                    initialTime: consumedTime ?? TimeOfDay.now(),
                  );
                  if (picked != null) {
                    setDialogState(() => consumedTime = picked);
                  }
                },
                icon: const Icon(Icons.schedule),
                label: Text(
                  consumedTime?.format(context) ?? 'Verzehrzeit hinzufügen',
                ),
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
              child: const Text('Speichern'),
            ),
          ],
        ),
      ),
    );
    if (accepted != true) return;
    await repository.updateMeal(day!['id'].toString(), meal['id'].toString(), {
      'meal_type': type,
      'custom_name': name.text.trim().isEmpty ? null : name.text.trim(),
      'consumed_time': consumedTime == null
          ? null
          : '${consumedTime!.hour.toString().padLeft(2, '0')}:${consumedTime!.minute.toString().padLeft(2, '0')}:00',
      'position': meal['position'],
      'note': meal['note'],
    });
    await _load();
  }

  Future<void> _deleteMeal(Map<String, dynamic> meal) async {
    final entries = (meal['entries'] as List).isNotEmpty;
    final confirmed = await _confirm(
      entries
          ? 'Mahlzeit und alle enthaltenen Verzehreinträge dauerhaft löschen?'
          : 'Leere Mahlzeit dauerhaft löschen?',
    );
    if (!confirmed) return;
    await repository.deleteMeal(
      day!['id'].toString(),
      meal['id'].toString(),
      confirm: entries,
    );
    await _load();
  }

  Future<void> _snapshotDetails(Map<String, dynamic> entry) async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Historischer Nährwertstand',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          Text(entry['source_display_name_snapshot'].toString()),
          Text('Erfasst: ${_entryAmount(entry)}'),
          Text('Normalisiert: ${_normalizedAmount(entry)}'),
          const Divider(),
          for (final raw
              in (entry['nutrient_snapshots'] as List).whereType<Map>())
            ListTile(
              dense: true,
              title: Text(raw['nutrient_code'].toString()),
              trailing: Text(
                raw['amount'] == null
                    ? 'unbekannt'
                    : '${GermanDecimal.formatString(raw['amount'])} ${raw['unit']}',
              ),
              subtitle: Text(raw['value_state'].toString()),
            ),
        ],
      ),
    );
  }

  Future<void> _editEntry(Map<String, dynamic> entry) async {
    final isFood = entry['entry_type'] == 'food';
    final quantity = TextEditingController(
      text: GermanDecimal.formatString(
        isFood ? entry['entered_quantity'] : entry['recipe_portion_count'],
      ),
    );
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Tatsächliche Menge bearbeiten'),
        content: TextField(
          controller: quantity,
          autofocus: true,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: isFood ? 'Menge' : 'Portionen',
            helperText: 'Komma und Punkt werden akzeptiert.',
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
    );
    if (accepted != true) return;
    final value = quantity.text.trim().replaceAll(',', '.');
    await repository.updateEntry(
      day!['id'].toString(),
      entry['id'].toString(),
      {
        'meal_id': entry['meal_id'],
        'entry_type': entry['entry_type'],
        'origin_type': entry['origin_type'],
        if (isFood) ...{
          'food_id': entry['food_id'],
          'entered_quantity': value,
          'entered_unit_code': entry['entered_unit_code'],
          'food_measure_id': entry['food_measure_id'],
        } else ...{
          'recipe_id': entry['recipe_id'],
          'recipe_portion_count': value,
        },
        'note': entry['note'],
        'client_operation_id': consumptionOperationId(),
        'expected_version': entry['version'],
      },
    );
    await _load();
  }

  Future<void> _resolveManualEntry(Map<String, dynamic> entry) async {
    final foods = await ref.read(foodRepositoryProvider).list();
    final recipes = await ref.read(recipeRepositoryProvider).list();
    if (!mounted) return;
    String type = foods.isNotEmpty ? 'food' : 'recipe';
    String? sourceId = foods.firstOrNull?.id ?? recipes.firstOrNull?.id;
    final quantity = TextEditingController(text: '1');
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Manuellen Eintrag klären'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: type,
                items: const [
                  DropdownMenuItem(value: 'food', child: Text('Lebensmittel')),
                  DropdownMenuItem(
                    value: 'recipe',
                    child: Text('Rezept/Gericht'),
                  ),
                ],
                onChanged: (value) => setDialogState(() {
                  type = value!;
                  sourceId = type == 'food'
                      ? foods.firstOrNull?.id
                      : recipes.firstOrNull?.id;
                }),
              ),
              DropdownButtonFormField<String>(
                initialValue: sourceId,
                decoration: const InputDecoration(
                  labelText: 'Tatsächliche Quelle',
                ),
                items: type == 'food'
                    ? foods
                          .map(
                            (item) => DropdownMenuItem(
                              value: item.id,
                              child: Text(item.name),
                            ),
                          )
                          .toList()
                    : recipes
                          .map(
                            (item) => DropdownMenuItem(
                              value: item.id,
                              child: Text(item.name),
                            ),
                          )
                          .toList(),
                onChanged: (value) => sourceId = value,
              ),
              TextField(
                controller: quantity,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: InputDecoration(
                  labelText: type == 'food' ? 'Menge in g' : 'Portionen',
                  helperText: 'Komma und Punkt werden akzeptiert.',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: sourceId == null
                  ? null
                  : () => Navigator.pop(context, true),
              child: const Text('Klären'),
            ),
          ],
        ),
      ),
    );
    if (accepted != true || sourceId == null) return;
    final value = quantity.text.trim().replaceAll(',', '.');
    await repository.updateEntry(
      day!['id'].toString(),
      entry['id'].toString(),
      {
        'meal_id': entry['meal_id'],
        'entry_type': type,
        'origin_type': entry['origin_type'],
        if (type == 'food') ...{
          'food_id': sourceId,
          'entered_quantity': value,
          'entered_unit_code': 'g',
        } else ...{
          'recipe_id': sourceId,
          'recipe_portion_count': value,
        },
        'note': entry['note'],
        'client_operation_id': consumptionOperationId(),
        'expected_version': entry['version'],
      },
    );
    await _load();
  }

  Future<void> _addEntry(Map<String, dynamic> meal) async {
    final foods = await ref.read(foodRepositoryProvider).list();
    final recipes = await ref.read(recipeRepositoryProvider).list();
    if (!mounted) return;
    String type = 'food';
    String? sourceId = foods.firstOrNull?.id;
    String unit = foods.firstOrNull?.referenceUnit ?? 'g';
    String? measureId;
    final quantity = TextEditingController(text: '1');
    final manual = TextEditingController();
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title: const Text('Ungeplant erfasst'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: type,
                    decoration: const InputDecoration(labelText: 'Eintrag'),
                    items: const [
                      DropdownMenuItem(
                        value: 'food',
                        child: Text('Lebensmittel'),
                      ),
                      DropdownMenuItem(
                        value: 'recipe',
                        child: Text('Rezept/Gericht'),
                      ),
                      DropdownMenuItem(
                        value: 'manual_unresolved',
                        child: Text('Manueller Eintrag'),
                      ),
                    ],
                    onChanged: (value) => setDialogState(() {
                      type = value!;
                      sourceId = type == 'food'
                          ? foods.firstOrNull?.id
                          : type == 'recipe'
                          ? recipes.firstOrNull?.id
                          : null;
                      unit = foods.firstOrNull?.referenceUnit ?? 'g';
                      measureId = null;
                    }),
                  ),
                  if (type != 'manual_unresolved')
                    DropdownButtonFormField<String>(
                      initialValue: sourceId,
                      decoration: InputDecoration(
                        labelText: type == 'food'
                            ? 'Lebensmittel'
                            : 'Rezept/Gericht',
                      ),
                      items: type == 'food'
                          ? foods
                                .map(
                                  (FoodItem source) => DropdownMenuItem(
                                    value: source.id,
                                    child: Text(
                                      source.name,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                )
                                .toList()
                          : recipes
                                .map(
                                  (RecipeItem source) => DropdownMenuItem(
                                    value: source.id,
                                    child: Text(
                                      source.name,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                )
                                .toList(),
                      onChanged: (value) => setDialogState(() {
                        sourceId = value;
                        final food = foods
                            .where((item) => item.id == value)
                            .firstOrNull;
                        unit = food?.referenceUnit ?? 'g';
                        measureId = null;
                      }),
                    )
                  else
                    TextField(
                      key: const Key('manual-consumption-name'),
                      controller: manual,
                      decoration: const InputDecoration(
                        labelText: 'Bezeichnung',
                      ),
                    ),
                  if (type != 'manual_unresolved')
                    TextField(
                      controller: quantity,
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: InputDecoration(
                        labelText: type == 'food' ? 'Menge' : 'Portionen',
                        helperText: 'Komma und Punkt werden akzeptiert.',
                      ),
                    ),
                  if (type == 'food')
                    DropdownButtonFormField<String>(
                      initialValue: measureId == null
                          ? unit
                          : 'measure:$measureId',
                      decoration: const InputDecoration(
                        labelText: 'Einheit oder Maß',
                      ),
                      items: _foodUnitItems(foods, sourceId),
                      onChanged: (value) => setDialogState(() {
                        if (value == null) return;
                        if (value.startsWith('measure:')) {
                          measureId = value.substring('measure:'.length);
                        } else {
                          measureId = null;
                          unit = value;
                        }
                      }),
                    ),
                  const SizedBox(height: 12),
                  const Text(
                    'Verzehreinträge verändern den Vorrat nicht automatisch.',
                  ),
                ],
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
          );
        },
      ),
    );
    if (accepted != true) return;
    final decimal = quantity.text.trim().replaceAll(',', '.');
    final payload = <String, dynamic>{
      'meal_id': meal['id'],
      'entry_type': type,
      'origin_type': 'unplanned',
      if (type == 'food') ...{
        'food_id': sourceId,
        'entered_quantity': decimal,
        if (measureId == null) 'entered_unit_code': unit,
        'food_measure_id': ?measureId,
      },
      if (type == 'recipe') ...{
        'recipe_id': sourceId,
        'recipe_portion_count': decimal,
      },
      if (type == 'manual_unresolved') 'manual_name': manual.text.trim(),
      'client_operation_id': consumptionOperationId(),
    };
    final preview = await repository.previewEntry(
      day!['id'].toString(),
      payload,
    );
    if (!mounted || !await _confirmPreview(preview)) return;
    await repository.addEntry(day!['id'].toString(), payload);
    await _load();
  }

  Future<void> _simpleOutcome(Map<String, dynamic> item, String outcome) async {
    if (outcome != 'consumed_as_planned' && outcome != 'skipped') {
      final sourceMealId = item['meal_id']?.toString();
      final meals = (day!['meals'] as List).whereType<Map>();
      final meal =
          meals
              .cast<Map>()
              .where(
                (candidate) =>
                    candidate['source_plan_meal_id']?.toString() ==
                    sourceMealId,
              )
              .firstOrNull ??
          meals.firstOrNull;
      if (meal == null) {
        _message(
          'Bitte lege zuerst eine Mahlzeit für den tatsächlichen Eintrag an.',
        );
        return;
      }
      final actualEntries = <Map<String, dynamic>>[];
      do {
        final actual = await _actualEntryForOutcome(
          Map<String, dynamic>.from(meal),
          replacement: outcome == 'replaced',
        );
        if (actual == null) return;
        actualEntries.add(actual);
        if (outcome != 'replaced') break;
        if (!mounted) return;
        final another =
            await showDialog<bool>(
              context: context,
              builder: (context) => AlertDialog(
                title: const Text('Weiteren Ersatz hinzufügen?'),
                content: const Text(
                  'Ein ersetzter Planeintrag kann aus mehreren tatsächlich konsumierten Lebensmitteln oder Rezepten bestehen.',
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: const Text('Nein'),
                  ),
                  FilledButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: const Text('Weiteren hinzufügen'),
                  ),
                ],
              ),
            ) ??
            false;
        if (!another) break;
      } while (true);
      await repository.outcome(day!['id'].toString(), item['id'].toString(), {
        'outcome_type': outcome,
        'actual_entries': actualEntries,
        'client_operation_id': consumptionOperationId(),
        'expected_day_version': day!['version'],
      });
      await _load();
      return;
    }
    await repository.outcome(day!['id'].toString(), item['id'].toString(), {
      'outcome_type': outcome,
      'client_operation_id': consumptionOperationId(),
      'expected_day_version': day!['version'],
    });
    await _load();
  }

  Future<void> _confirmWholeMeal(String planMealId) async {
    final entries = (day!['planned_entries'] as List)
        .whereType<Map>()
        .where(
          (item) =>
              item['meal_id'].toString() == planMealId &&
              item['status'] == 'pending',
        )
        .toList();
    final confirmed =
        await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Gesamte Mahlzeit wie geplant übernehmen?'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Für jeden folgenden Planeintrag wird ein tatsächlicher historischer Verzehreintrag angelegt:',
                  ),
                  const SizedBox(height: 8),
                  for (final item in entries) ...[
                    Text(
                      '• ${item['display_name']} – ${_plannedAmount(item).replaceFirst('Geplant: ', '')}',
                    ),
                    if (item['source_archived'] == true)
                      const Text(
                        '  Archivierte Quelle: Übernahme nutzt den historischen Planstand.',
                      ),
                    if (item['source_unavailable'] == true)
                      const Text(
                        '  Quelle nicht mehr verfügbar; bitte einzeln prüfen.',
                      ),
                    Text(
                      '  Ergebnis: ${_plannedNutrient(item, 'energy_kcal')}',
                    ),
                  ],
                  const SizedBox(height: 8),
                  const Text(
                    'Für jeden bestätigten Eintrag wird ein unveränderlicher historischer Nährwert-Snapshot angelegt.',
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Abbrechen'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Ausdrücklich bestätigen'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed) return;
    await repository.confirmWholeMeal(day!['id'].toString(), planMealId, {
      'client_operation_id': consumptionOperationId(),
      'expected_day_version': day!['version'],
    });
    await _load();
  }

  Future<Map<String, dynamic>?> _actualEntryForOutcome(
    Map<String, dynamic> meal, {
    required bool replacement,
  }) async {
    final foods = await ref.read(foodRepositoryProvider).list();
    final recipes = await ref.read(recipeRepositoryProvider).list();
    if (!mounted) return null;
    String type = 'food';
    String? sourceId = foods.firstOrNull?.id;
    String unit = foods.firstOrNull?.referenceUnit ?? 'g';
    final quantity = TextEditingController(text: '1');
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(
            replacement
                ? 'Tatsächlichen Ersatz erfassen'
                : 'Tatsächliche Menge',
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: type,
                decoration: const InputDecoration(labelText: 'Quelle'),
                items: const [
                  DropdownMenuItem(value: 'food', child: Text('Lebensmittel')),
                  DropdownMenuItem(
                    value: 'recipe',
                    child: Text('Rezept/Gericht'),
                  ),
                ],
                onChanged: (value) => setDialogState(() {
                  type = value!;
                  sourceId = type == 'food'
                      ? foods.firstOrNull?.id
                      : recipes.firstOrNull?.id;
                  unit = foods.firstOrNull?.referenceUnit ?? 'g';
                }),
              ),
              DropdownButtonFormField<String>(
                initialValue: sourceId,
                decoration: const InputDecoration(
                  labelText: 'Tatsächlich konsumiert',
                ),
                items: type == 'food'
                    ? foods
                          .map(
                            (source) => DropdownMenuItem(
                              value: source.id,
                              child: Text(
                                source.name,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList()
                    : recipes
                          .map(
                            (source) => DropdownMenuItem(
                              value: source.id,
                              child: Text(
                                source.name,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList(),
                onChanged: (value) {
                  sourceId = value;
                  final food = foods
                      .where((item) => item.id == value)
                      .firstOrNull;
                  if (food != null) unit = food.referenceUnit;
                },
              ),
              TextField(
                controller: quantity,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: InputDecoration(
                  labelText: type == 'food'
                      ? 'Tatsächliche Menge in g'
                      : 'Tatsächliche Portionen',
                  helperText: 'Komma und Punkt werden akzeptiert.',
                ),
              ),
              if (type == 'food')
                DropdownButtonFormField<String>(
                  initialValue: unit,
                  decoration: const InputDecoration(labelText: 'Einheit'),
                  items: (unit == 'ml' ? const ['ml', 'l'] : const ['g', 'kg'])
                      .map(
                        (value) =>
                            DropdownMenuItem(value: value, child: Text(value)),
                      )
                      .toList(),
                  onChanged: (value) => unit = value!,
                ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: sourceId == null
                  ? null
                  : () => Navigator.pop(context, true),
              child: const Text('Übernehmen'),
            ),
          ],
        ),
      ),
    );
    if (accepted != true || sourceId == null) return null;
    final decimal = quantity.text.trim().replaceAll(',', '.');
    final payload = <String, dynamic>{
      'meal_id': meal['id'],
      'entry_type': type,
      'origin_type': replacement ? 'replacement' : 'planned',
      if (type == 'food') ...{
        'food_id': sourceId,
        'entered_quantity': decimal,
        'entered_unit_code': unit,
      } else ...{
        'recipe_id': sourceId,
        'recipe_portion_count': decimal,
      },
      'client_operation_id': consumptionOperationId(),
    };
    final preview = await repository.previewEntry(
      day!['id'].toString(),
      payload,
    );
    if (!mounted || !await _confirmPreview(preview)) return null;
    return payload;
  }

  Future<void> _finalize() async {
    String? choice;
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text(
            'Sind alle relevanten Speisen und Getränke erfasst?',
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                key: const Key('consumption-completeness-choice'),
                initialValue: choice,
                decoration: const InputDecoration(labelText: 'Vollständigkeit'),
                items: const [
                  DropdownMenuItem(
                    value: 'complete_to_best_knowledge',
                    child: Text('Nach bestem Wissen vollständig'),
                  ),
                  DropdownMenuItem(
                    value: 'partial',
                    child: Text('Nur teilweise'),
                  ),
                  DropdownMenuItem(
                    value: 'uncertain',
                    child: Text('Vollständigkeit unklar'),
                  ),
                ],
                onChanged: (value) => setDialogState(() => choice = value),
              ),
              const Text(
                'Die Auswahl beschreibt nur deine eigene Einschätzung der Aufzeichnung.',
              ),
              const SizedBox(height: 8),
              for (final raw
                  in ((day!['summary'] as Map)['quality'] as Map)['warnings']
                      as List)
                if (raw is Map) Text('• ${raw['explanation_de']}'),
              const SizedBox(height: 8),
              const Text(
                'Verzehreinträge verändern den Vorrat nicht automatisch.',
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: choice == null
                  ? null
                  : () => Navigator.pop(context, true),
              child: const Text('Mit Hinweisen abschließen'),
            ),
          ],
        ),
      ),
    );
    if (accepted != true || choice == null) return;
    await repository.finalize(day!['id'].toString(), {
      'completeness_attestation': choice,
      'confirm_warnings': true,
      'client_operation_id': consumptionOperationId(),
      'expected_version': day!['version'],
    });
    await _load();
  }

  Future<void> _reopen() async {
    await repository.reopen(day!['id'].toString());
    await _load();
  }

  Future<void> _deleteEntry(String id) async {
    final confirmed = await _confirm('Eintrag dauerhaft löschen?');
    if (!confirmed) return;
    await repository.deleteEntry(day!['id'].toString(), id);
    await _load();
  }

  Future<void> _deleteDay() async {
    final confirmed = await _confirm(
      'Verzehrtag mit allen Einträgen und Snapshots dauerhaft löschen? Tagesplan und Vorrat bleiben erhalten.',
    );
    if (!confirmed) return;
    await repository.deleteDay(day!['id'].toString());
    await _load();
  }

  Future<bool> _confirm(String message) async =>
      await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Dauerhaft löschen'),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Löschen'),
            ),
          ],
        ),
      ) ??
      false;

  Future<void> _history() async {
    String? status;
    String? completeness;
    bool? unresolved;
    var result = await repository.history();
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setSheetState) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Verzehrverlauf',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            Wrap(
              spacing: 6,
              children: [
                FilterChip(
                  label: const Text('Offen'),
                  selected: status == 'open',
                  onSelected: (_) async {
                    status = status == 'open' ? null : 'open';
                    result = await repository.history(
                      status: status,
                      completeness: completeness,
                      unresolved: unresolved,
                    );
                    setSheetState(() {});
                  },
                ),
                FilterChip(
                  label: const Text('Finalisiert'),
                  selected: status == 'finalized',
                  onSelected: (_) async {
                    status = status == 'finalized' ? null : 'finalized';
                    result = await repository.history(
                      status: status,
                      completeness: completeness,
                      unresolved: unresolved,
                    );
                    setSheetState(() {});
                  },
                ),
                FilterChip(
                  label: const Text('Vollständig erfasst'),
                  selected: completeness == 'complete_to_best_knowledge',
                  onSelected: (_) async {
                    completeness = completeness == 'complete_to_best_knowledge'
                        ? null
                        : 'complete_to_best_knowledge';
                    result = await repository.history(
                      status: status,
                      completeness: completeness,
                      unresolved: unresolved,
                    );
                    setSheetState(() {});
                  },
                ),
                FilterChip(
                  label: const Text('Teilweise erfasst'),
                  selected: completeness == 'partial',
                  onSelected: (_) async {
                    completeness = completeness == 'partial' ? null : 'partial';
                    result = await repository.history(
                      status: status,
                      completeness: completeness,
                      unresolved: unresolved,
                    );
                    setSheetState(() {});
                  },
                ),
                FilterChip(
                  label: const Text('Mit ungeklärten Einträgen'),
                  selected: unresolved == true,
                  onSelected: (_) async {
                    unresolved = unresolved == true ? null : true;
                    result = await repository.history(
                      status: status,
                      completeness: completeness,
                      unresolved: unresolved,
                    );
                    setSheetState(() {});
                  },
                ),
              ],
            ),
            for (final raw in (result['items'] as List).whereType<Map>())
              ListTile(
                title: Text(raw['consumption_date'].toString()),
                subtitle: Text(
                  '${raw['status'] == 'finalized' ? 'Finalisiert' : 'Offen'} · '
                  '${consumptionAttestationLabel(raw['completeness_attestation']?.toString())}\n'
                  'Energie: ${_valueOrUnknown(raw['actual_energy_kcal'], 'kcal')} · '
                  '${raw['unresolved_entry_count']} ungeklärt',
                ),
                isThreeLine: true,
                onTap: () {
                  Navigator.pop(context);
                  selected = DateTime.parse(raw['consumption_date'].toString());
                  _load();
                },
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _weeklyOverview() async {
    final result = await repository.weekly(date);
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Tatsächlicher Verzehr der Woche',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          Text(
            '${result['recorded_day_count']} von 7 Tagen erfasst · ${result['finalized_day_count']} finalisiert',
          ),
          Text(
            '${result['complete_attestation_day_count']} nach eigener Einschätzung vollständig',
          ),
          Text(
            'Durchschnitt pro erfasstem Tag: ${_valueOrUnknown(result['average_energy_per_recorded_day_kcal'], 'kcal')}',
          ),
          if ((result['missing_day_count'] as num) > 0)
            const Text(
              'Fehlende Tage werden nicht als null gerechnet; der Durchschnitt ist nur auf erfasste Tage bezogen.',
            ),
          const Divider(),
          for (final indexed
              in (result['days'] as List).whereType<Map>().indexed)
            ListTile(
              leading: Text(_weekdays[indexed.$1]),
              title: Text(indexed.$2['date'].toString()),
              subtitle: Text(
                indexed.$2['recorded'] == true
                    ? '${indexed.$2['status'] == 'finalized' ? 'Finalisiert' : 'Offen'} · ${_valueOrUnknown(indexed.$2['actual_energy_kcal'], 'kcal')}'
                    : 'Keine Aufzeichnung – nicht als null gewertet',
              ),
            ),
        ],
      ),
    );
  }

  Future<bool> _confirmPreview(Map<String, dynamic> preview) async {
    final nutrients = (preview['nutrients'] as List? ?? const [])
        .whereType<Map>();
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Verzehr prüfen'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Normalisiert: ${_valueOrUnknown(preview['normalized_quantity'], preview['normalized_unit']?.toString() ?? '')}',
                  ),
                  for (final nutrient in nutrients.take(5))
                    Text(
                      '${nutrient['nutrient_code']}: ${_valueOrUnknown(nutrient['amount'], nutrient['unit'].toString())}',
                    ),
                  for (final warning
                      in (preview['warnings'] as List? ?? const []))
                    Text(
                      '• ${warning is Map ? warning['explanation_de'] ?? warning : warning}',
                    ),
                  const SizedBox(height: 8),
                  const Text(
                    'Verzehreinträge verändern den Vorrat nicht automatisch.',
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Zurück'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Speichern'),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: selected,
      firstDate: DateTime(2000),
      lastDate: DateTime.now(),
    );
    if (picked == null) return;
    selected = _dateOnly(picked);
    await _load();
  }

  Future<void> _guard(Future<void> Function() action) async {
    if (mutating) return;
    setState(() => mutating = true);
    try {
      await action();
    } catch (exception) {
      if (mounted) _message(exception.toString());
    } finally {
      if (mounted) setState(() => mutating = false);
    }
  }

  void _message(String value) => ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(value)));
}

const _mealTypes = {
  'breakfast': 'Frühstück',
  'morning_snack': 'Vormittagssnack',
  'lunch': 'Mittagessen',
  'afternoon_snack': 'Nachmittagssnack',
  'dinner': 'Abendessen',
  'evening_snack': 'Abendsnack',
  'other': 'Sonstiges',
};

const _weekdays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

List<DropdownMenuItem<String>> _foodUnitItems(
  List<FoodItem> foods,
  String? sourceId,
) {
  final food = foods.where((item) => item.id == sourceId).firstOrNull;
  final base = food?.referenceUnit ?? 'g';
  final units = base == 'ml' ? const ['ml', 'l'] : const ['g', 'kg'];
  return [
    for (final unit in units) DropdownMenuItem(value: unit, child: Text(unit)),
    for (final measure in food?.measures ?? const <FoodMeasure>[])
      DropdownMenuItem(
        value: 'measure:${measure.id}',
        child: Text(measure.name),
      ),
  ];
}

String _valueOrUnknown(dynamic value, String unit) => value == null
    ? 'unbekannt'
    : '${GermanDecimal.formatString(value)}${unit.isEmpty ? '' : ' $unit'}';

String _normalizedAmount(Map<dynamic, dynamic> entry) => _valueOrUnknown(
  entry['normalized_quantity'],
  entry['normalized_unit']?.toString() ?? '',
);

String _plannedAmount(Map<dynamic, dynamic> item) {
  if (item['entry_type'] == 'recipe') {
    return 'Geplant: ${_valueOrUnknown(item['planned_recipe_portions'], 'Portionen')}';
  }
  return 'Geplant: ${_valueOrUnknown(item['planned_quantity'], item['planned_unit']?.toString() ?? '')}';
}

String _actualOutcomeAmount(Map<dynamic, dynamic> item) {
  final outcome = item['outcome'];
  if (outcome is! Map) return 'noch nicht erfasst';
  final entries = (outcome['entries'] as List? ?? const [])
      .whereType<Map>()
      .toList();
  if (outcome['outcome_type'] == 'skipped') return 'übersprungen';
  if (entries.isEmpty) return 'nicht verfügbar';
  return entries.map(_entryAmount).join(' + ');
}

String _plannedNutrient(Map<dynamic, dynamic> item, String code) {
  final nutrient = (item['planned_nutrients'] as List? ?? const [])
      .whereType<Map>()
      .where((value) => value['nutrient_code'] == code)
      .firstOrNull;
  return nutrient == null
      ? 'Nährwert unbekannt'
      : _valueOrUnknown(nutrient['amount'], nutrient['unit'].toString());
}

String _dateTimeLabel(dynamic raw) {
  final value = DateTime.tryParse(raw.toString())?.toLocal();
  if (value == null) return raw.toString();
  return '${value.day}.${value.month}.${value.year}, '
      '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')} Uhr';
}

String _entryAmount(Map<dynamic, dynamic> item) {
  if (item['entry_type'] == 'manual_unresolved') {
    return 'Ohne Nährwertberechnung erfasst';
  }
  if (item['entry_type'] == 'recipe') {
    return '${GermanDecimal.formatString(item['recipe_portion_count'])} Portionen';
  }
  return '${GermanDecimal.formatString(item['entered_quantity'])} ${item['entered_unit_code'] ?? ''}';
}

String consumptionAttestationLabel(String? value) => switch (value) {
  'complete_to_best_knowledge' => 'Nach bestem Wissen vollständig erfasst',
  'partial' => 'Nur teilweise erfasst',
  'uncertain' => 'Vollständigkeit unklar',
  _ => 'Vollständigkeit noch nicht erklärt',
};

String consumptionOutcomeLabel(String value) => switch (value) {
  'consumed_as_planned' => 'Als konsumiert erfasst',
  'consumed_modified' => 'Tatsächliche Menge angepasst',
  'partially_consumed' => 'Teilweise konsumiert',
  'skipped' => 'Übersprungen',
  'replaced' => 'Ersetzt',
  _ => 'Offen',
};

DateTime _dateOnly(DateTime value) =>
    DateTime(value.year, value.month, value.day);
String _iso(DateTime value) =>
    '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

String consumptionOperationId() {
  final random = Random.secure();
  final bytes = List<int>.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final hex = bytes
      .map((value) => value.toRadixString(16).padLeft(2, '0'))
      .join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-'
      '${hex.substring(16, 20)}-${hex.substring(20)}';
}
