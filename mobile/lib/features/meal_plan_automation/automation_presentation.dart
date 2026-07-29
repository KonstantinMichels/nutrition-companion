const automationEngines = <String, String>{
  'greedy': 'Schneller regelbasierter Entwurf',
  'optimizer_strict': 'Gemeinsame Optimierung',
  'optimizer_explainable_relaxation': 'Optimierung mit erklärbarer Lockerung',
};

String automationEngineDescription(String engine) => switch (engine) {
  'greedy' =>
    'Wählt Mahlzeiten nacheinander aus. Schnell, aber nicht global optimiert.',
  'optimizer_strict' =>
    'Bewertet alle ausgewählten Mahlzeiten gemeinsam und hält alle strikten Regeln ein.',
  _ => 'Sucht zuerst strikt und zeigt notwendige Lockerungen vollständig an.',
};

String optimizerStatusLabel(String? status) => switch (status) {
  'optimal' => 'Optimale Lösung für das gewählte Modell gefunden',
  'feasible' => 'Beste gefundene Lösung innerhalb des Zeitlimits',
  'infeasible' => 'Keine zulässige Kombination gefunden',
  'time_limit_without_solution' => 'Im Zeitlimit wurde keine Lösung gefunden',
  _ => 'Optimizer-Ergebnis: ${status ?? 'unbekannt'}',
};

String automationAssessmentBasis(Object? value) {
  if (value is! Map) return 'Keine Einschätzung verfügbar';
  final calculatedAt = value['calculated_at']?.toString();
  if (calculatedAt != null && calculatedAt.isNotEmpty) {
    return 'Einschätzung $calculatedAt';
  }
  final id = value['id']?.toString();
  if (id != null && id.isNotEmpty) return 'Einschätzung $id';
  return 'Keine Einschätzung verfügbar';
}
