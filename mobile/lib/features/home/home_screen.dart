import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/formatting/date_formatters.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../nutrition_assessment/assessment_models.dart';
import 'home_controller.dart';

final class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(homeControllerProvider);
    return AppScaffold(
      title: 'Übersicht',
      actions: [
        IconButton(
          tooltip: 'Aktualisieren',
          onPressed: state.loading
              ? null
              : () => ref.read(homeControllerProvider.notifier).load(),
          icon: const Icon(Icons.refresh),
        ),
      ],
      body: RefreshIndicator(
        onRefresh: () => ref.read(homeControllerProvider.notifier).load(),
        child: ContentWidth(
          child: state.loading && state.summary == null
              ? const SizedBox(
                  height: 400,
                  child: Center(child: CircularProgressIndicator()),
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (state.message != null)
                      _StatusBanner(
                        message: state.message!,
                        warning: state.stale,
                      ),
                    if (state.summary == null)
                      const _EmptyHome()
                    else
                      _Latest(summary: state.summary!, cached: state.cached),
                  ],
                ),
        ),
      ),
    );
  }
}

final class _EmptyHome extends StatelessWidget {
  const _EmptyHome();

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Icon(
        Icons.eco_outlined,
        size: 72,
        color: Theme.of(context).colorScheme.primary,
      ),
      const SizedBox(height: 16),
      Text(
        'Deine erste Ernährungseinschätzung',
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      const SizedBox(height: 8),
      const Text(
        'Erhalte nachvollziehbare, wissenschaftlich referenzierte Schätzwerte für Energie und Nährstoffe auf Basis deiner Angaben.',
      ),
      const SizedBox(height: 12),
      const Text(
        'Die App ist für allgemein gesunde Erwachsene gedacht. Sie stellt keine Diagnose und ersetzt keine medizinische oder ernährungsfachliche Beratung.',
      ),
      const SizedBox(height: 24),
      FilledButton.icon(
        key: const Key('start-assessment'),
        onPressed: () => context.go('/onboarding?new=true'),
        icon: const Icon(Icons.arrow_forward),
        label: const Text('Einschätzung starten'),
      ),
    ],
  );
}

final class _Latest extends StatelessWidget {
  const _Latest({required this.summary, required this.cached});
  final AssessmentSummary summary;
  final bool cached;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Row(
        children: [
          Expanded(
            child: Text(
              'Letzte Einschätzung',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
          ),
          if (cached)
            const Chip(
              avatar: Icon(Icons.offline_bolt, size: 18),
              label: Text('Lokal gespeichert'),
            ),
        ],
      ),
      Text(DateFormatters.dateTime(summary.calculatedAt)),
      const SizedBox(height: 12),
      _EnergyCard(
        title: 'Erhaltungsenergie',
        value: summary.maintenanceEnergy.display,
        icon: Icons.balance_outlined,
      ),
      _EnergyCard(
        title: 'Aktueller Zielbereich',
        value: summary.targetEnergy.display,
        icon: Icons.track_changes_outlined,
      ),
      if (summary.macros.isNotEmpty)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Makronährstoffe',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                for (final entry in summary.macros.entries)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Text('${_macroLabel(entry.key)}: ${entry.value}'),
                  ),
              ],
            ),
          ),
        ),
      if (summary.warnings.isNotEmpty)
        Card(
          color: Theme.of(context).colorScheme.errorContainer,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Wichtige Hinweise',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                for (final warning in summary.warnings.take(3))
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.info_outline),
                    title: Text(warning.explanation),
                  ),
              ],
            ),
          ),
        ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: cached
            ? null
            : () => context.go('/assessment/${summary.id}'),
        child: Text(
          cached
              ? 'Vollständiger Bericht nur online verfügbar'
              : 'Vollständigen Bericht öffnen',
        ),
      ),
      const SizedBox(height: 8),
      OutlinedButton(
        onPressed: () => context.go('/history'),
        child: const Text('Verlauf öffnen'),
      ),
      const SizedBox(height: 8),
      OutlinedButton(
        onPressed: () => context.go('/profile'),
        child: const Text('Profil bearbeiten'),
      ),
      const SizedBox(height: 8),
      FilledButton.tonal(
        onPressed: () => context.go('/onboarding?new=true'),
        child: const Text('Neue Einschätzung erstellen'),
      ),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        onPressed: () => context.go('/training'),
        icon: const Icon(Icons.fitness_center),
        label: const Text('Training und Tagesziele'),
      ),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        key: const Key('open-consumption'),
        onPressed: () => context.go('/consumption'),
        icon: const Icon(Icons.restaurant_outlined),
        label: const Text('Verzehr erfassen'),
      ),
    ],
  );
}

final class _EnergyCard extends StatelessWidget {
  const _EnergyCard({
    required this.title,
    required this.value,
    required this.icon,
  });
  final String title;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Icon(icon, size: 34),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title),
                Text(value, style: Theme.of(context).textTheme.titleLarge),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

final class _StatusBanner extends StatelessWidget {
  const _StatusBanner({required this.message, required this.warning});
  final String message;
  final bool warning;

  @override
  Widget build(BuildContext context) => Card(
    color: warning
        ? Theme.of(context).colorScheme.errorContainer
        : Theme.of(context).colorScheme.secondaryContainer,
    child: ListTile(
      leading: Icon(warning ? Icons.warning_amber : Icons.offline_bolt),
      title: Text(message),
    ),
  );
}

String _macroLabel(String value) => switch (value) {
  'protein' => 'Protein',
  'fat' => 'Fett',
  'carbohydrates' => 'Kohlenhydrate',
  _ => value,
};
