import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/formatting/german_decimal.dart';
import 'recipe_availability_models.dart';

class RecipeAvailabilitySection extends ConsumerStatefulWidget {
  const RecipeAvailabilitySection({required this.recipeId, super.key});
  final String recipeId;
  @override
  ConsumerState<RecipeAvailabilitySection> createState() => _State();
}

class _State extends ConsumerState<RecipeAvailabilitySection> {
  String portions = '1', dateMode = 'include_all';
  bool optional = false, loading = false;
  RecipeAvailability? value;
  String? error;
  final controller = TextEditingController(text: '1');
  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final parsed = GermanDecimal.tryParse(controller.text);
    if (parsed == null || parsed <= 0) {
      setState(
        () =>
            error = 'Bitte gib eine gültige Portionszahl größer als null ein.',
      );
      return;
    }
    setState(() {
      loading = true;
      error = null;
      portions = controller.text;
    });
    try {
      final result = await ref
          .read(recipeAvailabilityRepositoryProvider)
          .detail(
            widget.recipeId,
            portions: portions,
            optional: optional,
            dateMode: dateMode,
          );
      if (mounted) setState(() => value = result);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Vorratsverfügbarkeit',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              IconButton(
                tooltip: 'Vorrat neu prüfen',
                onPressed: loading ? null : _load,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
          const Text(
            'Live-Berechnung aus dem erfassten Vorrat. Es wird nichts reserviert oder verändert.',
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: ['0,5', '1', '1,5', '2', '4']
                .map(
                  (v) => ChoiceChip(
                    label: Text(v),
                    selected: portions == v,
                    onSelected: (_) {
                      controller.text = v;
                      _load();
                    },
                  ),
                )
                .toList(),
          ),
          TextField(
            controller: controller,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText: 'Gewünschte Portionen',
              suffixIcon: IconButton(
                onPressed: _load,
                icon: const Icon(Icons.check),
              ),
            ),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Optionale Zutaten berücksichtigen'),
            value: optional,
            onChanged: (v) {
              optional = v;
              _load();
            },
          ),
          DropdownButtonFormField<String>(
            initialValue: dateMode,
            decoration: const InputDecoration(
              labelText: 'Datumsfelder berücksichtigen',
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
            onChanged: (v) {
              if (v != null) {
                dateMode = v;
                _load();
              }
            },
          ),
          if (loading) const LinearProgressIndicator(),
          if (error != null)
            Text(
              error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          if (value != null) ..._result(value!),
        ],
      ),
    ),
  );
  List<Widget> _result(RecipeAvailability data) => [
    const Divider(height: 24),
    Semantics(
      label: _label(data.state),
      child: Text(
        _label(data.state),
        style: Theme.of(context).textTheme.titleMedium,
      ),
    ),
    Text(
      'Rechnerisch möglich: ${data.maximum.isEmpty ? '—' : data.maximum} Portionen · Vollständige ganze Portionen: ${data.wholePortions ?? '—'}',
    ),
    if (data.limiting.isNotEmpty)
      Text('Begrenzende Zutaten: ${data.limiting.join(', ')}'),
    Text(
      'Berechnet mit dem erfassten Vorratsstand von ${DateFormatters.dateTime(data.calculatedAt)}',
    ),
    ...data.warnings.map(
      (w) => ListTile(
        contentPadding: EdgeInsets.zero,
        leading: const Icon(Icons.warning_amber),
        title: Text(w),
      ),
    ),
    ...data.ingredients.map(_ingredient),
  ];
  Widget _ingredient(AvailabilityIngredient i) => ExpansionTile(
    tilePadding: EdgeInsets.zero,
    title: Text(i.name),
    subtitle: Text(
      '${_state(i.state)} · Benötigt ${i.required} ${i.unit} · Im Vorrat ${i.available} ${i.unit}${i.missing != '0' ? ' · Fehlend ${i.missing} ${i.unit}' : ' · Rechnerischer Rest ${i.remaining ?? '0'} ${i.unit}'}',
    ),
    children: [
      if (i.estimated) const ListTile(title: Text('Geschätzte Umrechnung')),
      if (i.archived) const ListTile(title: Text('Archiviertes Lebensmittel')),
      if (i.lots.isEmpty)
        const ListTile(title: Text('Kein aktiver Bestand erfasst')),
      ...i.lots.map(
        (lot) => ListTile(
          title: Text(
            '${lot['location_name']} · ${GermanDecimal.formatString(lot['available_quantity'])} ${lot['canonical_unit']}',
          ),
          subtitle: Text(_dateStatus(lot['date_status'].toString())),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => context.push('/pantry/items/${lot['stock_lot_id']}'),
        ),
      ),
    ],
  );
  String _label(String s) => switch (s) {
    'fully_available' => 'Vollständig verfügbar',
    'partially_available' => 'Teilweise verfügbar',
    'not_available' => 'Nicht verfügbar',
    'empty_recipe' => 'Leeres Rezept',
    _ => 'Nicht vollständig berechenbar',
  };
  String _state(String s) => switch (s) {
    'fully_available' => 'Verfügbar',
    'partially_available' => 'Teilweise verfügbar',
    'not_available' => 'Nicht verfügbar',
    _ => 'Ungeklärt',
  };
  String _dateStatus(String s) => switch (s) {
    'past_best_before' => 'Mindesthaltbarkeitsdatum überschritten',
    'past_use_by' => 'Verbrauchsdatum überschritten',
    'date_today' => 'Datumsfeld ist heute',
    'expiring_soon' => 'Datumsfeld in Kürze erreicht',
    'valid' => 'Datumsfeld zukünftig',
    _ => 'Kein Datum',
  };
}
