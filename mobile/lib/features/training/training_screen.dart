import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import 'training_repository.dart';

final class TrainingScreen extends ConsumerStatefulWidget {
  const TrainingScreen({this.initialDate, super.key});
  final DateTime? initialDate;
  @override
  ConsumerState<TrainingScreen> createState() => _TrainingScreenState();
}

final class _TrainingScreenState extends ConsumerState<TrainingScreen> {
  bool loading = true;
  String? error;
  List<Map<String, dynamic>> items = [];
  List<Map<String, dynamic>> history = [];
  TrainingRepository get repository => ref.read(trainingRepositoryProvider);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final values = await Future.wait([
        repository.sessions(),
        repository.adjustments(),
        repository.preferences(),
      ]);
      if (!mounted) return;
      setState(() {
        items = values[0];
        history = values[1];
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

  @override
  Widget build(BuildContext context) => DefaultTabController(
    length: 2,
    child: AppScaffold(
      title: 'Training und Tagesziele',
      actions: [
        IconButton(
          onPressed: _load,
          tooltip: 'Aktualisieren',
          icon: const Icon(Icons.refresh),
        ),
      ],
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('add-training-session'),
        onPressed: () => _sessionDialog(),
        icon: const Icon(Icons.add),
        label: const Text('Training planen'),
      ),
      body: Column(
        children: [
          const TabBar(
            tabs: [
              Tab(text: 'Training'),
              Tab(text: 'Anpassungen'),
            ],
          ),
          Expanded(
            child: loading
                ? const Center(child: CircularProgressIndicator())
                : error != null
                ? _error()
                : TabBarView(children: [_sessions(), _adjustments()]),
          ),
        ],
      ),
    ),
  );

  Widget _error() => Center(
    child: Card(
      child: ListTile(
        leading: const Icon(Icons.error_outline),
        title: Text(error!),
        trailing: TextButton(
          onPressed: _load,
          child: const Text('Erneut versuchen'),
        ),
      ),
    ),
  );

  Widget _sessions() => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      ContentWidth(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Card(
              child: ListTile(
                leading: Icon(Icons.info_outline),
                title: Text('Manuell geplante Einheiten'),
                subtitle: Text(
                  'Eine geplante oder als durchgeführt markierte Einheit ist deine Angabe und keine Messung der tatsächlichen Belastung.',
                ),
              ),
            ),
            FilledButton.tonalIcon(
              key: const Key('calculate-training-adjustments'),
              onPressed: _adjustmentDialog,
              icon: const Icon(Icons.tune),
              label: const Text('Tagesziele prüfen'),
            ),
            if (items.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('Noch keine Trainingseinheit geplant.'),
                ),
              ),
            for (final item in items)
              Card(
                child: ExpansionTile(
                  leading: Icon(
                    item['status'] == 'cancelled'
                        ? Icons.event_busy
                        : Icons.fitness_center,
                  ),
                  title: Text(
                    item['title']?.toString() ?? _sport(item['sport_type']),
                  ),
                  subtitle: Text(
                    '${item['session_date']}${item['planned_start_time'] == null ? '' : ' · ${item['planned_start_time'].toString().substring(0, 5)} Uhr'} · ${item['planned_duration_minutes']} Min. · ${_intensity(item['perceived_intensity'])}\n${_inclusion(item['baseline_inclusion'])} · ${_status(item['status'])}',
                  ),
                  children: [
                    const ListTile(
                      title: Text('Hinweis'),
                      subtitle: Text(
                        'Änderungen an der Einheit verändern bereits gespeicherte Tagesanpassungen nicht automatisch.',
                      ),
                    ),
                    Wrap(
                      spacing: 8,
                      children: [
                        TextButton(
                          onPressed: () => _sessionDialog(existing: item),
                          child: const Text('Bearbeiten'),
                        ),
                        if (item['status'] != 'completed')
                          TextButton(
                            onPressed: () => _statusChange(item, 'complete'),
                            child: const Text('Als durchgeführt markieren'),
                          ),
                        if (item['status'] != 'cancelled')
                          TextButton(
                            onPressed: () => _statusChange(item, 'cancel'),
                            child: const Text('Absagen'),
                          ),
                        if (item['status'] == 'cancelled')
                          TextButton(
                            onPressed: () => _statusChange(item, 'restore'),
                            child: const Text('Wiederherstellen'),
                          ),
                        IconButton(
                          onPressed: () => _delete(item),
                          tooltip: 'Unreferenzierte Einheit löschen',
                          icon: const Icon(Icons.delete_outline),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    ],
  );

  Widget _adjustments() => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      ContentWidth(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            FilledButton.icon(
              onPressed: _adjustmentDialog,
              icon: const Icon(Icons.add_chart),
              label: const Text('Temporäre Zielanpassung erstellen'),
            ),
            const SizedBox(height: 12),
            if (history.isEmpty) const Text('Noch keine bestätigte Anpassung.'),
            for (final batch in history)
              Card(
                child: ExpansionTile(
                  leading: Icon(
                    batch['status'] == 'active'
                        ? Icons.check_circle_outline
                        : Icons.history,
                  ),
                  title: Text(
                    '${_strategy(batch['strategy'])} · ${_status(batch['status'])}',
                  ),
                  subtitle: Text(
                    batch['scope'] == 'iso_week'
                        ? 'Woche ab ${batch['iso_week_start']}'
                        : '${batch['single_date']}',
                  ),
                  children: [
                    for (final raw
                        in (batch['adjustments'] as List? ?? const []))
                      Builder(
                        builder: (_) {
                          final day = Map<String, dynamic>.from(raw as Map);
                          return ListTile(
                            title: Text(
                              '${day['adjustment_date']} · ${_loadLabel(day['load_category'])}',
                            ),
                            subtitle: Text(
                              'Basisziel ${_number(day['baseline_energy_target_kcal'])} kcal · Anpassung ${_signed(day['energy_delta_kcal'])} kcal · Tagesziel ${_number(day['adjusted_energy_target_kcal'])} kcal\nKohlenhydrat-Schwerpunkt ${_signed(day['carbohydrate_delta_g'])} g',
                            ),
                          );
                        },
                      ),
                  ],
                ),
              ),
            const Card(
              child: ListTile(
                leading: Icon(Icons.help_outline),
                title: Text('Wie wird die Tagesanpassung berechnet?'),
                subtitle: Text(
                  'Aus dem unveränderten Assessment-Basisziel, deinen Sessionangaben, der Einordnung zum Basisziel, einer Belastungskategorie und versionierten Grenzen. Eine Wochenumverteilung verändert die bestätigte Wochenenergie nicht.',
                ),
              ),
            ),
          ],
        ),
      ),
    ],
  );

  Future<void> _sessionDialog({Map<String, dynamic>? existing}) async {
    var day =
        DateTime.tryParse(existing?['session_date']?.toString() ?? '') ??
        widget.initialDate ??
        DateTime.now();
    var sport = existing?['sport_type']?.toString() ?? 'strength_training';
    var type = existing?['session_type']?.toString() ?? 'strength';
    var intensity = existing?['perceived_intensity']?.toString() ?? 'moderate';
    var inclusion = existing?['baseline_inclusion']?.toString() ?? 'unknown';
    TimeOfDay? start = _time(existing?['planned_start_time']);
    final duration = TextEditingController(
      text: existing?['planned_duration_minutes']?.toString() ?? '60',
    );
    final title = TextEditingController(
      text: existing?['title']?.toString() ?? '',
    );
    final note = TextEditingController(
      text: existing?['note']?.toString() ?? '',
    );
    var saving = false;
    await showDialog<void>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(
            existing == null ? 'Training planen' : 'Training bearbeiten',
          ),
          content: SizedBox(
            width: 460,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField(
                    initialValue: sport,
                    decoration: const InputDecoration(labelText: 'Sportart'),
                    items: _sports.entries
                        .map(
                          (e) => DropdownMenuItem(
                            value: e.key,
                            child: Text(e.value),
                          ),
                        )
                        .toList(),
                    onChanged: (v) => setLocal(() => sport = v!),
                  ),
                  DropdownButtonFormField(
                    initialValue: type,
                    decoration: const InputDecoration(
                      labelText: 'Trainingstyp',
                    ),
                    items: _types.entries
                        .map(
                          (e) => DropdownMenuItem(
                            value: e.key,
                            child: Text(e.value),
                          ),
                        )
                        .toList(),
                    onChanged: (v) => setLocal(() => type = v!),
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Datum'),
                    subtitle: Text(DateFormatters.date(day)),
                    trailing: const Icon(Icons.calendar_today),
                    onTap: () async {
                      final value = await showDatePicker(
                        context: context,
                        initialDate: day,
                        firstDate: DateTime(2000),
                        lastDate: DateTime(2100),
                        locale: const Locale('de'),
                      );
                      if (value != null) setLocal(() => day = value);
                    },
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Startzeit optional'),
                    subtitle: Text(start?.format(context) ?? 'Nicht angegeben'),
                    trailing: start == null
                        ? const Icon(Icons.schedule)
                        : IconButton(
                            onPressed: () => setLocal(() => start = null),
                            icon: const Icon(Icons.clear),
                          ),
                    onTap: () async {
                      final value = await showTimePicker(
                        context: context,
                        initialTime: start ?? TimeOfDay.now(),
                      );
                      if (value != null) setLocal(() => start = value);
                    },
                  ),
                  TextField(
                    controller: duration,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Geplante Dauer in Minuten',
                      helperText:
                          '5 bis 720 Minuten; keine Trainingsempfehlung',
                    ),
                  ),
                  DropdownButtonFormField(
                    initialValue: intensity,
                    decoration: const InputDecoration(
                      labelText: 'Geplante Intensität',
                    ),
                    items: _intensities.entries
                        .map(
                          (e) => DropdownMenuItem(
                            value: e.key,
                            child: Text(e.value),
                          ),
                        )
                        .toList(),
                    onChanged: (v) => setLocal(() => intensity = v!),
                  ),
                  DropdownButtonFormField(
                    initialValue: inclusion,
                    decoration: const InputDecoration(
                      labelText: 'Im Basisziel bereits berücksichtigt?',
                    ),
                    items: _inclusions.entries
                        .map(
                          (e) => DropdownMenuItem(
                            value: e.key,
                            child: Text(e.value),
                          ),
                        )
                        .toList(),
                    onChanged: (v) => setLocal(() => inclusion = v!),
                  ),
                  const Padding(
                    padding: EdgeInsets.only(top: 6),
                    child: Text(
                      'Warum muss ich das angeben? Regelmäßiges Training kann bereits im langfristigen Durchschnitt enthalten sein. Ein vollständiger zusätzlicher Aufschlag könnte es doppelt berücksichtigen.',
                    ),
                  ),
                  TextField(
                    controller: title,
                    decoration: const InputDecoration(
                      labelText: 'Titel optional',
                    ),
                  ),
                  TextField(
                    controller: note,
                    maxLines: 2,
                    decoration: const InputDecoration(
                      labelText: 'Private Notiz optional',
                    ),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(dialog),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      final minutes = int.tryParse(duration.text);
                      if (minutes == null) return;
                      setLocal(() => saving = true);
                      try {
                        await repository.saveSession({
                          'session_date': _apiDate(day),
                          'planned_start_time': start == null
                              ? null
                              : '${start!.hour.toString().padLeft(2, '0')}:${start!.minute.toString().padLeft(2, '0')}',
                          'sport_type': sport,
                          'session_type': type,
                          'planned_duration_minutes': minutes,
                          'perceived_intensity': intensity,
                          'baseline_inclusion': inclusion,
                          'title': title.text.trim().isEmpty
                              ? null
                              : title.text.trim(),
                          'note': note.text.trim().isEmpty
                              ? null
                              : note.text.trim(),
                          if (existing != null)
                            'expected_version': existing['version'],
                          'confirm_long_duration': minutes > 480,
                        }, id: existing?['id']?.toString());
                        if (dialog.mounted) Navigator.pop(dialog);
                        await _load();
                      } catch (exception) {
                        setLocal(() => saving = false);
                        if (mounted) {
                          ScaffoldMessenger.of(this.context).showSnackBar(
                            SnackBar(content: Text(exception.toString())),
                          );
                        }
                      }
                    },
              child: Text(saving ? 'Speichert …' : 'Speichern'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _adjustmentDialog() async {
    var scope = 'single_day';
    var strategy = 'none';
    var day = widget.initialDate ?? DateTime.now();
    final customEnergy = TextEditingController(text: '0');
    final customCarbs = TextEditingController(text: '0');
    Map<String, dynamic>? preview;
    var working = false;
    var linkPlans = false;
    var createPlans = false;
    var confirmReplacement = false;
    await showDialog<void>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (context, setLocal) {
          Map<String, dynamic> request() => {
            'scope': scope,
            if (scope == 'single_day')
              'date': _apiDate(day)
            else
              'week_anchor_date': _apiDate(day),
            'strategy': strategy,
            if (strategy == 'custom_manual')
              'selected_energy_deltas': {
                _apiDate(day): (GermanDecimal.tryParse(customEnergy.text) ?? 0)
                    .toString(),
              },
            if (strategy == 'custom_manual')
              'selected_carbohydrate_deltas': {
                _apiDate(day): (GermanDecimal.tryParse(customCarbs.text) ?? 0)
                    .toString(),
              },
          };
          final days = (preview?['days'] as List? ?? const [])
              .whereType<Map>()
              .toList();
          return AlertDialog(
            title: const Text('Temporäre Zielanpassung'),
            content: SizedBox(
              width: 520,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Die Funktion plant Tagesvariationen. Sie misst keinen Trainingsverbrauch und verändert dein Assessment nicht.',
                    ),
                    SegmentedButton(
                      segments: const [
                        ButtonSegment(
                          value: 'single_day',
                          label: Text('Ein Tag'),
                        ),
                        ButtonSegment(
                          value: 'iso_week',
                          label: Text('Eine Woche'),
                        ),
                      ],
                      selected: {scope},
                      onSelectionChanged: (v) => setLocal(() {
                        scope = v.first;
                        if (scope == 'single_day' &&
                            strategy == 'weekly_redistribution') {
                          strategy = 'none';
                        }
                        preview = null;
                      }),
                    ),
                    ListTile(
                      title: Text(
                        scope == 'single_day' ? 'Datum' : 'Woche mit Datum',
                      ),
                      subtitle: Text(DateFormatters.date(day)),
                      trailing: const Icon(Icons.calendar_today),
                      onTap: () async {
                        final value = await showDatePicker(
                          context: context,
                          initialDate: day,
                          firstDate: DateTime(2000),
                          lastDate: DateTime(2100),
                          locale: const Locale('de'),
                        );
                        if (value != null) {
                          setLocal(() {
                            day = value;
                            preview = null;
                          });
                        }
                      },
                    ),
                    DropdownButtonFormField(
                      initialValue: strategy,
                      decoration: const InputDecoration(labelText: 'Strategie'),
                      items: [
                        if (scope == 'iso_week')
                          const DropdownMenuItem(
                            value: 'weekly_redistribution',
                            child: Text('Wöchentliche Umverteilung'),
                          ),
                        const DropdownMenuItem(
                          value: 'bounded_additive',
                          child: Text('Zusätzlicher Trainingsaufschlag'),
                        ),
                        const DropdownMenuItem(
                          value: 'custom_manual',
                          child: Text('Manuelle Anpassung'),
                        ),
                        const DropdownMenuItem(
                          value: 'none',
                          child: Text('Keine Zielanpassung'),
                        ),
                      ],
                      onChanged: (v) => setLocal(() {
                        strategy = v!;
                        preview = null;
                      }),
                    ),
                    if (strategy == 'custom_manual') ...[
                      TextField(
                        controller: customEnergy,
                        keyboardType: const TextInputType.numberWithOptions(
                          signed: true,
                          decimal: true,
                        ),
                        decoration: const InputDecoration(
                          labelText: 'Energie-Anpassung kcal',
                        ),
                      ),
                      TextField(
                        controller: customCarbs,
                        keyboardType: const TextInputType.numberWithOptions(
                          signed: true,
                          decimal: true,
                        ),
                        decoration: const InputDecoration(
                          labelText: 'Kohlenhydrat-Schwerpunkt g',
                        ),
                      ),
                    ],
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: working
                          ? null
                          : () async {
                              setLocal(() => working = true);
                              try {
                                final value = await repository.preview(
                                  request(),
                                );
                                setLocal(() {
                                  preview = value;
                                  working = false;
                                });
                              } catch (exception) {
                                setLocal(() => working = false);
                                if (mounted) {
                                  ScaffoldMessenger.of(
                                    this.context,
                                  ).showSnackBar(
                                    SnackBar(
                                      content: Text(exception.toString()),
                                    ),
                                  );
                                }
                              }
                            },
                      icon: const Icon(Icons.calculate_outlined),
                      label: Text(
                        working ? 'Wird berechnet …' : 'Vorschau erstellen',
                      ),
                    ),
                    if (preview != null) ...[
                      const Divider(),
                      Text(
                        'Ausgangsziel: ${_number(preview!['source_assessment']['baseline_energy_target_kcal'])} kcal',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      if (preview!['source_assessment']['is_calibrated_revision'] ==
                          true)
                        const Text(
                          'Kalibrierte Assessment-Revision als unverändertes Basisziel',
                        ),
                      for (final raw in days)
                        Builder(
                          builder: (_) {
                            final value = Map<String, dynamic>.from(raw);
                            return ListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(
                                '${value['date']} · ${_loadLabel(value['load_category'])}',
                              ),
                              subtitle: Text(
                                'Vorgeschlagener Bereich ${_number(value['suggested_energy_delta_min_kcal'])} bis ${_number(value['suggested_energy_delta_max_kcal'])} kcal\nGewählt ${_signed(value['selected_energy_delta_kcal'])} kcal · Tagesziel ${_number(value['adjusted_energy_target_kcal'])} kcal\nTemporärer Kohlenhydrat-Schwerpunkt ${_signed(value['selected_carbohydrate_delta_g'])} g',
                              ),
                            );
                          },
                        ),
                      if (scope == 'iso_week')
                        ListTile(
                          title: Text(
                            preview!['weekly_summary']['balanced'] == true
                                ? 'Wochenenergie bleibt unverändert'
                                : 'Wochenbilanz verändert',
                          ),
                          subtitle: Text(
                            'Basis ${_number(preview!['weekly_summary']['baseline_weekly_energy_kcal'])} kcal · danach ${_number(preview!['weekly_summary']['adjusted_weekly_energy_kcal'])} kcal',
                          ),
                        ),
                      CheckboxListTile(
                        value: linkPlans,
                        onChanged: (v) => setLocal(() => linkPlans = v!),
                        title: const Text(
                          'Anpassungen auf vorhandene Tagespläne anwenden',
                        ),
                        subtitle: const Text(
                          'Ohne Auswahl bleiben vorhandene Pläne unverändert.',
                        ),
                      ),
                      if (linkPlans)
                        CheckboxListTile(
                          value: createPlans,
                          onChanged: (v) => setLocal(() => createPlans = v!),
                          title: const Text(
                            'Fehlende leere Tagespläne erstellen',
                          ),
                          subtitle: const Text(
                            'Es werden keine Mahlzeiten hinzugefügt.',
                          ),
                        ),
                      if ((preview!['existing_adjustments'] as List).isNotEmpty)
                        CheckboxListTile(
                          value: confirmReplacement,
                          onChanged: (v) =>
                              setLocal(() => confirmReplacement = v!),
                          title: const Text(
                            'Vorhandene Anpassungen ausdrücklich ersetzen',
                          ),
                          subtitle: const Text(
                            'Bereits verknüpfte historische Pläne behalten ihren bisherigen Snapshot.',
                          ),
                        ),
                    ],
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: working ? null : () => Navigator.pop(dialog),
                child: const Text('Schließen'),
              ),
              if (preview != null)
                FilledButton(
                  onPressed:
                      working ||
                          ((preview!['existing_adjustments'] as List)
                                  .isNotEmpty &&
                              !confirmReplacement)
                      ? null
                      : () async {
                          setLocal(() => working = true);
                          try {
                            final dateValues = days
                                .map((v) => v['date'].toString())
                                .toList();
                            final replacements =
                                (preview!['existing_adjustments'] as List)
                                    .whereType<Map>()
                                    .map((v) => v['id'].toString())
                                    .toList();
                            await repository.apply(
                              request(),
                              preview!['preview_token'].toString(),
                              _uuid(),
                              replace: replacements,
                              link: linkPlans ? dateValues : [],
                              create: linkPlans && createPlans
                                  ? dateValues
                                  : [],
                            );
                            if (dialog.mounted) Navigator.pop(dialog);
                            await _load();
                            if (mounted) {
                              ScaffoldMessenger.of(this.context).showSnackBar(
                                const SnackBar(
                                  content: Text(
                                    'Temporäre Tagesziele wurden bestätigt.',
                                  ),
                                ),
                              );
                            }
                          } catch (exception) {
                            setLocal(() => working = false);
                            if (mounted) {
                              ScaffoldMessenger.of(this.context).showSnackBar(
                                SnackBar(content: Text(exception.toString())),
                              );
                            }
                          }
                        },
                  child: Text(
                    working ? 'Wird übernommen …' : 'Ausdrücklich bestätigen',
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _statusChange(Map<String, dynamic> item, String action) async {
    await repository.sessionStatus(item['id'].toString(), action);
    await _load();
  }

  Future<void> _delete(Map<String, dynamic> item) async {
    try {
      await repository.deleteSession(item['id'].toString());
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }
}

const _sports = {
  'strength_training': 'Krafttraining',
  'running': 'Laufen',
  'cycling': 'Radfahren',
  'swimming': 'Schwimmen',
  'triathlon': 'Triathlon',
  'team_sport': 'Teamsport',
  'american_football': 'American Football',
  'combat_sport': 'Kampfsport',
  'racquet_sport': 'Rückschlagsport',
  'rowing': 'Rudern',
  'hiking': 'Wandern',
  'mobility': 'Mobilität',
  'recovery': 'Regeneration',
  'other': 'Andere Sportart',
};
const _types = {
  'recovery': 'Regeneration',
  'technique': 'Technik',
  'easy_endurance': 'Lockere Ausdauer',
  'moderate_endurance': 'Mittlere Ausdauer',
  'hard_endurance': 'Harte Ausdauer',
  'interval': 'Intervalle',
  'strength': 'Kraft',
  'mixed': 'Gemischt',
  'competition': 'Wettkampf',
  'long_session': 'Lange Einheit',
  'other': 'Andere Einheit',
};
const _intensities = {
  'very_easy': 'Sehr leicht',
  'easy': 'Leicht',
  'moderate': 'Mittel',
  'hard': 'Hart',
  'very_hard': 'Sehr hart',
};
const _inclusions = {
  'unknown': 'Nicht einschätzbar',
  'included_in_baseline': 'Bereits im Basisziel enthalten',
  'additional_to_baseline': 'Zusätzlich zum Basisziel',
  'partially_included': 'Teilweise enthalten',
};
String _sport(Object? v) => _sports[v] ?? v.toString();
String _intensity(Object? v) => _intensities[v] ?? v.toString();
String _inclusion(Object? v) => _inclusions[v] ?? v.toString();
String _strategy(Object? v) =>
    const {
      'weekly_redistribution': 'Wöchentliche Umverteilung',
      'bounded_additive': 'Zusätzlicher Trainingsaufschlag',
      'custom_manual': 'Manuelle Anpassung',
      'none': 'Keine Zielanpassung',
    }[v] ??
    v.toString();
String _status(Object? v) =>
    const {
      'planned': 'Geplant',
      'completed': 'Als durchgeführt markiert',
      'cancelled': 'Abgesagt',
      'active': 'Aktiv',
      'superseded': 'Ersetzt',
    }[v] ??
    v.toString();
String _loadLabel(Object? v) =>
    const {
      'rest': 'Ruhetag',
      'recovery': 'Regeneration',
      'light': 'Leichte Planungsbelastung',
      'moderate': 'Mittlere Planungsbelastung',
      'high': 'Hohe Planungsbelastung',
      'very_high': 'Sehr hohe Planungsbelastung',
      'mixed_uncertain': 'Gemischt · unsicher',
    }[v] ??
    v.toString();
String _number(Object? v) => GermanDecimal.formatString(v);
String _signed(Object? v) {
  final n = double.tryParse(v?.toString() ?? '') ?? 0;
  return '${n > 0 ? '+' : ''}${GermanDecimal.format(n, decimals: n == n.roundToDouble() ? 0 : 1)}';
}

String _apiDate(DateTime v) =>
    '${v.year.toString().padLeft(4, '0')}-${v.month.toString().padLeft(2, '0')}-${v.day.toString().padLeft(2, '0')}';
TimeOfDay? _time(Object? v) {
  final parts = v?.toString().split(':');
  if (parts == null || parts.length < 2) return null;
  return TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
}

String _uuid() {
  final r = Random.secure();
  final b = List<int>.generate(16, (_) => r.nextInt(256));
  b[6] = (b[6] & 15) | 64;
  b[8] = (b[8] & 63) | 128;
  final h = b.map((v) => v.toRadixString(16).padLeft(2, '0')).join();
  return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-${h.substring(16, 20)}-${h.substring(20)}';
}
