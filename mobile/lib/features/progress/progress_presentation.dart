const poundsToKilograms = 0.45359237;

double convertWeightToKilograms(double value, String unit) =>
    unit == 'lb' ? value * poundsToKilograms : value;

String progressTrendDirection(Object? value) => switch (value) {
  'decreasing' => 'sinkend',
  'increasing' => 'steigend',
  'stable' => 'weitgehend stabil',
  _ => 'nicht verfügbar',
};

const progressCalculationExplanation =
    'Pro Kalendertag wird der zeitlich späteste Messwert verwendet. '
    'Der gleitende Durchschnitt interpoliert keine fehlenden Tage.';
