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
}
