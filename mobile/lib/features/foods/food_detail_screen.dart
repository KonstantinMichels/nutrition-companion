import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/states.dart';
import 'food_list_screen.dart';
import 'food_models.dart';

final foodDetailProvider = FutureProvider.autoDispose.family<FoodItem, String>(
  (ref, id) => ref.watch(foodRepositoryProvider).detail(id),
);

final class FoodDetailScreen extends ConsumerWidget {
  const FoodDetailScreen({required this.id, super.key});

  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(foodDetailProvider(id));
    return AppScaffold(
      title: 'Lebensmittel',
      onBackPressed: () => context.go('/foods'),
      body: state.when(
        loading: () => const LoadingState(),
        error: (error, _) => ErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(foodDetailProvider(id)),
        ),
        data: (food) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(food.name, style: Theme.of(context).textTheme.headlineSmall),
            if (food.brand != null) Text(food.brand!),
            Text('pro 100 ${food.referenceUnit}'),
            Text(
              food.archived
                  ? 'Archiviert · schreibgeschützt'
                  : food.sourceType == 'open_food_facts'
                  ? 'Importiert aus Open Food Facts · bitte prüfen'
                  : 'Manuell eingetragen',
            ),
            const Divider(),
            for (final nutrient in food.nutrients)
              ListTile(
                title: Text(nutrient.name),
                trailing: Text('${nutrient.amount} ${nutrient.unit}'),
                subtitle: Text(
                  nutrient.derived ? 'Berechnet' : 'Manuell eingetragen',
                ),
              ),
            const Divider(),
            Text(
              food.quality == 'incomplete'
                  ? 'Fehlende Werte: Nicht angegeben'
                  : 'Grundnährwerte vollständig',
            ),
            const SizedBox(height: 16),
            if (!food.archived) ...[
              FilledButton(
                onPressed: () => context.go('/foods/$id/edit'),
                child: const Text('Bearbeiten'),
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.restaurant_menu),
                onPressed: () => context.go('/recipes/new?foodId=$id'),
                label: const Text('Als Gericht übernehmen'),
              ),
              OutlinedButton(
                onPressed: () => _archive(context, ref),
                child: const Text('Archivieren'),
              ),
            ] else
              FilledButton(
                onPressed: () => _restore(context, ref),
                child: const Text('Wiederherstellen'),
              ),
            const SizedBox(height: 8),
            TextButton.icon(
              icon: const Icon(Icons.delete_forever_outlined),
              label: const Text('Endgültig löschen'),
              style: TextButton.styleFrom(
                foregroundColor: Theme.of(context).colorScheme.error,
              ),
              onPressed: () => _permanentlyDelete(context, ref, food.name),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _archive(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Lebensmittel archivieren?'),
        content: const Text(
          'Es bleibt erhalten und kann später wiederhergestellt werden.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Archivieren'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await ref.read(foodRepositoryProvider).archive(id);
    ref.invalidate(foodListProvider);
    ref.invalidate(foodDetailProvider(id));
  }

  Future<void> _restore(BuildContext context, WidgetRef ref) async {
    await ref.read(foodRepositoryProvider).restore(id);
    ref.invalidate(foodListProvider);
    ref.invalidate(foodDetailProvider(id));
  }

  Future<void> _permanentlyDelete(
    BuildContext context,
    WidgetRef ref,
    String foodName,
  ) async {
    final router = GoRouter.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final errorColor = Theme.of(context).colorScheme.error;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        icon: Icon(
          Icons.warning_amber_rounded,
          color: Theme.of(dialogContext).colorScheme.error,
        ),
        title: const Text('Endgültig löschen?'),
        content: Text(
          '„$foodName“ sowie alle eingetragenen Nährwerte und Maße werden '
          'dauerhaft gelöscht. Diese Aktion kann nicht rückgängig gemacht werden.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(dialogContext).colorScheme.error,
              foregroundColor: Theme.of(dialogContext).colorScheme.onError,
            ),
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Dauerhaft löschen'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      await ref.read(foodRepositoryProvider).permanentlyDelete(id);
      ref.invalidate(foodListProvider);
      router.go('/foods');
      messenger.showSnackBar(
        const SnackBar(content: Text('Das Lebensmittel wurde gelöscht.')),
      );
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(
          content: Text('Löschen fehlgeschlagen: $error'),
          backgroundColor: errorColor,
        ),
      );
    }
  }
}
