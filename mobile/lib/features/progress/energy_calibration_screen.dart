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
  String method = 'target_response_proxy';
  String recordingConfidence = 'high';
  String routineRepresentativeness = 'representative';
  final Set<String> excludedConsumptionDays = {};
  final Set<String> confirmedConditionalDays = {};

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
        method == 'intake_informed'
            ? repository.intakeCalibrationWindows()
            : repository.calibrationWindows(),
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
    'method': method,
    'source_assessment_id': eligibility?['source_assessment_id'],
    'window_start': selected!['start_date'],
    'window_end': selected!['end_date'],
    'adherence': adherence,
    'context_stability': contextStability,
    if (method == 'intake_informed') ...{
      'recording_confidence': recordingConfidence,
      'routine_representativeness': routineRepresentativeness,
      'excluded_consumption_day_ids': excludedConsumptionDays.toList(),
      'conditional_day_confirmations': confirmedConditionalDays.toList(),
    },
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
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(
              value: 'target_response_proxy',
              label: Text('Zielbasiert'),
              icon: Icon(Icons.flag_outlined),
            ),
            ButtonSegment(
              value: 'intake_informed',
              label: Text('Aufnahmebasiert'),
              icon: Icon(Icons.restaurant_outlined),
            ),
          ],
          selected: {method},
          onSelectionChanged: working
              ? null
              : (value) {
                  setState(() {
                    method = value.first;
                    loading = true;
                    preview = null;
                    selected = null;
                  });
                  _load();
                },
        ),
        const SizedBox(height: 8),
        Text(
          method == 'intake_informed'
              ? 'Die aufnahmebasierte Methode nutzt deine finalisierten Verzehrtage. Sie reduziert die Annahme, dass ein Zielwert eingehalten wurde, bleibt aber von der Vollständigkeit der Aufzeichnung abhängig.'
              : 'Die zielbasierte Methode verwendet dein bisheriges Energie-Ziel als Näherung und benötigt eine Einschätzung zur Zieltreue.',
        ),
        const SizedBox(height: 12),
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
          if (method == 'target_response_proxy')
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
          if (method == 'target_response_proxy') const SizedBox(height: 12),
          if (method == 'target_response_proxy')
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
          if (method == 'intake_informed') ...[
            DropdownButtonFormField<String>(
              initialValue: recordingConfidence,
              decoration: const InputDecoration(
                labelText: 'Wie vollständig und genau wurde aufgezeichnet?',
              ),
              items: const [
                DropdownMenuItem(value: 'high', child: Text('Hoch')),
                DropdownMenuItem(value: 'moderate', child: Text('Moderat')),
                DropdownMenuItem(value: 'low', child: Text('Niedrig')),
                DropdownMenuItem(value: 'unknown', child: Text('Unbekannt')),
              ],
              onChanged: (value) => setState(() {
                recordingConfidence = value!;
                preview = null;
              }),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: routineRepresentativeness,
              decoration: const InputDecoration(
                labelText: 'Wie typisch war dein Alltag?',
              ),
              items: const [
                DropdownMenuItem(
                  value: 'representative',
                  child: Text('Repräsentativ'),
                ),
                DropdownMenuItem(
                  value: 'minor_changes',
                  child: Text('Kleinere Änderungen'),
                ),
                DropdownMenuItem(
                  value: 'major_changes',
                  child: Text('Deutliche Änderungen'),
                ),
                DropdownMenuItem(value: 'unknown', child: Text('Unbekannt')),
              ],
              onChanged: (value) => setState(() {
                routineRepresentativeness = value!;
                preview = null;
              }),
            ),
          ],
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
        if (method == 'intake_informed' && preview != null && proposal == null)
          Card(
            child: ListTile(
              leading: const Icon(Icons.balance_outlined),
              title: Text(
                preview?['calculation']?['result'] == 'direction_uncertain'
                    ? 'Richtung der Anpassung nicht eindeutig'
                    : preview?['eligibility']?['eligible'] == true
                    ? 'Keine relevante Anpassung vorgeschlagen'
                    : 'Datengrundlage noch nicht ausreichend',
              ),
              subtitle: Text(
                preview?['eligibility']?['eligible'] == true
                    ? 'Das bisherige Ziel bleibt bestehen. Die Unsicherheit erlaubt derzeit keine sinnvolle Änderung.'
                    : '${(preview?['blockers'] as List?)?.length ?? 0} Voraussetzungen sind noch nicht erfüllt.',
              ),
            ),
          ),
        if (method == 'intake_informed' && preview != null)
          _intakeEvidenceCard(),
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

  Widget _intakeEvidenceCard() {
    final intake = Map<String, dynamic>.from(
      preview?['intake_evidence'] as Map? ?? const {},
    );
    final calculation = Map<String, dynamic>.from(
      preview?['calculation'] as Map? ?? const {},
    );
    final days = (intake['days'] as List? ?? const [])
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Aufnahme-Evidenz',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(
              '${intake['usable_day_count'] ?? 0} nutzbare Tage · '
              '${GermanDecimal.formatString(intake['mean_recorded_intake_kcal'])} kcal/Tag im Mittel',
            ),
            if (intake['final_lower_kcal'] != null)
              Text(
                'Aufnahme-Unsicherheitsbereich: ${GermanDecimal.formatString(intake['final_lower_kcal'])}–${GermanDecimal.formatString(intake['final_upper_kcal'])} kcal/Tag',
              ),
            if (calculation['estimated_tdee_central_kcal'] != null)
              Text(
                'Geschätzter Verbrauch: ${GermanDecimal.formatString(calculation['estimated_tdee_central_kcal'])} kcal/Tag '
                '(${GermanDecimal.formatString(calculation['estimated_tdee_lower_kcal'])}–${GermanDecimal.formatString(calculation['estimated_tdee_upper_kcal'])})',
              ),
            const Divider(),
            const Text(
              'Verzehrtage prüfen',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            for (final day in days)
              CheckboxListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                value: day['eligibility_state'] == 'conditionally_usable'
                    ? confirmedConditionalDays.contains(day['id'])
                    : !excludedConsumptionDays.contains(day['id']) &&
                          day['eligibility_state'] == 'usable',
                onChanged: day['eligibility_state'] == 'usable'
                    ? (value) => setState(() {
                        if (value == false) {
                          excludedConsumptionDays.add(day['id'].toString());
                        } else {
                          excludedConsumptionDays.remove(day['id'].toString());
                        }
                        preview = null;
                      })
                    : day['eligibility_state'] == 'conditionally_usable'
                    ? (value) => setState(() {
                        if (value == true) {
                          confirmedConditionalDays.add(day['id'].toString());
                        } else {
                          confirmedConditionalDays.remove(day['id'].toString());
                        }
                        preview = null;
                      })
                    : null,
                title: Text(
                  '${day['date']} · ${GermanDecimal.formatString(day['recorded_energy_kcal'])} kcal',
                ),
                subtitle: Text(day['explanation_de']?.toString() ?? ''),
              ),
            const Text(
              'Ausgeschlossene Tage werden nicht verändert. Erstelle nach Änderungen die Vorschau erneut.',
            ),
          ],
        ),
      ),
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
