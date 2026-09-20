import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/design_system.dart';
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
    revealRootBackground: true,
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
          padding: EdgeInsets.fromLTRB(
            AppLayout.sectionOuterMargin,
            AppSpacing.sm,
            AppLayout.sectionOuterMargin,
            AppLayout.navigationContentInset +
                MediaQuery.viewPaddingOf(context).bottom,
          ),
          children: [
            NutritionSection(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NutritionSectionHeader(title: 'Neue Einkaufsliste'),
                  const SizedBox(height: AppSpacing.md),
                  Wrap(
                    spacing: AppSpacing.xs,
                    runSpacing: AppSpacing.xs,
                    children: [
                      FilledButton.icon(
                        onPressed: _create,
                        icon: const Icon(Icons.add),
                        label: const Text('Leere Liste'),
                      ),
                      NutritionActionPill(
                        label: 'Aus Plan',
                        icon: Icons.event_note,
                        onPressed: () =>
                            context.push('/shopping-lists/generate'),
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
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            if (items.isEmpty)
              const NutritionSection(
                child: Center(child: Text('Noch keine Einkaufsliste')),
              )
            else
              NutritionSection(
                child: Column(
                  children: [
                    for (var index = 0; index < items.length; index++)
                      NutritionListRow(
                        leading: Icon(
                          items[index].status == 'completed'
                              ? Icons.task_alt
                              : Icons.shopping_cart_outlined,
                        ),
                        title: Text(items[index].name),
                        subtitle: Text(
                          '${_source(items[index].sourceType)} · '
                          '${items[index].checkedCount}/${items[index].itemCount} erledigt',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context
                            .push('/shopping-lists/${items[index].id}')
                            .then((_) => reload()),
                        showDivider: index < items.length - 1,
                      ),
                  ],
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
