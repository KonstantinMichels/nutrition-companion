import 'package:intl/intl.dart';

abstract final class GermanDecimal {
  static final _inputPattern = RegExp(r'^[+-]?(?:\d+(?:[,.]\d+)?|[,.]\d+)$');

  static double? tryParse(String? input) {
    if (input == null) return null;
    final value = input.trim();
    if (value.isEmpty || !_inputPattern.hasMatch(value)) return null;
    final parsed = double.tryParse(value.replaceAll(',', '.'));
    return parsed != null && parsed.isFinite ? parsed : null;
  }

  static double parse(String input) {
    final parsed = tryParse(input);
    if (parsed == null) {
      throw const FormatException('Keine gültige Dezimalzahl.');
    }
    return parsed;
  }

  static String format(num value, {int decimals = 1}) =>
      NumberFormat.decimalPatternDigits(
        locale: 'de_DE',
        decimalDigits: decimals,
      ).format(value);

  /// Formats an API decimal exactly, without converting it through `double`.
  /// Trailing fractional zeroes are removed and German decimal commas are used.
  static String formatString(Object? input) {
    if (input == null) return '';
    final raw = input.toString().trim().replaceAll(',', '.');
    final match = RegExp(r'^([+-]?\d+)(?:\.(\d+))?$').firstMatch(raw);
    if (match == null) return input.toString();
    final integer = match.group(1)!;
    final fraction = (match.group(2) ?? '').replaceFirst(RegExp(r'0+$'), '');
    return fraction.isEmpty ? integer : '$integer,$fraction';
  }
}
