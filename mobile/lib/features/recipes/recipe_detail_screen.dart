import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/providers.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/states.dart';
import '../../core/formatting/german_decimal.dart';
import 'recipe_list_screen.dart';
import 'recipe_models.dart';
import 'recipe_comparison_section.dart';
import 'recipe_availability_section.dart';

final recipeDetailProvider = FutureProvider.autoDispose
    .family<RecipeItem, String>(
      (ref, id) => ref.watch(recipeRepositoryProvider).detail(id),
    );

final class RecipeDetailScreen extends ConsumerStatefulWidget {
  const RecipeDetailScreen({required this.id, super.key});
  final String id;
  @override
  ConsumerState<RecipeDetailScreen> createState() => _RecipeDetailScreenState();
}

final class _RecipeDetailScreenState extends ConsumerState<RecipeDetailScreen> {
  final servings = TextEditingController();
  Map<String, dynamic>? scaled;
  @override
  void dispose() {
    servings.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(recipeDetailProvider(widget.id));
    return AppScaffold(
      title: 'Rezept',
      onBackPressed: () => context.go('/recipes'),
      body: state.when(
        loading: () => const LoadingState(),
        error: (e, _) => ErrorState(
          message: e.toString(),
          onRetry: () => ref.invalidate(recipeDetailProvider(widget.id)),
        ),
        data: (recipe) {
          if (servings.text.isEmpty) servings.text = recipe.servings;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                recipe.name,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              if (recipe.description != null) Text(recipe.description!),
              Wrap(
                spacing: 8,
                children: recipe.tags
                    .map((tag) => Chip(label: Text(tag)))
                    .toList(),
              ),
              Text(
                '${recipe.servings} Portionen${recipe.archived ? ' · Archiviert' : ''}',
              ),
              for (final warning in recipe.warnings)
                ListTile(
                  leading: const Icon(Icons.warning_amber),
                  title: Text(warning),
                ),
              const Divider(),
              Text('Zutaten', style: Theme.of(context).textTheme.titleLarge),
              for (final item in recipe.ingredients)
                ListTile(
                  title: Text(item.foodName),
                  subtitle: Text(
                    '${item.quantity} ${item.unitName}${item.note == null ? '' : ' · ${item.note}'}${item.archived ? ' · Archiviertes Lebensmittel' : ''}${item.estimated ? ' · Geschätzte Umrechnung' : ''}',
                  ),
                ),
              TextField(
                controller: servings,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(
                  labelText: 'Portionen-Vorschau',
                ),
              ),
              OutlinedButton(
                onPressed: () async {
                  final result = await ref
                      .read(recipeRepositoryProvider)
                      .scale(widget.id, servings.text.replaceAll(',', '.'));
                  if (mounted) setState(() => scaled = result);
                },
                child: const Text('Mengen skalieren'),
              ),
              if (scaled != null)
                for (final item in scaled!['ingredients'] as List)
                  Text(
                    '${GermanDecimal.formatString(item['quantity'])} ${item['unit_code']} ${item['food_name']}',
                  ),
              const Divider(),
              Text(
                'Zubereitung',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              if (recipe.steps.isEmpty)
                const Text('Keine Schritte angegeben.')
              else
                for (var i = 0; i < recipe.steps.length; i++)
                  ListTile(
                    leading: CircleAvatar(child: Text('${i + 1}')),
                    title: Text(recipe.steps[i].instruction),
                  ),
              const Divider(),
              Text(
                'Nährwerte pro Portion',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              for (final n in recipe.nutrients.where(
                (n) => [
                  'energy_kcal',
                  'fat',
                  'carbohydrate',
                  'protein',
                  'fiber',
                ].contains(n.code),
              ))
                ListTile(
                  title: Text(n.name),
                  trailing: Text('${n.perServing} ${n.unit}'),
                  subtitle: !n.complete
                      ? const Text('Nicht vollständig')
                      : null,
                ),
              Text(
                recipe.weightStatus == 'unavailable'
                    ? 'Pro 100 g: Nicht verfügbar'
                    : 'Pro 100 g verfügbar',
              ),
              const Divider(),
              RecipeComparisonSection(recipeId: widget.id),
              RecipeAvailabilitySection(recipeId: widget.id),
              FilledButton.tonalIcon(
                key: const Key('recipe-pantry-aware-shopping'),
                onPressed: () => context.push(
                  '/pantry-aware-shopping?sourceType=recipe&sourceId=${widget.id}',
                ),
                icon: const Icon(Icons.shopping_cart_outlined),
                label: const Text('Fehlende Zutaten einkaufen'),
              ),
              const SizedBox(height: 16),
              if (!recipe.archived) ...[
                FilledButton(
                  onPressed: () => context.go('/recipes/${widget.id}/edit'),
                  child: const Text('Bearbeiten'),
                ),
                OutlinedButton(
                  onPressed: () async {
                    final copy = await ref
                        .read(recipeRepositoryProvider)
                        .duplicate(widget.id);
                    ref.invalidate(recipeListProvider);
                    if (context.mounted) {
                      context.go('/recipes/${copy.id}');
                    }
                  },
                  child: const Text('Duplizieren'),
                ),
                TextButton(
                  onPressed: () => _archive(context),
                  child: const Text('Archivieren'),
                ),
              ] else
                FilledButton(
                  onPressed: () async {
                    await ref.read(recipeRepositoryProvider).restore(widget.id);
                    ref.invalidate(recipeListProvider);
                    ref.invalidate(recipeDetailProvider(widget.id));
                  },
                  child: const Text('Wiederherstellen'),
                ),
              const SizedBox(height: 8),
              TextButton.icon(
                icon: const Icon(Icons.delete_forever_outlined),
                label: const Text('Endgültig löschen'),
                style: TextButton.styleFrom(
                  foregroundColor: Theme.of(context).colorScheme.error,
                ),
                onPressed: () => _permanentlyDelete(context, recipe.name),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _archive(BuildContext context) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('Rezept archivieren?'),
        content: const Text(
          'Es bleibt erhalten und kann wiederhergestellt werden.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialog, false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialog, true),
            child: const Text('Archivieren'),
          ),
        ],
      ),
    );
    if (yes == true) {
      await ref.read(recipeRepositoryProvider).archive(widget.id);
      ref.invalidate(recipeListProvider);
      ref.invalidate(recipeDetailProvider(widget.id));
    }
  }

  Future<void> _permanentlyDelete(
    BuildContext context,
    String recipeName,
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
        title: const Text('Rezept endgültig löschen?'),
        content: Text(
          '„$recipeName“ mit allen Zutaten und Zubereitungsschritten wird '
          'dauerhaft gelöscht. Die verwendeten Lebensmittel bleiben erhalten.',
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
      await ref.read(recipeRepositoryProvider).permanentlyDelete(widget.id);
      ref.invalidate(recipeListProvider);
      router.go('/recipes');
      messenger.showSnackBar(
        const SnackBar(content: Text('Das Rezept wurde gelöscht.')),
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
