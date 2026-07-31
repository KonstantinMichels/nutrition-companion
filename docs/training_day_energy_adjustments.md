# Trainingstag-Energieanpassungen

Trainingseinheiten und Tageszielanpassungen sind eine optionale, ausdrücklich bestätigte
Planungshilfe. Sie messen weder Energieverbrauch noch Leistungsbedarf. Eine geplante Einheit wird
nicht als durchgeführt behauptet und verändert keine unveränderliche Ernährungs-Einschätzung.

## Einheiten und Belastung

Einheiten speichern Datum, lokale Uhrzeit, Dauer, Sportart, Einheitstyp, Intensität und die
Angabe, ob die Belastung bereits im Aktivitätsniveau der Einschätzung enthalten ist. `unknown` ist
der sichere Standard. Das versionierte Regelwerk `training-day-adjustments/1.0` klassifiziert eine
Planungslast aus diesen Angaben und gibt eine Bandbreite statt einer exakten Verbrauchsbehauptung
aus.

## Strategien

- `none` ändert kein Ziel.
- `weekly_redistribution` verschiebt Energie innerhalb der Woche auf Trainingstage; die
  Wochensumme bleibt dezimalgenau erhalten.
- `bounded_additive` erlaubt nur bei ausdrücklich zusätzlicher Belastung eine begrenzte additive
  Energie- und Kohlenhydratanpassung.
- `custom_manual` speichert eine klar als manuell gekennzeichnete Anpassung.

Vorschauen persistieren nichts. Beim Anwenden werden Einschätzung, Einheiten, Regelversion,
Ausgangsziel und effektives Ziel als unveränderlicher Batch-/Tagessnapshot gespeichert. Ein
Vorschau-Token schützt vor veralteten Daten, eine Client-Operations-ID vor doppelter Anwendung.
Überlappende aktive Anpassungen benötigen eine ausdrückliche Ersetzungsbestätigung.

## Planung

Ein Snapshot kann ausdrücklich mit einem Tagesplan desselben Datums verknüpft werden. Der
Tagesplan zeigt Basisziel, Trainingsdifferenz und effektives Ziel getrennt. Eine Trennung löscht
weder Plan noch Snapshot. Wochenübersicht und automatische Entwürfe kennzeichnen berücksichtigte
Anpassungen und unvollständige Wochenumverteilungen. Bestehende Pläne werden nie stillschweigend
neu geschrieben.

## Datenschutz und Grenzen

Einheiten, Präferenzen, Batches und Tagessnapshots sind im Export enthalten und separat löschbar;
Planverknüpfungen werden dabei gelöst. Es werden keine externen Dienste, Wearables oder
Gesundheitsplattformen angesprochen. Die Funktion ist keine medizinische Beratung und keine
Messung von Kalorienverbrauch, Regeneration, Glykogen oder Trainingsleistung.

Der nächste erwartete Branch ist `feat/consumption-tracking-core`.

Consumption Tracking kann den bereits mit einem Tagesplan verknüpften unveränderlichen
Tagessnapshot beim Initialisieren übernehmen. Spätere Änderungen an Training oder Plan ersetzen
diese historische Zielbasis nicht stillschweigend.
