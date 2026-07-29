import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import 'daily_plan_models.dart';

final class DailyPlanScreen extends ConsumerStatefulWidget {
  const DailyPlanScreen({this.initialDate, super.key});
  final DateTime? initialDate;
  @override
  ConsumerState<DailyPlanScreen> createState() => _DailyPlanScreenState();
}

final class _DailyPlanScreenState extends ConsumerState<DailyPlanScreen> {
  late DateTime date;
  DailyPlan? plan;
  bool loading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    final source = widget.initialDate ?? DateTime.now();
    date = DateTime(source.year, source.month, source.day);
    Future.microtask(load);
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final repository = ref.read(dailyPlanRepositoryProvider);
      plan =
          await repository.byDate(date) ??
          await repository.archivedByDate(date);
    } on AppException catch (exception) {
      error = exception.message;
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> changeDate(DateTime value) async {
    date = DateTime(value.year, value.month, value.day);
    await load();
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Tagesplan',
    actions: [
      IconButton(
        onPressed: load,
        tooltip: 'Aktualisieren',
        icon: const Icon(Icons.refresh),
      ),
    ],
    body: ContentWidth(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _dateNavigation(),
          const SizedBox(height: 12),
          if (loading)
            const Center(child: CircularProgressIndicator())
          else if (error != null)
            _error()
          else if (plan == null)
            _empty()
          else
            _plan(plan!),
        ],
      ),
    ),
  );

  Widget _dateNavigation() => Row(
    children: [
      IconButton(
        key: const Key('daily-previous'),
        onPressed: () => changeDate(date.subtract(const Duration(days: 1))),
        tooltip: 'Vorheriger Tag',
        icon: const Icon(Icons.chevron_left),
      ),
      Expanded(
        child: OutlinedButton.icon(
          key: const Key('daily-date-picker'),
          onPressed: () async {
            final selected = await showDatePicker(
              context: context,
              initialDate: date,
              firstDate: DateTime(2000),
              lastDate: DateTime(2100),
              locale: const Locale('de'),
            );
            if (selected != null) await changeDate(selected);
          },
          icon: const Icon(Icons.calendar_today_outlined),
          label: Text(DateFormatters.date(date)),
        ),
      ),
      IconButton(
        key: const Key('daily-next'),
        onPressed: () => changeDate(date.add(const Duration(days: 1))),
        tooltip: 'Nächster Tag',
        icon: const Icon(Icons.chevron_right),
      ),
    ],
  );

  Widget _empty() => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          const Icon(Icons.event_note_outlined, size: 52),
          const SizedBox(height: 12),
          const Text('Für diesen Tag ist noch kein Tagesplan vorhanden.'),
          const SizedBox(height: 16),
          FilledButton.icon(
            key: const Key('create-daily-plan'),
            onPressed: () =>
                context.go('/daily-plan/edit?date=${apiDate(date)}'),
            icon: const Icon(Icons.add),
            label: const Text('Tagesplan erstellen'),
          ),
        ],
      ),
    ),
  );

  Widget _error() => Card(
    child: ListTile(
      leading: const Icon(Icons.error_outline),
      title: Text(error!),
      trailing: TextButton(
        onPressed: load,
        child: const Text('Erneut versuchen'),
      ),
    ),
  );

  Widget _plan(DailyPlan value) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      if (value.archived)
        const Card(
          child: ListTile(
            leading: Icon(Icons.archive_outlined),
            title: Text('Archivierter Tagesplan'),
            subtitle: Text('Dieser Plan ist schreibgeschützt.'),
          ),
        ),
      Text(
        value.name ?? 'Tagesplan für den ${DateFormatters.date(value.date)}',
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      Text(
        '${value.meals.length} Mahlzeiten · ${value.entryCount} Einträge · ${_quality(value.quality)}',
      ),
      const SizedBox(height: 12),
      _summary(value),
      for (final meal in value.meals) _meal(meal),
      if (value.warnings.isNotEmpty)
        ExpansionTile(
          title: const Text('Hinweise und Datenqualität'),
          children: value.warnings
              .map(
                (item) => ListTile(
                  leading: const Icon(Icons.info_outline),
                  title: Text(item),
                ),
              )
              .toList(),
        ),
      if (value.comparisons.isEmpty)
        const Card(
          child: ListTile(
            title: Text('Kein persönlicher Tagesvergleich'),
            subtitle: Text(
              'Wähle ein geeignetes Assessment aus, um Zielwerte zu vergleichen.',
            ),
          ),
        )
      else
        _comparisons(value),
      const SizedBox(height: 12),
      FilledButton.tonalIcon(
        key: const Key('daily-pantry-aware-shopping'),
        onPressed: () => context.push(
          '/pantry-aware-shopping?sourceType=daily_plan&sourceId=${value.id}',
        ),
        icon: const Icon(Icons.shopping_cart_outlined),
        label: const Text('Einkaufsbedarf abgleichen'),
      ),
      if (!value.archived)
        FilledButton.icon(
          onPressed: () => context.go(
            '/daily-plan/edit?id=${value.id}&date=${apiDate(value.date)}',
          ),
          icon: const Icon(Icons.edit_outlined),
          label: const Text('Tagesplan bearbeiten'),
        ),
      OutlinedButton.icon(
        onPressed: () => _duplicate(value),
        icon: const Icon(Icons.copy_outlined),
        label: const Text('Auf anderen Tag duplizieren'),
      ),
      if (value.archived)
        FilledButton.tonalIcon(
          onPressed: () => _restore(value),
          icon: const Icon(Icons.unarchive_outlined),
          label: const Text('Tagesplan wiederherstellen'),
        )
      else
        TextButton.icon(
          onPressed: () => _archive(value),
          icon: const Icon(Icons.archive_outlined),
          label: const Text('Tagesplan archivieren'),
        ),
      const SizedBox(height: 16),
      const Text(
        'Der Tagesplan beschreibt geplante Mengen und bestätigt keinen tatsächlichen Verzehr.',
      ),
    ],
  );

  Widget _summary(DailyPlan value) {
    const codes = ['energy_kcal', 'protein', 'carbohydrate', 'fat', 'fiber'];
    final shown = value.nutrients.where((item) => codes.contains(item.code));
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Tagesbilanz', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            for (final item in shown)
              Text(
                '${item.name}: ${item.amount ?? 'Nicht verfügbar'}${item.amount == null ? '' : ' ${item.unit}'}${item.complete ? '' : ' · Daten unvollständig'}',
              ),
          ],
        ),
      ),
    );
  }

  Widget _meal(DailyMeal meal) {
    final energy = meal.nutrients
        .where((item) => item.code == 'energy_kcal')
        .firstOrNull;
    final protein = meal.nutrients
        .where((item) => item.code == 'protein')
        .firstOrNull;
    return Card(
      child: ExpansionTile(
        title: Text(meal.name),
        subtitle: Text(
          '${meal.time == null ? '' : '${meal.time} Uhr · '}${meal.entries.length} Einträge · ${energy?.amount ?? '–'} kcal · ${protein?.amount ?? '–'} g Protein',
        ),
        children: meal.entries
            .map(
              (entry) => ListTile(
                leading: Icon(
                  entry.type == 'recipe'
                      ? Icons.menu_book_outlined
                      : Icons.restaurant_outlined,
                ),
                title: Text(entry.name),
                subtitle: Text(
                  entry.type == 'recipe'
                      ? '${entry.portions} Portionen'
                      : '${entry.quantity} ${entry.unitCode}${entry.estimated ? ' · Geschätzte Umrechnung' : ''}${entry.archived ? ' · Archiviert' : ''}',
                ),
              ),
            )
            .toList(),
      ),
    );
  }

  Widget _comparisons(DailyPlan value) => ExpansionTile(
    title: const Text('Persönlicher Tagesvergleich'),
    subtitle: const Text('Mindestwerte, Zielbereiche und Tageshöchstwerte'),
    children: [
      for (final item in value.comparisons)
        ListTile(
          leading: Icon(_relationIcon(item.relation)),
          title: Text(item.name),
          subtitle: Text(
            '${item.amount ?? 'Nicht verfügbar'} ${item.unit} · ${_kind(item.kind)}\n${item.explanation}${item.remaining == null ? '' : '\nVerbleibend: ${item.remaining} ${item.unit}${item.remainingStatus == 'exact' ? '' : ' (unsicher)'}'}',
          ),
          isThreeLine: true,
        ),
      const ListTile(
        title: Text('Berechnungsgrundlagen'),
        subtitle: Text(
          'Unveränderte Zielwerte des gewählten Assessments werden mit aktuellen Food- und Recipe-Core-Daten verglichen.',
        ),
      ),
    ],
  );

  Future<void> _archive(DailyPlan value) async {
    final confirmed = await _confirm(
      'Tagesplan archivieren?',
      'Der Plan bleibt einsehbar und kann wiederhergestellt werden.',
    );
    if (confirmed && value.id != null) {
      await ref.read(dailyPlanRepositoryProvider).archive(value.id!);
      await load();
    }
  }

  Future<void> _restore(DailyPlan value) async {
    try {
      await ref.read(dailyPlanRepositoryProvider).restore(value.id!);
      await load();
    } on AppException catch (exception) {
      _message(exception.message);
    }
  }

  Future<void> _duplicate(DailyPlan value) async {
    final target = await showDatePicker(
      context: context,
      initialDate: date.add(const Duration(days: 1)),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      locale: const Locale('de'),
    );
    if (target == null) return;
    var copyAssessment = true;
    if (!mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Tagesplan duplizieren?'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Zieldatum: ${DateFormatters.date(target)}'),
              CheckboxListTile(
                value: copyAssessment,
                onChanged: (value) =>
                    setDialogState(() => copyAssessment = value ?? true),
                title: const Text('Assessment-Auswahl kopieren'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialog, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialog, true),
              child: const Text('Duplizieren'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;
    try {
      await ref
          .read(dailyPlanRepositoryProvider)
          .duplicate(value.id!, target, copyAssessment: copyAssessment);
      await changeDate(target);
    } on AppException catch (exception) {
      _message(exception.message);
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

String _quality(String value) => switch (value) {
  'empty' => 'Leer',
  'incomplete' => 'Daten unvollständig',
  'extended' => 'Erweiterte Datenabdeckung',
  _ => 'Grundnährwerte vollständig',
};
String _kind(String value) => switch (value) {
  'minimum' => 'Mindestwert',
  'maximum' => 'Tageshöchstwert',
  'range' => 'Zielbereich',
  _ => 'Referenzwert',
};
IconData _relationIcon(String value) => switch (value) {
  'exceeds_limit' || 'above_range' => Icons.warning_amber_outlined,
  'unavailable' || 'indeterminate' => Icons.help_outline,
  _ => Icons.info_outline,
};
