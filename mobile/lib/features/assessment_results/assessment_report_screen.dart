import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../../core/widgets/states.dart';
import '../nutrition_assessment/assessment_models.dart';

final assessmentReportProvider =
    FutureProvider.family<AssessmentReport, String>(
      (ref, id) => ref.watch(assessmentRepositoryProvider).getById(id),
    );

final class AssessmentReportScreen extends ConsumerWidget {
  const AssessmentReportScreen({required this.assessmentId, super.key});
  final String assessmentId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final report = ref.watch(assessmentReportProvider(assessmentId));
    return AppScaffold(
      title: 'Ernährungseinschätzung',
      body: report.when(
        loading: () => const LoadingState(message: 'Bericht wird geladen …'),
        error: (error, _) => ErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(assessmentReportProvider(assessmentId)),
        ),
        data: (value) => ContentWidth(child: _Report(report: value)),
      ),
    );
  }
}

final class _Report extends StatelessWidget {
  const _Report({required this.report});
  final AssessmentReport report;

  @override
  Widget build(BuildContext context) {
    final summary = report.summary;
    _MetricSection section({
      required String title,
      required List<AssessmentMetric> metrics,
      String? subtitle,
      List<String> unavailable = const [],
    }) => _MetricSection(
      title: title,
      subtitle: subtitle,
      metrics: metrics,
      unavailable: unavailable,
      referenceSetVersion: report.referenceSetVersion,
      applicationRuleSetVersion: report.applicationRuleSetVersion,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Erstellt am ${DateFormatters.dateTime(summary.calculatedAt)}'),
        const SizedBox(height: 12),
        _ScopeCard(status: summary.supportedScopeStatus),
        _OverviewCard(summary: summary),
        section(
          title: 'Erhaltungsenergie',
          subtitle: 'Geschätzter täglicher Energiebedarf als Bereich',
          metrics: _select(report.metrics, const ['energy.maintenance']),
        ),
        section(
          title: 'Zielenergie',
          subtitle: 'Aus Ziel und Anwendungsvorgaben abgeleiteter Bereich',
          metrics: _select(report.metrics, const ['energy.goal_target']),
        ),
        section(
          title: 'Ruheenergie',
          metrics: _select(report.metrics, const [
            'energy.resting_energy',
            'energy.resting_energy_formula_comparison',
          ]),
        ),
        section(
          title: 'BMI',
          metrics: _select(report.metrics, const ['anthropometrics.bmi']),
        ),
        section(
          title: 'Taillenverhältnisse',
          metrics: _select(report.metrics, const [
            'anthropometrics.waist_to_height_ratio',
            'anthropometrics.waist_to_hip_ratio',
          ]),
        ),
        section(
          title: 'Körperzusammensetzung',
          metrics: _select(report.metrics, const [
            'body_composition.fat_mass_kg',
            'body_composition.fat_free_mass_kg',
          ]),
        ),
        section(
          title: 'Aktivität und PAL',
          metrics: _select(report.metrics, const ['activity.pal']),
        ),
        section(
          title: 'Protein',
          metrics: _prefix(report.metrics, const [
            'protein.',
            'macros.protein_',
          ]),
        ),
        section(
          title: 'Fett',
          metrics: _prefix(report.metrics, const [
            'macros.fat_',
            'macros.saturated_fat_',
          ]),
        ),
        section(
          title: 'Kohlenhydrate',
          metrics: _prefix(report.metrics, const ['macros.carbohydrate_']),
        ),
        section(
          title: 'Makronährstoff-Bilanz',
          metrics: _select(report.metrics, const ['macros.energy_sum']),
        ),
        section(
          title: 'Ballaststoffe',
          metrics: _prefix(report.metrics, const ['fiber.']),
        ),
        section(
          title: 'Flüssigkeit',
          metrics: _prefix(report.metrics, const ['hydration.']),
        ),
        section(
          title: 'Mikronährstoffe',
          metrics: _prefix(report.metrics, const ['micronutrients.']),
          unavailable: report.unavailableMicronutrients,
        ),
        _FoodGroups(groups: report.foodGroups),
        _Warnings(flags: summary.warnings),
        _Methodology(report: report),
        const SizedBox(height: 24),
        const Text(
          'Diese Einschätzung ist eine allgemeine, wissenschaftlich referenzierte Schätzung und nicht für Diagnose oder Behandlung bestimmt.',
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),
      ],
    );
  }
}

final class _ScopeCard extends StatelessWidget {
  const _ScopeCard({required this.status});
  final String status;

  @override
  Widget build(BuildContext context) {
    final supported = status == 'supported';
    return Card(
      color: supported
          ? Theme.of(context).colorScheme.primaryContainer
          : Theme.of(context).colorScheme.errorContainer,
      child: ListTile(
        leading: Icon(
          supported ? Icons.check_circle_outline : Icons.info_outline,
        ),
        title: Text(
          supported
              ? 'Automatisch unterstützter Bereich'
              : 'Außerhalb des automatisch unterstützten Bereichs',
        ),
        subtitle: Text(
          supported
              ? 'Die Angaben liegen im vorgesehenen Nutzerbereich des MVP.'
              : 'Einige Standardziele können bewusst fehlen. Bitte beachte die Hinweise und ziehe qualifizierte Beratung in Betracht.',
        ),
      ),
    );
  }
}

final class _OverviewCard extends StatelessWidget {
  const _OverviewCard({required this.summary});
  final AssessmentSummary summary;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Überblick', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          _valueRow('Erhaltungsenergie', summary.maintenanceEnergy.display),
          _valueRow('Zielenergie', summary.targetEnergy.display),
          for (final entry in summary.macros.entries)
            _valueRow(_label(entry.key), entry.value),
        ],
      ),
    ),
  );
}

final class _MetricSection extends StatelessWidget {
  const _MetricSection({
    required this.title,
    required this.metrics,
    this.subtitle,
    this.unavailable = const [],
    required this.referenceSetVersion,
    required this.applicationRuleSetVersion,
  });
  final String title;
  final String? subtitle;
  final List<AssessmentMetric> metrics;
  final List<String> unavailable;
  final String referenceSetVersion;
  final String applicationRuleSetVersion;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          if (subtitle != null) ...[const SizedBox(height: 4), Text(subtitle!)],
          if (metrics.isEmpty && unavailable.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Text('Für diese Einschätzung ist kein Wert verfügbar.'),
            ),
          for (final metric in metrics)
            _MetricTile(
              metric: metric,
              referenceSetVersion: referenceSetVersion,
              applicationRuleSetVersion: applicationRuleSetVersion,
            ),
          if (unavailable.isNotEmpty)
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              leading: const Icon(Icons.info_outline),
              title: const Text('Nicht verfügbare Referenzwerte'),
              subtitle: Text(
                '${unavailable.length} Werte wurden nicht erfunden oder ersetzt.',
              ),
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(unavailable.join(', ')),
                  ),
                ),
              ],
            ),
        ],
      ),
    ),
  );
}

final class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.metric,
    required this.referenceSetVersion,
    required this.applicationRuleSetVersion,
  });
  final AssessmentMetric metric;
  final String referenceSetVersion;
  final String applicationRuleSetVersion;

  @override
  Widget build(BuildContext context) {
    final value = metric.lowerValue != null && metric.upperValue != null
        ? '${GermanDecimal.format(metric.lowerValue!, decimals: 1)}–${GermanDecimal.format(metric.upperValue!, decimals: 1)} ${metric.unit}'
        : '${metric.displayValue}${metric.unit.isEmpty || metric.displayValue.contains(metric.unit) ? '' : ' ${metric.unit}'}';
    return ExpansionTile(
      key: ValueKey(metric.code),
      tilePadding: EdgeInsets.zero,
      title: Text(_label(metric.code)),
      subtitle: Text(value),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Wie wurde das berechnet?',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 6),
                Text(metric.explanation),
                const SizedBox(height: 12),
                _detail('Formel oder Regel', metric.methodCode),
                _detail(
                  'Eingaben',
                  const JsonEncoder.withIndent(
                    '  ',
                  ).convert(metric.calculationInputs),
                ),
                _detail(
                  'Wissenschaftliche Quelle',
                  _source(metric.sourceMetadata),
                ),
                _detail('Referenzsatz-Version', referenceSetVersion),
                if (metric.applicationRuleIdentifier != null)
                  _detail(
                    'Anwendungsregel',
                    '${metric.applicationRuleIdentifier!} (Regelsatz $applicationRuleSetVersion)',
                  ),
                _detail('Einordnung', _confidence(metric.confidenceType)),
                _detail('Grenzen und Unsicherheit', metric.limitations),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

final class _FoodGroups extends StatelessWidget {
  const _FoodGroups({required this.groups});
  final List<Map<String, dynamic>> groups;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Lebensmittelgruppen',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 6),
          const Text(
            'Allgemeine lebensmittelbezogene Empfehlungen; ohne Ernährungstagebuch wird keine Einhaltung bewertet.',
          ),
          if (groups.isEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: Text('Keine strukturierten Empfehlungen verfügbar.'),
            ),
          for (final group in groups)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.eco_outlined),
              title: Text(
                (group['display_name_de'] ?? group['name'] ?? group['code'])
                    .toString(),
              ),
              subtitle: Text(
                (group['recommendation_de'] ?? group['recommendation'] ?? '')
                    .toString(),
              ),
            ),
        ],
      ),
    ),
  );
}

final class _Warnings extends StatelessWidget {
  const _Warnings({required this.flags});
  final List<SafetyFlag> flags;

  @override
  Widget build(BuildContext context) => Card(
    color: flags.isEmpty ? null : Theme.of(context).colorScheme.errorContainer,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Hinweise und Sicherheitsmarkierungen',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          if (flags.isEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('Keine besonderen Hinweise für diese Einschätzung.'),
            ),
          for (final flag in flags)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.info_outline),
              title: Text(flag.explanation),
              subtitle: flag.recommendedAction.isEmpty
                  ? null
                  : Text(flag.recommendedAction),
            ),
        ],
      ),
    ),
  );
}

final class _Methodology extends StatelessWidget {
  const _Methodology({required this.report});
  final AssessmentReport report;

  @override
  Widget build(BuildContext context) => Card(
    child: ExpansionTile(
      title: const Text('Methodik und Versionen'),
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _detail(
                'Referenzsatz',
                '${report.referenceSetIdentifier} (${report.referenceSetVersion})',
              ),
              _detail(
                'Anwendungsregelsatz',
                '${report.applicationRuleSetIdentifier} (${report.applicationRuleSetVersion})',
              ),
              _detail('Engine-Version', report.engineVersion),
              const Text(
                'Alte Einschätzungen bleiben unverändert und werden nach Regel- oder Referenzänderungen nicht automatisch neu berechnet.',
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

List<AssessmentMetric> _select(
  List<AssessmentMetric> metrics,
  List<String> codes,
) => metrics
    .where((metric) => codes.contains(metric.code))
    .toList(growable: false);

List<AssessmentMetric> _prefix(
  List<AssessmentMetric> metrics,
  List<String> prefixes,
) => metrics
    .where((metric) => prefixes.any((prefix) => metric.code.startsWith(prefix)))
    .toList(growable: false);

Widget _valueRow(String label, String value) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 3),
  child: Row(
    children: [
      Expanded(child: Text(label)),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
    ],
  ),
);

Widget _detail(String label, String value) => Padding(
  padding: const EdgeInsets.only(bottom: 8),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
      SelectableText(value.isEmpty ? 'Nicht angegeben' : value),
    ],
  ),
);

String _source(Map<String, dynamic> source) {
  if (source.isEmpty) return 'Nicht angegeben';
  return source.entries
      .map((entry) => '${entry.key}: ${entry.value}')
      .join('\n');
}

String _confidence(String value) => switch (value) {
  'measured' => 'Gemessen',
  'derived' => 'Abgeleitet',
  'reference_target' => 'Referenzziel',
  _ => 'Geschätzt',
};

String _label(String code) {
  const labels = {
    'energy.maintenance': 'Erhaltungsenergie',
    'energy.goal_target': 'Zielenergie',
    'energy.resting_energy': 'Ruheenergie',
    'energy.resting_energy_formula_comparison': 'Formelschätzung zum Vergleich',
    'anthropometrics.bmi': 'Body-Mass-Index',
    'anthropometrics.waist_to_height_ratio': 'Taille-zu-Größe-Verhältnis',
    'anthropometrics.waist_to_hip_ratio': 'Taille-zu-Hüfte-Verhältnis',
    'body_composition.fat_mass_kg': 'Fettmasse',
    'body_composition.fat_free_mass_kg': 'Fettfreie Masse',
    'activity.pal': 'Physical Activity Level',
    'protein.grams_per_kg': 'Protein je kg Körpergewicht',
    'protein.grams_per_day': 'Proteinziel pro Tag',
    'macros.protein_grams': 'Protein',
    'macros.protein_energy_percent': 'Energieanteil Protein',
    'macros.fat_grams': 'Fett',
    'macros.fat_energy_percent': 'Energieanteil Fett',
    'macros.saturated_fat_max_grams': 'Gesättigte Fettsäuren (Maximum)',
    'macros.carbohydrate_grams': 'Kohlenhydrate',
    'macros.carbohydrate_energy_percent': 'Energieanteil Kohlenhydrate',
    'fiber.target': 'Ballaststoffe',
    'hydration.total_water': 'Gesamtwasser',
    'hydration.beverages': 'Wasser aus Getränken',
    'hydration.food': 'Wasser aus Lebensmitteln',
    'hydration.oxidation_water': 'Oxidationswasser',
  };
  return labels[code] ?? code.replaceAll('_', ' ');
}
