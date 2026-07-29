import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/date_formatters.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import 'pantry_add_screen.dart' show pantryOperationId;
import 'pantry_models.dart';
import 'pantry_screen.dart' show pantryDateStatus;

final class PantryDetailScreen extends ConsumerStatefulWidget {
  const PantryDetailScreen({required this.id, super.key});
  final String id;
  @override
  ConsumerState<PantryDetailScreen> createState() => _PantryDetailScreenState();
}

final class _PantryDetailScreenState extends ConsumerState<PantryDetailScreen> {
  PantryLot? lot;
  bool loading = true;
  String? error;
  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final value = await ref.read(pantryRepositoryProvider).detail(widget.id);
      if (mounted) setState(() => lot = value);
    } on AppException catch (exception) {
      if (mounted) setState(() => error = exception.message);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: lot?.foodName ?? 'Vorratsbestand',
    showNavigation: false,
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : error != null
        ? Center(child: Text(error!))
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _header(),
              _dates(),
              if (lot!.warnings.isNotEmpty)
                ...lot!.warnings.map(
                  (item) => Card(
                    child: ListTile(
                      leading: const Icon(Icons.warning_amber),
                      title: Text(item['message_de'].toString()),
                    ),
                  ),
                ),
              _actions(),
              _history(),
            ],
          ),
  );
  Widget _header() => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${lot!.quantity} ${lot!.unit}',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          Text('Verfügbar · ${lot!.locationName}'),
          Text('Ursprünglich: ${lot!.initialQuantity} ${lot!.initialUnit}'),
          if (lot!.estimated) const Text('Geschätzte Umrechnung'),
          if (lot!.foodArchived) const Text('Das Lebensmittel ist archiviert.'),
          if (lot!.depleted) const Text('Bestand aufgebraucht'),
          if (lot!.archived) const Text('Bestand archiviert'),
          if (lot!.note != null) Text('Notiz: ${lot!.note}'),
        ],
      ),
    ),
  );
  Widget _dates() => Card(
    child: Column(
      children: [
        ListTile(
          title: const Text('Datumsstatus'),
          subtitle: Text(pantryDateStatus(lot!.dateStatus)),
        ),
        _date('Kaufdatum', lot!.purchaseDate),
        _date('Öffnungsdatum', lot!.openedDate),
        _date('Mindesthaltbarkeitsdatum', lot!.bestBeforeDate),
        _date('Verbrauchsdatum', lot!.useByDate),
        const Padding(
          padding: EdgeInsets.all(12),
          child: Text(
            'Datumsangaben dienen der Bestandsübersicht. Die App bewertet nicht automatisch, ob ein Lebensmittel noch verzehrfähig ist.',
          ),
        ),
      ],
    ),
  );
  Widget _date(String label, DateTime? value) => ListTile(
    title: Text(label),
    trailing: Text(
      value == null ? 'Nicht angegeben' : DateFormatters.date(value),
    ),
  );
  Widget _actions() => Card(
    child: Padding(
      padding: const EdgeInsets.all(8),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          if (!lot!.archived) ...[
            OutlinedButton(
              onPressed: () => quantityDialog('add', 'Bestand erhöhen'),
              child: const Text('Bestand erhöhen'),
            ),
            OutlinedButton(
              onPressed: () => quantityDialog('consume', 'Verbraucht'),
              child: const Text('Verbraucht'),
            ),
            OutlinedButton(
              onPressed: () => quantityDialog('discard', 'Entsorgt'),
              child: const Text('Entsorgt'),
            ),
            OutlinedButton(
              onPressed: correctionDialog,
              child: const Text('Bestand korrigieren'),
            ),
            OutlinedButton(
              onPressed: transferDialog,
              child: const Text('Umlagern'),
            ),
            OutlinedButton(
              onPressed: archive,
              child: const Text('Archivieren'),
            ),
          ] else
            FilledButton.tonal(
              onPressed: restore,
              child: const Text('Wiederherstellen'),
            ),
        ],
      ),
    ),
  );
  Widget _history() => ExpansionTile(
    initiallyExpanded: true,
    title: const Text('Bewegungsverlauf'),
    children: lot!.movements.isEmpty
        ? [const ListTile(title: Text('Keine Bewegungen'))]
        : lot!.movements
              .map(
                (item) => ListTile(
                  leading: Icon(
                    item.delta.startsWith('-')
                        ? Icons.remove_circle_outline
                        : Icons.add_circle_outline,
                  ),
                  title: Text(_movement(item.type)),
                  subtitle: Text(
                    '${item.delta} ${item.unit} · ${item.before} → ${item.after} ${item.unit}\n${DateFormatters.dateTime(item.createdAt)}${item.note == null ? '' : ' · ${item.note}'}',
                  ),
                ),
              )
              .toList(),
  );
  Future<void> quantityDialog(String operation, String title) async {
    var amount = '1';
    var unit = lot!.unit;
    var note = '';
    final accepted = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: Text(title),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Aktuell: ${lot!.quantity} ${lot!.unit}'),
            TextFormField(
              initialValue: amount,
              onChanged: (value) => amount = value,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(labelText: 'Menge'),
            ),
            DropdownButtonFormField<String>(
              initialValue: unit,
              items: [
                DropdownMenuItem(value: lot!.unit, child: Text(lot!.unit)),
                DropdownMenuItem(
                  value: lot!.unit == 'g' ? 'kg' : 'l',
                  child: Text(lot!.unit == 'g' ? 'kg' : 'l'),
                ),
              ],
              onChanged: (value) => unit = value!,
            ),
            TextFormField(
              onChanged: (value) => note = value,
              decoration: const InputDecoration(labelText: 'Notiz (optional)'),
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
            child: const Text('Bestätigen'),
          ),
        ],
      ),
    );
    if (accepted != true) return;
    await _operation(operation, {
      'client_operation_id': pantryOperationId(),
      'quantity': GermanDecimal.parse(amount).toString(),
      'unit_code': unit,
      'note': note.trim().isEmpty ? null : note.trim(),
      'confirm_depleted_reuse': operation == 'add',
    });
  }

  Future<void> correctionDialog() async {
    var amount = lot!.quantity;
    var note = '';
    final accepted = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('Bestand korrigieren'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Erfasst: ${lot!.quantity} ${lot!.unit}'),
            TextFormField(
              initialValue: amount,
              onChanged: (value) => amount = value,
              decoration: const InputDecoration(
                labelText: 'Tatsächlicher neuer Gesamtbestand',
              ),
            ),
            TextFormField(
              onChanged: (value) => note = value,
              decoration: const InputDecoration(
                labelText: 'Notiz, z. B. Nachgezählt',
              ),
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
            child: const Text('Korrektur speichern'),
          ),
        ],
      ),
    );
    if (accepted == true) {
      await _operation('correct', {
        'client_operation_id': pantryOperationId(),
        'new_total_quantity': GermanDecimal.parse(amount).toString(),
        'unit_code': lot!.unit,
        'note': note,
      });
    }
  }

  Future<void> transferDialog() async {
    final locations = await ref.read(pantryRepositoryProvider).locations();
    if (!mounted) return;
    PantryLocation? target;
    var amount = lot!.quantity;
    final accepted = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('Bestand umlagern'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Aktuell: ${lot!.quantity} ${lot!.unit} in ${lot!.locationName}',
            ),
            DropdownButtonFormField<PantryLocation>(
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Ziellagerort'),
              items: locations
                  .where((item) => item.id != lot!.locationId && !item.archived)
                  .map(
                    (item) =>
                        DropdownMenuItem(value: item, child: Text(item.name)),
                  )
                  .toList(),
              onChanged: (value) => target = value,
            ),
            TextFormField(
              initialValue: amount,
              onChanged: (value) => amount = value,
              decoration: const InputDecoration(
                labelText: 'Umzulagernde Menge',
              ),
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
            child: const Text('Umlagern'),
          ),
        ],
      ),
    );
    if (accepted == true && target != null) {
      await _operation('transfer', {
        'client_operation_id': pantryOperationId(),
        'quantity': GermanDecimal.parse(amount).toString(),
        'unit_code': lot!.unit,
        'target_location_id': target!.id,
      });
    }
  }

  Future<void> _operation(String operation, Map<String, dynamic> data) async {
    try {
      await ref
          .read(pantryRepositoryProvider)
          .operation(lot!.id, operation, data);
      await load();
    } on AppException catch (exception) {
      _message(exception.message);
    }
  }

  Future<void> archive() async {
    final accepted = await _confirm(
      'Bestand archivieren?',
      'Der vorhandene Bestand wird aus den verfügbaren Mengen ausgeschlossen, aber nicht als verbraucht oder entsorgt markiert.',
    );
    if (!accepted) return;
    try {
      await ref.read(pantryRepositoryProvider).archive(lot!.id, confirm: true);
      await load();
    } on AppException catch (exception) {
      _message(exception.message);
    }
  }

  Future<void> restore() async {
    try {
      await ref.read(pantryRepositoryProvider).restore(lot!.id);
      await load();
    } on AppException catch (exception) {
      _message(exception.message);
    }
  }

  Future<bool> _confirm(String title, String content) async =>
      await showDialog<bool>(
        context: context,
        builder: (dialog) => AlertDialog(
          title: Text(title),
          content: Text(content),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialog, false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialog, true),
              child: const Text('Bestätigen'),
            ),
          ],
        ),
      ) ??
      false;
  void _message(String value) => ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(value)));
}

String _movement(String value) =>
    const {
      'initial_stock': 'Eingelagert',
      'add_stock': 'Bestand erhöht',
      'consume': 'Verbraucht',
      'discard': 'Entsorgt',
      'correction_increase': 'Nach oben korrigiert',
      'correction_decrease': 'Nach unten korrigiert',
      'transfer_out': 'Umlagerung',
      'transfer_in': 'Eingelagert durch Umlagerung',
      'restore': 'Wiederhergestellt',
    }[value] ??
    value;
