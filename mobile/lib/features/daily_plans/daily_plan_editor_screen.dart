import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../foods/food_models.dart';
import '../recipes/recipe_comparison_models.dart';
import '../recipes/recipe_models.dart';
import 'daily_plan_models.dart';

final class DailyPlanEditorScreen extends ConsumerStatefulWidget {
  const DailyPlanEditorScreen({
    this.id,
    required this.date,
    this.returnToWeeklyPlan = false,
    super.key,
  });
  final String? id;
  final DateTime date;
  final bool returnToWeeklyPlan;
  @override
  ConsumerState<DailyPlanEditorScreen> createState() =>
      _DailyPlanEditorScreenState();
}

final class _DailyPlanEditorScreenState
    extends ConsumerState<DailyPlanEditorScreen> {
  final name = TextEditingController();
  final notes = TextEditingController();
  final meals = <Map<String, dynamic>>[];
  List<ComparableAssessmentItem> assessments = [];
  String? assessmentId;
  DailyPlan? preview;
  bool loading = true, saving = false, previewing = false, dirty = false;
  String? error, draftNotice;

  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  @override
  void dispose() {
    name.dispose();
    notes.dispose();
    super.dispose();
  }

  Future<void> load() async {
    try {
      final comparable = await ref
          .read(recipeComparisonRepositoryProvider)
          .assessments();
      assessments = comparable.items.where((item) => item.usable).toList();
      assessmentId = comparable.latestId;
      if (widget.id != null) {
        final plan = await ref
            .read(dailyPlanRepositoryProvider)
            .detail(widget.id!);
        _fromPlan(plan);
      } else {
        final draft = await ref
            .read(dailyPlanDraftRepositoryProvider)
            .read(apiDate(widget.date));
        if (draft != null) {
          _fromPayload(draft);
          draftNotice = 'Verschlüsselter Entwurf wiederhergestellt';
        }
      }
    } on AppException catch (exception) {
      error = exception.message;
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void _fromPlan(DailyPlan plan) {
    name.text = plan.name ?? '';
    notes.text = plan.notes ?? '';
    assessmentId = plan.assessmentId;
    meals
      ..clear()
      ..addAll(
        plan.meals.map((meal) => Map<String, dynamic>.from(meal.toPayload())),
      );
    preview = plan;
  }

  void _fromPayload(Map<String, dynamic> payload) {
    name.text = payload['name']?.toString() ?? '';
    notes.text = payload['notes']?.toString() ?? '';
    assessmentId = payload['assessment_id']?.toString();
    meals
      ..clear()
      ..addAll(
        (payload['meals'] as List? ?? const []).whereType<Map>().map(
          (item) => Map<String, dynamic>.from(item)
            ..['entries'] = (item['entries'] as List? ?? const [])
                .whereType<Map>()
                .map((entry) => Map<String, dynamic>.from(entry))
                .toList(),
        ),
      );
  }

  Map<String, dynamic> get payload => {
    'plan_date': apiDate(widget.date),
    'assessment_id': assessmentId,
    'use_latest_assessment': false,
    'name': name.text.trim().isEmpty ? null : name.text.trim(),
    'notes': notes.text.trim().isEmpty ? null : notes.text.trim(),
    'meals': meals,
  };

  Future<void> changed([VoidCallback? mutation]) async {
    setState(() {
      mutation?.call();
      dirty = true;
      preview = null;
    });
    await ref
        .read(dailyPlanDraftRepositoryProvider)
        .write(apiDate(widget.date), payload);
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: widget.id == null ? 'Tagesplan erstellen' : 'Tagesplan bearbeiten',
    showNavigation: false,
    onBackPressed: _leave,
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : error != null
        ? Center(child: Text(error!))
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (draftNotice != null)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.lock_outline),
                    title: Text(draftNotice!),
                  ),
                ),
              Text(
                'Planinformation',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.calendar_today_outlined),
                title: Text(DateFormatters.date(widget.date)),
                subtitle: const Text('Lokales Kalenderdatum'),
              ),
              DropdownButtonFormField<String?>(
                initialValue: assessmentId,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Assessment für Tagesziele',
                ),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('Ohne persönlichen Vergleich'),
                  ),
                  ...assessments.map(
                    (item) => DropdownMenuItem<String?>(
                      value: item.id,
                      child: Text(
                        '${DateFormatters.date(item.calculatedAt)}${item.energyTarget == null ? '' : ' · ${item.energyTarget}'}',
                      ),
                    ),
                  ),
                ],
                onChanged: (value) => changed(() => assessmentId = value),
              ),
              _assessmentCard(),
              TextField(
                controller: name,
                decoration: const InputDecoration(labelText: 'Name (optional)'),
                onChanged: (_) => changed(),
              ),
              TextField(
                controller: notes,
                decoration: const InputDecoration(
                  labelText: 'Notizen (optional)',
                ),
                maxLines: 2,
                onChanged: (_) => changed(),
              ),
              const Divider(height: 32),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Geplante Mahlzeiten',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  IconButton(
                    onPressed: addMeal,
                    tooltip: 'Mahlzeit hinzufügen',
                    icon: const Icon(Icons.add_circle_outline),
                  ),
                ],
              ),
              if (meals.isEmpty)
                const Card(
                  child: ListTile(
                    title: Text('Noch keine Mahlzeit'),
                    subtitle: Text(
                      'Ein leerer Tagesplan kann gespeichert und später ergänzt werden.',
                    ),
                  ),
                ),
              for (var index = 0; index < meals.length; index++)
                _mealCard(index),
              OutlinedButton.icon(
                onPressed: addMeal,
                icon: const Icon(Icons.add),
                label: const Text('Mahlzeit hinzufügen'),
              ),
              const Divider(height: 32),
              FilledButton.tonalIcon(
                key: const Key('daily-preview'),
                onPressed: previewing ? null : refreshPreview,
                icon: previewing
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.calculate_outlined),
                label: Text(
                  previewing
                      ? 'Vorschau wird berechnet …'
                      : 'Tagesbilanz aktualisieren',
                ),
              ),
              if (preview != null) _preview(preview!),
              const SizedBox(height: 16),
              FilledButton(
                key: const Key('save-daily-plan'),
                onPressed: saving ? null : save,
                child: Text(
                  saving ? 'Wird gespeichert …' : 'Tagesplan speichern',
                ),
              ),
              TextButton(
                onPressed: _deleteDraft,
                child: const Text('Lokalen Entwurf löschen'),
              ),
            ],
          ),
  );

  Widget _mealCard(int index) {
    final meal = meals[index];
    final entries = meal['entries'] as List<Map<String, dynamic>>;
    return Card(
      key: ObjectKey(meal),
      child: ExpansionTile(
        initiallyExpanded: true,
        title: Text(
          (meal['custom_name']?.toString().trim().isNotEmpty ?? false)
              ? meal['custom_name'].toString()
              : _mealLabel(meal['meal_type'].toString()),
        ),
        subtitle: Text(
          '${meal['planned_time'] == null ? '' : '${meal['planned_time']} Uhr · '}${entries.length} Einträge',
        ),
        trailing: PopupMenuButton<String>(
          onSelected: (action) {
            if (action == 'edit') editMeal(index);
            if (action == 'delete') deleteMeal(index);
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'edit', child: Text('Mahlzeit bearbeiten')),
            PopupMenuItem(value: 'delete', child: Text('Mahlzeit löschen')),
          ],
        ),
        children: [
          for (var entryIndex = 0; entryIndex < entries.length; entryIndex++)
            ListTile(
              key: ObjectKey(entries[entryIndex]),
              onTap: () => editEntry(index, entryIndex),
              leading: Icon(
                entries[entryIndex]['entry_type'] == 'recipe'
                    ? Icons.menu_book_outlined
                    : Icons.restaurant_outlined,
              ),
              title: Text(
                entries[entryIndex]['source_name']?.toString() ?? 'Eintrag',
              ),
              subtitle: Text(
                entries[entryIndex]['entry_type'] == 'recipe'
                    ? '${GermanDecimal.formatString(entries[entryIndex]['recipe_portion_count'])} Portionen'
                    : '${GermanDecimal.formatString(entries[entryIndex]['food_quantity'])} ${entries[entryIndex]['unit_label'] ?? entries[entryIndex]['food_unit_code']}',
              ),
              trailing: PopupMenuButton<String>(
                tooltip: 'Eintrag-Aktionen',
                onSelected: (action) {
                  if (action == 'edit') editEntry(index, entryIndex);
                  if (action == 'up') {
                    changed(
                      () => entries.insert(
                        entryIndex - 1,
                        entries.removeAt(entryIndex),
                      ),
                    );
                  }
                  if (action == 'down') {
                    changed(
                      () => entries.insert(
                        entryIndex + 1,
                        entries.removeAt(entryIndex),
                      ),
                    );
                  }
                  if (action == 'remove') removeEntry(index, entryIndex);
                },
                itemBuilder: (_) => [
                  const PopupMenuItem(value: 'edit', child: Text('Bearbeiten')),
                  PopupMenuItem(
                    value: 'up',
                    enabled: entryIndex > 0,
                    child: const Text('Nach oben'),
                  ),
                  PopupMenuItem(
                    value: 'down',
                    enabled: entryIndex < entries.length - 1,
                    child: const Text('Nach unten'),
                  ),
                  const PopupMenuItem(
                    value: 'remove',
                    child: Text('Entfernen'),
                  ),
                ],
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: () => addRecipe(index),
                  icon: const Icon(Icons.menu_book_outlined),
                  label: const Text('Rezept hinzufügen'),
                ),
                OutlinedButton.icon(
                  onPressed: () => addFood(index),
                  icon: const Icon(Icons.restaurant_outlined),
                  label: const Text('Lebensmittel hinzufügen'),
                ),
                IconButton(
                  onPressed: index == 0
                      ? null
                      : () => changed(
                          () => meals.insert(index - 1, meals.removeAt(index)),
                        ),
                  tooltip: 'Mahlzeit nach oben',
                  icon: const Icon(Icons.arrow_upward),
                ),
                IconButton(
                  onPressed: index == meals.length - 1
                      ? null
                      : () => changed(
                          () => meals.insert(index + 1, meals.removeAt(index)),
                        ),
                  tooltip: 'Mahlzeit nach unten',
                  icon: const Icon(Icons.arrow_downward),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> addMeal() async {
    final value = await _mealDialog(null);
    if (value != null) await changed(() => meals.add(value));
  }

  Future<void> editMeal(int index) async {
    final value = await _mealDialog(meals[index]);
    if (value != null) await changed(() => meals[index] = value);
  }

  Future<Map<String, dynamic>?> _mealDialog(
    Map<String, dynamic>? current,
  ) async {
    var type = current?['meal_type']?.toString() ?? 'breakfast';
    var custom = current?['custom_name']?.toString() ?? '';
    TimeOfDay? time;
    final currentTime = current?['planned_time']?.toString();
    if (currentTime != null) {
      final parts = currentTime.split(':');
      time = TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
    }
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(
            current == null ? 'Mahlzeit hinzufügen' : 'Mahlzeit bearbeiten',
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: type,
                  decoration: const InputDecoration(labelText: 'Mahlzeitentyp'),
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
                TextFormField(
                  initialValue: custom,
                  onChanged: (value) => custom = value,
                  decoration: const InputDecoration(
                    labelText: 'Eigener Name (optional)',
                  ),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(
                    time == null
                        ? 'Keine geplante Uhrzeit'
                        : '${time!.format(context)} Uhr',
                  ),
                  trailing: const Icon(Icons.schedule),
                  onTap: () async {
                    final selected = await showTimePicker(
                      context: dialog,
                      initialTime: time ?? const TimeOfDay(hour: 12, minute: 0),
                    );
                    if (selected != null) setDialogState(() => time = selected);
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialog),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialog, {
                'meal_type': type,
                'custom_name': custom.trim().isEmpty ? null : custom.trim(),
                'planned_time': time == null
                    ? null
                    : '${time!.hour.toString().padLeft(2, '0')}:${time!.minute.toString().padLeft(2, '0')}',
                'notes': current?['notes'],
                'entries': current?['entries'] ?? <Map<String, dynamic>>[],
              }),
              child: const Text('Übernehmen'),
            ),
          ],
        ),
      ),
    );
    return result;
  }

  Future<void> deleteMeal(int index) async {
    final entries = meals[index]['entries'] as List;
    if (entries.isNotEmpty &&
        !await _confirm(
          'Mahlzeit löschen?',
          'Auch alle enthaltenen Einträge werden aus dem Entwurf entfernt.',
        )) {
      return;
    }
    await changed(() => meals.removeAt(index));
  }

  Future<void> removeEntry(int mealIndex, int entryIndex) async {
    if (!await _confirm(
      'Eintrag entfernen?',
      'Der Eintrag wird aus dieser geplanten Mahlzeit entfernt.',
    )) {
      return;
    }
    await changed(
      () => (meals[mealIndex]['entries'] as List).removeAt(entryIndex),
    );
  }

  Future<void> editEntry(int mealIndex, int entryIndex) async {
    final entries = meals[mealIndex]['entries'] as List<Map<String, dynamic>>;
    final entry = entries[entryIndex];
    final recipe = entry['entry_type'] == 'recipe';
    var amount = GermanDecimal.formatString(
      recipe ? entry['recipe_portion_count'] : entry['food_quantity'],
    );
    var note = entry['note']?.toString() ?? '';
    final accepted = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: Text('${entry['source_name']} bearbeiten'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              initialValue: amount,
              onChanged: (value) => amount = value,
              autofocus: true,
              decoration: InputDecoration(
                labelText: recipe ? 'Geplante Portionen' : 'Geplante Menge',
                suffixText: recipe
                    ? 'Portionen'
                    : entry['unit_label']?.toString() ??
                          entry['food_unit_code']?.toString(),
              ),
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
            ),
            TextFormField(
              initialValue: note,
              onChanged: (value) => note = value,
              decoration: const InputDecoration(labelText: 'Notiz (optional)'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialog, false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () {
              final parsed = GermanDecimal.tryParse(amount);
              if (parsed != null && parsed > 0) {
                Navigator.pop(dialog, true);
              }
            },
            child: const Text('Übernehmen'),
          ),
        ],
      ),
    );
    if (accepted == true) {
      await changed(() {
        entry[recipe ? 'recipe_portion_count' : 'food_quantity'] =
            GermanDecimal.parse(amount).toString();
        entry['note'] = note.trim().isEmpty ? null : note.trim();
      });
    }
  }

  Future<void> addRecipe(int mealIndex) async {
    final recipes = await ref.read(recipeRepositoryProvider).list();
    if (!mounted) return;
    RecipeItem? selected;
    var portion = '1';
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Rezept hinzufügen'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<RecipeItem>(
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Aktives Rezept'),
                items: recipes
                    .where((item) => !item.archived)
                    .map(
                      (item) => DropdownMenuItem(
                        value: item,
                        child: Text(item.name, overflow: TextOverflow.ellipsis),
                      ),
                    )
                    .toList(),
                onChanged: (value) => setDialogState(() => selected = value),
              ),
              TextFormField(
                initialValue: portion,
                onChanged: (value) => portion = value,
                decoration: const InputDecoration(
                  labelText: 'Geplante Portionen',
                ),
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialog),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () {
                final parsed = GermanDecimal.tryParse(portion);
                if (selected != null && parsed != null && parsed > 0) {
                  Navigator.pop(dialog, {
                    'entry_type': 'recipe',
                    'recipe_id': selected!.id,
                    'recipe_portion_count': parsed.toString(),
                    'source_name': selected!.name,
                  });
                }
              },
              child: const Text('Hinzufügen'),
            ),
          ],
        ),
      ),
    );
    if (result != null) {
      await changed(
        () => (meals[mealIndex]['entries'] as List<Map<String, dynamic>>).add(
          result,
        ),
      );
    }
  }

  Future<void> addFood(int mealIndex) async {
    final foods = await ref.read(foodRepositoryProvider).list();
    if (!mounted) return;
    FoodItem? selected;
    String? unit;
    var quantity = '100';
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (context, setDialogState) {
          final choices = selected == null
              ? <DropdownMenuItem<String>>[]
              : [
                  DropdownMenuItem(
                    value: 'base:${selected!.referenceUnit}',
                    child: Text(selected!.referenceUnit),
                  ),
                  ...selected!.measures.map(
                    (measure) => DropdownMenuItem(
                      value: 'measure:${measure.id}',
                      child: Text(measure.name),
                    ),
                  ),
                ];
          return AlertDialog(
            title: const Text('Lebensmittel hinzufügen'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<FoodItem>(
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Aktives Lebensmittel',
                    ),
                    items: foods
                        .where((item) => !item.archived)
                        .map(
                          (item) => DropdownMenuItem(
                            value: item,
                            child: Text(
                              '${item.name}${item.brand == null ? '' : ' · ${item.brand}'}',
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: (value) => setDialogState(() {
                      selected = value;
                      unit = value == null
                          ? null
                          : 'base:${value.referenceUnit}';
                    }),
                  ),
                  TextFormField(
                    initialValue: quantity,
                    onChanged: (value) => quantity = value,
                    decoration: const InputDecoration(
                      labelText: 'Geplante Menge',
                    ),
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                  ),
                  DropdownButtonFormField<String>(
                    key: ValueKey(selected?.id),
                    initialValue: unit,
                    decoration: const InputDecoration(
                      labelText: 'Einheit oder Haushaltsmaß',
                    ),
                    items: choices,
                    onChanged: (value) => setDialogState(() => unit = value),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialog),
                child: const Text('Abbrechen'),
              ),
              FilledButton(
                onPressed: () {
                  final parsed = GermanDecimal.tryParse(quantity);
                  if (selected == null ||
                      unit == null ||
                      parsed == null ||
                      parsed <= 0) {
                    return;
                  }
                  final measure = unit!.startsWith('measure:')
                      ? selected!.measures
                            .where((item) => 'measure:${item.id}' == unit)
                            .firstOrNull
                      : null;
                  Navigator.pop(dialog, {
                    'entry_type': 'food',
                    'food_id': selected!.id,
                    'food_quantity': parsed.toString(),
                    'food_unit_code':
                        measure?.unitCode ?? selected!.referenceUnit,
                    'food_measure_id': measure?.id,
                    'unit_label': measure?.name ?? selected!.referenceUnit,
                    'source_name': selected!.name,
                  });
                },
                child: const Text('Hinzufügen'),
              ),
            ],
          );
        },
      ),
    );
    if (result != null) {
      await changed(
        () => (meals[mealIndex]['entries'] as List<Map<String, dynamic>>).add(
          result,
        ),
      );
    }
  }

  Future<void> refreshPreview() async {
    setState(() => previewing = true);
    try {
      final result = await ref
          .read(dailyPlanRepositoryProvider)
          .preview(payload);
      if (mounted) setState(() => preview = result);
    } on AppException catch (exception) {
      _message(exception.message);
    } finally {
      if (mounted) setState(() => previewing = false);
    }
  }

  Widget _preview(DailyPlan value) {
    const main = ['energy_kcal', 'protein', 'carbohydrate', 'fat', 'fiber'];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Vorschau der Tagesbilanz',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            for (final item in value.nutrients.where(
              (item) => main.contains(item.code),
            ))
              Text(
                '${item.name}: ${item.amount ?? 'Nicht verfügbar'}${item.amount == null ? '' : ' ${item.unit}'}${item.complete ? '' : ' · Daten unvollständig'}',
              ),
            if (value.comparisons.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Ohne Assessment ist nur die Nährwertsumme verfügbar.',
                ),
              )
            else ...[
              const Divider(height: 24),
              Text(
                'Vergleich mit dem Assessment',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              for (final comparison in value.comparisons.where(
                (item) => main.contains(item.code),
              ))
                _comparisonPreview(comparison),
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text(
                  'Alle ${value.comparisons.length} Zielwerte anzeigen',
                ),
                children: value.comparisons
                    .where((item) => !main.contains(item.code))
                    .map(_comparisonPreview)
                    .toList(),
              ),
            ],
            if (value.warnings.isNotEmpty) Text(value.warnings.first),
          ],
        ),
      ),
    );
  }

  Widget _assessmentCard() {
    final selected = assessments
        .where((item) => item.id == assessmentId)
        .firstOrNull;
    return Card(
      color: Theme.of(context).colorScheme.secondaryContainer,
      child: ListTile(
        leading: Icon(
          assessmentId == null
              ? Icons.info_outline
              : Icons.track_changes_outlined,
        ),
        title: Text(
          assessmentId == null
              ? 'Kein persönlicher Vergleich'
              : 'Persönliche Tagesziele aktiv',
        ),
        subtitle: Text(
          selected == null
              ? 'Der Plan wird trotzdem vollständig berechnet. Ein Assessment kann jederzeit ausgewählt werden.'
              : 'Assessment vom ${DateFormatters.date(selected.calculatedAt)}${selected.energyTarget == null ? '' : '\nEnergie-Zielbereich: ${selected.energyTarget}'}',
        ),
      ),
    );
  }

  Widget _comparisonPreview(DailyComparison item) => ListTile(
    contentPadding: EdgeInsets.zero,
    leading: Icon(_comparisonIcon(item.relation)),
    title: Text(item.name),
    subtitle: Text(
      'Geplant: ${item.amount ?? 'Nicht verfügbar'}${item.amount == null ? '' : ' ${item.unit}'}\n'
      '${_targetKindLabel(item.kind)}: ${_targetText(item)}\n'
      '${item.explanation}'
      '${item.remaining == null ? '' : '\nVerbleibend: ${item.remaining} ${item.unit}${item.remainingStatus == 'exact' ? '' : ' (wegen unvollständiger Daten unsicher)'}'}',
    ),
    isThreeLine: true,
  );

  Future<void> save() async {
    if (saving) return;
    setState(() => saving = true);
    try {
      final result = await ref
          .read(dailyPlanRepositoryProvider)
          .save(payload, id: widget.id);
      await ref
          .read(dailyPlanDraftRepositoryProvider)
          .delete(apiDate(widget.date));
      dirty = false;
      if (mounted) {
        if (widget.returnToWeeklyPlan) {
          context.pop();
        } else {
          context.go('/daily-plan?date=${apiDate(result.date)}');
        }
      }
    } on AppException catch (exception) {
      _message(exception.message);
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> _deleteDraft() async {
    await ref
        .read(dailyPlanDraftRepositoryProvider)
        .delete(apiDate(widget.date));
    if (mounted) setState(() => draftNotice = null);
    _message('Der lokale Entwurf wurde gelöscht.');
  }

  Future<void> _leave() async {
    if (!dirty ||
        await _confirm(
          'Editor verlassen?',
          'Der verschlüsselte Entwurf bleibt 30 Tage gespeichert.',
        )) {
      if (mounted) {
        if (widget.returnToWeeklyPlan) {
          context.pop();
        } else {
          context.go('/daily-plan?date=${apiDate(widget.date)}');
        }
      }
    }
  }

  Future<bool> _confirm(String title, String content) async =>
      await showDialog<bool>(
        context: context,
        builder: (dialog) => AlertDialog(
          title: Text(title),
          content: Text(content),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialog, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialog, true),
              child: const Text('Bestätigen'),
            ),
          ],
        ),
      ) ??
      false;
  void _message(String value) {
    if (mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(value)));
    }
  }
}

const _mealTypes = {
  'breakfast': 'Frühstück',
  'morning_snack': 'Vormittagssnack',
  'lunch': 'Mittagessen',
  'afternoon_snack': 'Nachmittagssnack',
  'dinner': 'Abendessen',
  'evening_snack': 'Abendsnack',
  'other': 'Andere Mahlzeit',
};
String _mealLabel(String code) => _mealTypes[code] ?? 'Andere Mahlzeit';

String _targetKindLabel(String kind) => switch (kind) {
  'minimum' => 'Mindestwert',
  'maximum' => 'Tageshöchstwert',
  'range' => 'Zielbereich',
  _ => 'Referenzwert',
};

String _targetText(DailyComparison item) => switch (item.kind) {
  'range' =>
    item.targetMinimum == null || item.targetMaximum == null
        ? 'Nicht verfügbar'
        : '${item.targetMinimum} bis ${item.targetMaximum} ${item.unit}',
  'minimum' => '${item.targetMinimum ?? item.targetValue ?? '–'} ${item.unit}',
  'maximum' => '${item.targetMaximum ?? item.targetValue ?? '–'} ${item.unit}',
  _ => '${item.targetValue ?? '–'} ${item.unit}',
};

IconData _comparisonIcon(String relation) => switch (relation) {
  'above_range' || 'exceeds_limit' => Icons.warning_amber_outlined,
  'unavailable' || 'indeterminate' => Icons.help_outline,
  _ => Icons.info_outline,
};
