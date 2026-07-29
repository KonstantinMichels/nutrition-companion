import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/providers.dart';
import '../../core/errors/app_exception.dart';
import '../../core/formatting/german_decimal.dart';
import '../../core/widgets/app_scaffold.dart';
import '../foods/food_models.dart';
import 'recipe_detail_screen.dart';
import 'recipe_list_screen.dart';

final class RecipeFormScreen extends ConsumerStatefulWidget {
  const RecipeFormScreen({this.id, this.initialFoodId, super.key});
  final String? id, initialFoodId;
  @override
  ConsumerState<RecipeFormScreen> createState() => _RecipeFormScreenState();
}

final class _IngredientDraft {
  _IngredientDraft({
    this.food,
    String quantity = '',
    this.measure,
    this.customUnit,
    String equivalent = '',
    this.equivalentUnit,
  }) : quantity = TextEditingController(text: quantity),
       equivalent = TextEditingController(text: equivalent);
  FoodItem? food;
  final TextEditingController quantity;
  final TextEditingController equivalent;
  FoodMeasure? measure;
  String? customUnit;
  String? equivalentUnit;
  void dispose() {
    quantity.dispose();
    equivalent.dispose();
  }
}

final class _RecipeFormScreenState extends ConsumerState<RecipeFormScreen> {
  final formKey = GlobalKey<FormState>();
  final name = TextEditingController();
  final description = TextEditingController();
  final servings = TextEditingController(text: '2');
  final finishedWeight = TextEditingController();
  final ingredients = <_IngredientDraft>[];
  final steps = <TextEditingController>[];
  List<FoodItem> foods = [];
  final tags = <String>{};
  bool loading = true, saving = false;
  static const tagLabels = {
    'breakfast': 'Frühstück',
    'lunch': 'Mittagessen',
    'dinner': 'Abendessen',
    'snack': 'Snack',
    'vegetarian': 'Vegetarisch',
    'vegan': 'Vegan',
    'high_protein': 'Proteinreich',
    'quick': 'Schnell',
    'meal_prep': 'Meal Prep',
    'budget_friendly': 'Preiswert',
    'prepared_food': 'Fertiggericht',
  };
  static const customUnits = {
    'piece': 'Stück',
    'serving': 'Portion',
    'slice': 'Scheibe',
    'teaspoon': 'Teelöffel',
    'tablespoon': 'Esslöffel',
  };
  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  Future<void> load() async {
    foods = await ref.read(foodRepositoryProvider).list();
    if (widget.id != null) {
      final recipe = await ref
          .read(recipeRepositoryProvider)
          .detail(widget.id!);
      name.text = recipe.name;
      description.text = recipe.description ?? '';
      servings.text = recipe.servings;
      tags.addAll(
        tagLabels.entries
            .where((e) => recipe.tags.contains(e.value))
            .map((e) => e.key),
      );
      for (final item in recipe.ingredients) {
        final food = foods.where((f) => f.id == item.foodId).firstOrNull;
        if (food != null) {
          ingredients.add(
            _IngredientDraft(
              food: food,
              quantity: item.quantity,
              measure: food.measures
                  .where((m) => m.unitCode == item.unitCode)
                  .firstOrNull,
              customUnit: item.unitType == 'custom_measure'
                  ? item.unitCode
                  : null,
              equivalent: item.equivalentQuantity ?? '',
              equivalentUnit: item.equivalentUnit,
            ),
          );
        }
      }
      for (final step in recipe.steps) {
        steps.add(TextEditingController(text: step.instruction));
      }
    } else if (widget.initialFoodId != null) {
      final food = foods.where((f) => f.id == widget.initialFoodId).firstOrNull;
      if (food != null) {
        ingredients.add(_IngredientDraft(food: food, quantity: '100'));
        name.text = food.name;
        tags.add('prepared_food');
      }
    }
    if (mounted) {
      setState(() {
        loading = false;
        if (ingredients.isEmpty) ingredients.add(_IngredientDraft());
      });
    }
  }

  @override
  void dispose() {
    name.dispose();
    description.dispose();
    servings.dispose();
    finishedWeight.dispose();
    for (final i in ingredients) {
      i.dispose();
    }
    for (final s in steps) {
      s.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AppScaffold(
    title: widget.id == null ? 'Rezept anlegen' : 'Rezept bearbeiten',
    showNavigation: false,
    onBackPressed: () => _discard(context),
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : Form(
            key: formKey,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  'Grundangaben',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                TextFormField(
                  controller: name,
                  decoration: const InputDecoration(labelText: 'Name *'),
                  validator: (v) => v == null || v.trim().isEmpty
                      ? 'Name ist erforderlich.'
                      : null,
                ),
                TextFormField(
                  controller: description,
                  decoration: const InputDecoration(
                    labelText: 'Beschreibung (optional)',
                  ),
                  maxLines: 2,
                ),
                TextFormField(
                  controller: servings,
                  decoration: const InputDecoration(labelText: 'Portionen *'),
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  validator: _positive,
                ),
                TextFormField(
                  controller: finishedWeight,
                  decoration: const InputDecoration(
                    labelText: 'Fertiggewicht in g (optional)',
                  ),
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  validator: (v) =>
                      v == null || v.isEmpty ? null : _positive(v),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 6,
                  children: tagLabels.entries
                      .map(
                        (e) => FilterChip(
                          label: Text(e.value),
                          selected: tags.contains(e.key),
                          onSelected: (on) => setState(
                            () => on ? tags.add(e.key) : tags.remove(e.key),
                          ),
                        ),
                      )
                      .toList(),
                ),
                const Divider(),
                Text('Zutaten', style: Theme.of(context).textTheme.titleLarge),
                for (var index = 0; index < ingredients.length; index++)
                  _ingredientCard(index),
                OutlinedButton.icon(
                  onPressed: () =>
                      setState(() => ingredients.add(_IngredientDraft())),
                  icon: const Icon(Icons.add),
                  label: const Text('Zutat hinzufügen'),
                ),
                const Divider(),
                Text(
                  'Zubereitung',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                for (var index = 0; index < steps.length; index++)
                  Card(
                    child: ListTile(
                      title: TextField(
                        controller: steps[index],
                        decoration: InputDecoration(
                          labelText: 'Schritt ${index + 1}',
                        ),
                      ),
                      leading: Column(
                        children: [
                          IconButton(
                            onPressed: index == 0
                                ? null
                                : () => _moveStep(index, -1),
                            icon: const Icon(Icons.arrow_upward),
                            tooltip: 'Nach oben',
                          ),
                        ],
                      ),
                      trailing: IconButton(
                        onPressed: () =>
                            setState(() => steps.removeAt(index).dispose()),
                        icon: const Icon(Icons.delete_outline),
                      ),
                    ),
                  ),
                OutlinedButton.icon(
                  onPressed: () =>
                      setState(() => steps.add(TextEditingController())),
                  icon: const Icon(Icons.add),
                  label: const Text('Schritt hinzufügen'),
                ),
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: saving ? null : save,
                  child: Text(
                    saving ? 'Wird gespeichert …' : 'Rezept speichern',
                  ),
                ),
              ],
            ),
          ),
  );
  Widget _ingredientCard(int index) {
    final item = ingredients[index];
    final choices = item.food == null ? <FoodMeasure>[] : item.food!.measures;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            DropdownButtonFormField<FoodItem>(
              initialValue: item.food,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Lebensmittel *'),
              items: foods
                  .map(
                    (f) => DropdownMenuItem(
                      value: f,
                      child: Text(
                        '${f.name}${f.brand == null ? '' : ' · ${f.brand}'}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (food) => setState(() {
                item.food = food;
                item.measure = null;
                item.customUnit = null;
                item.equivalent.clear();
                item.equivalentUnit = food?.referenceUnit;
              }),
              validator: (v) => v == null ? 'Lebensmittel auswählen.' : null,
            ),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: item.quantity,
                    decoration: const InputDecoration(labelText: 'Menge *'),
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    validator: _positive,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: item.measure != null
                        ? 'saved:${item.measure!.id}'
                        : item.customUnit != null
                        ? 'custom:${item.customUnit}'
                        : 'base',
                    decoration: const InputDecoration(labelText: 'Einheit'),
                    items: [
                      DropdownMenuItem(
                        value: 'base',
                        child: Text(item.food?.referenceUnit ?? 'g'),
                      ),
                      ...choices.map(
                        (m) => DropdownMenuItem(
                          value: 'saved:${m.id}',
                          child: Text(m.name),
                        ),
                      ),
                      ...customUnits.entries.map(
                        (entry) => DropdownMenuItem(
                          value: 'custom:${entry.key}',
                          child: Text(entry.value),
                        ),
                      ),
                    ],
                    onChanged: (value) => setState(() {
                      item.measure = value?.startsWith('saved:') == true
                          ? choices
                                .where((m) => 'saved:${m.id}' == value)
                                .firstOrNull
                          : null;
                      item.customUnit = value?.startsWith('custom:') == true
                          ? value!.substring(7)
                          : null;
                      item.equivalentUnit ??= item.food?.referenceUnit;
                    }),
                  ),
                ),
              ],
            ),
            if (item.customUnit != null)
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: item.equivalent,
                      decoration: InputDecoration(
                        labelText:
                            '1 ${customUnits[item.customUnit]} entspricht',
                      ),
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      validator: _positive,
                    ),
                  ),
                  const SizedBox(width: 12),
                  DropdownButton<String>(
                    value:
                        item.equivalentUnit ?? item.food?.referenceUnit ?? 'g',
                    items: const [
                      DropdownMenuItem(value: 'g', child: Text('g')),
                      DropdownMenuItem(value: 'ml', child: Text('ml')),
                    ],
                    onChanged: (value) =>
                        setState(() => item.equivalentUnit = value),
                  ),
                ],
              ),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                IconButton(
                  onPressed: index == 0
                      ? null
                      : () => _moveIngredient(index, -1),
                  icon: const Icon(Icons.arrow_upward),
                  tooltip: 'Nach oben',
                ),
                IconButton(
                  onPressed: index == ingredients.length - 1
                      ? null
                      : () => _moveIngredient(index, 1),
                  icon: const Icon(Icons.arrow_downward),
                  tooltip: 'Nach unten',
                ),
                IconButton(
                  onPressed: ingredients.length == 1
                      ? null
                      : () => setState(
                          () => ingredients.removeAt(index).dispose(),
                        ),
                  icon: const Icon(Icons.delete_outline),
                  tooltip: 'Entfernen',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String? _positive(String? value) {
    final parsed = GermanDecimal.tryParse(value);
    return parsed == null || parsed <= 0
        ? 'Bitte einen Wert größer als null eingeben.'
        : null;
  }

  void _moveIngredient(int index, int delta) => setState(
    () => ingredients.insert(index + delta, ingredients.removeAt(index)),
  );
  void _moveStep(int index, int delta) =>
      setState(() => steps.insert(index + delta, steps.removeAt(index)));
  Future<void> save() async {
    if (!formKey.currentState!.validate()) return;
    if (ingredients.any((i) => i.food == null)) return;
    setState(() => saving = true);
    final payload = {
      'name': name.text,
      'description': description.text.trim().isEmpty
          ? null
          : description.text.trim(),
      'servings': GermanDecimal.parse(servings.text).toString(),
      'finished_weight_g': finishedWeight.text.trim().isEmpty
          ? null
          : GermanDecimal.parse(finishedWeight.text).toString(),
      'tags': tags.toList(),
      'ingredients': ingredients
          .map(
            (i) => {
              'food_id': i.food!.id,
              'quantity': GermanDecimal.parse(i.quantity.text).toString(),
              'unit_type': i.measure != null
                  ? 'measure'
                  : i.customUnit != null
                  ? 'custom_measure'
                  : 'base',
              'unit_code':
                  i.measure?.unitCode ?? i.customUnit ?? i.food!.referenceUnit,
              'food_measure_id': i.measure?.id,
              'equivalent_quantity': i.customUnit == null
                  ? null
                  : GermanDecimal.parse(i.equivalent.text).toString(),
              'equivalent_unit': i.customUnit == null
                  ? null
                  : i.equivalentUnit ?? i.food!.referenceUnit,
            },
          )
          .toList(),
      'steps': steps
          .where((s) => s.text.trim().isNotEmpty)
          .map((s) => {'instruction': s.text.trim()})
          .toList(),
    };
    try {
      final recipe = await ref
          .read(recipeRepositoryProvider)
          .save(payload, id: widget.id);
      ref.invalidate(recipeListProvider);
      ref.invalidate(recipeDetailProvider(recipe.id));
      if (mounted) context.go('/recipes/${recipe.id}');
    } on AppException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> _discard(BuildContext context) async {
    final leave = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('Änderungen verwerfen?'),
        content: const Text('Nicht gespeicherte Eingaben gehen verloren.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialog, false),
            child: const Text('Weiter bearbeiten'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialog, true),
            child: const Text('Verwerfen'),
          ),
        ],
      ),
    );
    if (leave == true && context.mounted) {
      context.go(widget.id == null ? '/recipes' : '/recipes/${widget.id}');
    }
  }
}
