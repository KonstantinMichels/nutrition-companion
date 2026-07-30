import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nutrition_companion/features/progress/progress_presentation.dart';
import 'package:nutrition_companion/features/progress/progress_screen.dart';

void main() {
  test('pound conversion uses the documented exact factor', () {
    expect(convertWeightToKilograms(1, 'lb'), 0.45359237);
    expect(convertWeightToKilograms(80, 'kg'), 80);
  });

  test('trend wording is neutral and calculation is transparent', () {
    expect(progressTrendDirection('decreasing'), 'sinkend');
    expect(progressTrendDirection('stable'), 'weitgehend stabil');
    expect(progressCalculationExplanation, contains('keine fehlenden Tage'));
    final wording = [
      progressTrendDirection('decreasing'),
      progressTrendDirection('increasing'),
      progressCalculationExplanation,
    ].join(' ').toLowerCase();
    expect(wording, isNot(contains('versagt')));
    expect(wording, isNot(contains('gesundes gewicht')));
    expect(wording, isNot(contains('fettverlust bestätigt')));
  });

  testWidgets('chart renders raw points and trend in light and dark themes', (
    tester,
  ) async {
    final points = <Map<String, dynamic>>[
      {'representative_value_kg': '80', 'rolling_average_kg': null},
      {'representative_value_kg': '79', 'rolling_average_kg': '79.5'},
    ];
    for (final brightness in [Brightness.light, Brightness.dark]) {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData(brightness: brightness),
          home: Builder(
            builder: (context) => CustomPaint(
              size: const Size(300, 180),
              painter: ProgressChartPainter(
                points,
                Theme.of(context).colorScheme,
              ),
            ),
          ),
        ),
      );
      expect(find.byType(CustomPaint), findsWidgets);
    }
  });
}
