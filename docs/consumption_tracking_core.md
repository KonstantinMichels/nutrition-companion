# Consumption Tracking Core

## Zweck und Abgrenzung

Die Verzehrerfassung speichert ausschließlich, was eine Person ausdrücklich als tatsächlich
konsumiert meldet. Ein Tagesplan, ein abgehakter Einkauf oder eine Vorratsbewegung ist kein
Verzehrnachweis. Das Modul verändert weder Tagespläne noch Vorrat oder Einkaufslisten und erzeugt
keine automatische Ernährungs- oder Adhärenzbewertung. Alle Angaben sind selbst berichtet;
Nährstoffaufnahme beziehungsweise -absorption wird nicht gemessen.

## Tage, Mahlzeiten und Einträge

Pro Profil und lokalem Datum besteht höchstens ein `ConsumptionDay`. Er kann ohne Tagesplan
angelegt oder ausdrücklich aus einem Tagesplan initialisiert werden. Dabei entstehen nur
Mahlzeitenhüllen und offene Planeinträge, noch keine tatsächlichen Verzehreinträge.
Zukünftige Tage sind nicht zulässig, weil sie noch keinen tatsächlichen Verzehr beschreiben können.

`ConsumptionMeal` erlaubt mehrere Mahlzeiten desselben Typs, optionale Namen und lokale Uhrzeiten.
`ConsumptionEntry` unterstützt Food-Core-Lebensmittel in g, kg, ml, l oder einem kompatiblen
Haushaltsmaß, Recipe-Core-Rezepte mit dezimaler Portionszahl und manuelle ungeklärte Einträge ohne
erfundene Nährwerte.

Food- und Recipe-Einträge speichern Anzeigename, Quell-ID/-version, Normalisierung,
Archivzustand, relevante FoodMeasure-/Portionsmetadaten, Berechnungsregel und relationale
Nährwertsnapshots. `known`, `true_zero`, `unknown` und
`not_applicable` bleiben unterscheidbar. Änderungen oder Archivierung einer Quelle schreiben
historische Snapshots nicht um. Bei einer ausdrücklichen Mengen-/Quelländerung werden Snapshots
transaktional ersetzt. Nicht mehr verfügbare Quellen bleiben über Snapshots lesbar.

## Planabgleich

Ein noch nicht entschiedener Planeintrag ist `pending`. Eine ausdrückliche Entscheidung kann
`consumed_as_planned`, `consumed_modified`, `partially_consumed`, `skipped` oder `replaced` sein.
„Wie geplant“ erzeugt immer einen tatsächlichen historischen Eintrag. „Übersprungen“ erzeugt
keinen. Ersatz unterstützt mehrere tatsächliche Food-/Recipe-Einträge. Teilweise ist eine
ausdrückliche Aussage und wird nicht allein aus einer kleineren Zahl abgeleitet.

„Gesamte Mahlzeit wie geplant übernehmen“ zeigt die betroffenen Einträge und benötigt eine
Bestätigung. Alle Ergebnisse bleiben vom Tagesplan getrennt. Nachträgliche Planänderungen setzen
Entscheidungen nicht zurück; neue Planeinträge erscheinen offen, geänderte/entfernte Quellen
erzeugen einen strukturierten Hinweis.

## Summen, Ziele und Woche

Mahlzeit- und Tagessummen werden ausschließlich aus gespeicherten Nährwertsnapshots aggregiert.
Unbekannt wird nie als null behandelt; bekannte Summen sind bei Lücken Untergrenzen. Der
Zielvergleich verwendet die beim Anlegen gespeicherte unveränderliche Einschätzungsbasis und eine
gegebenenfalls verknüpfte Trainingstag-Anpassung. Minimum, Maximum, Bereich, Referenz und
Informationswert behalten die konservative Tagesplansemantik. Geplant-versus-erfasst ist
beschreibend und kein Compliance-Score; Ersatz wird nicht fälschlich mengenidentisch verglichen.
Die Zielbeschreibungen selbst werden im Tag gespeichert. Deshalb bleibt der historische Vergleich
auch nach einer zulässigen Löschung der ursprünglichen Einschätzung nachvollziehbar.

Die Wochenübersicht umfasst Montag bis Sonntag und weist erfasste, finalisierte, subjektiv
vollständige, teilweise/unklare und fehlende Tage getrennt aus. Fehlende Tage gelten nicht als
Nullaufnahme und werden nicht standardmäßig in einen Sieben-Tage-Durchschnitt eingerechnet.
Der filterbare Verlauf zeigt Status, Vollständigkeit, bekannte Energie, Ziel-/Planbezug und
ungeklärte Einträge, ohne vollständige Snapshot-Payloads in der Listenantwort auszugeben.

## Abschluss und Löschung

Ein Tag bleibt offen, bis die Person ihn ausdrücklich als „nach bestem Wissen vollständig“, „nur
teilweise“ oder „Vollständigkeit unklar“ abschließt. Vollständig ist nicht vorausgewählt. Hinweise
auf offene Planeinträge, ungeklärte Einträge und Datenlücken dürfen nach Bestätigung einen ehrlichen
Teil- oder Unsicherheitstag nicht blockieren. Finalisierte Tage sind schreibgeschützt und können
wieder geöffnet werden.

Einträge und Tage lassen sich dauerhaft löschen. Kaskaden entfernen Mahlzeiten, Snapshots und
Entscheidungen innerhalb des Moduls, niemals jedoch Tagespläne, Foods, Recipes, Assessments,
Trainingstag-Anpassungen, Vorrat oder Einkaufslisten.

## Datenschutz und Grenzen

Alle Routen erzwingen Profilbesitz. Der Export enthält Tage, Mahlzeiten, Zeiten, Mengen, Quell- und
Nährwertsnapshots, Entscheidungen, Notizen und Zeitstempel. Der separate Datenschutzlöschpfad
entfernt alle Verzehrdaten. Es gibt keine Analytics, Werbung, externe API oder Drittlandübermittlung.

Nicht implementiert sind Foto-, Barcode-, Beleg-, Restaurant-, Wearable- oder Health-Connect-
Erfassung, automatische Vorratsbuchung, automatische Planänderung, Absorptionsmessung,
Adhärenzscore und automatische Zielkalibrierung. Unfertige Formulare werden derzeit nicht lokal
persistiert. Eine konservative Readiness-Metrik löst keine Kalibrierung aus und behauptet keine
objektive Vollständigkeit.

Nächster erwarteter Branch: `feat/intake-informed-energy-calibration`.
