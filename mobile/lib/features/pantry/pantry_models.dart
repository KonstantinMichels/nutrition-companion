import '../../core/formatting/german_decimal.dart';

final class PantryLocation {
  const PantryLocation({
    required this.id,
    required this.name,
    required this.type,
    required this.position,
    required this.archived,
    required this.lotCount,
  });
  factory PantryLocation.fromJson(Map<String, dynamic> json) => PantryLocation(
    id: json['id'].toString(),
    name: json['name'].toString(),
    type: json['location_type'].toString(),
    position: json['position'] as int,
    archived: json['is_archived'] == true,
    lotCount: json['active_lot_count'] as int? ?? 0,
  );
  final String id, name, type;
  final int position, lotCount;
  final bool archived;
}

final class PantryLot {
  const PantryLot({
    required this.id,
    required this.foodId,
    required this.foodName,
    required this.brand,
    required this.foodArchived,
    required this.locationId,
    required this.locationName,
    required this.quantity,
    required this.unit,
    required this.initialQuantity,
    required this.initialUnit,
    required this.estimated,
    required this.purchaseDate,
    required this.openedDate,
    required this.bestBeforeDate,
    required this.useByDate,
    required this.dateStatus,
    required this.note,
    required this.depleted,
    required this.archived,
    required this.movements,
    required this.warnings,
  });
  factory PantryLot.fromJson(Map<String, dynamic> json) {
    final food = Map<String, dynamic>.from(json['food'] as Map);
    final location = Map<String, dynamic>.from(json['location'] as Map);
    return PantryLot(
      id: json['id'].toString(),
      foodId: food['id'].toString(),
      foodName: food['name'].toString(),
      brand: food['brand']?.toString(),
      foodArchived: food['is_archived'] == true,
      locationId: location['id'].toString(),
      locationName: location['name'].toString(),
      quantity: GermanDecimal.formatString(json['current_quantity']),
      unit: json['normalized_unit'].toString(),
      initialQuantity: GermanDecimal.formatString(
        json['initial_entered_quantity'],
      ),
      initialUnit: json['initial_entered_unit_code'].toString(),
      estimated: json['initial_conversion_estimated'] == true,
      purchaseDate: _date(json['purchase_date']),
      openedDate: _date(json['opened_date']),
      bestBeforeDate: _date(json['best_before_date']),
      useByDate: _date(json['use_by_date']),
      dateStatus: json['date_status'].toString(),
      note: json['note']?.toString(),
      depleted: json['is_depleted'] == true,
      archived: json['is_archived'] == true,
      movements: (json['movements'] as List? ?? const [])
          .whereType<Map>()
          .map(
            (item) => PantryMovement.fromJson(Map<String, dynamic>.from(item)),
          )
          .toList(),
      warnings: (json['warnings'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList(),
    );
  }
  final String id,
      foodId,
      foodName,
      locationId,
      locationName,
      quantity,
      unit,
      initialQuantity,
      initialUnit,
      dateStatus;
  final String? brand, note;
  final DateTime? purchaseDate, openedDate, bestBeforeDate, useByDate;
  final bool foodArchived, estimated, depleted, archived;
  final List<PantryMovement> movements;
  final List<Map<String, dynamic>> warnings;
}

final class PantryMovement {
  const PantryMovement({
    required this.type,
    required this.delta,
    required this.unit,
    required this.before,
    required this.after,
    required this.note,
    required this.createdAt,
    required this.estimated,
    required this.sourceType,
  });
  factory PantryMovement.fromJson(Map<String, dynamic> json) => PantryMovement(
    type: json['movement_type'].toString(),
    delta: GermanDecimal.formatString(json['quantity_delta']),
    unit: json['normalized_unit'].toString(),
    before: GermanDecimal.formatString(json['balance_before']),
    after: GermanDecimal.formatString(json['balance_after']),
    note: json['note']?.toString(),
    createdAt: DateTime.parse(json['created_at'].toString()),
    estimated: json['conversion_estimated'] == true,
    sourceType: json['source_type']?.toString() ?? 'manual',
  );
  final String type, delta, unit, before, after, sourceType;
  final String? note;
  final DateTime createdAt;
  final bool estimated;
}

final class PantryAvailability {
  const PantryAvailability({
    required this.foodId,
    required this.name,
    required this.brand,
    required this.quantity,
    required this.unit,
    required this.lotCount,
    required this.locations,
    required this.archivedFood,
  });
  factory PantryAvailability.fromJson(Map<String, dynamic> json) =>
      PantryAvailability(
        foodId: json['food_id'].toString(),
        name: json['food_name'].toString(),
        brand: json['brand']?.toString(),
        quantity: GermanDecimal.formatString(json['available_quantity']),
        unit: json['unit'].toString(),
        lotCount: json['active_lot_count'] as int,
        locations: (json['locations'] as List)
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList(),
        archivedFood: json['archived_food'] == true,
      );
  final String foodId, name, quantity, unit;
  final String? brand;
  final int lotCount;
  final List<Map<String, dynamic>> locations;
  final bool archivedFood;
}

DateTime? _date(Object? value) =>
    value == null ? null : DateTime.tryParse(value.toString());
