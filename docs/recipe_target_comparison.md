# Recipe Target Comparison

Der persönliche Rezeptvergleich vergleicht eine frei wählbare Anzahl normaler Rezeptportionen mit den unveränderlichen Zielwerten einer gespeicherten Nutrition Assessment. Standardmäßig wird die neueste unterstützte Einschätzung mit mindestens einem vergleichbaren Ziel verwendet; ältere eigene Einschätzungen können ausdrücklich ausgewählt werden. Nicht unterstützte oder zielwertlose Einschätzungen bleiben sichtbar, sind aber nicht auswählbar.

## Berechnungsbasis

Die ausgewählte Einschätzung wird weder verändert noch neu berechnet. Das Rezept nutzt dagegen seine aktuellen Food-Core-Werte. Änderungen an Rezept oder Lebensmitteln können daher bei derselben historischen Einschätzung zu einem anderen aktuellen Vergleich führen. Vergleichsergebnisse, Prozentwerte, Erklärungen, Portionsauswahl und Auswahlzustand werden nicht gespeichert oder lokal gecacht.

Für `portion_count > 0` bis höchstens 100 gilt ohne Zwischenrundung:

```text
ausgewählte Menge = bekannte Nährstoffmenge pro Rezeptportion × portion_count
```

Die zentrale versionierte Zuordnung verwendet `energy.goal_target`, `protein.grams_per_day`, die Grammbereiche für Fett und Kohlenhydrate, den Höchstwert gesättigter Fettsäuren, `fiber.target` sowie verfügbare `micronutrients.*`. Flutter leitet keine Zielsemantik aus Texten ab.

## Zielarten

- `minimum`: bekannter Beitrag zum Mindestwert; ein niedriger Anteil einer einzelnen Mahlzeit ist keine Warnung.
- `maximum`: Nutzung eines Tageshöchstwertes, niemals als zu erfüllendes Ziel bezeichnet. Bei unvollständigen Daten bleibt die Einhaltung unbestimmt, außer der bekannte Anteil überschreitet den Wert bereits.
- `range`: Prozentbeitrag zur unteren und oberen Grenze. Unterhalb eines Tagesbereichs ist eine einzelne Mahlzeit nicht negativ. Bei unvollständigen Daten bleibt die Lage unbestimmt, außer der bekannte Anteil liegt bereits oberhalb der Obergrenze.
- `reference`: neutraler bekannter Beitrag zu einem Referenzwert, ohne Bedarfs- oder Mangelbehauptung.

Zielwerte von null, negative/fehlende Ziele, nicht kompatible Einheiten und vollständig fehlende Rezeptwerte werden als nicht vergleichbar ausgegeben, niemals als `0 %`.

## Einheiten und Datenabdeckung

Die dezimalgenaue zentrale Umrechnung unterstützt g, mg und µg, kcal und kJ sowie echte ml/l-Umrechnungen. IU oder nährstoffspezifische Stoffumrechnungen werden nicht erfunden. Salz/Natrium bleibt Aufgabe der vorhandenen Food-Core-Auflösung.

Recipe Core liefert bekannte/relevante Zutaten, fehlende Zutaten und Abdeckungsquote. Ein unvollständiger Minimums- oder Referenzbeitrag ist eine bekannte Untergrenze. Datenabdeckung bezeichnet Vollständigkeit der gespeicherten Zutatenwerte, keine statistische Sicherheit.

## Darstellung und Grenzen

Die Rezeptdetailansicht lädt den Abschnitt „Persönlicher Vergleich“ erst beim Öffnen. Sie bietet Assessment-Auswahl, Schnellmengen 0,5/1/1,5/2, manuelle deutsche Dezimaleingabe, gruppierte Nährstoffe, Datenqualität und „Wie wird verglichen?“. Archivierte Rezepte bleiben schreibgeschützt vergleichbar.

Es gibt keinen Health Score, keine Ampel, Rezeptbewertung, Rangfolge, Empfehlung, Diagnose oder medizinische Interpretation. Der Vergleich bildet nur eine Rezeptmenge ab, nicht den gesamten Tag. Es existieren keine historischen Rezept-Nährwertsnapshots, Mahlzeitenkombinationen oder Restzielberechnungen. Nächster Schritt ist `feat/daily-meal-planning`.
