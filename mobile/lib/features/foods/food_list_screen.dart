import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/design_system.dart';
import '../../core/widgets/states.dart';
import 'food_models.dart';

final foodListProvider = FutureProvider.autoDispose
    .family<List<FoodItem>, ({String query, bool archived})>(
      (ref, filter) => ref
          .watch(foodRepositoryProvider)
          .list(query: filter.query, archived: filter.archived),
    );

final class FoodListScreen extends ConsumerStatefulWidget {
  const FoodListScreen({super.key});
  @override
  ConsumerState<FoodListScreen> createState() => _FoodListScreenState();
}

final class _FoodListScreenState extends ConsumerState<FoodListScreen> {
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
    final state = ref.watch(foodListProvider(filter));
    return AppScaffold(
      title: 'Lebensmittel',
      revealRootBackground: true,
      actions: [
        IconButton(
          onPressed: () => context.go('/foods/scan'),
          tooltip: 'Barcode scannen',
          icon: const Icon(Icons.qr_code_scanner),
        ),
      ],
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.go('/foods/new'),
        icon: const Icon(Icons.add),
        label: const Text('Neu'),
      ),
      body: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppLayout.sectionOuterMargin,
          AppSpacing.sm,
          AppLayout.sectionOuterMargin,
          0,
        ),
        child: Column(
          children: [
            NutritionSection(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                children: [
                  TextField(
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.search),
                      labelText: 'Name oder Marke suchen',
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
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Archivierte anzeigen'),
                    value: archived,
                    onChanged: (value) => setState(() => archived = value),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Expanded(
              child: state.when(
                loading: () => const LoadingState(),
                error: (e, _) => ErrorState(
                  message: e.toString(),
                  onRetry: () => ref.invalidate(foodListProvider(filter)),
                ),
                data: (items) => items.isEmpty
                    ? const Center(
                        child: Text('Noch keine Lebensmittel gespeichert.'),
                      )
                    : NutritionSection(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.xl,
                          vertical: AppSpacing.sm,
                        ),
                        child: ListView.builder(
                          padding: EdgeInsets.only(
                            bottom:
                                AppLayout.navigationContentInset +
                                MediaQuery.viewPaddingOf(context).bottom,
                          ),
                          itemCount: items.length,
                          itemBuilder: (_, index) {
                            final food = items[index];
                            return NutritionListRow(
                              title: Text(food.name),
                              subtitle: Text(
                                '${food.brand ?? 'Ohne Marke'} · pro 100 ${food.referenceUnit}\n${food.quality == 'incomplete' ? 'Unvollständige Angaben' : 'Grundwerte vollständig'}${food.archived ? ' · Archiviert' : ''}',
                              ),
                              isThreeLine: true,
                              trailing: const Icon(Icons.chevron_right),
                              onTap: () => context.go('/foods/${food.id}'),
                              showDivider: index < items.length - 1,
                            );
                          },
                        ),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
