import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/states.dart';
import 'shopping_list_models.dart';

class ShoppingListsScreen extends ConsumerStatefulWidget {
  const ShoppingListsScreen({super.key});
  @override
  ConsumerState<ShoppingListsScreen> createState() => _ShoppingListsState();
}

class _ShoppingListsState extends ConsumerState<ShoppingListsScreen> {
  bool archived = false;
  late Future<List<ShoppingListSummary>> future;
  @override
  void initState() {
    super.initState();
    future = _load();
  }

  Future<List<ShoppingListSummary>> _load() =>
      ref.read(shoppingListRepositoryProvider).lists(archived: archived);
  void reload() {
    setState(() {
      future = _load();
    });
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Einkaufslisten',
    actions: [IconButton(onPressed: reload, icon: const Icon(Icons.refresh))],
    body: FutureBuilder<List<ShoppingListSummary>>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return ErrorState(
            message: snapshot.error.toString(),
            onRetry: reload,
          );
        }
        final items = snapshot.data ?? [];
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Wrap(
              spacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: _create,
                  icon: const Icon(Icons.add),
                  label: const Text('Leere Liste'),
                ),
                OutlinedButton.icon(
                  onPressed: () => context.push('/shopping-lists/generate'),
                  icon: const Icon(Icons.event_note),
                  label: const Text('Aus Plan'),
                ),
                FilterChip(
                  label: const Text('Archivierte'),
                  selected: archived,
                  onSelected: (value) {
                    archived = value;
                    reload();
                  },
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (items.isEmpty)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: Text('Noch keine Einkaufsliste')),
              )
            else
              ...items.map(
                (item) => Card(
                  child: ListTile(
                    leading: Icon(
                      item.status == 'completed'
                          ? Icons.task_alt
                          : Icons.shopping_cart_outlined,
                    ),
                    title: Text(item.name),
                    subtitle: Text(
                      '${_source(item.sourceType)} · '
                      '${item.checkedCount}/${item.itemCount} erledigt',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context
                        .push('/shopping-lists/${item.id}')
                        .then((_) => reload()),
                  ),
                ),
              ),
          ],
        );
      },
    ),
  );

  String _source(String source) => switch (source) {
    'daily_plan' => 'Tagesplan',
    'weekly_plan' => 'Wochenplan',
    _ => 'Manuell',
  };

  Future<void> _create() async {
    final controller = TextEditingController(text: 'Einkaufsliste');
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Leere Liste erstellen'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Name'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Erstellen'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (name == null || name.isEmpty) return;
    final result = await ref.read(shoppingListRepositoryProvider).create(name);
    if (mounted) {
      context
          .push('/shopping-lists/${result.summary.id}')
          .then((_) => reload());
    }
  }
}
