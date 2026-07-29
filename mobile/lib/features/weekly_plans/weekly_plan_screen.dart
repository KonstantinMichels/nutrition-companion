import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import 'weekly_plan_models.dart';

final class WeeklyPlanScreen extends ConsumerStatefulWidget {
  const WeeklyPlanScreen({super.key});
  @override
  ConsumerState<WeeklyPlanScreen> createState() => _WeeklyPlanScreenState();
}

final class _WeeklyPlanScreenState extends ConsumerState<WeeklyPlanScreen> {
  DateTime anchor = DateTime.now();
  WeeklyPlan? week;
  bool loading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final value = await ref
          .read(weeklyPlanRepositoryProvider)
          .overview(anchor);
      if (mounted) setState(() => week = value);
    } on AppException catch (exception) {
      if (mounted) setState(() => error = exception.message);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Wochenplan',
    actions: [
      IconButton(
        key: const Key('weekly-today'),
        tooltip: 'Aktuelle Woche',
        onPressed: () {
          anchor = DateTime.now();
          load();
        },
        icon: const Icon(Icons.today),
      ),
      IconButton(
        key: const Key('weekly-date-picker'),
        tooltip: 'Woche auswählen',
        onPressed: pickWeek,
        icon: const Icon(Icons.date_range),
      ),
    ],
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : error != null
        ? _error()
        : RefreshIndicator(
            onRefresh: load,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _header(week!),
                _summary(week!),
                FilledButton.tonalIcon(
                  key: const Key('weekly-pantry-aware-shopping'),
                  onPressed: () => context.push(
                    '/pantry-aware-shopping?sourceType=weekly_plan&weekAnchor=${_apiDate(week!.weekStart)}',
                  ),
                  icon: const Icon(Icons.shopping_cart_outlined),
                  label: const Text('Wocheneinkauf abgleichen'),
                ),
                ...week!.days.map(_dayCard),
                _nutrients(week!),
                _targets(week!),
                _quality(week!),
              ],
            ),
          ),
  );

  Widget _error() => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(error!, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          FilledButton.icon(
            key: const Key('weekly-retry'),
            onPressed: load,
            icon: const Icon(Icons.refresh),
            label: const Text('Erneut versuchen'),
          ),
        ],
      ),
    ),
  );

  Widget _header(WeeklyPlan value) => Row(
    children: [
      IconButton(
        key: const Key('weekly-previous'),
        tooltip: 'Vorherige Woche',
        onPressed: () {
          anchor = value.weekStart.subtract(const Duration(days: 7));
          load();
        },
        icon: const Icon(Icons.chevron_left),
      ),
      Expanded(
        child: Semantics(
          header: true,
          child: Column(
            children: [
              Text(
                'KW ${value.weekNumber}',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              Text(
                '${_short(value.weekStart)}–${DateFormatters.date(value.weekEnd)}',
              ),
            ],
          ),
        ),
      ),
      IconButton(
        key: const Key('weekly-next'),
        tooltip: 'Nächste Woche',
        onPressed: () {
          anchor = value.weekStart.add(const Duration(days: 7));
          load();
        },
        icon: const Icon(Icons.chevron_right),
      ),
    ],
  );

  Widget _summary(WeeklyPlan value) {
    final planned = value.counts['planned_days'] ?? 0;
    final missing = value.counts['missing_plan_days'] ?? 0;
    final energy = value.nutrient('energy_kcal');
    final protein = value.nutrient('protein');
    return Card(
      key: const Key('weekly-summary'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Wochenübersicht',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              '$planned von 7 Tagen geplant · $missing Tage ohne aktiven Plan',
            ),
            if (energy != null)
              Text(
                'Wochensumme Energie: ${_value(energy.amount, energy.unit)}',
              ),
            if (energy != null)
              Text(
                'Ø Energie pro geplantem Tag: ${_value(energy.average, energy.unit)}',
              ),
            if (protein != null)
              Text(
                'Ø Eiweiß pro geplantem Tag: ${_value(protein.average, protein.unit)}',
              ),
            Text(
              'Verglichene Tage: ${value.counts['comparable_target_days'] ?? 0}',
            ),
            Text(
              'Datenstatus: ${_qualityLabel(value.quality['quality_level']?.toString())}',
            ),
            if (value.quality['mixed_assessment_basis'] == true)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Diese Woche verwendet unterschiedliche Assessments. Die Wochenziele wurden aus den jeweiligen Tageszielen zusammengesetzt.',
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _dayCard(WeeklyDay day) {
    final planned = day.state == 'planned';
    return Card(
      child: ExpansionTile(
        leading: Icon(
          planned ? Icons.event_available : Icons.event_note_outlined,
        ),
        title: Text(
          '${_weekday(day.weekday)}, ${DateFormatters.date(day.date)}',
        ),
        subtitle: Text(_daySubtitle(day)),
        trailing: PopupMenuButton<String>(
          tooltip: 'Aktionen für ${_weekday(day.weekday)}',
          onSelected: (action) => _dayAction(day, action),
          itemBuilder: (_) => [
            PopupMenuItem(
              value: 'open',
              child: Text(
                day.plan == null ? 'Tagesplan erstellen' : 'Tagesplan öffnen',
              ),
            ),
            if (day.plan != null)
              const PopupMenuItem(
                value: 'duplicate',
                child: Text('Tag kopieren'),
              ),
          ],
        ),
        children: [
          if (day.state == 'archived_only')
            const ListTile(title: Text('Nur archivierte Tagespläne vorhanden')),
          if (planned) ...[
            ListTile(
              title: Text(
                '${day.summary['meal_count']} Mahlzeiten · ${day.summary['entry_count']} Einträge',
              ),
              subtitle: Text(
                'Energie: ${_value(day.summary['energy_kcal']?.toString(), 'kcal')} · Eiweiß: ${_value(day.summary['protein_g']?.toString(), 'g')}',
              ),
            ),
            for (final meal in day.meals)
              ListTile(
                leading: const Icon(Icons.restaurant_menu),
                title: Text(meal['name']?.toString() ?? 'Mahlzeit'),
                subtitle: Text('${meal['entry_count']} Einträge'),
                trailing: PopupMenuButton<String>(
                  tooltip: 'Mahlzeit übertragen',
                  onSelected: (action) =>
                      transfer(day, meal, move: action == 'move'),
                  itemBuilder: (_) => const [
                    PopupMenuItem(
                      value: 'copy',
                      child: Text('Mahlzeit kopieren'),
                    ),
                    PopupMenuItem(
                      value: 'move',
                      child: Text('Mahlzeit verschieben'),
                    ),
                  ],
                ),
              ),
          ],
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () => openDay(day),
                icon: Icon(day.plan == null ? Icons.add : Icons.open_in_new),
                label: Text(
                  day.plan == null ? 'Tagesplan erstellen' : 'Tagesplan öffnen',
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _nutrients(WeeklyPlan value) => ExpansionTile(
    title: const Text('Wochensumme und Tagesmittel'),
    subtitle: const Text('Mittelwerte beziehen sich auf geplante Tage'),
    children: value.totals
        .where(
          (item) => const {
            'energy_kcal',
            'protein',
            'carbohydrate',
            'fat',
            'fiber',
          }.contains(item.code),
        )
        .map(
          (item) => ListTile(
            title: Text(item.name),
            subtitle: Text(
              'Summe: ${_value(item.amount, item.unit)} · Ø: ${_value(item.average, item.unit)}\nDatenabdeckung: ${_coverage(item.coverage)}${item.complete ? '' : ' · unvollständig'}',
            ),
          ),
        )
        .toList(),
  );

  Widget _targets(WeeklyPlan value) => ExpansionTile(
    title: const Text('Wochenziele im Vergleich'),
    subtitle: Text(
      'Vergleich für ${value.counts['comparable_target_days'] ?? 0} geplante Tage mit Zielwerten',
    ),
    children: value.comparisons
        .map(
          (item) => ListTile(
            leading: Icon(
              item.relation.contains('above')
                  ? Icons.warning_amber
                  : Icons.info_outline,
            ),
            title: Text(item.name),
            subtitle: Text(
              '${_value(item.amount, item.unit)} geplant · ${item.targetDays} Zieltage\n${_target(item)}\n${item.explanation}',
            ),
          ),
        )
        .toList(),
  );

  Widget _quality(WeeklyPlan value) => ExpansionTile(
    title: const Text('Datenqualität und Berechnungsgrundlagen'),
    children: [
      ListTile(
        title: Text(
          '${value.quality['basic_nutrition_complete_day_count']} geplante Tage mit vollständigen Basisdaten',
        ),
        subtitle: Text(
          '${value.quality['estimated_conversion_count']} geschätzte Umrechnungen · ${value.quality['archived_reference_count']} archivierte Quellen',
        ),
      ),
      for (final warning in value.warnings)
        ListTile(
          leading: Icon(
            warning['severity'] == 'warning'
                ? Icons.warning_amber
                : Icons.info_outline,
          ),
          title: Text(warning['explanation_de']?.toString() ?? ''),
        ),
      const ListTile(
        title: Text('Berechnungsgrundlage'),
        subtitle: Text(
          'Fehlende Tage gelten nicht als Null-Verzehr. Zielwerte werden nur für geplante Tage mit kompatiblen Assessments summiert. Die Darstellung ist keine Diagnose.',
        ),
      ),
    ],
  );

  Future<void> pickWeek() async {
    final selected = await showDatePicker(
      context: context,
      initialDate: anchor,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      helpText: 'Woche über ein Datum auswählen',
    );
    if (selected != null) {
      anchor = selected;
      await load();
    }
  }

  Future<void> openDay(WeeklyDay day) async {
    final id = day.plan?['id']?.toString();
    await context.push(
      '/daily-plan/edit?date=${_apiDate(day.date)}&returnTo=weekly-plan${id == null ? '' : '&id=$id'}',
    );
    if (mounted) await load();
  }

  Future<void> _dayAction(WeeklyDay day, String action) async {
    if (action == 'open') return openDay(day);
    if (action == 'duplicate') await duplicateDay(day);
  }

  Future<void> duplicateDay(WeeklyDay day) async {
    final target = await showDatePicker(
      context: context,
      initialDate: day.date.add(const Duration(days: 1)),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      helpText: 'Zieldatum für Tageskopie',
    );
    if (target == null || !mounted) return;
    try {
      await ref
          .read(dailyPlanRepositoryProvider)
          .duplicate(day.plan!['id'].toString(), target, copyAssessment: true);
      _message('Der Tagesplan wurde kopiert.');
      await load();
    } on AppException catch (exception) {
      _message(exception.message);
    }
  }

  Future<void> transfer(
    WeeklyDay sourceDay,
    Map<String, dynamic> meal, {
    required bool move,
  }) async {
    final targetDate = await showDatePicker(
      context: context,
      initialDate: sourceDay.date.add(const Duration(days: 1)),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      helpText: move ? 'Zieldatum zum Verschieben' : 'Zieldatum zum Kopieren',
    );
    if (targetDate == null || !mounted) return;
    final targetDay = week!.days
        .where((item) => _sameDate(item.date, targetDate))
        .firstOrNull;
    String mode = 'new_meal';
    String? targetMealId;
    if (targetDay != null && targetDay.meals.isNotEmpty) {
      final choice = await showDialog<String>(
        context: context,
        builder: (dialog) => SimpleDialog(
          title: const Text('Mahlzeit übernehmen als'),
          children: [
            SimpleDialogOption(
              onPressed: () => Navigator.pop(dialog, 'new'),
              child: const Text('Neue Mahlzeit'),
            ),
            ...targetDay.meals.map(
              (item) => SimpleDialogOption(
                onPressed: () => Navigator.pop(dialog, item['id'].toString()),
                child: Text('An „${item['name']}“ anhängen'),
              ),
            ),
          ],
        ),
      );
      if (choice == null) return;
      if (choice != 'new') {
        mode = 'append_to_existing_meal';
        targetMealId = choice;
      }
    }
    if (move &&
        !await _confirm(
          'Mahlzeit verschieben?',
          '„${meal['name']}“ wird aus ${DateFormatters.date(sourceDay.date)} entfernt und nach ${DateFormatters.date(targetDate)} verschoben.',
        )) {
      return;
    }
    try {
      await ref
          .read(weeklyPlanRepositoryProvider)
          .transfer(
            move: move,
            sourcePlanId: sourceDay.plan!['id'].toString(),
            sourceMealId: meal['id'].toString(),
            targetDate: targetDate,
            copyMode: mode,
            targetMealId: targetMealId,
          );
      _message(
        move ? 'Die Mahlzeit wurde verschoben.' : 'Die Mahlzeit wurde kopiert.',
      );
      await load();
    } on AppException catch (exception) {
      _message(exception.message);
    }
  }

  Future<bool> _confirm(String title, String text) async =>
      await showDialog<bool>(
        context: context,
        builder: (dialog) => AlertDialog(
          title: Text(title),
          content: Text(text),
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

  void _message(String value) => ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(value)));
}

String _short(DateTime value) =>
    '${value.day.toString().padLeft(2, '0')}.${value.month.toString().padLeft(2, '0')}.';
String _apiDate(DateTime value) =>
    '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
bool _sameDate(DateTime a, DateTime b) =>
    a.year == b.year && a.month == b.month && a.day == b.day;
String _weekday(String value) =>
    const {
      'monday': 'Montag',
      'tuesday': 'Dienstag',
      'wednesday': 'Mittwoch',
      'thursday': 'Donnerstag',
      'friday': 'Freitag',
      'saturday': 'Samstag',
      'sunday': 'Sonntag',
    }[value] ??
    value;
String _value(String? value, String unit) => value == null
    ? 'nicht verfügbar'
    : '${GermanDecimal.formatString(value)} $unit';
String _coverage(String? value) {
  final number = double.tryParse(value ?? '');
  return number == null
      ? 'nicht verfügbar'
      : '${GermanDecimal.format(number * 100, decimals: 0)} %';
}

String _daySubtitle(WeeklyDay day) => switch (day.state) {
  'planned' =>
    '${day.summary['meal_count']} Mahlzeiten · ${day.summary['entry_count']} Einträge',
  'empty_plan' => 'Tagesplan ohne Einträge',
  'archived_only' => 'Nur archivierte Tagespläne',
  _ => 'Noch kein Tagesplan',
};
String _qualityLabel(String? value) => switch (value) {
  'empty_week' => 'Noch keine geplanten Tage',
  'partial_week' => 'Teilweise geplante Woche',
  'planned_week' => 'Vollständig geplant, Daten teilweise unvollständig',
  'complete_week' => 'Vollständig geplant mit vollständigen Basisdaten',
  _ => 'Nicht verfügbar',
};
String _target(WeeklyComparison item) => switch (item.kind) {
  'minimum' => 'Summierter Mindestwert: ${_value(item.minimum, item.unit)}',
  'maximum' => 'Summierter Tageshöchstwert: ${_value(item.maximum, item.unit)}',
  'range' =>
    'Summierter Zielbereich: ${_value(item.minimum, item.unit)} bis ${_value(item.maximum, item.unit)}',
  'reference' => 'Summierter Referenzwert: ${_value(item.value, item.unit)}',
  _ => 'Nicht kompatible Berechnungsgrundlage',
};
