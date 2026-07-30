import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import 'progress_repository.dart';

final class EnergyCalibrationScreen extends ConsumerStatefulWidget {
  const EnergyCalibrationScreen({super.key});

  @override
  ConsumerState<EnergyCalibrationScreen> createState() =>
      _EnergyCalibrationScreenState();
}

final class _EnergyCalibrationScreenState
    extends ConsumerState<EnergyCalibrationScreen> {
  bool loading = true;
  bool working = false;
  String? error;
  Map<String, dynamic>? eligibility;
  List<Map<String, dynamic>> windows = [];
  List<Map<String, dynamic>> history = [];
  Map<String, dynamic>? selected;
  Map<String, dynamic>? preview;
  String adherence = 'high';
  String contextStability = 'stable';

  ProgressRepository get repository => ref.read(progressRepositoryProvider);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final values = await Future.wait([
        repository.calibrationEligibility(),
        repository.calibrationWindows(),
        repository.calibrationHistory(),
      ]);
      if (!mounted) return;
      final available = values[1] as List<Map<String, dynamic>>;
      setState(() {
        eligibility = values[0] as Map<String, dynamic>;
        windows = available;
        history = values[2] as List<Map<String, dynamic>>;
        selected = eligibility?['source_assessment_id'] == null
            ? null
            : available.where((item) => item['eligible'] == true).firstOrNull;
        loading = false;
        error = null;
      });
    } catch (exception) {
      if (mounted) {
        setState(() {
          loading = false;
          error = exception.toString();
        });
      }
    }
  }

  Map<String, dynamic> _request() => {
    'source_assessment_id': eligibility?['source_assessment_id'],
    'window_start': selected!['start_date'],
    'window_end': selected!['end_date'],
    'adherence': adherence,
    'context_stability': contextStability,
  };

  Future<void> _createPreview() async {
    setState(() {
      working = true;
      preview = null;
      error = null;
    });
    try {
      final value = await repository.calibrationPreview(_request());
      if (mounted) {
        setState(() {
          preview = value;
          working = false;
        });
      }
    } catch (exception) {
      if (mounted) {
        setState(() {
          error = exception.toString();
          working = false;
        });
      }
    }
  }

  Future<void> _apply() async {
    final proposal = Map<String, dynamic>.from(preview!['proposal'] as Map);
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Neues Energie-Ziel bestätigen?'),
        content: Text(
          'Anpassung: ${_signed(proposal['proposed_adjustment_kcal_per_day'])} kcal/Tag\n'
          'Neues Ziel: ${GermanDecimal.formatString(proposal['proposed_target_kcal_per_day'])} kcal/Tag\n\n'
          'Die bisherige Einschätzung und bestehende Pläne bleiben unverändert. Es wird eine neue Einschätzungsrevision erstellt.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Anpassung übernehmen'),
          ),
        ],
      ),
    );
    if (accepted != true) return;
    setState(() => working = true);
    try {
      await repository.applyCalibration(
        _request(),
        preview!['preview_token'].toString(),
        _uuid(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Neue Einschätzungsrevision wurde erstellt.'),
        ),
      );
      preview = null;
      await _load();
    } catch (exception) {
      if (mounted) {
        setState(() {
          error = exception.toString();
          working = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Energie-Ziel kalibrieren',
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [ContentWidth(child: _content())],
          ),
  );

  Widget _content() {
    final proposal = preview?['proposal'] is Map
        ? Map<String, dynamic>.from(preview!['proposal'] as Map)
        : null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Card(
          child: ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('Schätzung, keine Messung'),
            subtitle: Text(
              'Der Gewichtsverlauf kann Hinweise für eine vorsichtige Korrektur geben. Er misst weder deine tatsächliche Energieaufnahme noch deinen Energieverbrauch.',
            ),
          ),
        ),
        if (error != null)
          Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(error!),
            ),
          ),
        if (selected == null)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                'Noch nicht genügend geeignete Daten. Benötigt werden mindestens 21 Tage, 8 repräsentative Messtage, 3 Kalenderwochen und Messungen am Anfang sowie Ende des Fensters. Aktuell: ${eligibility?['representative_days'] ?? 0} Messtage.',
              ),
            ),
          )
        else ...[
          DropdownButtonFormField<Map<String, dynamic>>(
            initialValue: selected,
            decoration: const InputDecoration(labelText: 'Auswertungsfenster'),
            items: windows
                .where((item) => item['eligible'] == true)
                .map(
                  (item) => DropdownMenuItem(
                    value: item,
                    child: Text(
                      '${item['start_date']} bis ${item['end_date']} · ${item['representative_days']} Messtage',
                    ),
                  ),
                )
                .toList(),
            onChanged: (value) => setState(() {
              selected = value;
              preview = null;
            }),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: adherence,
            decoration: const InputDecoration(
              labelText: 'Wie gut wurde das bisherige Ziel eingehalten?',
            ),
            items: const [
              DropdownMenuItem(
                value: 'high',
                child: Text('Weitgehend eingehalten'),
              ),
              DropdownMenuItem(
                value: 'moderate',
                child: Text('Teilweise eingehalten'),
              ),
              DropdownMenuItem(value: 'low', child: Text('Kaum eingehalten')),
              DropdownMenuItem(
                value: 'unknown',
                child: Text('Nicht einschätzbar'),
              ),
            ],
            onChanged: (value) => setState(() {
              adherence = value!;
              preview = null;
            }),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: contextStability,
            decoration: const InputDecoration(
              labelText: 'Haben sich Aktivität oder Alltag verändert?',
            ),
            items: const [
              DropdownMenuItem(
                value: 'stable',
                child: Text('Nein, weitgehend stabil'),
              ),
              DropdownMenuItem(
                value: 'minor_changes',
                child: Text('Kleinere Änderungen'),
              ),
              DropdownMenuItem(
                value: 'major_changes',
                child: Text('Deutliche Änderungen'),
              ),
              DropdownMenuItem(
                value: 'unknown',
                child: Text('Nicht einschätzbar'),
              ),
            ],
            onChanged: (value) => setState(() {
              contextStability = value!;
              preview = null;
            }),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: working ? null : _createPreview,
            icon: const Icon(Icons.calculate_outlined),
            label: Text(working ? 'Wird geprüft …' : 'Vorschlag prüfen'),
          ),
        ],
        if (proposal != null)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: proposal['available'] == true
                    ? [
                        Text(
                          'Vorgeschlagene Anpassung: ${_signed(proposal['proposed_adjustment_kcal_per_day'])} kcal/Tag',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        Text(
                          'Neuer Bereich: ${GermanDecimal.formatString(proposal['proposed_target_lower_kcal_per_day'])}–${GermanDecimal.formatString(proposal['proposed_target_upper_kcal_per_day'])} kcal/Tag',
                        ),
                        Text(
                          'Unsicherheitsbereich der rechnerischen Anpassung: ${GermanDecimal.formatString(proposal['adjustment_lower_kcal_per_day'])} bis ${GermanDecimal.formatString(proposal['adjustment_upper_kcal_per_day'])} kcal/Tag',
                        ),
                        const SizedBox(height: 12),
                        FilledButton(
                          onPressed: working ? null : _apply,
                          child: const Text('Prüfen und übernehmen'),
                        ),
                      ]
                    : [
                        const Text(
                          'Keine belastbare Anpassung vorgeschlagen',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        Text(_reason(proposal['reason']?.toString())),
                      ],
              ),
            ),
          ),
        if (history.isNotEmpty) ...[
          const SizedBox(height: 20),
          Text(
            'Bisherige Kalibrierungen',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          for (final item in history)
            ListTile(
              leading: Icon(
                item['status'] == 'accepted'
                    ? Icons.check_circle_outline
                    : Icons.history,
              ),
              title: Text(
                '${_status(item['status'])}${item['accepted_adjustment_kcal_per_day'] == null ? '' : ' · ${_signed(item['accepted_adjustment_kcal_per_day'])} kcal/Tag'}',
              ),
              subtitle: Text(
                '${item['window_start']} bis ${item['window_end']}',
              ),
            ),
        ],
      ],
    );
  }
}

String _signed(Object? value) {
  final number = double.tryParse(value?.toString() ?? '') ?? 0;
  return '${number > 0 ? '+' : ''}${GermanDecimal.format(number, decimals: 0)}';
}

String _reason(String? value) => switch (value) {
  'ADHERENCE_BLOCKED' =>
    'Ohne ausreichend eingehaltenes Ziel wäre eine Korrektur nicht belastbar.',
  'CONTEXT_BLOCKED' =>
    'Deutliche oder unbekannte Änderungen im Alltag verhindern eine belastbare Zuordnung.',
  'UNCERTAINTY_CROSSES_ZERO' =>
    'Der Unsicherheitsbereich umfasst keine Änderung. Das bisherige Ziel bleibt bestehen.',
  'WITHIN_DEADBAND' =>
    'Die berechnete Abweichung ist klein. Das bisherige Ziel bleibt bestehen.',
  _ => 'Die Datengrundlage reicht für einen Vorschlag noch nicht aus.',
};

String _status(Object? value) => switch (value) {
  'accepted' => 'Übernommen',
  'declined' => 'Abgelehnt',
  'superseded' => 'Durch neuere Kalibrierung ersetzt',
  _ => value.toString(),
};

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
