final class ShoppingListSummary {
  const ShoppingListSummary({
    required this.id,
    required this.name,
    required this.status,
    required this.sourceType,
    required this.itemCount,
    required this.checkedCount,
    required this.archived,
  });
  final String id, name, status, sourceType;
  final int itemCount, checkedCount;
  final bool archived;
  factory ShoppingListSummary.fromJson(Map<String, dynamic> json) =>
      ShoppingListSummary(
        id: json['id'].toString(),
        name: json['name'].toString(),
        status: json['status'].toString(),
        sourceType: json['source_type'].toString(),
        itemCount: _number(json['active_item_count'])?.toInt() ?? 0,
        checkedCount: _number(json['checked_item_count'])?.toInt() ?? 0,
        archived: json['is_archived'] == true,
      );
}

final class ShoppingItem {
  const ShoppingItem({
    required this.id,
    required this.name,
    required this.category,
    required this.checked,
    required this.origin,
    this.quantity,
    this.unit,
    this.required,
    this.available,
    this.suggested,
    this.sourceStatus = 'current',
    this.pantryHandoffState = 'not_started',
    this.pantryTransferred = 0,
  });
  final String id, name, category, origin, sourceStatus, pantryHandoffState;
  final bool checked;
  final num? quantity, required, available, suggested;
  final num pantryTransferred;
  final String? unit;
  factory ShoppingItem.fromJson(Map<String, dynamic> json) => ShoppingItem(
    id: json['id'].toString(),
    name: json['name']?.toString() ?? 'Unbenannt',
    category: json['category_code']?.toString() ?? 'other',
    checked: json['is_checked'] == true,
    origin: json['origin_type']?.toString() ?? 'manual',
    quantity:
        _number(json['purchase_quantity']) ?? _number(json['manual_quantity']),
    unit:
        json['purchase_unit_code']?.toString() ??
        json['manual_unit_label']?.toString(),
    required: _number(json['required_quantity']),
    available: _number(json['pantry_available_quantity']),
    suggested: _number(json['suggested_purchase_quantity']),
    sourceStatus: json['source_status']?.toString() ?? 'current',
    pantryHandoffState:
        json['pantry_handoff_state']?.toString() ?? 'not_started',
    pantryTransferred: _number(json['pantry_transferred_quantity']) ?? 0,
  );
}

final class ShoppingListDetail {
  const ShoppingListDetail({
    required this.summary,
    required this.items,
    required this.version,
    required this.pantryConsidered,
  });
  final ShoppingListSummary summary;
  final List<ShoppingItem> items;
  final int version;
  final bool pantryConsidered;
  factory ShoppingListDetail.fromJson(Map<String, dynamic> json) =>
      ShoppingListDetail(
        summary: ShoppingListSummary.fromJson(json),
        items: (json['items'] as List? ?? const [])
            .whereType<Map>()
            .map((e) => ShoppingItem.fromJson(Map<String, dynamic>.from(e)))
            .toList(),
        version: _number(json['version'])?.toInt() ?? 1,
        pantryConsidered: json['pantry_considered'] == true,
      );
}

num? _number(Object? value) {
  if (value == null) return null;
  if (value is num) return value;
  return num.tryParse(value.toString().trim().replaceAll(',', '.'));
}
