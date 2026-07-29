import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/formatting/german_decimal.dart';
import 'recipe_comparison_models.dart';

final class RecipeComparisonSection extends ConsumerStatefulWidget {
  const RecipeComparisonSection({required this.recipeId, super.key});
  final String recipeId;

  @override
  ConsumerState<RecipeComparisonSection> createState() =>
      _RecipeComparisonSectionState();
}

final class _RecipeComparisonSectionState
    extends ConsumerState<RecipeComparisonSection> {
  final portion = TextEditingController(text: '1');
  List<ComparableAssessmentItem> assessments = const [];
  RecipeComparison? result;
  String? assessmentId, errorCode, errorMessage;
  bool opened = false, loading = false;

  @override
  void dispose() {
    portion.dispose();
    super.dispose();
  }

  Future<void> load({bool loadAssessments = false}) async {
    final value = GermanDecimal.tryParse(portion.text);
    if (value == null || value <= 0 || value > 100) {
      setState(() {
        errorCode = 'INVALID_PORTION_COUNT';
        errorMessage = 'Bitte gib eine Portionszahl zwischen 0 und 100 ein.';
      });
      return;
    }
    setState(() {
      loading = true;
      errorCode = errorMessage = null;
    });
    try {
      if (loadAssessments || assessments.isEmpty) {
        final selection = await ref
            .read(recipeComparisonRepositoryProvider)
            .assessments();
        assessments = selection.items;
        assessmentId ??= selection.latestId;
      }
      result = await ref
          .read(recipeComparisonRepositoryProvider)
          .compare(
            widget.recipeId,
            assessmentId: assessmentId,
            portionCount: value.toString(),
          );
      assessmentId = result!.assessmentId;
    } on AppException catch (error) {
      errorCode = error.code;
      errorMessage = error.message;
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Card(
    child: ExpansionTile(
      key: const Key('personal-comparison-section'),
      leading: const Icon(Icons.compare_arrows),
      title: const Text('Persönlicher Vergleich'),
      subtitle: const Text(
        'Mit einer unveränderten Ernährungsanalyse vergleichen',
      ),
      onExpansionChanged: (expanded) {
        if (expanded && !opened) {
          opened = true;
          load(loadAssessments: true);
        }
      },
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [
        if (loading && result == null) const LinearProgressIndicator(),
        if (errorCode == 'NO_USABLE_ASSESSMENT')
          _NoAssessment(onCreate: () => context.go('/onboarding?new=true'))
        else if (errorMessage != null)
          ListTile(
            leading: const Icon(Icons.error_outline),
            title: Text(errorMessage!),
            trailing: TextButton(
              onPressed: load,
              child: const Text('Erneut versuchen'),
            ),
          )
        else ...[
          if (assessments.isNotEmpty)
            DropdownButtonFormField<String>(
              initialValue: assessmentId,
              decoration: const InputDecoration(labelText: 'Assessment'),
              items: assessments
                  .map(
                    (item) => DropdownMenuItem(
                      value: item.id,
                      enabled: item.usable,
                      child: Text(
                        '${DateFormatters.date(item.calculatedAt)} · ${_goal(item.goalType)}'
                        '${item.usable ? '' : ' · Nicht geeignet'}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
              onChanged: loading
                  ? null
                  : (value) {
                      assessmentId = value;
                      load();
                    },
            ),
          const SizedBox(height: 8),
          const Align(
            alignment: Alignment.centerLeft,
            child: Text('Verglichene Menge'),
          ),
          Wrap(
            spacing: 6,
            children: ['0,5', '1', '1,5', '2']
                .map(
                  (value) => ChoiceChip(
                    label: Text('$value Portionen'),
                    selected: portion.text == value,
                    onSelected: loading
                        ? null
                        : (_) {
                            setState(() => portion.text = value);
                            load();
                          },
                  ),
                )
                .toList(),
          ),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: portion,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: const InputDecoration(
                    labelText: 'Anzahl Portionen',
                  ),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: loading ? null : load,
                child: const Text('Anwenden'),
              ),
            ],
          ),
          if (loading && result != null) const LinearProgressIndicator(),
          if (result != null) _ComparisonResult(result: result!),
        ],
      ],
    ),
  );
}

final class _NoAssessment extends StatelessWidget {
  const _NoAssessment({required this.onCreate});
  final VoidCallback onCreate;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(12),
    child: Column(
      children: [
        const Text(
          'Für den persönlichen Vergleich benötigst du zuerst eine Ernährungsanalyse.',
        ),
        FilledButton(
          onPressed: onCreate,
          child: const Text('Ernährungsanalyse erstellen'),
        ),
      ],
    ),
  );
}

final class _ComparisonResult extends StatelessWidget {
  const _ComparisonResult({required this.result});
  final RecipeComparison result;
  @override
  Widget build(BuildContext context) {
    final overview = result.items.where(
      (item) => {
        'energy_kcal',
        'protein',
        'carbohydrate',
        'fat',
        'fiber',
      }.contains(item.code),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 12),
        Text(
          'Assessment vom ${DateFormatters.date(result.assessmentDate)} · ${_goal(result.goalType)}',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        for (final notice in result.notices)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.info_outline),
            title: Text(notice),
          ),
        for (final item in overview) _ComparisonTile(item: item),
        for (final group in result.groups)
          ExpansionTile(
            title: Text(group.name),
            children: group.items
                .map((item) => _ComparisonTile(item: item))
                .toList(),
          ),
        ExpansionTile(
          title: const Text('Datenqualität'),
          children: [
            for (final item in result.items.where(
              (item) => item.status != 'complete',
            ))
              ListTile(
                title: Text(item.name),
                subtitle: Text(
                  item.status == 'partial'
                      ? 'Bekannter Anteil · Datenabdeckung ${item.coverage} %'
                      : 'Nicht vergleichbar',
                ),
              ),
          ],
        ),
        ExpansionTile(
          key: const Key('comparison-calculation-details'),
          title: const Text('Wie wird verglichen?'),
          children: [
            Text('Verglichene Menge: ${result.portionCount} Portionen'),
            Text('Gespeicherte Rezeptportionen: ${result.baseServings}'),
            Text('Referenzstand: ${result.referenceVersion}'),
            Text('Regelstand: ${result.ruleVersion}'),
            Text(
              'Rezeptstand: ${DateFormatters.dateTime(result.recipeUpdatedAt)}',
            ),
            for (final item
                in result.items.where((item) => item.formula != null).take(5))
              ListTile(title: Text(item.name), subtitle: Text(item.formula!)),
          ],
        ),
      ],
    );
  }
}

final class _ComparisonTile extends StatelessWidget {
  const _ComparisonTile({required this.item});
  final ComparisonItem item;
  @override
  Widget build(BuildContext context) => ListTile(
    contentPadding: EdgeInsets.zero,
    leading: Icon(
      item.status == 'unavailable'
          ? Icons.help_outline
          : item.status == 'partial'
          ? Icons.info_outline
          : item.relation == 'exceeds_limit'
          ? Icons.warning_amber
          : Icons.calculate_outlined,
    ),
    title: Text(item.name),
    subtitle: Text(
      '${item.explanation}\n${item.status == 'partial' ? 'Datenabdeckung: ${item.coverage} %' : ''}',
    ),
    trailing: Text(
      item.selectedAmount == null
          ? 'Nicht vergleichbar'
          : '${item.selectedAmount} ${item.unit}',
      textAlign: TextAlign.end,
    ),
  );
}

String _goal(String value) => switch (value) {
  'maintain_weight' => 'Gewicht halten',
  'lose_weight' => 'Gewicht reduzieren',
  'gain_weight' => 'Gewicht erhöhen',
  'general_health' => 'Allgemeine Gesundheit',
  'athletic_performance' => 'Sportliche Leistung',
  _ => value,
};
