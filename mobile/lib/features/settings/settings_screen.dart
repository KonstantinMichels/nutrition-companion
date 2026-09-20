import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../../app/branding.dart';
import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../../core/widgets/design_system.dart';
import 'theme_controller.dart';

final packageInfoProvider = FutureProvider<PackageInfo>(
  (ref) => PackageInfo.fromPlatform(),
);

final class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(themeControllerProvider);
    final config = ref.watch(appConfigProvider);
    final package = ref.watch(packageInfoProvider);
    return AppScaffold(
      title: 'Einstellungen & Informationen',
      revealRootBackground: true,
      body: ContentWidth(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            NutritionSection(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const NutritionSectionHeader(
                    title: 'Darstellung',
                    subtitle: 'Wähle, wie die App auf diesem Gerät erscheint.',
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  SegmentedButton<ThemeMode>(
                    segments: const [
                      ButtonSegment(
                        value: ThemeMode.system,
                        icon: Icon(Icons.settings_brightness),
                        label: Text('System'),
                      ),
                      ButtonSegment(
                        value: ThemeMode.light,
                        icon: Icon(Icons.light_mode),
                        label: Text('Hell'),
                      ),
                      ButtonSegment(
                        value: ThemeMode.dark,
                        icon: Icon(Icons.dark_mode),
                        label: Text('Dunkel'),
                      ),
                    ],
                    selected: {mode},
                    onSelectionChanged: (value) => ref
                        .read(themeControllerProvider.notifier)
                        .setTheme(value.first),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppLayout.sectionGap),
            NutritionSection(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const NutritionSectionHeader(
                    title: 'App',
                    subtitle: 'Version und technische Umgebung',
                  ),
                  const SizedBox(height: AppSpacing.md),
                  NutritionSubSurface(
                    child: Row(
                      children: [
                        const Icon(Icons.apps_outlined),
                        const SizedBox(width: AppSpacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(AppBranding.productName),
                              package.when(
                                data: (value) => Text(
                                  'Version ${value.version} (${value.buildNumber})',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                                loading: () =>
                                    const Text('Version wird geladen …'),
                                error: (_, _) =>
                                    const Text('Version nicht verfügbar'),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (config.isDevelopment) ...[
                    const SizedBox(height: AppSpacing.sm),
                    NutritionSubSurface(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.developer_mode),
                          const SizedBox(width: AppSpacing.md),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('Entwicklungsverbindung'),
                                const SizedBox(height: AppSpacing.xxs),
                                SelectableText(
                                  config.apiBaseUrl.toString(),
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: AppLayout.sectionGap),
            const NutritionSection(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  NutritionSectionHeader(
                    title: 'Informationen',
                    subtitle: 'Methodik, Einordnung und rechtliche Hinweise',
                  ),
                  SizedBox(height: AppSpacing.sm),
                  _InfoTile(
                    title: 'Methodischer Hinweis',
                    text:
                        'Die Ergebnisse sind geschätzte, wissenschaftlich referenzierte Zielbereiche auf Basis deiner Angaben. Reale Bedarfe können abweichen. Die App ist nicht für Diagnose oder Behandlung bestimmt.',
                  ),
                  _InfoTile(
                    title: 'Wissenschaftliche Grundlagen',
                    text:
                        'Berichte nennen je Kennzahl die vom Backend gespeicherte Quelle, Referenzsatz-Version, Formel oder Regel und Einschränkungen. Zentral sind DGE/ÖGE-Referenzen und die Mifflin-St.-Jeor-Gleichung, soweit verifiziert und für den Nutzerbereich verfügbar.',
                  ),
                  _InfoTile(
                    title: 'Produktpositionierung',
                    text:
                        'Persönliche Ernährungs- und Lebensstilplanung für allgemein gesunde Erwachsene. Kein Medizinprodukt, keine Diagnose, keine Therapie und kein Ersatz für ärztliche oder ernährungsfachliche Beratung.',
                  ),
                  _InfoTile(
                    title: 'Datenschutzinformation',
                    text:
                        'Die derzeitige Datenschutzinformation und der Einwilligungstext sind Entwürfe. Sie sind vor einer öffentlichen Veröffentlichung durch qualifizierte deutsche oder europäische Fachleute rechtlich, datenschutzrechtlich und regulatorisch zu prüfen.',
                  ),
                  _InfoTile(
                    title: 'Paketkennung',
                    text:
                        '${AppBranding.packageIdentifier} ist eine temporäre Entwicklungskennung und muss vor Veröffentlichung ersetzt werden.',
                    showDivider: false,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

final class _InfoTile extends StatelessWidget {
  const _InfoTile({
    required this.title,
    required this.text,
    this.showDivider = true,
  });
  final String title;
  final String text;
  final bool showDivider;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      ExpansionTile(
        tilePadding: EdgeInsets.zero,
        title: Text(title),
        childrenPadding: const EdgeInsets.only(bottom: AppSpacing.md),
        children: [Align(alignment: Alignment.centerLeft, child: Text(text))],
      ),
      if (showDivider) const Divider(),
    ],
  );
}
