import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/core/formatting/german_decimal.dart';

void main() {
  group('GermanDecimal', () {
    test('parses comma and dot decimals', () {
      expect(GermanDecimal.tryParse('82,5'), 82.5);
      expect(GermanDecimal.tryParse('82.5'), 82.5);
      expect(GermanDecimal.tryParse(' 1,40 '), 1.4);
    });

    test('rejects malformed and non-finite inputs', () {
      for (final value in [
        '82,5.1',
        '1,2,3',
        'NaN',
        'Infinity',
        '1e3',
        '',
        '--2',
      ]) {
        expect(GermanDecimal.tryParse(value), isNull, reason: value);
      }
    });

    test('formats using German decimal separator', () {
      expect(GermanDecimal.format(82.5), contains(','));
    });

    test('removes API scale zeroes without losing meaningful decimals', () {
      expect(GermanDecimal.formatString('360.000000000'), '360');
      expect(GermanDecimal.formatString('2.500000'), '2,5');
      expect(GermanDecimal.formatString('0.010200'), '0,0102');
      expect(GermanDecimal.formatString('already text'), 'already text');
    });
  });
}
