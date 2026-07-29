import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../app/providers.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/errors/app_exception.dart';
import '../../core/widgets/app_scaffold.dart';
import 'food_list_screen.dart';
import 'food_models.dart';

final class BarcodeScannerScreen extends ConsumerStatefulWidget {
  const BarcodeScannerScreen({super.key});

  @override
  ConsumerState<BarcodeScannerScreen> createState() =>
      _BarcodeScannerScreenState();
}

final class _BarcodeScannerScreenState
    extends ConsumerState<BarcodeScannerScreen> {
  final controller = MobileScannerController(
    formats: const [
      BarcodeFormat.ean8,
      BarcodeFormat.ean13,
      BarcodeFormat.upcA,
      BarcodeFormat.upcE,
      BarcodeFormat.itf14,
    ],
  );
  final manualCode = TextEditingController();
  BarcodePreview? preview;
  bool loading = false;
  bool importing = false;
  bool confirmIncomplete = false;
  String? error;

  @override
  void dispose() {
    controller.dispose();
    manualCode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: 'Barcode scannen',
    showNavigation: false,
    onBackPressed: () => context.go('/foods'),
    body: preview == null ? _scanner(context) : _preview(context),
  );

  Widget _scanner(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      const Text(
        'Scanne den EAN-Code auf der Verpackung. Der Barcode wird zur '
        'Produktsuche an Open Food Facts übertragen.',
      ),
      const SizedBox(height: 16),
      SizedBox(
        height: 300,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: MobileScanner(
            controller: controller,
            onDetect: (capture) {
              if (loading || capture.barcodes.isEmpty) return;
              final value = capture.barcodes.first.rawValue;
              if (value != null) _lookup(value);
            },
            errorBuilder: (context, scannerError) => Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  scannerError.errorCode ==
                          MobileScannerErrorCode.permissionDenied
                      ? 'Kamerazugriff wurde nicht erlaubt.'
                      : 'Die Kamera konnte nicht gestartet werden.',
                ),
              ),
            ),
          ),
        ),
      ),
      if (loading) ...[
        const SizedBox(height: 16),
        const Center(child: CircularProgressIndicator()),
        const Center(child: Text('Produkt wird gesucht …')),
      ],
      if (error != null) ...[
        const SizedBox(height: 16),
        Text(
          error!,
          style: TextStyle(color: Theme.of(context).colorScheme.error),
        ),
        TextButton(
          onPressed: () => context.go('/foods/new'),
          child: const Text('Lebensmittel manuell anlegen'),
        ),
      ],
      const SizedBox(height: 20),
      TextField(
        controller: manualCode,
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(
          labelText: 'Barcode manuell eingeben',
          hintText: 'EAN-8 oder EAN-13',
        ),
        onSubmitted: _lookup,
      ),
      const SizedBox(height: 8),
      OutlinedButton(
        onPressed: loading ? null : () => _lookup(manualCode.text),
        child: const Text('Barcode suchen'),
      ),
    ],
  );

  Widget _preview(BuildContext context) {
    final product = preview!;
    final knownCodes = product.nutrients
        .map((item) => item['nutrient_code']?.toString())
        .toSet();
    const requiredCodes = {'energy_kcal', 'fat', 'carbohydrate', 'protein'};
    final missing = requiredCodes.difference(knownCodes);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (product.imageUrl != null)
          Center(
            child: Image.network(
              product.imageUrl!,
              height: 160,
              errorBuilder: (_, _, _) => const SizedBox.shrink(),
            ),
          ),
        Text(product.name, style: Theme.of(context).textTheme.headlineSmall),
        if (product.brand != null) Text(product.brand!),
        if (product.quantityLabel != null) Text(product.quantityLabel!),
        Text('Barcode: ${product.barcode}'),
        Text('Nährwerte pro 100 ${product.referenceUnit}'),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Quelle: Open Food Facts'),
                for (final warning in product.warnings)
                  Text('Hinweis: $warning'),
              ],
            ),
          ),
        ),
        for (final nutrient in product.nutrients)
          ListTile(
            title: Text(_nutrientName(nutrient['nutrient_code'].toString())),
            trailing: Text(
              '${GermanDecimal.formatString(nutrient['amount'])} ${nutrient['unit']}',
            ),
          ),
        if (missing.isNotEmpty) ...[
          Text(
            'Nicht angegeben: ${missing.map(_nutrientName).join(', ')}',
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
          CheckboxListTile(
            value: confirmIncomplete,
            onChanged: (value) =>
                setState(() => confirmIncomplete = value ?? false),
            title: const Text('Unvollständige Angaben trotzdem importieren'),
          ),
        ],
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: importing || (missing.isNotEmpty && !confirmIncomplete)
              ? null
              : () => _import(),
          icon: const Icon(Icons.download_done),
          label: Text(importing ? 'Wird gespeichert …' : 'Produkt übernehmen'),
        ),
        OutlinedButton.icon(
          onPressed: importing || (missing.isNotEmpty && !confirmIncomplete)
              ? null
              : () => _import(asPreparedDish: true),
          icon: const Icon(Icons.restaurant_menu),
          label: const Text('Als Fertiggericht übernehmen'),
        ),
        TextButton(
          onPressed: _scanAgain,
          child: const Text('Anderen Barcode scannen'),
        ),
      ],
    );
  }

  Future<void> _lookup(String code) async {
    final normalized = code.trim();
    if (normalized.isEmpty || loading) return;
    setState(() {
      loading = true;
      error = null;
    });
    await controller.stop();
    try {
      final result = await ref
          .read(foodRepositoryProvider)
          .lookupBarcode(normalized);
      if (!mounted) return;
      setState(() => preview = result);
    } on AppException catch (exception) {
      if (!mounted) return;
      setState(() => error = exception.message);
      await controller.start();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _import({
    bool confirmDuplicate = false,
    bool asPreparedDish = false,
  }) async {
    if (importing || preview == null) return;
    setState(() => importing = true);
    try {
      final food = await ref
          .read(foodRepositoryProvider)
          .importBarcode(
            preview!,
            confirmIncomplete: confirmIncomplete,
            confirmDuplicate: confirmDuplicate,
          );
      ref.invalidate(foodListProvider);
      if (mounted) {
        context.go(
          asPreparedDish
              ? '/recipes/new?foodId=${food.id}'
              : '/foods/${food.id}',
        );
      }
    } on AppException catch (exception) {
      if (!mounted) return;
      if (exception.code == 'FOOD_DUPLICATE_WARNING' && !confirmDuplicate) {
        final proceed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: const Text('Mögliche Dublette'),
            content: Text('${exception.message} Trotzdem speichern?'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('Abbrechen'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: const Text('Trotzdem speichern'),
              ),
            ],
          ),
        );
        if (proceed == true) {
          setState(() => importing = false);
          await _import(confirmDuplicate: true, asPreparedDish: asPreparedDish);
          return;
        }
      } else {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(exception.message)));
      }
    } finally {
      if (mounted) setState(() => importing = false);
    }
  }

  Future<void> _scanAgain() async {
    setState(() {
      preview = null;
      error = null;
      confirmIncomplete = false;
    });
    await controller.start();
  }
}

String _nutrientName(String code) => switch (code) {
  'energy_kcal' => 'Energie',
  'fat' => 'Fett',
  'saturated_fat' => 'Gesättigte Fettsäuren',
  'carbohydrate' => 'Kohlenhydrate',
  'sugars' => 'Zucker',
  'fiber' => 'Ballaststoffe',
  'protein' => 'Eiweiß',
  'salt' => 'Salz',
  'sodium' => 'Natrium',
  _ => code,
};
