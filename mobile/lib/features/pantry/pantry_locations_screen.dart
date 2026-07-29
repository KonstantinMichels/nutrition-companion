import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/widgets/app_scaffold.dart';
import 'pantry_models.dart';

final class PantryLocationsScreen extends ConsumerStatefulWidget {
  const PantryLocationsScreen({super.key});
  @override
  ConsumerState<PantryLocationsScreen> createState() =>
      _PantryLocationsScreenState();
}

final class _PantryLocationsScreenState
    extends ConsumerState<PantryLocationsScreen> {
  List<PantryLocation> items = [];
  bool loading = true, archived = false;
  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  Future<void> load() async {
    final value = await ref
        .read(pantryRepositoryProvider)
        .locations(archived: archived);
    if (mounted) {
      setState(() {
        items = value;
        loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Lagerorte',
    showNavigation: false,
    floatingActionButton: FloatingActionButton.extended(
      onPressed: () => edit(),
      icon: const Icon(Icons.add),
      label: const Text('Lagerort'),
    ),
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
            children: [
              SwitchListTile(
                title: const Text('Archivierte Lagerorte anzeigen'),
                value: archived,
                onChanged: (value) {
                  archived = value;
                  load();
                },
              ),
              for (final item in items)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.shelves),
                    title: Text(item.name),
                    subtitle: Text(
                      '${_type(item.type)} · ${item.lotCount} aktive Bestände${item.archived ? ' · Archiviert' : ''}',
                    ),
                    trailing: PopupMenuButton<String>(
                      onSelected: (action) => action == 'edit'
                          ? edit(item)
                          : action == 'restore'
                          ? restore(item)
                          : archive(item),
                      itemBuilder: (_) => [
                        if (!item.archived)
                          const PopupMenuItem(
                            value: 'edit',
                            child: Text('Bearbeiten'),
                          ),
                        PopupMenuItem(
                          value: item.archived ? 'restore' : 'archive',
                          child: Text(
                            item.archived ? 'Wiederherstellen' : 'Archivieren',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
  );
  Future<void> edit([PantryLocation? item]) async {
    var name = item?.name ?? '';
    var type = item?.type ?? 'pantry';
    final accepted = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: Text(item == null ? 'Lagerort anlegen' : 'Lagerort bearbeiten'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              initialValue: name,
              onChanged: (value) => name = value,
              decoration: const InputDecoration(labelText: 'Name'),
            ),
            DropdownButtonFormField<String>(
              initialValue: type,
              decoration: const InputDecoration(labelText: 'Art'),
              items: const [
                DropdownMenuItem(
                  value: 'pantry',
                  child: Text('Vorratsschrank'),
                ),
                DropdownMenuItem(
                  value: 'refrigerator',
                  child: Text('Kühlschrank'),
                ),
                DropdownMenuItem(
                  value: 'freezer',
                  child: Text('Gefrierschrank'),
                ),
                DropdownMenuItem(value: 'kitchen', child: Text('Küche')),
                DropdownMenuItem(value: 'cellar', child: Text('Keller')),
                DropdownMenuItem(
                  value: 'other',
                  child: Text('Anderer Lagerort'),
                ),
              ],
              onChanged: (value) => type = value!,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialog, false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialog, true),
            child: const Text('Speichern'),
          ),
        ],
      ),
    );
    if (accepted == true && name.trim().isNotEmpty) {
      try {
        await ref.read(pantryRepositoryProvider).saveLocation({
          'name': name.trim(),
          'location_type': type,
        }, id: item?.id);
        await load();
      } on AppException catch (exception) {
        _message(exception.message);
      }
    }
  }

  Future<void> archive(PantryLocation item) async {
    try {
      await ref.read(pantryRepositoryProvider).archiveLocation(item.id);
      await load();
    } on AppException catch (exception) {
      _message(exception.message);
    }
  }

  Future<void> restore(PantryLocation item) async {
    try {
      await ref.read(pantryRepositoryProvider).restoreLocation(item.id);
      await load();
    } on AppException catch (exception) {
      _message(exception.message);
    }
  }

  void _message(String value) => ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(value)));
}

String _type(String value) =>
    const {
      'pantry': 'Vorratsschrank',
      'refrigerator': 'Kühlschrank',
      'freezer': 'Gefrierschrank',
      'kitchen': 'Küche',
      'cellar': 'Keller',
      'other': 'Anderer Lagerort',
    }[value] ??
    value;
