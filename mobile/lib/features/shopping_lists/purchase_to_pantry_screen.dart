import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../pantry/pantry_models.dart';

class PurchaseToPantryScreen extends ConsumerStatefulWidget {
  const PurchaseToPantryScreen({required this.listId, super.key});
  final String listId;
  @override
  ConsumerState<PurchaseToPantryScreen> createState() => _State();
}

class _State extends ConsumerState<PurchaseToPantryScreen> {
  bool loading = true, submitting = false;
  String? error, listName;
  List<Map<String, dynamic>> items = [];
  List<PantryLocation> locations = [];
  final selected = <String>{};
  final quantities = <String, TextEditingController>{};
  final selectedLocations = <String, String>{};
  final complete = <String, bool>{};
  final mappedFoods = <String, String>{};
  final units = <String, String>{};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final controller in quantities.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final values = await Future.wait([
        ref
            .read(shoppingListRepositoryProvider)
            .handoffEligibility(widget.listId),
        ref.read(pantryRepositoryProvider).locations(),
      ]);
      final eligibility = values[0] as Map<String, dynamic>;
      locations = values[1] as List<PantryLocation>;
      items = (eligibility['items'] as List)
          .whereType<Map>()
          .map((value) => Map<String, dynamic>.from(value))
          .toList();
      listName = (eligibility['shopping_list'] as Map)['name'].toString();
      for (final item in items) {
        final id = item['shopping_list_item_id'].toString();
        if (item['preselected'] == true) selected.add(id);
        quantities[id] = TextEditingController(
          text: GermanDecimal.formatString(item['planned_purchase_quantity']),
        );
        complete[id] = item['handoff_state'] != 'completed';
        units[id] = item['planned_purchase_unit']?.toString() ?? 'g';
        if (locations.length == 1) selectedLocations[id] = locations.first.id;
      }
    } catch (value) {
      error = value.toString();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'In Vorrat übernehmen',
    showNavigation: false,
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : error != null
        ? Center(child: Text(error!))
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                listName ?? 'Einkaufsliste',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              const Text(
                'Abgehakte Einträge sind vorausgewählt. Erst deine ausdrückliche Bestätigung legt Vorratsbestände an. Der Status der Einkaufsliste bleibt unverändert.',
              ),
              const SizedBox(height: 16),
              ...items.map(_item),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: selected.isEmpty || submitting ? null : _review,
                icon: const Icon(Icons.inventory_2_outlined),
                label: Text(
                  submitting ? 'Wird übernommen …' : 'Übernahme prüfen',
                ),
              ),
            ],
          ),
  );

  Widget _item(Map<String, dynamic> item) {
    final id = item['shopping_list_item_id'].toString();
    final foodBacked = item['food_id'] != null || mappedFoods[id] != null;
    final enabled = foodBacked;
    final isSelected = selected.contains(id);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              value: isSelected,
              onChanged: enabled
                  ? (value) async {
                      if (value == true &&
                          item['handoff_state'] == 'completed') {
                        final confirmed = await showDialog<bool>(
                          context: context,
                          builder: (context) => AlertDialog(
                            title: const Text('Weiteren Bestand hinzufügen?'),
                            content: const Text(
                              'Dieser Eintrag wurde bereits vollständig übernommen. Möchtest du weiteren Bestand hinzufügen?',
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(context, false),
                                child: const Text('Abbrechen'),
                              ),
                              FilledButton(
                                onPressed: () => Navigator.pop(context, true),
                                child: const Text('Weiter'),
                              ),
                            ],
                          ),
                        );
                        if (confirmed != true) return;
                      }
                      setState(() {
                        if (value == true) {
                          selected.add(id);
                        } else {
                          selected.remove(id);
                        }
                      });
                    }
                  : null,
              title: Text(item['name']?.toString() ?? 'Unbenannt'),
              subtitle: Text(
                !foodBacked
                    ? 'Freitext muss zuerst einem Lebensmittel zugeordnet werden.'
                    : item['handoff_state'] == 'completed'
                    ? 'Bereits vollständig übernommen'
                    : item['checked'] == true
                    ? 'Abgehakter Eintrag'
                    : 'Nicht abgehakter Eintrag – bewusst auswählen',
              ),
            ),
            if (item['food_id'] == null)
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton.icon(
                  onPressed: () => _mapFood(id),
                  icon: const Icon(Icons.search),
                  label: Text(
                    mappedFoods[id] == null
                        ? 'Lebensmittel zuordnen'
                        : 'Zuordnung ändern',
                  ),
                ),
              ),
            if (isSelected) ...[
              TextField(
                controller: quantities[id],
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: InputDecoration(
                  labelText: 'Tatsächlich gekauft',
                  suffixText: units[id],
                  helperText:
                      'Geplante Einkaufsmenge: ${GermanDecimal.formatString(item['planned_purchase_quantity'])} ${item['planned_purchase_unit'] ?? ''}',
                ),
              ),
              DropdownButtonFormField<String>(
                initialValue: {'g', 'kg', 'ml', 'l'}.contains(units[id])
                    ? units[id]
                    : 'g',
                decoration: const InputDecoration(labelText: 'Einheit'),
                items: const [
                  DropdownMenuItem(value: 'g', child: Text('Gramm')),
                  DropdownMenuItem(value: 'kg', child: Text('Kilogramm')),
                  DropdownMenuItem(value: 'ml', child: Text('Milliliter')),
                  DropdownMenuItem(value: 'l', child: Text('Liter')),
                ],
                onChanged: (value) {
                  if (value != null) setState(() => units[id] = value);
                },
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: selectedLocations[id],
                decoration: const InputDecoration(labelText: 'Lagerort'),
                items: locations
                    .map(
                      (location) => DropdownMenuItem(
                        value: location.id,
                        child: Text(location.name),
                      ),
                    )
                    .toList(),
                onChanged: (value) => setState(() {
                  if (value != null) selectedLocations[id] = value;
                }),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Artikel nach Übernahme abschließen'),
                value: complete[id] ?? true,
                onChanged: (value) => setState(() => complete[id] = value),
              ),
              const Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Standard: Neuen Bestand anlegen. Kaufdatum ist heute; weitere Datumsangaben bleiben leer.',
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Map<String, dynamic>? _payload() {
    final result = <Map<String, dynamic>>[];
    for (final item in items.where(
      (value) => selected.contains(value['shopping_list_item_id'].toString()),
    )) {
      final id = item['shopping_list_item_id'].toString();
      final quantity = GermanDecimal.tryParse(quantities[id]?.text);
      final location = selectedLocations[id];
      if (quantity == null || quantity <= 0 || location == null) {
        setState(
          () => error =
              'Bitte gib für alle ausgewählten Einträge eine gültige Menge und einen Lagerort an.',
        );
        return null;
      }
      final unit = units[id] ?? 'g';
      result.add({
        'shopping_list_item_id': id,
        if (mappedFoods[id] != null) 'mapped_food_id': mappedFoods[id],
        'actual_quantity': quantity.toString(),
        'unit_code': unit,
        'mark_item_handoff_completed': complete[id] ?? true,
        'confirm_additional_after_completion':
            item['handoff_state'] == 'completed',
        'destinations': [
          {
            'destination_type': 'new_stock_lot',
            'pantry_location_id': location,
            'quantity': quantity.toString(),
            'unit_code': unit,
            'purchase_date': _date(DateTime.now()),
          },
        ],
      });
    }
    return {'items': result};
  }

  Future<void> _review() async {
    final payload = _payload();
    if (payload == null) return;
    setState(() {
      submitting = true;
      error = null;
    });
    try {
      final preview = await ref
          .read(shoppingListRepositoryProvider)
          .handoffPreview(widget.listId, payload);
      if (!mounted) return;
      final summary = Map<String, dynamic>.from(preview['summary'] as Map);
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Übernahme bestätigen?'),
          content: Text(
            '${summary['selected_item_count']} Artikel, ${summary['new_stock_lot_count']} neue Bestände.\n\nErst nach der Bestätigung werden Bestände und Bestandsbewegungen angelegt.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Zurück'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Übernehmen'),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
      await ref
          .read(shoppingListRepositoryProvider)
          .applyHandoff(widget.listId, {
            ...payload,
            'preview_token': preview['preview_token'],
            'client_operation_id': _uuid(),
          });
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Übernahme abgeschlossen'),
          content: const Text(
            'Die bestätigten Lebensmittel wurden als neue Bestände angelegt. Die Einkaufsliste und ihre Haken wurden nicht verändert.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Zur Einkaufsliste'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(context);
                context.go('/pantry');
              },
              child: const Text('Vorrat öffnen'),
            ),
          ],
        ),
      );
      if (mounted) context.pop();
    } catch (value) {
      if (mounted) setState(() => error = value.toString());
    } finally {
      if (mounted) setState(() => submitting = false);
    }
  }

  Future<void> _mapFood(String itemId) async {
    final foods = await ref.read(foodRepositoryProvider).list();
    if (!mounted) return;
    final selectedFood = await showDialog<dynamic>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Lebensmittel zuordnen'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView(
            shrinkWrap: true,
            children: foods
                .map(
                  (food) => ListTile(
                    title: Text(food.name),
                    subtitle: food.brand == null ? null : Text(food.brand!),
                    onTap: () => Navigator.pop(context, food),
                  ),
                )
                .toList(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Überspringen'),
          ),
        ],
      ),
    );
    if (selectedFood != null) {
      setState(() {
        mappedFoods[itemId] = selectedFood.id.toString();
        units[itemId] = selectedFood.referenceUnit.toString();
      });
    }
  }

  String _date(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
  String _uuid() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    final hex = bytes
        .map((value) => value.toRadixString(16).padLeft(2, '0'))
        .join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }
}
