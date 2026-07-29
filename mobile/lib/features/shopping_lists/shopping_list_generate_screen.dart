import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/providers.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';

class ShoppingListGenerateScreen extends ConsumerStatefulWidget {
  const ShoppingListGenerateScreen({super.key});
  @override
  ConsumerState<ShoppingListGenerateScreen> createState() => _State();
}

class _State extends ConsumerState<ShoppingListGenerateScreen> {
  bool weekly = false, pantry = true, loading = false;
  DateTime date = DateTime.now();
  Map<String, dynamic>? preview;
  String? error;
  final name = TextEditingController();
  Map<String, dynamic>? payload;
  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Aus Plan erstellen',
    showNavigation: false,
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        SegmentedButton<bool>(
          segments: const [
            ButtonSegment(
              value: false,
              label: Text('Tagesplan'),
              icon: Icon(Icons.today),
            ),
            ButtonSegment(
              value: true,
              label: Text('Wochenplan'),
              icon: Icon(Icons.calendar_view_week),
            ),
          ],
          selected: {weekly},
          onSelectionChanged: (v) => setState(() {
            weekly = v.first;
            preview = null;
          }),
        ),
        ListTile(
          title: Text(
            weekly
                ? 'Woche ab ${DateFormatters.date(_monday(date))}'
                : DateFormatters.date(date),
          ),
          trailing: const Icon(Icons.date_range),
          onTap: _pick,
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Vorrat berücksichtigen'),
          subtitle: const Text(
            'Der Vorrat wird nur für die Berechnung verwendet und nicht reserviert oder verändert.',
          ),
          value: pantry,
          onChanged: (v) => setState(() => pantry = v),
        ),
        FilledButton.icon(
          onPressed: loading ? null : _preview,
          icon: const Icon(Icons.calculate_outlined),
          label: Text(loading ? 'Wird berechnet …' : 'Vorschau berechnen'),
        ),
        if (error != null)
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(
              error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        if (preview != null) ..._previewWidgets(),
      ],
    ),
  );
  List<Widget> _previewWidgets() {
    final p = preview!,
        items = (p['items'] as List).whereType<Map>().toList(),
        unresolved = (p['unresolved_requirements'] as List).length;
    return [
      const Divider(height: 32),
      Text(
        '${items.length} Lebensmittel · ${(p['source_days'] as List).length} Tage',
        style: Theme.of(context).textTheme.titleMedium,
      ),
      ...items.map(
        (i) => ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(i['food_name'].toString()),
          subtitle: Text(
            'Benötigt ${GermanDecimal.formatString(i['required_quantity'])} ${i['canonical_unit']} · Vorrat ${GermanDecimal.formatString(i['pantry_available_quantity'])}',
          ),
          trailing: Text(
            '${GermanDecimal.formatString(i['suggested_purchase_quantity'])} ${i['canonical_unit']}',
          ),
        ),
      ),
      if (unresolved > 0)
        Text(
          '$unresolved Anforderungen: Prüfung erforderlich',
          style: TextStyle(color: Theme.of(context).colorScheme.error),
        ),
      TextField(
        controller: name,
        decoration: const InputDecoration(labelText: 'Listenname (optional)'),
      ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: loading ? _none : _create,
        child: const Text('Einkaufsliste erstellen'),
      ),
    ];
  }

  void _none() {}
  DateTime _monday(DateTime d) => d.subtract(Duration(days: d.weekday - 1));
  Future<void> _pick() async {
    final value = await showDatePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
      initialDate: date,
    );
    if (value != null) {
      setState(() {
        date = value;
        preview = null;
      });
    }
  }

  Future<void> _preview() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      if (weekly) {
        payload = {
          'week_anchor_date': _apiDate(date),
          'pantry_considered': pantry,
        };
      } else {
        final plan = await ref.read(dailyPlanRepositoryProvider).byDate(date);
        if (plan == null) {
          throw Exception('Für diesen Tag gibt es keinen Tagesplan.');
        }
        payload = {'daily_plan_id': plan.id, 'pantry_considered': pantry};
      }
      final result = await ref
          .read(shoppingListRepositoryProvider)
          .preview(payload!);
      setState(() => preview = result);
    } catch (e) {
      setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _create() async {
    if (payload == null) return;
    setState(() => loading = true);
    try {
      final data = {
        ...payload!,
        if (name.text.trim().isNotEmpty) 'name': name.text.trim(),
      };
      final list = await ref
          .read(shoppingListRepositoryProvider)
          .generate(data);
      if (mounted) context.go('/shopping-lists/${list.summary.id}');
    } catch (e) {
      setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  String _apiDate(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}
