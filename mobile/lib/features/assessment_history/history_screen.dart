import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../../core/widgets/states.dart';
import '../../core/widgets/design_system.dart';
import '../nutrition_assessment/assessment_models.dart';

final assessmentHistoryProvider = FutureProvider<List<AssessmentSummary>>(
  (ref) => ref.watch(assessmentRepositoryProvider).history(),
);

final class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(assessmentHistoryProvider);
    return AppScaffold(
      title: 'Einschätzungsverlauf',
      revealRootBackground: true,
      body: history.when(
        loading: () => const LoadingState(),
        error: (error, _) => ErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(assessmentHistoryProvider),
        ),
        data: (items) => ContentWidth(
          child: items.isEmpty
              ? const _EmptyHistory()
              : Column(
                  children: [
                    NutritionSection(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const NutritionSectionHeader(
                            title: 'Gespeicherte Einschätzungen',
                            subtitle:
                                'Profiländerungen überschreiben frühere Ergebnisse nicht.',
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          for (var index = 0; index < items.length; index++)
                            _HistoryRow(
                              item: items[index],
                              showDivider: index < items.length - 1,
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}

final class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.item, required this.showDivider});
  final AssessmentSummary item;
  final bool showDivider;

  @override
  Widget build(BuildContext context) => NutritionListRow(
    title: Text(DateFormatters.dateTime(item.calculatedAt)),
    subtitle: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Ziel: ${_goal(item.goalType)}'),
        Text(
          'Zielenergie: ${item.energyTargetLabel ?? item.targetEnergy.display}',
        ),
        Text(
          item.warnings.isEmpty
              ? 'Keine Warnhinweise'
              : '${item.warnings.length} Hinweis(e)',
        ),
      ],
    ),
    trailing: const Icon(Icons.chevron_right),
    onTap: () => context.go('/assessment/${item.id}'),
    showDivider: showDivider,
  );
}

final class _EmptyHistory extends StatelessWidget {
  const _EmptyHistory();

  @override
  Widget build(BuildContext context) => NutritionSection(
    child: Column(
      children: [
        const Icon(Icons.history, size: 64),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Noch keine Einschätzungen',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: AppSpacing.md),
        FilledButton(
          onPressed: () => context.go('/onboarding?new=true'),
          child: const Text('Einschätzung starten'),
        ),
      ],
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
