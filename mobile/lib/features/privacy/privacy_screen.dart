import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/formatting/date_formatters.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/content_width.dart';
import '../../core/widgets/states.dart';
import '../assessment_history/history_screen.dart';
import '../home/home_controller.dart';
import '../onboarding/onboarding_controller.dart';
import '../profile/profile_screen.dart';
import '../foods/food_list_screen.dart';
import '../recipes/recipe_list_screen.dart';
import 'privacy_repository.dart';

final class PrivacyScreen extends ConsumerStatefulWidget {
  const PrivacyScreen({super.key});

  @override
  ConsumerState<PrivacyScreen> createState() => _PrivacyScreenState();
}

final class _PrivacyScreenState extends ConsumerState<PrivacyScreen> {
  bool busy = false;
  String? status;

  @override
  Widget build(BuildContext context) {
    final consents = ref.watch(consentsProvider);
    return AppScaffold(
      title: 'Datenschutz & Daten',
      body: ContentWidth(
        child: AbsorbPointer(
          absorbing: busy,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (busy) const LinearProgressIndicator(),
              if (status != null)
                Card(
                  color: Theme.of(context).colorScheme.secondaryContainer,
                  child: ListTile(title: Text(status!)),
                ),
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(
                    'Hier steuerst du deine Daten. Einwilligung widerrufen, zukünftige Verarbeitung stoppen und gespeicherte Daten löschen sind unterschiedliche Vorgänge.',
                  ),
                ),
              ),
              _heading(context, 'Gespeicherte Profildaten'),
              ListTile(
                leading: const Icon(Icons.person_outline),
                title: const Text('Profil ansehen und bearbeiten'),
                subtitle: const Text(
                  'Körper-, Aktivitäts-, Ziel-, Ernährungs- und Screening-Daten',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.go('/profile'),
              ),
              _heading(context, 'Einwilligungen'),
              consents.when(
                loading: () => const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (error, _) => ErrorState(
                  message: error.toString(),
                  onRetry: () => ref.invalidate(consentsProvider),
                ),
                data: (items) => items.isEmpty
                    ? const ListTile(
                        leading: Icon(Icons.info_outline),
                        title: Text('Keine Einwilligungsdatensätze vorhanden.'),
                      )
                    : Column(
                        children: [
                          for (final consent in items)
                            _ConsentTile(
                              consent: consent,
                              onWithdraw: consent.status == 'granted'
                                  ? () => _withdraw(consent)
                                  : null,
                            ),
                        ],
                      ),
              ),
              _heading(context, 'Export'),
              ListTile(
                leading: const Icon(Icons.ios_share),
                title: const Text('Daten als JSON exportieren'),
                subtitle: const Text(
                  'Der Export wird nur auf deine Aktion temporär erstellt und an die Android-Teilen-Funktion übergeben.',
                ),
                onTap: _export,
              ),
              _heading(context, 'Lokale Daten'),
              ListTile(
                leading: const Icon(Icons.edit_note),
                title: const Text('Lokalen Onboarding-Entwurf löschen'),
                subtitle: const Text(
                  'Löscht den verschlüsselten unfertigen Entwurf auf diesem Gerät.',
                ),
                onTap: () => _confirmAction(
                  title: 'Entwurf löschen?',
                  explanation:
                      'Deine noch nicht übermittelten Eingaben gehen auf diesem Gerät verloren.',
                  confirmLabel: 'Entwurf löschen',
                  action: () =>
                      ref.read(privacyRepositoryProvider).clearDraft(),
                  success: 'Lokaler Entwurf wurde gelöscht.',
                  after: () => ref.invalidate(onboardingControllerProvider),
                ),
              ),
              ListTile(
                leading: const Icon(Icons.offline_bolt_outlined),
                title: const Text('Lokalen Ergebnis-Cache löschen'),
                subtitle: const Text(
                  'Online gespeicherte Einschätzungen bleiben erhalten.',
                ),
                onTap: () => _confirmAction(
                  title: 'Lokalen Cache löschen?',
                  explanation:
                      'Die letzte Zusammenfassung ist danach offline nicht mehr verfügbar.',
                  confirmLabel: 'Cache löschen',
                  action: () =>
                      ref.read(privacyRepositoryProvider).clearCache(),
                  success: 'Lokaler Ergebnis-Cache wurde gelöscht.',
                  after: () => ref.invalidate(homeControllerProvider),
                ),
              ),
              _heading(context, 'Löschen'),
              ListTile(
                leading: const Icon(Icons.history_toggle_off),
                title: const Text('Gesamten Einschätzungsverlauf löschen'),
                subtitle: const Text(
                  'Profil und Einwilligungen bleiben erhalten. Die Einschätzungen werden tatsächlich gelöscht.',
                ),
                onTap: () => _confirmAction(
                  title: 'Einschätzungsverlauf löschen?',
                  explanation:
                      'Alle bisherigen Berichte und zugehörigen Kennzahlen und Hinweise werden dauerhaft gelöscht. Das lässt sich nicht rückgängig machen.',
                  confirmLabel: 'Verlauf endgültig löschen',
                  action: () =>
                      ref.read(privacyRepositoryProvider).deleteHistory(),
                  success: 'Einschätzungsverlauf wurde gelöscht.',
                  after: () {
                    ref.invalidate(assessmentHistoryProvider);
                    ref.invalidate(homeControllerProvider);
                  },
                ),
              ),
              ListTile(
                leading: const Icon(Icons.restaurant_menu),
                title: const Text('Alle Rezepte löschen'),
                subtitle: const Text(
                  'Lebensmittel und persönliche Profildaten bleiben erhalten.',
                ),
                onTap: () => _confirmAction(
                  title: 'Alle Rezepte endgültig löschen?',
                  explanation:
                      'Alle Rezepte samt Zutatenlisten und Zubereitungsschritten werden dauerhaft gelöscht. Die verwendeten Lebensmittel bleiben erhalten.',
                  confirmLabel: 'Rezepte löschen',
                  action: () =>
                      ref.read(privacyRepositoryProvider).deleteRecipes(),
                  success: 'Alle Rezepte wurden gelöscht.',
                  after: () => ref.invalidate(recipeListProvider),
                ),
              ),
              ListTile(
                leading: const Icon(Icons.local_grocery_store_outlined),
                title: const Text('Alle Lebensmittel löschen'),
                subtitle: const Text(
                  'Profil und Einschätzungen bleiben erhalten. Verwendete Lebensmittel erfordern vorher das Löschen der Rezepte.',
                ),
                onTap: () => _confirmAction(
                  title: 'Alle Lebensmittel endgültig löschen?',
                  explanation:
                      'Alle Lebensmittel, Nährwerte und Maße werden dauerhaft gelöscht. Falls Rezepte darauf verweisen, wird die Aktion sicher abgebrochen.',
                  confirmLabel: 'Lebensmittel löschen',
                  action: () =>
                      ref.read(privacyRepositoryProvider).deleteFoods(),
                  success: 'Alle Lebensmittel wurden gelöscht.',
                  after: () => ref.invalidate(foodListProvider),
                ),
              ),
              Card(
                color: Theme.of(context).colorScheme.errorContainer,
                child: ListTile(
                  leading: const Icon(Icons.delete_forever_outlined),
                  title: const Text('Alles löschen'),
                  subtitle: const Text(
                    'Löscht Profil, Einschätzungen, Rezepte, Lebensmittel, Einwilligungen und lokale App-Daten.',
                  ),
                  onTap: _deleteProfile,
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'Datenschutzinformation: Entwurf – vor einer öffentlichen Veröffentlichung professionell rechtlich und datenschutzrechtlich zu prüfen.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _withdraw(ConsentRecord consent) async {
    final confirmed = await _confirmation(
      'Einwilligung widerrufen?',
      'Der Widerruf verhindert neue Einschätzungen. Bereits gespeicherte Daten werden dadurch nicht automatisch gelöscht. Nutze dafür die getrennten Löschfunktionen.',
      'Einwilligung widerrufen',
    );
    if (!confirmed) return;
    await _run(() async {
      await ref.read(privacyRepositoryProvider).withdraw(consent.id);
      ref.invalidate(consentsProvider);
    }, 'Einwilligung wurde widerrufen. Neue Einschätzungen sind gesperrt.');
  }

  Future<void> _export() async {
    final confirmed = await _confirmation(
      'Datenexport erstellen?',
      'Die JSON-Datei enthält sensible persönliche Daten. Wähle in der Teilen-Funktion einen sicheren Empfänger oder Speicherort.',
      'Export erstellen',
    );
    if (!confirmed) return;
    await _run(
      () => ref.read(privacyRepositoryProvider).exportAndShare(),
      'Export wurde an die Teilen-Funktion übergeben; die temporäre App-Datei wurde anschließend gelöscht.',
    );
  }

  Future<void> _deleteProfile() async {
    final confirmed = await _confirmation(
      'Wirklich alle Daten endgültig löschen?',
      'Profil, Messungen, Aktivitäten, Ziele, Einschränkungen, Screening-Antworten, Einschätzungen, Rezepte, Lebensmittel, Einwilligungen und lokale App-Daten werden dauerhaft gelöscht. Dies kann nicht rückgängig gemacht werden.',
      'Alles endgültig löschen',
      destructive: true,
    );
    if (!confirmed) return;
    await _run(() async {
      await ref.read(privacyRepositoryProvider).deleteProfile();
      ref.invalidate(profileBundleProvider);
      ref.invalidate(assessmentHistoryProvider);
      ref.invalidate(homeControllerProvider);
      ref.invalidate(onboardingControllerProvider);
      ref.invalidate(consentsProvider);
      if (mounted) context.go('/home');
    }, 'Profil und zugehörige Daten wurden gelöscht.');
  }

  Future<void> _confirmAction({
    required String title,
    required String explanation,
    required String confirmLabel,
    required Future<void> Function() action,
    required String success,
    VoidCallback? after,
  }) async {
    final confirmed = await _confirmation(title, explanation, confirmLabel);
    if (!confirmed) return;
    await _run(() async {
      await action();
      after?.call();
    }, success);
  }

  Future<bool> _confirmation(
    String title,
    String explanation,
    String label, {
    bool destructive = false,
  }) async =>
      await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(title),
          content: Text(explanation),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              style: destructive
                  ? FilledButton.styleFrom(
                      backgroundColor: Theme.of(context).colorScheme.error,
                    )
                  : null,
              onPressed: () => Navigator.pop(context, true),
              child: Text(label),
            ),
          ],
        ),
      ) ??
      false;

  Future<void> _run(Future<void> Function() action, String success) async {
    setState(() {
      busy = true;
      status = null;
    });
    try {
      await action();
      if (mounted) setState(() => status = success);
    } catch (error) {
      if (mounted) setState(() => status = 'Aktion fehlgeschlagen: $error');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }
}

final class _ConsentTile extends StatelessWidget {
  const _ConsentTile({required this.consent, required this.onWithdraw});
  final ConsentRecord consent;
  final VoidCallback? onWithdraw;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(
              consent.status == 'granted'
                  ? Icons.check_circle_outline
                  : Icons.block,
            ),
            title: Text(
              consent.status == 'granted'
                  ? 'Einwilligung aktiv'
                  : 'Einwilligung widerrufen',
            ),
            subtitle: Text(
              'Zweck: ${consent.purposeCode}\nTextversion: ${consent.textVersion}'
              '${consent.grantedAt == null ? '' : '\nErteilt: ${DateFormatters.dateTime(consent.grantedAt!)}'}'
              '${consent.withdrawnAt == null ? '' : '\nWiderrufen: ${DateFormatters.dateTime(consent.withdrawnAt!)}'}',
            ),
          ),
          if (onWithdraw != null)
            OutlinedButton.icon(
              onPressed: onWithdraw,
              icon: const Icon(Icons.undo),
              label: const Text('Einwilligung widerrufen'),
            ),
        ],
      ),
    ),
  );
}

Widget _heading(BuildContext context, String value) => Padding(
  padding: const EdgeInsets.only(top: 22, bottom: 6),
  child: Text(value, style: Theme.of(context).textTheme.titleLarge),
);
