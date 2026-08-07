# Aufnahmebasierte Energie-Kalibrierung

Die Methode `intake_informed` ergänzt die bestehende zielbasierte Kalibrierung. Sie nutzt nur
finalisierte und als vollständig bestätigte Verzehrtage sowie repräsentative Gewichtswerte aus
demselben lokalen Datumsfenster. Fehlende Tage werden nicht ergänzt und geplante Mahlzeiten,
Einkaufslisten oder Vorratsbewegungen sind keine Aufnahme-Evidenz.

Das versionierte Regelwerk `intake-informed/1.0` verlangt 21–90 Tage (bevorzugt 28–56),
mindestens 14 nutzbare Aufnahmetage mit 70 Prozent Kalenderabdeckung, drei Wochen,
Randabdeckung und höchstens vier aufeinanderfolgende fehlende Tage. Ab 28 Tagen werden zudem
Wochen- und Wochenendtage geprüft. Die Gewichtsevidenz verwendet dieselbe robuste Trendlogik
wie die dynamische Kalibrierung.

Die zentrale Aufnahme ist das arithmetische Mittel der eingeschlossenen Tage. Ein
95-Prozent-t-Intervall wird um eine ausdrückliche Aufzeichnungsunsicherheit (hoch: 5 Prozent,
moderat: 10 Prozent; kleinere Routineänderungen zusätzlich 3 Prozentpunkte) erweitert. Aus
`Energiebilanz = Aufnahme − Verbrauch` folgt die vorsichtige TDEE-Schätzung. Sämtliche
Kombinationen der Aufnahme- und Bilanzgrenzen fließen in das Ergebnis ein. Schneidet das
Anpassungsintervall null oder liegt die zentrale Änderung innerhalb 100 kcal/Tag, wird keine
Änderung angeboten. Andernfalls begrenzen 200 kcal/Tag und 8 Prozent des Ausgangs-TDEE die
Anpassung; moderate Aufzeichnungsqualität und kleinere Routineänderungen halbieren den Cap
jeweils.

Vorschauen werden nicht gespeichert. Beim Übernehmen werden Kalibrierung, verwendete und
ausgeschlossene Evidenzwerte sowie Regel- und Berechnungssnapshots unveränderlich gespeichert.
Die Ausgangseinschätzung bleibt unverändert; eine neue Assessment-Revision bewahrt die bisherige
Zielanpassung. Eine eigene akzeptierte Anpassung darf nur kleiner und gleichgerichtet sein.

Die Werte sind Schätzungen aus selbst berichteten Angaben. Sie messen weder tatsächliche
Aufnahme, Absorption noch Energieverbrauch und sind nicht diagnostisch. Es gibt keine
automatische Anwendung und keine Vorratsänderung.

Nächster fachlicher Branch: `feat/pantry-consumption-reconciliation`.

Der Vorratsabgleich verändert weder historische Aufnahme-Energie noch die Eignung oder
Ergebnisse dieser Kalibrierung. Er ist ausschließlich eine bestätigte Bestandsbuchung.
