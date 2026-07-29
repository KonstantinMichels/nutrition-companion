import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/providers.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/states.dart';
import 'recipe_models.dart';
import 'recipe_availability_models.dart';

final recipeListProvider = FutureProvider.autoDispose
    .family<List<RecipeItem>, ({String query, bool archived})>(
      (ref, filter) => ref
          .watch(recipeRepositoryProvider)
          .list(query: filter.query, archived: filter.archived),
    );

final recipeAvailabilityListProvider = FutureProvider.autoDispose
    .family<
      List<RecipeAvailabilitySummary>,
      ({String query, bool archived, String availability})
    >((ref, filter) {
      return ref
          .watch(recipeAvailabilityRepositoryProvider)
          .summaries(
            query: filter.query,
            archived: filter.archived,
            state: filter.availability == 'all' ? null : filter.availability,
          );
    });

final class RecipeListScreen extends ConsumerStatefulWidget {
  const RecipeListScreen({super.key});
  @override
  ConsumerState<RecipeListScreen> createState() => _RecipeListScreenState();
}

final class _RecipeListScreenState extends ConsumerState<RecipeListScreen> {
  String query = '';
  bool archived = false;
  String availability = 'all';
  Timer? timer;
  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final filter = (
      query: query,
      archived: archived,
      availability: availability,
    );
    final state = ref.watch(recipeAvailabilityListProvider(filter));
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
            DropdownButtonFormField<String>(
              initialValue: availability,
              decoration: const InputDecoration(
                labelText: 'Vorratsverfügbarkeit',
              ),
              items: const [
                DropdownMenuItem(value: 'all', child: Text('Alle Rezepte')),
                DropdownMenuItem(
                  value: 'fully_available',
                  child: Text('Vollständig verfügbar'),
                ),
                DropdownMenuItem(
                  value: 'partially_available',
                  child: Text('Teilweise verfügbar'),
                ),
                DropdownMenuItem(
                  value: 'not_available',
                  child: Text('Nicht verfügbar'),
                ),
                DropdownMenuItem(
                  value: 'unresolved',
                  child: Text('Nicht berechenbar'),
                ),
              ],
              onChanged: (value) {
                if (value != null) setState(() => availability = value);
              },
            ),
            const SizedBox(height: 8),
            Expanded(
              child: state.when(
                loading: () => const LoadingState(),
                error: (e, _) => ErrorState(
                  message: e.toString(),
                  onRetry: () =>
                      ref.invalidate(recipeAvailabilityListProvider(filter)),
                ),
                data: (items) => items.isEmpty
                    ? const Center(
                        child: Text('Noch keine Rezepte gespeichert.'),
                      )
                    : ListView.builder(
                        itemCount: items.length,
                        itemBuilder: (_, index) {
                          final item = items[index];
                          return Card(
                            child: ListTile(
                              title: Text(item.name),
                              subtitle: Text(_availabilityText(item)),
                              trailing: const Icon(Icons.chevron_right),
                              onTap: () =>
                                  context.go('/recipes/${item.recipeId}'),
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

  String _availabilityText(RecipeAvailabilitySummary item) {
    final status = switch (item.state) {
      'fully_available' => 'Vollständig verfügbar',
      'partially_available' => 'Teilweise verfügbar',
      'not_available' => 'Nicht verfügbar',
      'empty_recipe' => 'Leeres Rezept',
      _ => 'Nicht vollständig berechenbar',
    };
    final maximum = item.maximum.isEmpty
        ? ''
        : ' · Rechnerisch ${item.maximum} Portionen';
    final missing = item.missing == 0
        ? ''
        : ' · ${item.missing} fehlende Zutaten';
    final unresolved = item.unresolved == 0
        ? ''
        : ' · ${item.unresolved} ungeklärt';
    final archivedLabel = item.archived ? ' · Archiviert' : '';
    return '$status$maximum$missing$unresolved$archivedLabel';
  }
}
