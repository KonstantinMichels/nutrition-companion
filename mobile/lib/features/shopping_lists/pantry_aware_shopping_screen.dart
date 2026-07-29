import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';

class PantryAwareShoppingScreen extends ConsumerStatefulWidget {
  const PantryAwareShoppingScreen({
    required this.sourceType,
    this.sourceId,
    this.weekAnchor,
    this.targetListId,
    super.key,
  });
  final String sourceType;
  final String? sourceId;
  final DateTime? weekAnchor;
  final String? targetListId;

  @override
  ConsumerState<PantryAwareShoppingScreen> createState() => _State();
}

class _State extends ConsumerState<PantryAwareShoppingScreen> {
  final portions = TextEditingController(text: '1');
  final newName = TextEditingController(text: 'Einkauf');
  late final String occurrenceId = _uuid();
  List<Map<String, dynamic>> lists = [];
  String? selectedList;
  String dateMode = 'include_all';
  bool createNew = false;
  bool otherLists = true;
  bool optionalIngredients = false;
  bool loading = true;
  bool applying = false;
  String? error;
  Map<String, dynamic>? result;
  final Set<String> acceptedDuplicates = {};
  final Map<String, dynamic> resolutions = {};
  final Set<String> excludedFoods = {};
  final Set<String> resetOverrides = {};
  bool previewDirty = false;

  @override
  void initState() {
    super.initState();
    selectedList = widget.targetListId;
    Future.microtask(_loadLists);
  }

  @override
  void dispose() {
    portions.dispose();
    newName.dispose();
    super.dispose();
  }

  Future<void> _loadLists() async {
    try {
      lists = await ref
          .read(pantryAwareShoppingRepositoryProvider)
          .eligibleLists();
      if (selectedList == null) {
        final eligible = lists.where((item) => item['eligible'] == true);
        if (eligible.isNotEmpty) selectedList = eligible.first['id'].toString();
        if (selectedList == null) createNew = true;
      }
    } catch (exception) {
      error = exception.toString();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Map<String, dynamic> _request() {
    final request = <String, dynamic>{
      'source_type': widget.sourceType,
      'pantry_date_mode': dateMode,
      'include_other_open_lists': otherLists,
      'include_optional_recipe_ingredients': optionalIngredients,
      'intentional_duplicate_source_ids': acceptedDuplicates.toList(),
      'excluded_food_ids': excludedFoods.toList(),
      'target_item_resolutions': resolutions,
      'reset_override_item_ids': resetOverrides.toList(),
      'create_new_list': createNew,
      if (createNew) 'new_list_name': newName.text.trim(),
      if (!createNew) 'target_shopping_list_id': selectedList,
    };
    switch (widget.sourceType) {
      case 'recipe':
        request.addAll({
          'recipe_id': widget.sourceId,
          'recipe_portion_count': portions.text,
          'source_occurrence_id': occurrenceId,
        });
      case 'daily_plan':
        request['daily_plan_id'] = widget.sourceId;
      case 'weekly_plan':
        request['week_anchor_date'] = _date(widget.weekAnchor!);
      case 'shopping_list_reconciliation':
        request['target_shopping_list_id'] = widget.targetListId;
        request['create_new_list'] = false;
    }
    return request;
  }

  Future<void> _preview() async {
    if (!createNew && selectedList == null) {
      setState(() => error = 'Bitte wähle eine offene Einkaufsliste.');
      return;
    }
    if (createNew && newName.text.trim().isEmpty) {
      setState(() => error = 'Bitte gib einen Namen für die neue Liste ein.');
      return;
    }
    setState(() {
      loading = true;
      error = null;
    });
    try {
      result = await ref
          .read(pantryAwareShoppingRepositoryProvider)
          .preview(_request());
      previewDirty = false;
    } catch (exception) {
      error = exception.toString();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _apply() async {
    final preview = result;
    if (preview == null || applying) return;
    setState(() {
      applying = true;
      error = null;
    });
    try {
      final applied = await ref
          .read(pantryAwareShoppingRepositoryProvider)
          .apply(_request(), preview['preview_token'].toString(), _uuid());
      if (mounted) {
        context.go('/shopping-lists/${applied['target_shopping_list_id']}');
      }
    } catch (exception) {
      if (mounted) {
        setState(() => error = exception.toString());
      }
    } finally {
      if (mounted) setState(() => applying = false);
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Einkaufsbedarf abgleichen',
    showNavigation: false,
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _sourceCard(),
        _options(),
        _target(),
        if (error != null)
          Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: ListTile(
              leading: const Icon(Icons.error_outline),
              title: Text(error!),
            ),
          ),
        if (loading)
          const Center(child: CircularProgressIndicator())
        else
          FilledButton.icon(
            key: const Key('pantry-aware-preview'),
            onPressed: _preview,
            icon: const Icon(Icons.calculate_outlined),
            label: Text(
              result == null ? 'Vorschau berechnen' : 'Neu berechnen',
            ),
          ),
        if (result != null) _previewResult(result!),
      ],
    ),
  );

  Widget _sourceCard() => Card(
    child: ListTile(
      leading: const Icon(Icons.restaurant_menu),
      title: Text(_sourceLabel()),
      subtitle: const Text(
        'Aktueller Bedarf wird mit Vorrat und offenen Einkaufslisten verglichen.',
      ),
    ),
  );

  Widget _options() => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          if (widget.sourceType == 'recipe') ...[
            TextField(
              key: const Key('pantry-aware-portions'),
              controller: portions,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(labelText: 'Rezeptportionen'),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Optionale Zutaten berücksichtigen'),
              value: optionalIngredients,
              onChanged: (value) => setState(() => optionalIngredients = value),
            ),
          ],
          DropdownButtonFormField<String>(
            key: const Key('pantry-aware-date-mode'),
            initialValue: dateMode,
            decoration: const InputDecoration(
              labelText: 'Datumsbehandlung im Vorrat',
            ),
            items: const [
              DropdownMenuItem(
                value: 'include_all',
                child: Text('Alle aktiven Bestände'),
              ),
              DropdownMenuItem(
                value: 'exclude_past_use_by',
                child: Text('Überschrittenes Verbrauchsdatum ausnehmen'),
              ),
              DropdownMenuItem(
                value: 'exclude_all_past_dates',
                child: Text('Alle überschrittenen Datumsfelder ausnehmen'),
              ),
            ],
            onChanged: (value) => setState(() => dateMode = value!),
          ),
          SwitchListTile(
            key: const Key('pantry-aware-other-lists'),
            contentPadding: EdgeInsets.zero,
            title: const Text('Andere offene Einkaufslisten berücksichtigen'),
            subtitle: const Text(
              'Diese Mengen gelten als geplant, nicht als gekauft.',
            ),
            value: otherLists,
            onChanged: (value) => setState(() => otherLists = value),
          ),
        ],
      ),
    ),
  );

  Widget _target() => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Neue Einkaufsliste erstellen'),
            value: createNew,
            onChanged: widget.sourceType == 'shopping_list_reconciliation'
                ? null
                : (value) => setState(() => createNew = value),
          ),
          if (createNew)
            TextField(
              controller: newName,
              decoration: const InputDecoration(
                labelText: 'Name der Einkaufsliste',
              ),
            )
          else
            DropdownButtonFormField<String>(
              key: const Key('pantry-aware-target-list'),
              initialValue: selectedList,
              decoration: const InputDecoration(
                labelText: 'Ziel-Einkaufsliste',
              ),
              items: lists
                  .map(
                    (item) => DropdownMenuItem(
                      value: item['id'].toString(),
                      enabled: item['eligible'] == true,
                      child: Text(
                        '${item['name']}${item['eligible'] == true ? '' : ' · nicht verfügbar'}',
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (value) => setState(() => selectedList = value),
            ),
        ],
      ),
    ),
  );

  Widget _previewResult(Map<String, dynamic> value) {
    final duplicates = (value['duplicate_sources'] as List? ?? const [])
        .whereType<Map>();
    final items = (value['items'] as List? ?? const []).whereType<Map>();
    final unresolved = (value['unresolved_requirements'] as List? ?? const [])
        .whereType<Map>();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 16),
        Text('Vorschau', style: Theme.of(context).textTheme.headlineSmall),
        for (final duplicate in duplicates)
          CheckboxListTile(
            value: acceptedDuplicates.contains(duplicate['source_identity']),
            title: const Text(
              'Bedarf ist bereits auf einer offenen Liste eingeplant',
            ),
            subtitle: const Text('Trotzdem bewusst noch einmal einplanen'),
            onChanged: (checked) {
              setState(() {
                final identity = duplicate['source_identity'].toString();
                if (checked == true) {
                  acceptedDuplicates.add(identity);
                } else {
                  acceptedDuplicates.remove(identity);
                }
                result = null;
              });
            },
          ),
        for (final item in items) _item(item),
        if (unresolved.isNotEmpty)
          ExpansionTile(
            title: Text('${unresolved.length} ungeklärte Anforderungen'),
            children: unresolved
                .map(
                  (row) => ListTile(title: Text(row['explanation'].toString())),
                )
                .toList(),
          ),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Annahmen',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                for (final text in (value['assumptions'] as List? ?? const []))
                  Text('• $text'),
              ],
            ),
          ),
        ),
        FilledButton.icon(
          key: const Key('pantry-aware-apply'),
          onPressed: applying || previewDirty ? null : _apply,
          icon: const Icon(Icons.check),
          label: Text(
            applying
                ? 'Wird übernommen …'
                : previewDirty
                ? 'Bitte Vorschau neu berechnen'
                : 'Änderungen bestätigen',
          ),
        ),
      ],
    );
  }

  Widget _item(Map<dynamic, dynamic> item) {
    final foodId = item['food_id'].toString();
    final conflict = {
      'one_manual_food_match',
      'multiple_matching_items',
    }.contains(item['target_item_state']);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              item['food_name'].toString(),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (widget.sourceType == 'recipe')
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: !excludedFoods.contains(foodId),
                title: const Text('Für die Einkaufsliste berücksichtigen'),
                onChanged: (checked) => setState(() {
                  if (checked == false) {
                    excludedFoods.add(foodId);
                  } else {
                    excludedFoods.remove(foodId);
                  }
                  previewDirty = true;
                }),
              ),
            Text(
              'Gesamt benötigt: ${_amount(item['combined_requirement'], item['canonical_unit'])}',
            ),
            Text(
              'Im Vorrat: ${_amount(item['pantry_available'], item['canonical_unit'])}',
            ),
            Text(
              'Auf anderen Listen: ${_amount(item['other_open_list_commitment'], item['canonical_unit'])}',
            ),
            Text(
              'Auf dieser Liste: ${_amount(item['target_existing_commitment'], item['canonical_unit'])}',
            ),
            Text(
              'Neuer Vorschlag: ${_amount(item['desired_target_commitment'], item['canonical_unit'])}',
            ),
            Text(
              'Änderung: ${_signed(item['suggested_target_change'], item['canonical_unit'])}',
            ),
            if (item['quantity_overridden'] == true)
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: resetOverrides.contains(item['target_item_id']),
                title: const Text('Manuell angepasst · Menge bleibt erhalten'),
                subtitle: const Text('Auf aktuellen Vorschlag setzen'),
                onChanged: (checked) => setState(() {
                  final id = item['target_item_id'].toString();
                  if (checked == true) {
                    resetOverrides.add(id);
                  } else {
                    resetOverrides.remove(id);
                  }
                }),
              ),
            if (conflict)
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: resolutions[foodId] == 'create_separate',
                title: const Text('Separaten erzeugten Eintrag erstellen'),
                subtitle: const Text(
                  'Der manuelle Eintrag bleibt unverändert.',
                ),
                onChanged: (checked) => setState(() {
                  if (checked == true) {
                    resolutions[foodId] = 'create_separate';
                  } else {
                    resolutions.remove(foodId);
                  }
                }),
              ),
          ],
        ),
      ),
    );
  }

  String _amount(Object? value, Object? unit) =>
      '${GermanDecimal.formatString(value)} ${unit ?? ''}';
  String _signed(Object? value, Object? unit) {
    final number = num.tryParse(value.toString()) ?? 0;
    return '${number > 0 ? '+' : ''}${GermanDecimal.format(number)} ${unit ?? ''}';
  }

  String _sourceLabel() => switch (widget.sourceType) {
    'recipe' => 'Fehlende Rezeptzutaten einkaufen',
    'daily_plan' => 'Tagesplan abgleichen',
    'weekly_plan' => 'Wocheneinkauf abgleichen',
    _ => 'Einkaufsliste mit aktuellem Bedarf abgleichen',
  };
}

String _date(DateTime value) =>
    '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

String _uuid() {
  final random = Random.secure();
  final bytes = List<int>.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final hex = bytes
      .map((byte) => byte.toRadixString(16).padLeft(2, '0'))
      .join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}
