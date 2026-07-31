# Dynamische Energie-Kalibrierung

Die Funktion erzeugt ausschließlich einen transparenten Vorschlag. Sie misst weder die
tatsächliche Energieaufnahme noch den tatsächlichen Energieverbrauch und verändert keine
Zielwerte automatisch. Erst eine ausdrückliche Bestätigung erzeugt eine neue, unveränderliche
Einschätzungsrevision; die Quell-Einschätzung und vorhandene Tages- oder Wochenpläne bleiben
unverändert.

## Evidenz und Regeln

Das Regelwerk `dynamic-energy-calibration/1.0` verlangt ein Fenster von mindestens 21 und
höchstens 90 Tagen, mindestens acht repräsentative Messtage, drei Kalenderwochen sowie je zwei
Messtage im ersten und letzten Drittel. 28 bis 42 Tage werden bevorzugt. Mehrere Messungen eines
Tages werden nach derselben dokumentierten Repräsentantenregel wie im Fortschrittsmodul
verdichtet.

Der lineare OLS-Trend enthält Standardfehler und approximative 95-%-Grenzen. Die Umrechnung nutzt
eine versionierte Bandbreite von 6.500, 7.700 und 9.500 kcal/kg. Wenn der resultierende
Anpassungsbereich null schneidet oder die zentrale Abweichung unter 75 kcal/Tag liegt, wird keine
Änderung vorgeschlagen. Vorschläge sind auf 200 kcal/Tag und 10 % des angenommenen Energie-Ziels
begrenzt. Bei nur moderater Einhaltung oder kleineren Kontextänderungen wird die Kappe halbiert.
Niedrige/unbekannte Einhaltung sowie deutliche/unbekannte Kontextänderungen blockieren den
Vorschlag.

## API und Lebenszyklus

`GET /api/v1/energy-calibration/eligibility` und `/eligible-windows` erklären Eignung und
Blocker. `POST /preview` ist transient und liefert einen an Quelle, Evidenz und Regeln gebundenen
Token. `POST /apply` prüft alles erneut, ist über `client_operation_id` idempotent und speichert
Evidenz-, Vorschlags- und Regel-Snapshots. Veraltete Vorschauen werden mit HTTP 409 abgelehnt.
`POST /decline`, `/history` und `/{id}` bilden Entscheidung und Historie ab.

Kalibrierungsdaten sind im Datenschutzexport enthalten und werden mit Einschätzungsverlauf oder
Profil gelöscht. Der Verarbeitungszweck ist im Privacy-Registry dokumentiert.

## Nächster Branch

`feat/training-day-energy-adjustments` ist implementiert. Trainingstag-Anpassungen bleiben
separate Planungssnapshots und ändern weder Kalibrierungsvorschläge noch historische
Einschätzungen. Der nächste erwartete Branch ist `feat/consumption-tracking-core`.

Consumption Tracking stellt lediglich eine konservative spätere Nutzbarkeitsmetrik bereit. Die
dynamische Kalibrierung liest in diesem Branch keine Verzehrdaten und ändert ihre Regeln nicht.
