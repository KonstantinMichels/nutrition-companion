import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../foods/food_models.dart';
import 'consumption_repository.dart';
import 'pantry_reconciliation_repository.dart';

final class PantryReconciliationScreen extends ConsumerStatefulWidget {
  const PantryReconciliationScreen({
    required this.dayId,
    this.entryId,
    super.key,
  });
  final String dayId;
  final String? entryId;

  @override
  ConsumerState<PantryReconciliationScreen> createState() =>
      _PantryReconciliationScreenState();
}

final class _PantryReconciliationScreenState
    extends ConsumerState<PantryReconciliationScreen> {
  bool loading = true;
  bool working = false;
  String? error;
  Map<String, dynamic>? day;
  Map<String, dynamic>? preview;
  Map<String, dynamic>? result;
  final Map<String, String> contexts = {};
  final Map<String, String> quantities = {};
  final Map<String, String> ingredientContexts = {};
  final Set<String> optionalIncluded = {};
  final Set<String> pastUseByConfirmed = {};
  final Map<String, Map<String, String>> lotQuantities = {};
  final Map<String, String> mappedFoods = {};
  List<FoodItem> foods = const [];
  String applyMode = 'all_or_nothing';
  bool previewDirty = false;

  ConsumptionRepository get consumption =>
      ref.read(consumptionRepositoryProvider);
  PantryReconciliationRepository get repository =>
      ref.read(pantryReconciliationRepositoryProvider);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final values = await Future.wait([
        consumption.detail(widget.dayId),
        ref.read(foodRepositoryProvider).list(),
      ]);
      final value = values[0] as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        day = value;
        foods = values[1] as List<FoodItem>;
        for (final entry in _entries(value)) {
          contexts.putIfAbsent(entry['id'].toString(), () => 'unknown');
        }
        loading = false;
      });
    } catch (exception) {
      if (mounted) {
        setState(() {
          error = exception.toString();
          loading = false;
        });
      }
    }
  }

  List<Map<String, dynamic>> _entries(
    Map<String, dynamic> value,
  ) => (value['meals'] as List? ?? const [])
      .whereType<Map>()
      .expand((meal) => (meal['entries'] as List? ?? const []).whereType<Map>())
      .map((entry) => Map<String, dynamic>.from(entry))
      .where((entry) => widget.entryId == null || entry['id'] == widget.entryId)
      .toList();

  Map<String, dynamic> _request() {
    final cachedEntries = <String, Map<String, dynamic>>{
      for (final item
          in (preview?['entries'] as List? ?? const []).whereType<Map>())
        item['consumption_entry_id'].toString(): Map<String, dynamic>.from(
          item,
        ),
    };
    return {
      'expected_day_version': day!['version'],
      'apply_mode': applyMode,
      'entries': [
        for (final entry in _entries(day!))
          {
            'consumption_entry_id': entry['id'],
            'expected_entry_version': entry['version'],
            'source_context': contexts[entry['id']] ?? 'unknown',
            if (entry['entry_type'] == 'food' &&
                {
                  'from_pantry',
                  'partially_from_pantry',
                }.contains(contexts[entry['id']]))
              'selected_pantry_quantity':
                  quantities[entry['id']] ?? entry['normalized_quantity'],
            if (entry['entry_type'] == 'food' &&
                (cachedEntries[entry['id']]?['requirements'] as List? ??
                        const [])
                    .whereType<Map>()
                    .isNotEmpty &&
                (lotQuantities[((cachedEntries[entry['id']]!['requirements']
                                    as List)
                                .whereType<Map>()
                                .first)['requirement_key']
                            .toString()] ??
                        const {})
                    .values
                    .any((value) => (double.tryParse(value) ?? 0) > 0))
              'allocations': [
                for (final lot
                    in ((((cachedEntries[entry['id']]!['requirements'] as List)
                                    .whereType<Map>()
                                    .first)['available_lots']
                                as List? ??
                            const []))
                        .whereType<Map>())
                  if ((double.tryParse(
                            lotQuantities[((cachedEntries[entry['id']]!['requirements']
                                            as List)
                                        .whereType<Map>()
                                        .first)['requirement_key']
                                    .toString()]?[lot['stock_lot_id']
                                    .toString()] ??
                                '0',
                          ) ??
                          0) >
                      0)
                    {
                      'stock_lot_id': lot['stock_lot_id'],
                      'quantity':
                          lotQuantities[((cachedEntries[entry['id']]!['requirements']
                                      as List)
                                  .whereType<Map>()
                                  .first)['requirement_key']
                              .toString()]![lot['stock_lot_id'].toString()],
                      'expected_lot_version': lot['version'],
                    },
              ],
            if (entry['entry_type'] == 'recipe')
              'requirements': [
                for (final raw
                    in (cachedEntries[entry['id']]?['requirements'] as List? ??
                            const [])
                        .whereType<Map>())
                  {
                    'recipe_ingredient_snapshot_id':
                        raw['recipe_ingredient_snapshot_id'],
                    'source_context':
                        ingredientContexts[raw['requirement_key']] ??
                        (raw['optional_ingredient'] == true
                            ? 'not_used'
                            : 'from_pantry'),
                    'selected_pantry_quantity':
                        (ingredientContexts[raw['requirement_key']] ??
                                (raw['optional_ingredient'] == true
                                    ? 'not_used'
                                    : 'from_pantry'))
                            .contains('pantry')
                        ? quantities[raw['requirement_key']] ??
                              raw['remaining_reconcilable_quantity'] ??
                              '0'
                        : '0',
                    'include_optional': optionalIncluded.contains(
                      raw['requirement_key'],
                    ),
                    if ((lotQuantities[raw['requirement_key']] ?? const {})
                        .values
                        .any((value) => (double.tryParse(value) ?? 0) > 0))
                      'allocations': [
                        for (final lot
                            in (raw['available_lots'] as List? ?? const [])
                                .whereType<Map>())
                          if ((double.tryParse(
                                    lotQuantities[raw['requirement_key']]?[lot['stock_lot_id']
                                            .toString()] ??
                                        '0',
                                  ) ??
                                  0) >
                              0)
                            {
                              'stock_lot_id': lot['stock_lot_id'],
                              'quantity':
                                  lotQuantities[raw['requirement_key']]![lot['stock_lot_id']
                                      .toString()],
                              'expected_lot_version': lot['version'],
                            },
                      ],
                  },
              ],
            if (entry['entry_type'] == 'manual_unresolved')
              'requirements': [
                if (mappedFoods[entry['id']] != null)
                  {
                    'food_id': mappedFoods[entry['id']],
                    'food_name_snapshot': foods
                        .firstWhere(
                          (food) => food.id == mappedFoods[entry['id']],
                        )
                        .name,
                    'source_context': contexts[entry['id']],
                    'selected_pantry_quantity': quantities[entry['id']] ?? '0',
                  },
              ],
          },
      ],
    };
  }

  Future<void> _createPreview() async {
    setState(() {
      working = true;
      error = null;
      result = null;
    });
    try {
      final value = await repository.preview(widget.dayId, _request());
      if (!mounted) return;
      setState(() {
        preview = value;
        previewDirty = false;
        working = false;
      });
    } catch (exception) {
      if (mounted) {
        setState(() {
          error = exception.toString();
          working = false;
        });
      }
    }
  }

  Future<void> _apply() async {
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Bestandsbewegungen bestätigen?'),
        content: Text(
          '${preview?['summary']?['movement_count'] ?? 0} Bestandsbewegungen werden erstellt. '
          'Die Verzehr- und Nährwertdaten bleiben unverändert.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Bestätigen'),
          ),
        ],
      ),
    );
    if (accepted != true) return;
    setState(() => working = true);
    try {
      final value = await repository.apply(
        widget.dayId,
        _request(),
        preview!['preview_token'].toString(),
        _uuid(),
        pastUseByConfirmed.toList(),
      );
      if (mounted) {
        setState(() {
          result = value;
          preview = null;
          working = false;
        });
      }
    } catch (exception) {
      if (mounted) {
        setState(() {
          error = exception.toString();
          working = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Mit Vorrat abgleichen',
    body: ContentWidth(
      child: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const Card(
                  child: ListTile(
                    leading: Icon(Icons.info_outline),
                    title: Text(
                      'Der Vorrat wird erst nach deiner Bestätigung verändert.',
                    ),
                    subtitle: Text(
                      'Ein Verzehreintrag beweist nicht, dass die Menge aus deinem Vorrat stammt.',
                    ),
                  ),
                ),
                if (error != null)
                  Card(
                    color: Theme.of(context).colorScheme.errorContainer,
                    child: ListTile(
                      title: Text(error!),
                      trailing: IconButton(
                        icon: const Icon(Icons.refresh),
                        onPressed: _createPreview,
                      ),
                    ),
                  ),
                if (result != null) _resultCard(),
                OutlinedButton.icon(
                  onPressed: working ? null : _showHistory,
                  icon: const Icon(Icons.history),
                  label: const Text('Abgleichsverlauf und Korrekturen'),
                ),
                if (result == null && _entries(day!).isEmpty)
                  const Card(
                    child: ListTile(
                      title: Text(
                        'Für diesen Tag gibt es keine offenen Verzehreinträge zum Vorratsabgleich.',
                      ),
                    ),
                  ),
                if (result == null)
                  for (final entry in _entries(day!)) _entryCard(entry),
                if (preview != null && result == null) _previewCard(),
                if (result == null) ...[
                  const SizedBox(height: 12),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(
                        value: 'all_or_nothing',
                        label: Text('Alles oder nichts'),
                      ),
                      ButtonSegment(
                        value: 'apply_selected_valid_items',
                        label: Text('Gültige Auswahl'),
                      ),
                    ],
                    selected: {applyMode},
                    onSelectionChanged: (value) => setState(() {
                      applyMode = value.first;
                      preview = null;
                    }),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: working || _entries(day!).isEmpty
                        ? null
                        : _createPreview,
                    icon: const Icon(Icons.inventory_2_outlined),
                    label: Text(
                      working ? 'Wird geprüft …' : 'Bestandsbewegungen prüfen',
                    ),
                  ),
                ],
              ],
            ),
    ),
  );

  Widget _entryCard(Map<String, dynamic> entry) {
    final id = entry['id'].toString();
    final isRecipe = entry['entry_type'] == 'recipe';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              entry['source_display_name_snapshot'].toString(),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(
              isRecipe
                  ? '${GermanDecimal.formatString(entry['recipe_portion_count'])} Portionen'
                  : 'Als konsumiert erfasst: ${GermanDecimal.formatString(entry['normalized_quantity'])} ${entry['normalized_unit'] ?? ''}',
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: contexts[id],
              decoration: const InputDecoration(labelText: 'Herkunft'),
              items: [
                if (isRecipe)
                  const DropdownMenuItem(
                    value: 'prepared_from_pantry_for_this_entry',
                    child: Text('Für diesen Eintrag aus Vorrat zubereitet'),
                  ),
                const DropdownMenuItem(
                  value: 'from_pantry',
                  child: Text('Aus dem Vorrat entnommen'),
                ),
                const DropdownMenuItem(
                  value: 'partially_from_pantry',
                  child: Text('Teilweise aus dem Vorrat'),
                ),
                if (isRecipe)
                  const DropdownMenuItem(
                    value: 'leftovers_already_accounted_for',
                    child: Text('Reste – bereits berücksichtigt'),
                  ),
                const DropdownMenuItem(
                  value: 'not_from_pantry',
                  child: Text('Nicht aus dem Vorrat'),
                ),
                const DropdownMenuItem(
                  value: 'already_accounted_for',
                  child: Text('Bereits anderweitig berücksichtigt'),
                ),
                const DropdownMenuItem(
                  value: 'unknown',
                  child: Text('Noch nicht abgeglichen'),
                ),
              ],
              onChanged: (value) => setState(() {
                contexts[id] = value!;
                preview = null;
              }),
            ),
            if (entry['entry_type'] == 'food' &&
                contexts[id] == 'partially_from_pantry')
              TextFormField(
                initialValue:
                    quantities[id] ?? entry['normalized_quantity']?.toString(),
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: InputDecoration(
                  labelText:
                      'Aus Vorrat entnommen (${entry['normalized_unit']})',
                ),
                onChanged: (value) {
                  quantities[id] = value.replaceAll(',', '.');
                  preview = null;
                },
              ),
            if (entry['entry_type'] == 'manual_unresolved' &&
                {
                  'from_pantry',
                  'partially_from_pantry',
                }.contains(contexts[id])) ...[
              DropdownButtonFormField<String>(
                initialValue: mappedFoods[id],
                decoration: const InputDecoration(
                  labelText: 'Lebensmittel ausdrücklich zuordnen',
                ),
                items: [
                  for (final food in foods)
                    DropdownMenuItem(value: food.id, child: Text(food.name)),
                ],
                onChanged: (value) => setState(() {
                  mappedFoods[id] = value!;
                  preview = null;
                }),
              ),
              TextFormField(
                initialValue: quantities[id],
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: InputDecoration(
                  labelText: mappedFoods[id] == null
                      ? 'Zuzuordnende Menge'
                      : 'Zuzuordnende Menge (${foods.firstWhere((food) => food.id == mappedFoods[id]).referenceUnit})',
                ),
                onChanged: (value) {
                  quantities[id] = value.replaceAll(',', '.');
                  preview = null;
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _previewCard() {
    final entries = (preview!['entries'] as List).whereType<Map>();
    final warnings = (preview!['warnings'] as List? ?? const [])
        .whereType<Map>();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Vorschau', style: Theme.of(context).textTheme.titleLarge),
            for (final entry in entries)
              for (final raw
                  in (entry['requirements'] as List).whereType<Map>())
                _requirementTile(Map<String, dynamic>.from(raw)),
            for (final warning in warnings)
              ListTile(
                leading: const Icon(Icons.warning_amber_outlined),
                title: Text(warning['explanation_de'].toString()),
              ),
            FilledButton(
              onPressed:
                  working ||
                      previewDirty ||
                      preview!['summary']['movement_count'] == 0
                  ? null
                  : _apply,
              child: const Text('Bestandsbewegungen bestätigen'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _requirementTile(Map<String, dynamic> item) {
    final key = item['requirement_key'].toString();
    final pastUseBy = (item['allocations'] as List).whereType<Map>().where(
      (a) => a['date_status'] == 'past_use_by',
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Divider(),
        Text(
          item['food_name'].toString(),
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        Text(
          'Theoretisch/erfasst: ${GermanDecimal.formatString(item['theoretical_required_quantity'])} ${item['canonical_unit'] ?? ''}',
        ),
        Text(
          'Bereits abgebucht: ${GermanDecimal.formatString(item['previously_reconciled_quantity'])} ${item['canonical_unit'] ?? ''}',
        ),
        Text(
          'Noch abgleichbar: ${GermanDecimal.formatString(item['remaining_reconcilable_quantity'])} ${item['canonical_unit'] ?? ''}',
        ),
        Text(
          'Verfügbar: ${GermanDecimal.formatString(item['pantry_available_quantity'])} ${item['canonical_unit'] ?? ''}',
        ),
        if (item['recipe_ingredient_snapshot_id'] != null)
          DropdownButtonFormField<String>(
            initialValue:
                ingredientContexts[key] ??
                (item['optional_ingredient'] == true
                    ? 'not_used'
                    : 'from_pantry'),
            decoration: const InputDecoration(labelText: 'Zutatenentscheidung'),
            items: const [
              DropdownMenuItem(
                value: 'from_pantry',
                child: Text('Aus dem Vorrat'),
              ),
              DropdownMenuItem(
                value: 'partially_from_pantry',
                child: Text('Teilweise aus dem Vorrat'),
              ),
              DropdownMenuItem(
                value: 'not_from_pantry',
                child: Text('Nicht aus dem Vorrat'),
              ),
              DropdownMenuItem(
                value: 'already_accounted_for',
                child: Text('Bereits berücksichtigt'),
              ),
              DropdownMenuItem(
                value: 'not_used',
                child: Text('Nicht verwendet'),
              ),
              DropdownMenuItem(
                value: 'unresolved',
                child: Text('Noch ungeklärt'),
              ),
            ],
            onChanged: (value) => setState(() {
              ingredientContexts[key] = value!;
              previewDirty = true;
            }),
          ),
        if ((ingredientContexts[key] ?? 'from_pantry').contains('pantry'))
          TextFormField(
            initialValue:
                quantities[key] ??
                item['remaining_reconcilable_quantity']?.toString(),
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText:
                  'Aus Vorrat entnommen (${item['canonical_unit'] ?? ''})',
            ),
            onChanged: (value) {
              quantities[key] = value.replaceAll(',', '.');
              setState(() => previewDirty = true);
            },
          ),
        if (item['optional_ingredient'] == true)
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: optionalIncluded.contains(key),
            title: const Text('Optionale Zutat einbeziehen'),
            onChanged: (value) => setState(() {
              value ? optionalIncluded.add(key) : optionalIncluded.remove(key);
              previewDirty = true;
            }),
          ),
        for (final lot in (item['allocations'] as List).whereType<Map>())
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.inventory_2_outlined),
            title: Text(
              '${lot['location_name']} · ${GermanDecimal.formatString(lot['allocated_quantity'])} ${lot['canonical_unit']}',
            ),
            subtitle: Text(_dateStatus(lot['date_status']?.toString())),
          ),
        ExpansionTile(
          tilePadding: EdgeInsets.zero,
          title: const Text('Chargen manuell auswählen oder aufteilen'),
          subtitle: const Text(
            'Ohne Eingabe gilt der deterministische Vorschlag oben.',
          ),
          children: [
            for (final lot
                in (item['available_lots'] as List? ?? const [])
                    .whereType<Map>())
              TextFormField(
                initialValue:
                    lotQuantities[key]?[lot['stock_lot_id'].toString()] ?? '',
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: InputDecoration(
                  labelText:
                      '${lot['location_name']} · verfügbar ${GermanDecimal.formatString(lot['available_quantity'])} ${lot['canonical_unit']}',
                  helperText: _dateStatus(lot['date_status']?.toString()),
                ),
                onChanged: (value) {
                  lotQuantities.putIfAbsent(key, () => {})[lot['stock_lot_id']
                      .toString()] = value.replaceAll(
                    ',',
                    '.',
                  );
                  setState(() => previewDirty = true);
                },
              ),
          ],
        ),
        for (final lot in pastUseBy)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: pastUseByConfirmed.contains(lot['stock_lot_id']),
            onChanged: (value) => setState(() {
              value == true
                  ? pastUseByConfirmed.add(lot['stock_lot_id'].toString())
                  : pastUseByConfirmed.remove(lot['stock_lot_id'].toString());
            }),
            title: const Text(
              'Charge mit überschrittenem Verbrauchsdatum trotzdem auswählen',
            ),
            subtitle: const Text(
              'Daraus folgt keine Aussage zur Lebensmittelsicherheit.',
            ),
          ),
        if ((double.tryParse(item['uncovered_quantity']?.toString() ?? '0') ??
                0) >
            0)
          Text(
            'Nicht gedeckt: ${GermanDecimal.formatString(item['uncovered_quantity'])} ${item['canonical_unit'] ?? ''}',
          ),
        if (previewDirty)
          OutlinedButton(
            onPressed: working ? null : _createPreview,
            child: const Text('Vorschau mit Änderungen aktualisieren'),
          ),
      ],
    );
  }

  Widget _resultCard() => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Icon(Icons.check_circle_outline, size: 48),
          Text(
            'Bestandsbewegungen erstellt',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          for (final requirement
              in (result!['requirements'] as List).whereType<Map>())
            for (final allocation
                in (requirement['allocations'] as List).whereType<Map>())
              ListTile(
                title: Text(
                  '${requirement['food_name']} · ${GermanDecimal.formatString(allocation['allocated_quantity'])} ${allocation['canonical_unit']}',
                ),
                subtitle: Text(
                  '${allocation['location_name']} · verbleibend ${GermanDecimal.formatString(allocation['lot_available_after'])} ${allocation['canonical_unit']}',
                ),
              ),
        ],
      ),
    ),
  );

  Future<void> _showHistory() async {
    setState(() => working = true);
    try {
      final value = await repository.history(dayId: widget.dayId);
      if (!mounted) return;
      setState(() => working = false);
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (context) => DraggableScrollableSheet(
          expand: false,
          initialChildSize: .75,
          builder: (context, controller) => ListView(
            controller: controller,
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                'Abgleichsverlauf',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Text(
                'Originalbewegungen bleiben auch nach einer Korrektur nachvollziehbar.',
              ),
              for (final raw
                  in (value['items'] as List? ?? const []).whereType<Map>())
                _historyBatch(Map<String, dynamic>.from(raw), context),
            ],
          ),
        ),
      );
    } catch (exception) {
      if (mounted) {
        setState(() {
          working = false;
          error = exception.toString();
        });
      }
    }
  }

  Widget _historyBatch(
    Map<String, dynamic> batch,
    BuildContext sheetContext,
  ) => Card(
    child: ExpansionTile(
      title: Text('Abgleich ${batch['consumption_day_date']}'),
      subtitle: Text('Status: ${batch['status']}'),
      children: [
        for (final requirement
            in (batch['requirements'] as List? ?? const []).whereType<Map>())
          for (final allocation
              in (requirement['allocations'] as List? ?? const [])
                  .whereType<Map>())
            ListTile(
              title: Text(
                '${requirement['food_name']} · ${GermanDecimal.formatString(allocation['active_quantity'])} ${allocation['canonical_unit']} aktiv',
              ),
              subtitle: Text(allocation['location_name'].toString()),
              trailing:
                  (double.tryParse(allocation['active_quantity'].toString()) ??
                          0) >
                      0
                  ? IconButton(
                      tooltip: 'Ganz oder teilweise zurückbuchen',
                      icon: const Icon(Icons.undo),
                      onPressed: () async {
                        Navigator.pop(sheetContext);
                        await _reverseAllocation(batch, allocation);
                      },
                    )
                  : null,
            ),
      ],
    ),
  );

  Future<void> _reverseAllocation(Map batch, Map allocation) async {
    final controller = TextEditingController(
      text: allocation['active_quantity'].toString(),
    );
    final quantity = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Gegenbewegung erstellen'),
        content: TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: 'Menge (${allocation['canonical_unit']})',
            helperText:
                'Maximal ${GermanDecimal.formatString(allocation['active_quantity'])}',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () =>
                Navigator.pop(context, controller.text.replaceAll(',', '.')),
            child: const Text('Prüfen'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (quantity == null) return;
    final request = {
      'reason': 'wrong_quantity',
      'note': 'Manuelle Korrektur in der App',
      'selections': [
        {'allocation_id': allocation['id'], 'quantity': quantity},
      ],
    };
    setState(() => working = true);
    try {
      final checked = await repository.reversalPreview(
        batch['id'].toString(),
        request,
      );
      if (!mounted) return;
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Gegenbewegung bestätigen?'),
          content: const Text(
            'Der ursprüngliche Abzug bleibt erhalten; die Menge wird über eine neue Gegenbewegung zurückgebucht.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Zurückbuchen'),
            ),
          ],
        ),
      );
      if (confirmed == true) {
        await repository.reverse(
          batch['id'].toString(),
          request,
          checked['preview_token'].toString(),
          _uuid(),
        );
      }
      if (mounted) setState(() => working = false);
    } catch (exception) {
      if (mounted) {
        setState(() {
          working = false;
          error = exception.toString();
        });
      }
    }
  }
}

String _dateStatus(String? value) => switch (value) {
  'valid' => 'Datum gültig',
  'expiring_soon' => 'Datum bald erreicht',
  'date_today' => 'Datum heute',
  'past_best_before' => 'Mindesthaltbarkeitsdatum überschritten',
  'past_use_by' => 'Verbrauchsdatum überschritten',
  _ => 'Kein Datum',
};

String _uuid() {
  final random = Random.secure();
  final bytes = List<int>.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  String hex(int value) => value.toRadixString(16).padLeft(2, '0');
  final value = bytes.map(hex).join();
  return '${value.substring(0, 8)}-${value.substring(8, 12)}-${value.substring(12, 16)}-${value.substring(16, 20)}-${value.substring(20)}';
}
