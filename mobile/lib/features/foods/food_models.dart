final class FoodNutrient {
  const FoodNutrient({
    required this.code,
    required this.name,
    required this.amount,
    required this.unit,
    required this.derived,
  });
  factory FoodNutrient.fromJson(Map<String, dynamic> json) => FoodNutrient(
    code: json['nutrient_code'].toString(),
    name: json['display_name_de'].toString(),
    amount: json['amount'].toString(),
    unit: json['unit'].toString(),
    derived: json['is_derived'] == true,
  );
  final String code, name, amount, unit;
  final bool derived;
}

final class FoodItem {
  const FoodItem({
    required this.id,
    required this.name,
    required this.brand,
    required this.category,
    required this.referenceUnit,
    required this.sourceType,
    required this.sourceName,
    required this.archived,
    required this.quality,
    required this.nutrients,
    this.description,
  });
  factory FoodItem.fromJson(Map<String, dynamic> json) => FoodItem(
    id: json['id'].toString(),
    name: json['name'].toString(),
    brand: json['brand']?.toString(),
    description: json['description']?.toString(),
    category: json['category_code']?.toString(),
    referenceUnit: json['reference_unit'].toString(),
    sourceType: json['source_type']?.toString() ?? 'user_entered',
    sourceName: json['source_name']?.toString(),
    archived: json['is_archived'] == true,
    quality: (json['quality'] as Map)['quality_level'].toString(),
    nutrients: (json['nutrients'] as List)
        .whereType<Map>()
        .map((e) => FoodNutrient.fromJson(Map<String, dynamic>.from(e)))
        .toList(),
  );
  final String id, name, referenceUnit, sourceType, quality;
  final String? brand, description, category, sourceName;
  final bool archived;
  final List<FoodNutrient> nutrients;
}

final class BarcodePreview {
  const BarcodePreview({
    required this.barcode,
    required this.name,
    required this.brand,
    required this.quantityLabel,
    required this.referenceUnit,
    required this.nutrients,
    required this.imageUrl,
    required this.sourceName,
    required this.sourceVersion,
    required this.warnings,
  });

  factory BarcodePreview.fromJson(Map<String, dynamic> json) => BarcodePreview(
    barcode: json['barcode'].toString(),
    name: json['name'].toString(),
    brand: json['brand']?.toString(),
    quantityLabel: json['quantity_label']?.toString(),
    referenceUnit: json['reference_unit'].toString(),
    nutrients: (json['nutrients'] as List)
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList(growable: false),
    imageUrl: json['image_url']?.toString(),
    sourceName: json['source_name'].toString(),
    sourceVersion: json['source_version']?.toString(),
    warnings: (json['warnings'] as List)
        .map((item) => item.toString())
        .toList(),
  );

  final String barcode, name, referenceUnit, sourceName;
  final String? brand, quantityLabel, imageUrl, sourceVersion;
  final List<Map<String, dynamic>> nutrients;
  final List<String> warnings;

  Map<String, dynamic> toJson() => {
    'barcode': barcode,
    'name': name,
    'brand': brand,
    'quantity_label': quantityLabel,
    'reference_unit': referenceUnit,
    'nutrients': nutrients,
    'image_url': imageUrl,
    'source_name': sourceName,
    'source_version': sourceVersion,
    'warnings': warnings,
  };
}
