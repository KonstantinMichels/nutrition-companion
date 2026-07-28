import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../../app/branding.dart';
import '../../app/providers.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
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
      body: ContentWidth(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Darstellung', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
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
            const SizedBox(height: 24),
            Text('App', style: Theme.of(context).textTheme.titleLarge),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text(AppBranding.productName),
              subtitle: package.when(
                data: (value) =>
                    Text('Version ${value.version} (${value.buildNumber})'),
                loading: () => const Text('Version wird geladen …'),
                error: (_, _) => const Text('Version nicht verfügbar'),
              ),
            ),
            if (config.isDevelopment)
              Card(
                child: ListTile(
                  leading: const Icon(Icons.developer_mode),
                  title: const Text('Entwicklungsverbindung'),
                  subtitle: SelectableText(config.apiBaseUrl.toString()),
                ),
              ),
            const SizedBox(height: 16),
            const _InfoTile(
              title: 'Methodischer Hinweis',
              text:
                  'Die Ergebnisse sind geschätzte, wissenschaftlich referenzierte Zielbereiche auf Basis deiner Angaben. Reale Bedarfe können abweichen. Die App ist nicht für Diagnose oder Behandlung bestimmt.',
            ),
            const _InfoTile(
              title: 'Wissenschaftliche Grundlagen',
              text:
                  'Berichte nennen je Kennzahl die vom Backend gespeicherte Quelle, Referenzsatz-Version, Formel oder Regel und Einschränkungen. Zentral sind DGE/ÖGE-Referenzen und die Mifflin-St.-Jeor-Gleichung, soweit verifiziert und für den Nutzerbereich verfügbar.',
            ),
            const _InfoTile(
              title: 'Produktpositionierung',
              text:
                  'Persönliche Ernährungs- und Lebensstilplanung für allgemein gesunde Erwachsene. Kein Medizinprodukt, keine Diagnose, keine Therapie und kein Ersatz für ärztliche oder ernährungsfachliche Beratung.',
            ),
            const _InfoTile(
              title: 'Datenschutzinformation',
              text:
                  'Die derzeitige Datenschutzinformation und der Einwilligungstext sind Entwürfe. Sie sind vor einer öffentlichen Veröffentlichung durch qualifizierte deutsche oder europäische Fachleute rechtlich, datenschutzrechtlich und regulatorisch zu prüfen.',
            ),
            const _InfoTile(
              title: 'Paketkennung',
              text:
                  '${AppBranding.packageIdentifier} ist eine temporäre Entwicklungskennung und muss vor Veröffentlichung ersetzt werden.',
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}

final class _InfoTile extends StatelessWidget {
  const _InfoTile({required this.title, required this.text});
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) => Card(
    child: ExpansionTile(
      title: Text(title),
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [Align(alignment: Alignment.centerLeft, child: Text(text))],
    ),
  );
}
