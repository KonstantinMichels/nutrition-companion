import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../../core/widgets/states.dart';
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
                    const Text(
                      'Jede Einschätzung ist ein unveränderlicher historischer Stand. Profiländerungen überschreiben frühere Ergebnisse nicht.',
                    ),
                    const SizedBox(height: 12),
                    for (final item in items) _HistoryCard(item: item),
                  ],
                ),
        ),
      ),
    );
  }
}

final class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.item});
  final AssessmentSummary item;

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      contentPadding: const EdgeInsets.all(16),
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
    ),
  );
}

final class _EmptyHistory extends StatelessWidget {
  const _EmptyHistory();

  @override
  Widget build(BuildContext context) => Column(
    children: [
      const SizedBox(height: 48),
      const Icon(Icons.history, size: 64),
      const SizedBox(height: 16),
      Text(
        'Noch keine Einschätzungen',
        style: Theme.of(context).textTheme.titleLarge,
      ),
      const SizedBox(height: 16),
      FilledButton(
        onPressed: () => context.go('/onboarding?new=true'),
        child: const Text('Einschätzung starten'),
      ),
    ],
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
