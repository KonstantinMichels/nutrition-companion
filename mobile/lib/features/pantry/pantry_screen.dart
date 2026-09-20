import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../core/errors/app_exception.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/design_system.dart';
import 'pantry_models.dart';

final class PantryScreen extends ConsumerStatefulWidget {
  const PantryScreen({super.key});
  @override
  ConsumerState<PantryScreen> createState() => _PantryScreenState();
}

final class _PantryScreenState extends ConsumerState<PantryScreen> {
  final search = TextEditingController();
  Timer? debounce;
  bool loading = true,
      byLocation = false,
      showDepleted = false,
      showArchived = false;
  String? error, statusFilter;
  Map<String, dynamic> summary = {};
  List<PantryAvailability> foods = [];
  List<PantryLot> lots = [];
  List<PantryLocation> locations = [];

  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  @override
  void dispose() {
    debounce?.cancel();
    search.dispose();
    super.dispose();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final repository = ref.read(pantryRepositoryProvider);
      final values = await Future.wait([
        repository.summary(),
        repository.availability(),
        repository.lots(
          query: search.text,
          depleted: showDepleted,
          archived: showArchived,
          status: statusFilter,
        ),
        repository.locations(archived: showArchived),
      ]);
      if (mounted) {
        setState(() {
          summary = values[0] as Map<String, dynamic>;
          foods = values[1] as List<PantryAvailability>;
          lots = values[2] as List<PantryLot>;
          locations = values[3] as List<PantryLocation>;
        });
      }
    } on AppException catch (exception) {
      if (mounted) setState(() => error = exception.message);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Vorrat',
    revealRootBackground: true,
    actions: [
      IconButton(
        tooltip: 'Lagerorte verwalten',
        onPressed: () async {
          await context.push('/pantry/locations');
          if (mounted) load();
        },
        icon: const Icon(Icons.shelves),
      ),
    ],
    floatingActionButton: FloatingActionButton.extended(
      onPressed: () async {
        await context.push('/pantry/add');
        if (mounted) load();
      },
      icon: const Icon(Icons.add),
      label: const Text('Lebensmittel hinzufügen'),
    ),
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : error != null
        ? _error()
        : RefreshIndicator(
            onRefresh: load,
            child: ListView(
              padding: EdgeInsets.fromLTRB(
                AppLayout.sectionOuterMargin,
                AppSpacing.sm,
                AppLayout.sectionOuterMargin,
                AppLayout.navigationContentInset +
                    MediaQuery.viewPaddingOf(context).bottom,
              ),
              children: [
                _summary(),
                const SizedBox(height: AppSpacing.sm),
                NutritionSection(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Column(
                    children: [
                      TextField(
                        controller: search,
                        decoration: const InputDecoration(
                          prefixIcon: Icon(Icons.search),
                          labelText: 'Vorrat durchsuchen',
                        ),
                        onChanged: (_) {
                          debounce?.cancel();
                          debounce = Timer(
                            const Duration(milliseconds: 350),
                            load,
                          );
                        },
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      SegmentedButton<bool>(
                        segments: const [
                          ButtonSegment(
                            value: false,
                            label: Text('Lebensmittel'),
                            icon: Icon(Icons.restaurant),
                          ),
                          ButtonSegment(
                            value: true,
                            label: Text('Lagerort'),
                            icon: Icon(Icons.shelves),
                          ),
                        ],
                        selected: {byLocation},
                        onSelectionChanged: (value) =>
                            setState(() => byLocation = value.first),
                      ),
                      _filters(),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                if (lots.isEmpty)
                  _empty()
                else
                  NutritionSection(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.md,
                      vertical: AppSpacing.xs,
                    ),
                    child: Column(
                      children: byLocation
                          ? [
                              for (
                                var index = 0;
                                index < locations.length;
                                index++
                              )
                                _location(
                                  locations[index],
                                  index < locations.length - 1,
                                ),
                            ]
                          : [
                              for (var index = 0; index < foods.length; index++)
                                _food(foods[index], index < foods.length - 1),
                            ],
                    ),
                  ),
              ],
            ),
          ),
  );

  Widget _summary() => NutritionSection(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const NutritionSectionHeader(title: 'Vorratsübersicht'),
        const SizedBox(height: AppSpacing.sm),
        Text(
          '${summary['active_food_count'] ?? 0} Lebensmittel · ${summary['active_lot_count'] ?? 0} aktive Bestände',
        ),
        Text(
          '${summary['expiring_soon_count'] ?? 0} mit nahem Datum · ${(summary['past_best_before_count'] ?? 0) + (summary['past_use_by_count'] ?? 0)} mit überschrittenem Datum',
        ),
        const SizedBox(height: AppSpacing.xs),
        const Text(
          'Datumsangaben dienen der Bestandsübersicht. Die App bewertet nicht automatisch, ob ein Lebensmittel noch verzehrfähig ist.',
        ),
      ],
    ),
  );
  Widget _filters() => ExpansionTile(
    title: const Text('Filter'),
    children: [
      SwitchListTile(
        title: const Text('Aufgebrauchte anzeigen'),
        value: showDepleted,
        onChanged: (value) {
          showDepleted = value;
          load();
        },
      ),
      SwitchListTile(
        title: const Text('Archivierte anzeigen'),
        value: showArchived,
        onChanged: (value) {
          showArchived = value;
          load();
        },
      ),
      DropdownButtonFormField<String?>(
        initialValue: statusFilter,
        decoration: const InputDecoration(labelText: 'Datumsstatus'),
        items: const [
          DropdownMenuItem(value: null, child: Text('Alle Datumszustände')),
          DropdownMenuItem(
            value: 'expiring_soon',
            child: Text('Datum in Kürze'),
          ),
          DropdownMenuItem(value: 'date_today', child: Text('Heute datiert')),
          DropdownMenuItem(
            value: 'past_best_before',
            child: Text('MHD überschritten'),
          ),
          DropdownMenuItem(
            value: 'past_use_by',
            child: Text('Verbrauchsdatum überschritten'),
          ),
          DropdownMenuItem(value: 'no_date', child: Text('Ohne Datum')),
        ],
        onChanged: (value) {
          statusFilter = value;
          load();
        },
      ),
      const SizedBox(height: 8),
    ],
  );
  Widget _food(PantryAvailability item, bool showDivider) {
    final foodLots = lots.where((lot) => lot.foodId == item.foodId).toList();
    return Column(
      children: [
        ExpansionTile(
          leading: const Icon(Icons.inventory_2_outlined),
          title: Text(
            '${item.name}${item.brand == null ? '' : ' · ${item.brand}'}',
          ),
          subtitle: Text(
            '${item.quantity} ${item.unit} verfügbar · ${item.lotCount} Bestände',
          ),
          children: [
            if (item.archivedFood)
              const ListTile(
                leading: Icon(Icons.warning_amber),
                title: Text('Das Lebensmittel ist archiviert.'),
              ),
            for (final lot in foodLots) _lotTile(lot),
          ],
        ),
        if (showDivider) const Divider(),
      ],
    );
  }

  Widget _location(PantryLocation item, bool showDivider) {
    final locationLots = lots
        .where((lot) => lot.locationId == item.id)
        .toList();
    return Column(
      children: [
        ExpansionTile(
          leading: Icon(_locationIcon(item.type)),
          title: Text(item.name),
          subtitle: Text('${locationLots.length} Bestände'),
          children: locationLots.isEmpty
              ? [const ListTile(title: Text('Kein aktiver Bestand'))]
              : locationLots.map(_lotTile).toList(),
        ),
        if (showDivider) const Divider(),
      ],
    );
  }

  Widget _lotTile(PantryLot lot) => ListTile(
    onTap: () async {
      await context.push('/pantry/items/${lot.id}');
      if (mounted) load();
    },
    title: Text(lot.foodName),
    subtitle: Text(
      '${lot.quantity} ${lot.unit} · ${lot.locationName}\n${_dateStatus(lot.dateStatus)}',
    ),
    isThreeLine: true,
    trailing: const Icon(Icons.chevron_right),
  );
  Widget _empty() => NutritionSection(
    child: Column(
      children: [
        const Icon(Icons.inventory_2_outlined, size: 48),
        const SizedBox(height: 12),
        const Text('Noch keine Lebensmittel im Vorrat'),
        const SizedBox(height: 12),
        FilledButton(
          onPressed: () => context.push('/pantry/add'),
          child: const Text('Lebensmittel hinzufügen'),
        ),
      ],
    ),
  );
  Widget _error() => Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(error!, textAlign: TextAlign.center),
        FilledButton.icon(
          key: const Key('pantry-retry'),
          onPressed: load,
          icon: const Icon(Icons.refresh),
          label: const Text('Erneut versuchen'),
        ),
      ],
    ),
  );
}

String pantryDateStatus(String value) => _dateStatus(value);
String _dateStatus(String value) => switch (value) {
  'expiring_soon' => 'Datum in Kürze',
  'date_today' => 'Heute datiert',
  'past_best_before' => 'Mindesthaltbarkeitsdatum überschritten',
  'past_use_by' => 'Verbrauchsdatum überschritten',
  'no_date' => 'Kein Datum angegeben',
  _ => 'Datum hinterlegt',
};
IconData _locationIcon(String type) => switch (type) {
  'refrigerator' => Icons.kitchen,
  'freezer' => Icons.ac_unit,
  'cellar' => Icons.warehouse,
  _ => Icons.shelves,
};
