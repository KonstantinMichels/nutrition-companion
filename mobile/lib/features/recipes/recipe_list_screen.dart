import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/providers.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/states.dart';
import 'recipe_models.dart';

final recipeListProvider = FutureProvider.autoDispose
    .family<List<RecipeItem>, ({String query, bool archived})>(
      (ref, filter) => ref
          .watch(recipeRepositoryProvider)
          .list(query: filter.query, archived: filter.archived),
    );

final class RecipeListScreen extends ConsumerStatefulWidget {
  const RecipeListScreen({super.key});
  @override
  ConsumerState<RecipeListScreen> createState() => _RecipeListScreenState();
}

final class _RecipeListScreenState extends ConsumerState<RecipeListScreen> {
  String query = '';
  bool archived = false;
  Timer? timer;
  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final filter = (query: query, archived: archived);
    final state = ref.watch(recipeListProvider(filter));
    return AppScaffold(
      title: 'Rezepte',
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.go('/recipes/new'),
        icon: const Icon(Icons.add),
        label: const Text('Rezept'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                labelText: 'Rezepte suchen',
              ),
              onChanged: (value) {
                timer?.cancel();
                timer = Timer(
                  const Duration(milliseconds: 350),
                  () => setState(() => query = value),
                );
              },
            ),
            SwitchListTile(
              title: const Text('Archivierte anzeigen'),
              value: archived,
              onChanged: (value) => setState(() => archived = value),
            ),
            Expanded(
              child: state.when(
                loading: () => const LoadingState(),
                error: (e, _) => ErrorState(
                  message: e.toString(),
                  onRetry: () => ref.invalidate(recipeListProvider(filter)),
                ),
                data: (items) => items.isEmpty
                    ? const Center(
                        child: Text('Noch keine Rezepte gespeichert.'),
                      )
                    : ListView.builder(
                        itemCount: items.length,
                        itemBuilder: (_, index) {
                          final item = items[index];
                          final energy = item.nutrients
                              .where((n) => n.code == 'energy_kcal')
                              .firstOrNull;
                          return Card(
                            child: ListTile(
                              title: Text(item.name),
                              subtitle: Text(
                                '${item.servings} Portionen · ${item.tags.join(', ')}\n${energy == null ? 'Energie nicht vollständig' : '${energy.perServing} kcal pro Portion'}${item.archived ? ' · Archiviert' : ''}',
                              ),
                              isThreeLine: true,
                              trailing: const Icon(Icons.chevron_right),
                              onTap: () => context.go('/recipes/${item.id}'),
                            ),
                          );
                        },
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
