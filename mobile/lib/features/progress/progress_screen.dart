import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import 'progress_repository.dart';
import 'progress_presentation.dart';
import 'energy_calibration_screen.dart';

final class ProgressScreen extends ConsumerStatefulWidget {
  const ProgressScreen({super.key});

  @override
  ConsumerState<ProgressScreen> createState() => _ProgressScreenState();
}

final class _ProgressScreenState extends ConsumerState<ProgressScreen> {
  Map<String, dynamic>? overview;
  List<Map<String, dynamic>> weights = [];
  List<Map<String, dynamic>> measurements = [];
  List<Map<String, dynamic>> compositions = [];
  List<Map<String, dynamic>> goals = [];
  bool loading = true;
  String? error;
  int window = 7;

  ProgressRepository get repository => ref.read(progressRepositoryProvider);

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
        repository.overview(window: window),
        repository.weights(),
        repository.measurements(),
        repository.composition(),
        repository.goals(),
      ]);
      if (!mounted) return;
      setState(() {
        overview = values[0] as Map<String, dynamic>;
        weights = ((values[1] as Map)['items'] as List)
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
        measurements = ((values[2] as Map)['items'] as List)
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
        compositions = ((values[3] as Map)['items'] as List)
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
        goals = values[4] as List<Map<String, dynamic>>;
        loading = false;
      });
    } catch (exception) {
      if (!mounted) return;
      setState(() {
        loading = false;
        error = exception.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
    length: 4,
    child: AppScaffold(
      title: 'Fortschritt',
      actions: [
        IconButton(
          onPressed: loading ? null : _load,
          icon: const Icon(Icons.refresh),
          tooltip: 'Aktualisieren',
        ),
      ],
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('add-progress-weight'),
        onPressed: () => _weightDialog(),
        icon: const Icon(Icons.add),
        label: const Text('Gewicht'),
      ),
      body: Column(
        children: [
          const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'Übersicht'),
              Tab(text: 'Gewicht'),
              Tab(text: 'Körpermaße'),
              Tab(text: 'Ziele'),
            ],
          ),
          Expanded(
            child: loading
                ? const Center(child: CircularProgressIndicator())
                : error != null
                ? _ErrorState(message: error!, retry: _load)
                : TabBarView(
                    children: [
                      _overview(),
                      _weightHistory(),
                      _body(),
                      _goals(),
                    ],
                  ),
          ),
        ],
      ),
    ),
  );

  Widget _overview() {
    final latest = Map<String, dynamic>.from(
      (overview?['latest'] as Map?) ?? {},
    );
    final trend = Map<String, dynamic>.from((overview?['trend'] as Map?) ?? {});
    final points =
        (((overview?['chart'] as Map?)?['points'] as List?) ?? const [])
            .cast<Map>();
    final quality = Map<String, dynamic>.from(
      (overview?['data_quality'] as Map?) ?? {},
    );
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ContentWidth(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (latest['raw_weight_kg'] == null)
                  _Empty(
                    title: 'Noch keine Gewichtsmessungen',
                    action: 'Ersten Messwert hinzufügen',
                    onTap: _weightDialog,
                  )
                else ...[
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      _Metric(
                        label: 'Letzter Messwert',
                        value:
                            '${GermanDecimal.formatString(latest['raw_weight_kg'])} kg',
                      ),
                      _Metric(
                        label: 'Gleitender Durchschnitt',
                        value: latest['trend_weight_kg'] == null
                            ? 'Noch nicht verfügbar'
                            : '${GermanDecimal.formatString(latest['trend_weight_kg'])} kg',
                      ),
                      _Metric(
                        label: 'Linearer Trend',
                        value: _trendLabel(trend),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  SegmentedButton<int>(
                    segments: const [
                      ButtonSegment(value: 7, label: Text('7 Tage')),
                      ButtonSegment(value: 14, label: Text('14 Tage')),
                      ButtonSegment(value: 28, label: Text('28 Tage')),
                    ],
                    selected: {window},
                    onSelectionChanged: (value) {
                      window = value.first;
                      _load();
                    },
                  ),
                  const SizedBox(height: 12),
                  Semantics(
                    label:
                        'Gewichtsdiagramm mit Rohwerten und gleitendem Durchschnitt. ${points.length} repräsentative Tage.',
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Gewichtsverlauf',
                              style: TextStyle(fontWeight: FontWeight.bold),
                            ),
                            const Text(
                              '● Messwert   ━ Gleitender Durchschnitt',
                            ),
                            SizedBox(
                              height: 180,
                              child: CustomPaint(
                                painter: ProgressChartPainter(
                                  points,
                                  Theme.of(context).colorScheme,
                                ),
                                size: Size.infinite,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.info_outline),
                    title: Text(
                      'Datengrundlage: ${quality['representative_day_count'] ?? 0} Messtage',
                    ),
                    subtitle: const Text(
                      'Rohwerte und berechnete Trends bleiben klar getrennt. Fehlende Tage werden nicht interpoliert.',
                    ),
                  ),
                ),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.tune),
                    title: const Text('Energie-Ziel kalibrieren'),
                    subtitle: const Text(
                      'Gewichtsverlauf prüfen und eine konservative Anpassung bewusst bestätigen.',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => const EnergyCalibrationScreen(),
                      ),
                    ),
                  ),
                ),
                for (final warning
                    in ((overview?['warnings'] as List?) ?? const [])
                        .cast<Map>())
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.info_outline),
                      title: Text(warning['explanation_de'].toString()),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _weightHistory() => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      const Text(
        'Alle Rohmessungen',
        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
      ),
      const Text('Mehrere Messungen am selben Tag bleiben einzeln erhalten.'),
      for (final item in weights)
        Card(
          child: ListTile(
            title: Text(
              '${GermanDecimal.formatString(item['entered_weight'])} ${item['entered_unit']}',
            ),
            subtitle: Text(
              '${item['observed_on']}${item['observed_time'] == null ? '' : ' · ${item['observed_time']}'}${item['measurement_context'] == 'unspecified' ? '' : ' · ${_context(item['measurement_context'])}'}${item['note'] == null ? '' : '\nNotiz vorhanden'}',
            ),
            leading: item['source_type'] == 'assessment'
                ? const Tooltip(
                    message: 'Aus einer Ernährungseinschätzung übernommen',
                    child: Icon(Icons.assessment_outlined),
                  )
                : const Tooltip(
                    message: 'Manuell eingetragener Messwert',
                    child: Icon(Icons.edit_outlined),
                  ),
            onTap: () => _weightDialog(existing: item),
            trailing: IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Messwert dauerhaft löschen',
              onPressed: () => _deleteWeight(item),
            ),
          ),
        ),
    ],
  );

  Widget _body() => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      FilledButton.tonalIcon(
        onPressed: _measurementDialog,
        icon: const Icon(Icons.straighten),
        label: const Text('Körpermaß hinzufügen'),
      ),
      OutlinedButton.icon(
        onPressed: _compositionDialog,
        icon: const Icon(Icons.monitor_weight_outlined),
        label: const Text('Körperzusammensetzung hinzufügen'),
      ),
      const Padding(
        padding: EdgeInsets.only(top: 12),
        child: Text(
          'Körpermaße',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
      for (final item in measurements)
        ListTile(
          title: Text(_measurementLabel(item['measurement_type'])),
          subtitle: Text(
            '${GermanDecimal.formatString(item['entered_value'])} ${item['entered_unit']} · ${item['observed_on']}',
          ),
        ),
      const Padding(
        padding: EdgeInsets.only(top: 12),
        child: Text(
          'Körperzusammensetzung',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
      const Text(
        'Werte verschiedener Messmethoden sind nur eingeschränkt direkt vergleichbar.',
      ),
      for (final item in compositions)
        ListTile(
          title: Text(_compositionValue(item)),
          subtitle: Text(
            '${_method(item['measurement_method'])} · ${item['observed_on']}',
          ),
        ),
    ],
  );

  Widget _goals() {
    final active = goals.where((g) => g['status'] == 'active').firstOrNull;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (active == null)
          _Empty(
            title: 'Noch kein aktives Fortschrittsziel',
            action: 'Ziel festlegen',
            onTap: _goalDialog,
          )
        else
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _goalLabel(active['goal_type']),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  Text('Start: ${active['start_date']}'),
                  Text(_goalTarget(active)),
                  if (active['target_date'] != null)
                    Text('Zieldatum: ${active['target_date']}'),
                  const Text(
                    'Fortschritt wird bevorzugt anhand des gleitenden Durchschnitts berechnet.',
                  ),
                  Wrap(
                    children: [
                      TextButton(
                        onPressed: () => _goalStatus(active, true),
                        child: const Text('Ziel abschließen'),
                      ),
                      TextButton(
                        onPressed: () => _goalStatus(active, false),
                        child: const Text('Ziel abbrechen'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        FilledButton.tonal(
          onPressed: _goalDialog,
          child: Text(
            active == null ? 'Ziel festlegen' : 'Neues Ziel festlegen',
          ),
        ),
        const Divider(),
        const Text(
          'Frühere Ziele',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        for (final goal in goals.where((g) => g['status'] != 'active'))
          ListTile(
            title: Text(_goalLabel(goal['goal_type'])),
            subtitle: Text('${goal['status']} · ${goal['start_date']}'),
          ),
      ],
    );
  }

  Future<void> _weightDialog({Map<String, dynamic>? existing}) async {
    final controller = TextEditingController(
      text: existing == null
          ? ''
          : GermanDecimal.formatString(existing['entered_weight']),
    );
    final note = TextEditingController(
      text: existing?['note']?.toString() ?? '',
    );
    var unit = existing?['entered_unit']?.toString() ?? 'kg';
    var contextValue =
        existing?['measurement_context']?.toString() ?? 'unspecified';
    var day =
        DateTime.tryParse(existing?['observed_on']?.toString() ?? '') ??
        DateTime.now();
    var observationTime = _parseTime(existing?['observed_time']);
    var saving = false;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(
            existing == null ? 'Gewicht hinzufügen' : 'Messwert bearbeiten',
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  key: const Key('progress-weight-input'),
                  controller: controller,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: const InputDecoration(
                    labelText: 'Gewicht',
                    hintText: 'z. B. 82,5',
                  ),
                ),
                DropdownButtonFormField(
                  initialValue: unit,
                  decoration: const InputDecoration(labelText: 'Einheit'),
                  items: const [
                    DropdownMenuItem(value: 'kg', child: Text('Kilogramm')),
                    DropdownMenuItem(value: 'lb', child: Text('Pfund')),
                  ],
                  onChanged: (v) => setDialogState(() => unit = v!),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Datum'),
                  subtitle: Text('${day.day}.${day.month}.${day.year}'),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: context,
                      firstDate: DateTime(2000),
                      lastDate: DateTime.now(),
                      initialDate: day,
                    );
                    if (picked != null) setDialogState(() => day = picked);
                  },
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Uhrzeit optional'),
                  subtitle: Text(
                    observationTime == null
                        ? 'Nicht angegeben'
                        : observationTime!.format(context),
                  ),
                  trailing: observationTime == null
                      ? const Icon(Icons.schedule)
                      : IconButton(
                          tooltip: 'Uhrzeit entfernen',
                          onPressed: () =>
                              setDialogState(() => observationTime = null),
                          icon: const Icon(Icons.clear),
                        ),
                  onTap: () async {
                    final picked = await showTimePicker(
                      context: context,
                      initialTime: observationTime ?? TimeOfDay.now(),
                    );
                    if (picked != null) {
                      setDialogState(() => observationTime = picked);
                    }
                  },
                ),
                DropdownButtonFormField(
                  initialValue: contextValue,
                  decoration: const InputDecoration(
                    labelText: 'Messsituation optional',
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'unspecified',
                      child: Text('Nicht angegeben'),
                    ),
                    DropdownMenuItem(value: 'morning', child: Text('Morgens')),
                    DropdownMenuItem(value: 'evening', child: Text('Abends')),
                    DropdownMenuItem(
                      value: 'before_meal',
                      child: Text('Vor einer Mahlzeit'),
                    ),
                    DropdownMenuItem(
                      value: 'after_meal',
                      child: Text('Nach einer Mahlzeit'),
                    ),
                    DropdownMenuItem(
                      value: 'after_training',
                      child: Text('Nach dem Training'),
                    ),
                    DropdownMenuItem(
                      value: 'other',
                      child: Text('Andere Situation'),
                    ),
                  ],
                  onChanged: (v) => setDialogState(() => contextValue = v!),
                ),
                TextField(
                  controller: note,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Private Notiz optional',
                  ),
                ),
                if (unit == 'lb' &&
                    GermanDecimal.tryParse(controller.text) != null)
                  Text(
                    'Entspricht ungefähr ${GermanDecimal.format(convertWeightToKilograms(GermanDecimal.parse(controller.text), unit), decimals: 2)} kg',
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(dialogContext),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      final value = GermanDecimal.tryParse(controller.text);
                      if (value == null) return;
                      setDialogState(() => saving = true);
                      final data = {
                        'observed_on': _isoDate(day),
                        'observed_time': observationTime == null
                            ? null
                            : '${observationTime!.hour.toString().padLeft(2, '0')}:${observationTime!.minute.toString().padLeft(2, '0')}:00',
                        'entered_weight': value.toString(),
                        'entered_unit': unit,
                        'measurement_context': contextValue,
                        'note': note.text.trim().isEmpty
                            ? null
                            : note.text.trim(),
                        if (existing != null)
                          'expected_version': existing['version'],
                      };
                      try {
                        await repository.saveWeight(
                          data,
                          id: existing?['id']?.toString(),
                        );
                        if (dialogContext.mounted) Navigator.pop(dialogContext);
                        await _load();
                      } on AppException catch (exception) {
                        if (exception.code ==
                                'PROGRESS_PLAUSIBILITY_CONFIRMATION_REQUIRED' &&
                            dialogContext.mounted) {
                          final confirm = await showDialog<bool>(
                            context: dialogContext,
                            builder: (confirmContext) => AlertDialog(
                              title: const Text('Eingabe prüfen'),
                              content: Text(exception.message),
                              actions: [
                                TextButton(
                                  onPressed: () =>
                                      Navigator.pop(confirmContext, false),
                                  child: const Text('Zurück'),
                                ),
                                FilledButton(
                                  onPressed: () =>
                                      Navigator.pop(confirmContext, true),
                                  child: const Text('Trotzdem speichern'),
                                ),
                              ],
                            ),
                          );
                          if (confirm == true) {
                            data['confirm_unusual_change'] = true;
                            await repository.saveWeight(
                              data,
                              id: existing?['id']?.toString(),
                            );
                            if (dialogContext.mounted) {
                              Navigator.pop(dialogContext);
                            }
                            await _load();
                          }
                        } else if (mounted) {
                          ScaffoldMessenger.of(this.context).showSnackBar(
                            SnackBar(content: Text(exception.message)),
                          );
                        }
                      } finally {
                        if (dialogContext.mounted) {
                          setDialogState(() => saving = false);
                        }
                      }
                    },
              child: Text(saving ? 'Speichert…' : 'Speichern'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _deleteWeight(Map<String, dynamic> item) async {
    final confirmed =
        await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Messwert dauerhaft löschen?'),
            content: const Text(
              'Der ausgewählte Messwert wird vollständig entfernt. Trends werden anschließend neu berechnet.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Abbrechen'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Dauerhaft löschen'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed) return;
    await repository.deleteWeight(
      item['id'].toString(),
      item['version'] as int,
    );
    await _load();
  }

  Future<void> _measurementDialog() async {
    final value = TextEditingController();
    var type = 'waist';
    var unit = 'cm';
    await showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Körpermaß hinzufügen'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField(
                initialValue: type,
                decoration: const InputDecoration(labelText: 'Messart'),
                items: _measurementTypes.entries
                    .map(
                      (e) =>
                          DropdownMenuItem(value: e.key, child: Text(e.value)),
                    )
                    .toList(),
                onChanged: (v) => setState(() => type = v!),
              ),
              TextField(
                controller: value,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(labelText: 'Umfang'),
              ),
              DropdownButtonFormField(
                initialValue: unit,
                items: const [
                  DropdownMenuItem(value: 'cm', child: Text('Zentimeter')),
                  DropdownMenuItem(value: 'in', child: Text('Zoll')),
                ],
                onChanged: (v) => setState(() => unit = v!),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () async {
                final parsed = GermanDecimal.tryParse(value.text);
                if (parsed == null) return;
                await repository.addMeasurement({
                  'measurement_type': type,
                  'observed_on': _isoDate(DateTime.now()),
                  'entered_value': parsed.toString(),
                  'entered_unit': unit,
                  'measurement_method': 'tape_measure',
                });
                if (context.mounted) Navigator.pop(context);
                await _load();
              },
              child: const Text('Speichern'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _compositionDialog() async {
    final fat = TextEditingController();
    final lean = TextEditingController();
    final mass = TextEditingController();
    var method = 'unspecified';
    await showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Körperzusammensetzung'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: fat,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: const InputDecoration(
                    labelText: 'Körperfettwert % optional',
                  ),
                ),
                TextField(
                  controller: lean,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: const InputDecoration(
                    labelText: 'Fettfreie Masse kg optional',
                  ),
                ),
                TextField(
                  controller: mass,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: const InputDecoration(
                    labelText: 'Fettmasse kg optional',
                  ),
                ),
                DropdownButtonFormField(
                  initialValue: method,
                  decoration: const InputDecoration(labelText: 'Messmethode'),
                  items: _methods.entries
                      .map(
                        (e) => DropdownMenuItem(
                          value: e.key,
                          child: Text(e.value),
                        ),
                      )
                      .toList(),
                  onChanged: (v) => setState(() => method = v!),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () async {
                final a = GermanDecimal.tryParse(fat.text),
                    b = GermanDecimal.tryParse(lean.text),
                    c = GermanDecimal.tryParse(mass.text);
                if (a == null && b == null && c == null) return;
                await repository.addComposition({
                  'observed_on': _isoDate(DateTime.now()),
                  'body_fat_percent': a?.toString(),
                  'lean_mass_kg': b?.toString(),
                  'fat_mass_kg': c?.toString(),
                  'measurement_method': method,
                });
                if (context.mounted) Navigator.pop(context);
                await _load();
              },
              child: const Text('Speichern'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _goalDialog() async {
    var type = 'lose_weight';
    final target = TextEditingController();
    final min = TextEditingController();
    final max = TextEditingController();
    final hasActive = goals.any((g) => g['status'] == 'active');
    await showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Fortschrittsziel festlegen'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField(
                initialValue: type,
                items: const [
                  DropdownMenuItem(
                    value: 'lose_weight',
                    child: Text('Gewicht reduzieren'),
                  ),
                  DropdownMenuItem(
                    value: 'gain_weight',
                    child: Text('Gewicht erhöhen'),
                  ),
                  DropdownMenuItem(
                    value: 'maintain_weight',
                    child: Text('Zielbereich halten'),
                  ),
                  DropdownMenuItem(
                    value: 'custom',
                    child: Text('Eigenes Gewichtsziel'),
                  ),
                ],
                onChanged: (v) => setState(() => type = v!),
              ),
              if (type == 'maintain_weight') ...[
                TextField(
                  controller: min,
                  decoration: const InputDecoration(
                    labelText: 'Zielbereich von kg',
                  ),
                ),
                TextField(
                  controller: max,
                  decoration: const InputDecoration(
                    labelText: 'Zielbereich bis kg',
                  ),
                ),
              ] else
                TextField(
                  controller: target,
                  decoration: const InputDecoration(
                    labelText: 'Zielgewicht kg',
                  ),
                ),
              const Text(
                'Dieses Ziel ändert keine Ernährungsziele automatisch.',
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () async {
                if (hasActive) {
                  final replace = await showDialog<bool>(
                    context: context,
                    builder: (c) => AlertDialog(
                      title: const Text('Aktives Ziel ersetzen?'),
                      content: const Text(
                        'Das bisherige Ziel bleibt als ersetzt in der Historie erhalten.',
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(c, false),
                          child: const Text('Nein'),
                        ),
                        FilledButton(
                          onPressed: () => Navigator.pop(c, true),
                          child: const Text('Ersetzen'),
                        ),
                      ],
                    ),
                  );
                  if (replace != true) return;
                }
                await repository.addGoal({
                  'goal_type': type,
                  'start_date': _isoDate(DateTime.now()),
                  'use_latest_weight': true,
                  'target_weight_kg': type == 'maintain_weight'
                      ? null
                      : GermanDecimal.tryParse(target.text)?.toString(),
                  'target_weight_min_kg': type == 'maintain_weight'
                      ? GermanDecimal.tryParse(min.text)?.toString()
                      : null,
                  'target_weight_max_kg': type == 'maintain_weight'
                      ? GermanDecimal.tryParse(max.text)?.toString()
                      : null,
                  'replace_active': hasActive,
                });
                if (context.mounted) Navigator.pop(context);
                await _load();
              },
              child: const Text('Speichern'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _goalStatus(Map<String, dynamic> goal, bool complete) async {
    if (complete) {
      await repository.completeGoal(
        goal['id'].toString(),
        goal['version'] as int,
      );
    } else {
      await repository.cancelGoal(
        goal['id'].toString(),
        goal['version'] as int,
      );
    }
    await _load();
  }
}

final class ProgressChartPainter extends CustomPainter {
  ProgressChartPainter(this.points, this.colors);
  final List<Map> points;
  final ColorScheme colors;
  @override
  void paint(Canvas canvas, Size size) {
    if (points.isEmpty) return;
    final values = points
        .expand((p) => [p['representative_value_kg'], p['rolling_average_kg']])
        .where((v) => v != null)
        .map((v) => double.parse(v.toString()))
        .toList();
    if (values.isEmpty) return;
    final min = values.reduce((a, b) => a < b ? a : b),
        max = values.reduce((a, b) => a > b ? a : b),
        span = (max - min).abs() < 0.1 ? 1 : max - min;
    Offset point(int i, double v) => Offset(
      points.length == 1
          ? size.width / 2
          : i * size.width / (points.length - 1),
      size.height - (v - min) / span * size.height,
    );
    final raw = Paint()
      ..color = colors.primary
      ..style = PaintingStyle.fill;
    final line = Paint()
      ..color = colors.tertiary
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke;
    final path = Path();
    var started = false;
    for (var i = 0; i < points.length; i++) {
      final rawValue = double.tryParse(
        points[i]['representative_value_kg'].toString(),
      );
      if (rawValue != null) canvas.drawCircle(point(i, rawValue), 4, raw);
      final rolling = double.tryParse(
        points[i]['rolling_average_kg']?.toString() ?? '',
      );
      if (rolling != null) {
        final p = point(i, rolling);
        if (!started) {
          path.moveTo(p.dx, p.dy);
          started = true;
        } else {
          path.lineTo(p.dx, p.dy);
        }
      }
    }
    canvas.drawPath(path, line);
  }

  @override
  bool shouldRepaint(covariant ProgressChartPainter old) =>
      old.points != points || old.colors != colors;
}

final class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});
  final String label, value;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 180,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label),
            Text(value, style: Theme.of(context).textTheme.titleLarge),
          ],
        ),
      ),
    ),
  );
}

final class _Empty extends StatelessWidget {
  const _Empty({
    required this.title,
    required this.action,
    required this.onTap,
  });
  final String title, action;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          const Icon(Icons.show_chart, size: 48),
          Text(title),
          FilledButton(onPressed: onTap, child: Text(action)),
        ],
      ),
    ),
  );
}

final class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.retry});
  final String message;
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) => Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(message),
        FilledButton(onPressed: retry, child: const Text('Erneut versuchen')),
      ],
    ),
  );
}

const _measurementTypes = {
  'waist': 'Taille',
  'hip': 'Hüfte',
  'neck': 'Hals',
  'chest': 'Brust',
  'upper_arm_left': 'Oberarm links',
  'upper_arm_right': 'Oberarm rechts',
  'thigh_left': 'Oberschenkel links',
  'thigh_right': 'Oberschenkel rechts',
  'calf_left': 'Wade links',
  'calf_right': 'Wade rechts',
  'other': 'Andere Messung',
};
const _methods = {
  'bioelectrical_impedance': 'Bioelektrische Impedanz',
  'caliper': 'Caliper',
  'dexa': 'DEXA',
  'hydrostatic': 'Hydrostatisch',
  'manual_estimate': 'Manuelle Schätzung',
  'other': 'Andere',
  'unspecified': 'Nicht angegeben',
};
String _isoDate(DateTime date) =>
    '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
TimeOfDay? _parseTime(Object? value) {
  final parts = value?.toString().split(':') ?? const [];
  if (parts.length < 2) return null;
  final hour = int.tryParse(parts[0]);
  final minute = int.tryParse(parts[1]);
  if (hour == null || minute == null) return null;
  return TimeOfDay(hour: hour, minute: minute);
}

String _context(Object? value) =>
    {
      'morning': 'Morgens',
      'evening': 'Abends',
      'before_meal': 'Vor einer Mahlzeit',
      'after_meal': 'Nach einer Mahlzeit',
      'after_training': 'Nach dem Training',
      'other': 'Andere Situation',
    }[value] ??
    'Nicht angegeben';
String _measurementLabel(Object? value) =>
    _measurementTypes[value] ?? value.toString();
String _method(Object? value) => _methods[value] ?? value.toString();
String _trendLabel(Map<String, dynamic> trend) {
  if (trend['available'] != true) return 'Daten noch nicht ausreichend';
  final direction = progressTrendDirection(trend['direction']);
  return '$direction · ${GermanDecimal.formatString(trend['kg_per_week'])} kg/Woche';
}

String _compositionValue(Map<String, dynamic> item) => [
  if (item['body_fat_percent'] != null)
    'Körperfett ${GermanDecimal.formatString(item['body_fat_percent'])} %',
  if (item['lean_mass_kg'] != null)
    'Fettfreie Masse ${GermanDecimal.formatString(item['lean_mass_kg'])} kg',
  if (item['fat_mass_kg'] != null)
    'Fettmasse ${GermanDecimal.formatString(item['fat_mass_kg'])} kg',
].join(' · ');
String _goalLabel(Object? value) =>
    {
      'lose_weight': 'Gewicht reduzieren',
      'gain_weight': 'Gewicht erhöhen',
      'maintain_weight': 'Zielbereich halten',
      'custom': 'Eigenes Gewichtsziel',
    }[value] ??
    'Fortschrittsziel';
String _goalTarget(Map<String, dynamic> goal) =>
    goal['target_weight_kg'] != null
    ? 'Zielwert: ${GermanDecimal.formatString(goal['target_weight_kg'])} kg'
    : 'Zielbereich: ${GermanDecimal.formatString(goal['target_weight_min_kg'])}–${GermanDecimal.formatString(goal['target_weight_max_kg'])} kg';
