import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/providers.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import 'food_detail_screen.dart';
import 'food_list_screen.dart';

final class FoodFormScreen extends ConsumerStatefulWidget {
  const FoodFormScreen({this.id, super.key});
  final String? id;
  @override
  ConsumerState<FoodFormScreen> createState() => _FoodFormScreenState();
}

final class _FoodFormScreenState extends ConsumerState<FoodFormScreen> {
  final formKey = GlobalKey<FormState>();
  final name = TextEditingController();
  final brand = TextEditingController();
  final fields = {
    for (final code in [
      'energy_kcal',
      'fat',
      'saturated_fat',
      'carbohydrate',
      'sugars',
      'fiber',
      'protein',
      'salt',
    ])
      code: TextEditingController(),
  };
  String unit = 'g';
  bool saving = false, incomplete = false, loaded = false;
  static const labels = {
    'energy_kcal': 'Energie',
    'fat': 'Fett',
    'saturated_fat': 'Gesättigte Fettsäuren',
    'carbohydrate': 'Kohlenhydrate',
    'sugars': 'Zucker',
    'fiber': 'Ballaststoffe',
    'protein': 'Eiweiß',
    'salt': 'Salz',
  };
  @override
  void dispose() {
    name.dispose();
    brand.dispose();
    for (final c in fields.values) {
      c.dispose();
    }
    super.dispose();
  }

  void prefill(dynamic food) {
    if (loaded) return;
    loaded = true;
    name.text = food.name;
    brand.text = food.brand ?? '';
    unit = food.referenceUnit;
    for (final n in food.nutrients) {
      if (!n.derived && fields.containsKey(n.code)) {
        fields[n.code]!.text = n.amount.replaceAll('.', ',');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.id != null) {
      ref.watch(foodDetailProvider(widget.id!)).whenData(prefill);
    }
    return AppScaffold(
      title: widget.id == null
          ? 'Lebensmittel anlegen'
          : 'Lebensmittel bearbeiten',
      showNavigation: false,
      onBackPressed: () => _discard(context),
      body: Form(
        key: formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Grundangaben', style: Theme.of(context).textTheme.titleLarge),
            TextFormField(
              controller: name,
              decoration: const InputDecoration(labelText: 'Name *'),
              validator: (v) => v == null || v.trim().isEmpty
                  ? 'Name ist erforderlich.'
                  : null,
            ),
            TextFormField(
              controller: brand,
              decoration: const InputDecoration(labelText: 'Marke (optional)'),
            ),
            const SizedBox(height: 20),
            Text('Bezugsbasis', style: Theme.of(context).textTheme.titleLarge),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'g', label: Text('100 g')),
                ButtonSegment(value: 'ml', label: Text('100 ml')),
              ],
              selected: {unit},
              onSelectionChanged: (v) => setState(() => unit = v.first),
            ),
            const Text('Alle Werte gelten für die gewählte Bezugsbasis.'),
            const SizedBox(height: 20),
            Text(
              'Grundnährwerte',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            for (final entry in fields.entries)
              TextFormField(
                controller: entry.value,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'[0-9,.]')),
                ],
                decoration: InputDecoration(
                  labelText:
                      '${labels[entry.key]} (${entry.key == 'energy_kcal' ? 'kcal' : 'g'}) ${['energy_kcal', 'fat', 'carbohydrate', 'protein'].contains(entry.key) ? '*' : '(optional)'}',
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return null;
                  try {
                    if (GermanDecimal.parse(v) < 0) {
                      return 'Wert darf nicht negativ sein.';
                    }
                  } catch (_) {
                    return 'Bitte gültige Zahl eingeben.';
                  }
                  return null;
                },
              ),
            if (fields['energy_kcal']!.text.isNotEmpty)
              Text('kJ wird beim Speichern berechnet.'),
            CheckboxListTile(
              value: incomplete,
              onChanged: (v) => setState(() => incomplete = v ?? false),
              title: const Text('Unvollständige Grundwerte bewusst speichern'),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: saving ? null : save,
              child: Text(saving ? 'Wird gespeichert …' : 'Speichern'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> save() async {
    if (!formKey.currentState!.validate()) return;
    final nutrients = <Map<String, dynamic>>[];
    for (final e in fields.entries) {
      if (e.value.text.trim().isNotEmpty) {
        nutrients.add({
          'nutrient_code': e.key,
          'amount': GermanDecimal.parse(e.value.text).toString(),
          'unit': e.key == 'energy_kcal' ? 'kcal' : 'g',
        });
      }
    }
    setState(() => saving = true);
    try {
      final food = await ref.read(foodRepositoryProvider).save({
        'name': name.text,
        'brand': brand.text.trim().isEmpty ? null : brand.text.trim(),
        'reference_quantity': '100',
        'reference_unit': unit,
        'nutrients': nutrients,
        'confirm_incomplete': incomplete,
        'confirm_reference_change': true,
      }, id: widget.id);
      ref.invalidate(foodListProvider);
      ref.invalidate(foodDetailProvider(food.id));
      if (mounted) context.go('/foods/${food.id}');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> _discard(BuildContext context) async {
    final leave = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Änderungen verwerfen?'),
        content: const Text('Nicht gespeicherte Eingaben gehen verloren.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Weiter bearbeiten'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Verwerfen'),
          ),
        ],
      ),
    );
    if (leave == true && context.mounted) {
      context.go(widget.id == null ? '/foods' : '/foods/${widget.id}');
    }
  }
}
