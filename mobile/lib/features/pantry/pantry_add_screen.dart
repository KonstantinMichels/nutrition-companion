import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../daily_plans/daily_plan_models.dart' show apiDate;
import '../foods/food_models.dart';
import 'pantry_models.dart';

final class PantryAddScreen extends ConsumerStatefulWidget {
  const PantryAddScreen({super.key});
  @override
  ConsumerState<PantryAddScreen> createState() => _PantryAddScreenState();
}

final class _PantryAddScreenState extends ConsumerState<PantryAddScreen> {
  final quantity = TextEditingController(text: '1');
  final note = TextEditingController();
  List<FoodItem> foods = [];
  List<PantryLocation> locations = [];
  FoodItem? food;
  PantryLocation? location;
  String? unit;
  String? measureId;
  DateTime? purchase, opened, bestBefore, useBy;
  bool loading = true, saving = false;
  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  @override
  void dispose() {
    quantity.dispose();
    note.dispose();
    super.dispose();
  }

  Future<void> load() async {
    final values = await Future.wait([
      ref.read(foodRepositoryProvider).list(),
      ref.read(pantryRepositoryProvider).locations(),
    ]);
    if (mounted) {
      setState(() {
        foods = values[0] as List<FoodItem>;
        locations = values[1] as List<PantryLocation>;
        loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Vorrat hinzufügen',
    showNavigation: false,
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              DropdownButtonFormField<FoodItem>(
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Lebensmittel'),
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
                onChanged: (value) => setState(() {
                  food = value;
                  unit = value?.referenceUnit;
                  measureId = null;
                }),
              ),
              TextField(
                controller: quantity,
                decoration: const InputDecoration(labelText: 'Menge'),
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
              ),
              DropdownButtonFormField<String>(
                key: ValueKey(food?.id),
                initialValue: unit,
                decoration: const InputDecoration(
                  labelText: 'Einheit oder Haushaltsmaß',
                ),
                items: food == null
                    ? []
                    : [
                        DropdownMenuItem(
                          value: food!.referenceUnit,
                          child: Text(food!.referenceUnit),
                        ),
                        DropdownMenuItem(
                          value: food!.referenceUnit == 'g' ? 'kg' : 'l',
                          child: Text(food!.referenceUnit == 'g' ? 'kg' : 'l'),
                        ),
                        ...food!.measures.map(
                          (measure) => DropdownMenuItem(
                            value: 'measure:${measure.id}',
                            child: Text(measure.name),
                          ),
                        ),
                      ],
                onChanged: (value) => setState(() {
                  unit = value;
                  measureId = value?.startsWith('measure:') == true
                      ? value!.substring(8)
                      : null;
                }),
              ),
              if (food != null && unit != null)
                ListTile(
                  leading: const Icon(Icons.calculate_outlined),
                  title: const Text('Normalisierte Menge'),
                  subtitle: Text(_preview()),
                ),
              DropdownButtonFormField<PantryLocation>(
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Lagerort'),
                items: locations
                    .where((item) => !item.archived)
                    .map(
                      (item) =>
                          DropdownMenuItem(value: item, child: Text(item.name)),
                    )
                    .toList(),
                onChanged: (value) => setState(() => location = value),
              ),
              _date('Kaufdatum', purchase, (value) => purchase = value),
              _date('Öffnungsdatum', opened, (value) => opened = value),
              _date(
                'Mindesthaltbarkeitsdatum',
                bestBefore,
                (value) => bestBefore = value,
              ),
              _date('Verbrauchsdatum', useBy, (value) => useBy = value),
              TextField(
                controller: note,
                decoration: const InputDecoration(
                  labelText: 'Notiz (optional)',
                ),
                maxLines: 2,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: saving ? null : save,
                child: Text(saving ? 'Wird gespeichert …' : 'Bestand anlegen'),
              ),
              const Padding(
                padding: EdgeInsets.only(top: 16),
                child: Text(
                  'Datumsangaben dienen nur der Übersicht und sind keine automatische Sicherheitsbewertung.',
                ),
              ),
            ],
          ),
  );
  Widget _date(
    String label,
    DateTime? value,
    ValueChanged<DateTime?> changed,
  ) => ListTile(
    contentPadding: EdgeInsets.zero,
    title: Text(label),
    subtitle: Text(
      value == null
          ? 'Nicht angegeben'
          : '${value.day.toString().padLeft(2, '0')}.${value.month.toString().padLeft(2, '0')}.${value.year}',
    ),
    trailing: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (value != null)
          IconButton(
            onPressed: () => setState(() => changed(null)),
            icon: const Icon(Icons.clear),
          ),
        IconButton(
          onPressed: () async {
            final selected = await showDatePicker(
              context: context,
              initialDate: value ?? DateTime.now(),
              firstDate: DateTime(2000),
              lastDate: DateTime(2100),
            );
            if (selected != null) setState(() => changed(selected));
          },
          icon: const Icon(Icons.calendar_today),
        ),
      ],
    ),
  );
  String _preview() {
    final value = GermanDecimal.tryParse(quantity.text);
    if (value == null || food == null || unit == null) return 'Menge prüfen';
    if (measureId != null) {
      return '$value × ${food!.measures.firstWhere((item) => item.id == measureId).name} (wird serverseitig exakt normalisiert)';
    }
    final factor = unit == 'kg' || unit == 'l' ? 1000 : 1;
    return '${GermanDecimal.format(value * factor)} ${food!.referenceUnit}';
  }

  Future<void> save() async {
    final parsed = GermanDecimal.tryParse(quantity.text);
    if (food == null ||
        location == null ||
        unit == null ||
        parsed == null ||
        parsed <= 0) {
      _message(
        'Bitte Lebensmittel, Menge, Einheit und Lagerort vollständig angeben.',
      );
      return;
    }
    setState(() => saving = true);
    try {
      await ref.read(pantryRepositoryProvider).create({
        'client_operation_id': _uuid(),
        'food_id': food!.id,
        'location_id': location!.id,
        'quantity': parsed.toString(),
        'unit_code': measureId == null
            ? unit
            : food!.measures
                  .firstWhere((item) => item.id == measureId)
                  .unitCode,
        'food_measure_id': measureId,
        'purchase_date': purchase == null ? null : apiDate(purchase!),
        'opened_date': opened == null ? null : apiDate(opened!),
        'best_before_date': bestBefore == null ? null : apiDate(bestBefore!),
        'use_by_date': useBy == null ? null : apiDate(useBy!),
        'note': note.text.trim().isEmpty ? null : note.text.trim(),
      });
      if (mounted) context.pop();
    } on AppException catch (exception) {
      _message(exception.message);
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  void _message(String value) => ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(value)));
}

String pantryOperationId() => _uuid();
String _uuid() {
  final random = Random.secure();
  final bytes = List<int>.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  String hex(int value) => value.toRadixString(16).padLeft(2, '0');
  final raw = bytes.map(hex).join();
  return '${raw.substring(0, 8)}-${raw.substring(8, 12)}-${raw.substring(12, 16)}-${raw.substring(16, 20)}-${raw.substring(20)}';
}
