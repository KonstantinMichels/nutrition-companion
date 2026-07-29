import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/providers.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../../core/widgets/states.dart';
import 'shopping_list_models.dart';

class ShoppingListDetailScreen extends ConsumerStatefulWidget {
  const ShoppingListDetailScreen({required this.id, super.key});
  final String id;
  @override
  ConsumerState<ShoppingListDetailScreen> createState() => _State();
}

class _State extends ConsumerState<ShoppingListDetailScreen> {
  Future<ShoppingListDetail>? future;
  final Set<String> changingItems = {};
  @override
  void initState() {
    super.initState();
    future = _load();
  }

  Future<ShoppingListDetail> _load() =>
      ref.read(shoppingListRepositoryProvider).detail(widget.id);
  void reload() {
    setState(() {
      future = _load();
    });
  }

  @override
  Widget build(BuildContext context) => FutureBuilder(
    future: future,
    builder: (context, s) {
      final data = s.data;
      return AppScaffold(
        title: data?.summary.name ?? 'Einkaufsliste',
        showNavigation: false,
        actions: [
          if (data != null)
            PopupMenuButton<String>(
              onSelected: (v) => _action(v, data),
              itemBuilder: (_) => [
                if (data.summary.sourceType != 'manual')
                  const PopupMenuItem(
                    value: 'refresh',
                    child: Text('Aus Plan aktualisieren'),
                  ),
                if (!data.summary.archived && data.items.isNotEmpty)
                  const PopupMenuItem(
                    value: 'pantry-handoff',
                    child: Text('In Vorrat übernehmen'),
                  ),
                if (!data.summary.archived && data.summary.status == 'open')
                  const PopupMenuItem(
                    value: 'pantry-aware',
                    child: Text('Mit Bedarf und Vorrat abgleichen'),
                  ),
                PopupMenuItem(
                  value: data.summary.status == 'completed'
                      ? 'reopen'
                      : 'complete',
                  child: Text(
                    data.summary.status == 'completed'
                        ? 'Wieder öffnen'
                        : 'Abschließen',
                  ),
                ),
                PopupMenuItem(
                  value: data.summary.archived ? 'restore' : 'archive',
                  child: Text(
                    data.summary.archived ? 'Wiederherstellen' : 'Archivieren',
                  ),
                ),
              ],
            ),
        ],
        floatingActionButton: data == null
            ? null
            : FloatingActionButton.extended(
                onPressed: _add,
                icon: const Icon(Icons.add),
                label: const Text('Eintrag'),
              ),
        body: s.connectionState != ConnectionState.done
            ? const Center(child: CircularProgressIndicator())
            : s.hasError
            ? ErrorState(message: s.error.toString(), onRetry: reload)
            : _body(data!),
      );
    },
  );
  Widget _body(ShoppingListDetail d) {
    final groups = <String, List<ShoppingItem>>{};
    for (final i in d.items) {
      groups.putIfAbsent(i.checked ? 'done' : i.category, () => []).add(i);
    }
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        LinearProgressIndicator(
          value: d.summary.itemCount == 0
              ? 0
              : d.summary.checkedCount / d.summary.itemCount,
        ),
        const SizedBox(height: 8),
        Text('${d.summary.checkedCount} von ${d.summary.itemCount} erledigt'),
        if (d.pantryConsidered)
          const ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(Icons.inventory_2_outlined),
            title: Text('Vorrat berücksichtigt'),
            subtitle: Text(
              'Der Vorrat wurde nur berechnet, nicht reserviert oder verändert.',
            ),
          ),
        ...groups.entries.expand(
          (g) => [
            Padding(
              padding: const EdgeInsets.only(top: 16, bottom: 6),
              child: Text(
                g.key == 'done' ? 'Erledigt' : _category(g.key),
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            ...g.value.map(_row),
          ],
        ),
      ],
    );
  }

  Widget _row(ShoppingItem i) => Card(
    child: ListTile(
      leading: Checkbox(
        value: i.checked,
        onChanged: changingItems.contains(i.id) ? null : (_) => _toggle(i),
      ),
      title: Text(i.name),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(_amount(i)),
          if (i.origin == 'generated')
            Text(
              'Benötigt ${_quantity(i.required, i.unit)} · '
              'Vorrat ${_quantity(i.available, i.unit)} · '
              'Vorgeschlagen ${_quantity(i.suggested, i.unit)}',
            ),
          if (i.sourceStatus == 'no_longer_required')
            const Text('Nicht mehr aus dem aktuellen Plan benötigt'),
          if (i.pantryTransferred > 0)
            Text(
              'In Vorrat übernommen: ${_quantity(i.pantryTransferred, i.unit)} · '
              '${i.pantryHandoffState == 'completed' ? 'Abgeschlossen' : 'Teilweise übernommen'}',
            ),
        ],
      ),
      trailing: IconButton(
        icon: const Icon(Icons.delete_outline),
        onPressed: () => _remove(i),
      ),
    ),
  );
  String _amount(ShoppingItem i) => i.quantity == null
      ? 'Ohne Mengenangabe'
      : '${_n(i.quantity)} ${i.unit ?? ''}';
  String _n(num? n) => n == null ? '—' : GermanDecimal.format(n);
  String _quantity(num? value, String? unit) {
    if (value == null) return '—';
    return '${_n(value)}${unit == null || unit.isEmpty ? '' : ' $unit'}';
  }

  String _category(String c) =>
      const {
        'produce': 'Obst & Gemüse',
        'dairy': 'Milchprodukte',
        'meat': 'Fleisch & Fisch',
        'bakery': 'Backwaren',
        'frozen': 'Tiefkühl',
        'beverages': 'Getränke',
        'household': 'Haushalt',
        'other': 'Sonstiges',
      }[c] ??
      c;
  Future<void> _toggle(ShoppingItem i) async {
    setState(() => changingItems.add(i.id));
    try {
      await ref
          .read(shoppingListRepositoryProvider)
          .setChecked(widget.id, i.id, !i.checked);
      if (mounted) reload();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Abhaken fehlgeschlagen: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => changingItems.remove(i.id));
    }
  }

  Future<void> _remove(ShoppingItem i) async {
    await ref.read(shoppingListRepositoryProvider).remove(widget.id, i.id);
    reload();
  }

  Future<void> _add() async {
    final name = TextEditingController(),
        qty = TextEditingController(),
        unit = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Freitext hinzufügen'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: 'Name'),
            ),
            TextField(
              controller: qty,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(labelText: 'Menge (optional)'),
            ),
            TextField(
              controller: unit,
              decoration: const InputDecoration(
                labelText: 'Einheit (optional)',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Hinzufügen'),
          ),
        ],
      ),
    );
    if (ok != true || name.text.trim().isEmpty) return;
    await ref.read(shoppingListRepositoryProvider).addText(widget.id, {
      'name': name.text.trim(),
      'quantity': GermanDecimal.tryParse(qty.text),
      'unit_code': unit.text.trim().isEmpty ? null : unit.text.trim(),
      'category_code': 'other',
    });
    reload();
  }

  Future<void> _action(String action, ShoppingListDetail d) async {
    final repo = ref.read(shoppingListRepositoryProvider);
    if (action == 'pantry-handoff') {
      await context.push('/shopping-lists/${widget.id}/pantry-handoff');
    } else if (action == 'pantry-aware') {
      await context.push(
        '/pantry-aware-shopping?sourceType=shopping_list_reconciliation&targetListId=${widget.id}',
      );
      reload();
    } else if (action == 'refresh') {
      final p = await repo.refreshPreview(widget.id);
      if (!mounted) return;
      final apply = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Änderungen übernehmen?'),
          content: Text(
            '${(p['new_items'] as List).length} neu, ${(p['removed_requirements'] as List).length} nicht mehr benötigt, ${(p['changed_required_quantities'] as List).length} geändert.\nDer Vorrat wird nicht verändert.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Aktualisieren'),
            ),
          ],
        ),
      );
      if (apply == true) {
        await repo.refresh(widget.id, (p['preview_version'] as num).toInt());
      }
    } else {
      await repo.state(widget.id, action);
    }
    reload();
  }
}
