import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../../core/widgets/design_system.dart';
import '../nutrition_assessment/assessment_models.dart';
import 'home_controller.dart';

final class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(homeControllerProvider);
    return AppScaffold(
      title: 'Übersicht',
      revealRootBackground: true,
      showAppBar: false,
      respectTopSafeArea: false,
      body: AnnotatedRegion<SystemUiOverlayStyle>(
        value: Theme.of(context).brightness == Brightness.light
            ? SystemUiOverlayStyle.dark.copyWith(
                statusBarColor: Colors.transparent,
                systemNavigationBarColor: Colors.transparent,
                systemNavigationBarContrastEnforced: false,
              )
            : SystemUiOverlayStyle.light.copyWith(
                statusBarColor: Colors.transparent,
                systemNavigationBarColor: Colors.transparent,
                systemNavigationBarContrastEnforced: false,
              ),
        child: RefreshIndicator(
          onRefresh: () => ref.read(homeControllerProvider.notifier).load(),
          child: ContentWidth(
            padding: const EdgeInsets.fromLTRB(
              AppLayout.sectionOuterMargin,
              0,
              AppLayout.sectionOuterMargin,
              AppSpacing.xl,
            ),
            child: state.loading && state.summary == null
                ? const _LoadingOverview()
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _Overview(
                        summary: state.summary,
                        cached: state.cached,
                        statusMessage: state.message,
                        statusWarning: state.stale,
                        onRefresh: state.loading
                            ? null
                            : () => ref
                                  .read(homeControllerProvider.notifier)
                                  .load(),
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}

final class _Overview extends StatelessWidget {
  const _Overview({
    required this.summary,
    required this.cached,
    required this.onRefresh,
    required this.statusMessage,
    required this.statusWarning,
  });
  final AssessmentSummary? summary;
  final bool cached;
  final VoidCallback? onRefresh;
  final String? statusMessage;
  final bool statusWarning;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      if (summary == null)
        _EmptyAssessment(
          onRefresh: onRefresh,
          statusMessage: statusMessage,
          statusWarning: statusWarning,
        )
      else
        _CurrentAssessment(
          summary: summary!,
          cached: cached,
          onRefresh: onRefresh,
          statusMessage: statusMessage,
          statusWarning: statusWarning,
        ),
      const SizedBox(height: AppLayout.sectionGap),
      NutritionSection(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const NutritionSectionHeader(
              title: 'Direkt loslegen',
              subtitle: 'Häufige Aufgaben schnell öffnen',
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                NutritionQuickAction(
                  icon: Icons.add_circle_outline,
                  label: 'Erfassen',
                  onTap: () => context.go('/consumption'),
                ),
                NutritionQuickAction(
                  icon: Icons.qr_code_scanner,
                  label: 'Scannen',
                  onTap: () => context.go('/foods/scan'),
                ),
                NutritionQuickAction(
                  icon: Icons.event_note_outlined,
                  label: 'Plan',
                  onTap: () => context.go('/daily-plan'),
                ),
                NutritionQuickAction(
                  icon: Icons.shopping_cart_outlined,
                  label: 'Einkauf',
                  onTap: () => context.go('/shopping-lists'),
                ),
              ],
            ),
          ],
        ),
      ),
      const SizedBox(height: AppLayout.sectionGap),
      NutritionFeatureOverview(
        title: 'Planung',
        description:
            'Tages- und Wochenpläne erstellen und die Plan-Automatisierung nutzen.',
        icon: Icons.calendar_month_outlined,
        actionLabel: 'Tagesplan öffnen',
        onOpen: () => context.go('/daily-plan'),
        secondaryActionLabel: 'Wochenplan',
        onSecondaryOpen: () => context.go('/weekly-plan'),
      ),
      const SizedBox(height: AppLayout.sectionGap),
      NutritionFeatureOverview(
        title: 'Verzehr & Fortschritt',
        description:
            'Mahlzeiten erfassen, Tageswerte vergleichen und Entwicklungen verfolgen.',
        icon: Icons.insights_outlined,
        actionLabel: 'Verzehr öffnen',
        onOpen: () => context.go('/consumption'),
        secondaryActionLabel: 'Fortschritt',
        onSecondaryOpen: () => context.go('/progress'),
      ),
      const SizedBox(height: AppLayout.sectionGap),
      NutritionFeatureOverview(
        title: 'Lebensmittel & Rezepte',
        description:
            'Lebensmittel verwalten, Barcodes scannen und eigene Rezepte zusammenstellen.',
        icon: Icons.menu_book_outlined,
        actionLabel: 'Lebensmittel',
        onOpen: () => context.go('/foods'),
        secondaryActionLabel: 'Rezepte',
        onSecondaryOpen: () => context.go('/recipes'),
      ),
      const SizedBox(height: AppLayout.sectionGap),
      NutritionFeatureOverview(
        title: 'Vorrat & Einkauf',
        description:
            'Bestände, Lagerorte und Einkaufslisten zusammenhängend verwalten.',
        icon: Icons.inventory_2_outlined,
        actionLabel: 'Vorrat öffnen',
        onOpen: () => context.go('/pantry'),
        secondaryActionLabel: 'Einkauf',
        onSecondaryOpen: () => context.go('/shopping-lists'),
      ),
      const SizedBox(height: AppLayout.sectionGap),
      NutritionFeatureOverview(
        title: 'Training & Tagesziele',
        description:
            'Trainingstage pflegen und daraus angepasste Energieziele nachvollziehen.',
        icon: Icons.fitness_center,
        actionLabel: 'Training öffnen',
        onOpen: () => context.go('/training'),
      ),
      const SizedBox(height: AppSpacing.xl),
    ],
  );
}

final class _LoadingOverview extends StatelessWidget {
  const _LoadingOverview();

  @override
  Widget build(BuildContext context) => NutritionHeroSection(
    child: SizedBox(
      height: 320,
      child: Center(
        child: CircularProgressIndicator(
          color: Theme.of(context).colorScheme.primary,
        ),
      ),
    ),
  );
}

final class _EmptyAssessment extends StatelessWidget {
  const _EmptyAssessment({
    required this.onRefresh,
    required this.statusMessage,
    required this.statusWarning,
  });

  final VoidCallback? onRefresh;
  final String? statusMessage;
  final bool statusWarning;

  @override
  Widget build(BuildContext context) => NutritionHeroSection(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Icon(
          Icons.eco_outlined,
          size: 64,
          color: Theme.of(context).colorScheme.primary,
        ),
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            Expanded(
              child: Text(
                'Deine erste Ernährungseinschätzung',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ),
            IconButton(
              tooltip: 'Aktualisieren',
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        if (statusMessage != null) ...[
          const SizedBox(height: AppSpacing.sm),
          _AssessmentStatus(message: statusMessage!, warning: statusWarning),
        ],
        const SizedBox(height: AppSpacing.xs),
        const Text(
          'Erhalte nachvollziehbare Zielbereiche für Energie und Nährstoffe auf Basis deiner Angaben.',
        ),
        const SizedBox(height: AppSpacing.xl),
        FilledButton.icon(
          key: const Key('start-assessment'),
          onPressed: () => context.go('/onboarding?new=true'),
          icon: const Icon(Icons.arrow_forward),
          label: const Text('Einschätzung starten'),
        ),
      ],
    ),
  );
}

final class _CurrentAssessment extends StatelessWidget {
  const _CurrentAssessment({
    required this.summary,
    required this.cached,
    required this.onRefresh,
    required this.statusMessage,
    required this.statusWarning,
  });
  final AssessmentSummary summary;
  final bool cached;
  final VoidCallback? onRefresh;
  final String? statusMessage;
  final bool statusWarning;

  @override
  Widget build(BuildContext context) => NutritionHeroSection(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        NutritionSectionHeader(
          title: 'Aktuelle Einschätzung',
          subtitle: DateFormatters.dateTime(summary.calculatedAt),
          action: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (cached)
                const Chip(
                  avatar: Icon(Icons.offline_bolt, size: 18),
                  label: Text('Lokal'),
                ),
              IconButton(
                tooltip: 'Aktualisieren',
                onPressed: onRefresh,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
        ),
        if (statusMessage != null) ...[
          const SizedBox(height: AppSpacing.sm),
          _AssessmentStatus(message: statusMessage!, warning: statusWarning),
        ],
        const SizedBox(height: AppSpacing.xl),
        _EnergyMetric(
          title: summary.energyTargetLabel ?? 'Aktueller Zielbereich',
          value: summary.targetEnergy.display,
          icon: Icons.track_changes_outlined,
          prominent: true,
        ),
        const SizedBox(height: AppSpacing.sm),
        _EnergyMetric(
          title: 'Erhaltungsenergie',
          value: summary.maintenanceEnergy.display,
          icon: Icons.balance_outlined,
        ),
        if (summary.macros.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.xl),
          Text(
            'Makronährstoffziele',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: AppSpacing.xs),
          for (final entry in summary.macros.entries)
            NutritionListRow(
              title: Text(_macroLabel(entry.key)),
              trailing: Text(
                entry.value,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              showDivider: entry.key != summary.macros.keys.last,
            ),
        ],
        if (summary.warnings.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.lg),
          NutritionSubSurface(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Wichtige Hinweise',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: AppSpacing.xs),
                for (final warning in summary.warnings.take(3))
                  Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.info_outline, size: 20),
                        const SizedBox(width: AppSpacing.xs),
                        Expanded(child: Text(warning.explanation)),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.xl),
        Text(
          'Einschätzung verwalten',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            NutritionQuickAction(
              icon: Icons.description_outlined,
              label: 'Bericht',
              onTap: cached
                  ? null
                  : () => context.go('/assessment/${summary.id}'),
            ),
            NutritionQuickAction(
              icon: Icons.add_chart_outlined,
              label: 'Neu',
              onTap: () => context.go('/onboarding?new=true'),
            ),
            NutritionQuickAction(
              icon: Icons.history,
              label: 'Verlauf',
              onTap: () => context.go('/history'),
            ),
            NutritionQuickAction(
              icon: Icons.person_outline,
              label: 'Profil',
              onTap: () => context.go('/profile'),
            ),
          ],
        ),
        if (cached) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Der vollständige Bericht ist nur online verfügbar.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ],
    ),
  );
}

final class _EnergyMetric extends StatelessWidget {
  const _EnergyMetric({
    required this.title,
    required this.value,
    required this.icon,
    this.prominent = false,
  });
  final String title;
  final String value;
  final IconData icon;
  final bool prominent;

  @override
  Widget build(BuildContext context) => NutritionSubSurface(
    child: Row(
      children: [
        Icon(icon, size: prominent ? 36 : 28),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title),
              Text(
                value,
                style: prominent
                    ? Theme.of(context).textTheme.headlineMedium
                    : Theme.of(context).textTheme.titleLarge,
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

final class _AssessmentStatus extends StatelessWidget {
  const _AssessmentStatus({required this.message, required this.warning});
  final String message;
  final bool warning;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: warning
          ? Theme.of(context).colorScheme.errorContainer
          : Theme.of(context).colorScheme.secondaryContainer,
      borderRadius: BorderRadius.circular(AppRadii.medium),
    ),
    child: Padding(
      padding: const EdgeInsets.all(AppSpacing.sm),
      child: Row(
        children: [
          Icon(warning ? Icons.warning_amber : Icons.offline_bolt),
          const SizedBox(width: AppSpacing.sm),
          Expanded(child: Text(message)),
        ],
      ),
    ),
  );
}

String _macroLabel(String value) => switch (value) {
  'protein' => 'Protein',
  'fat' => 'Fett',
  'carbohydrates' => 'Kohlenhydrate',
  _ => value,
};
