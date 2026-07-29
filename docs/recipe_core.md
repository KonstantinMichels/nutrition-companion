# Recipe Core

Recipe Core verwaltet profilgebundene Rezepte aus vorhandenen Food-Core-Lebensmitteln. Ein Rezept enthält Portionenzahl, geordnete Zutaten und Zubereitungsschritte, optionale Zeiten, Tags und ein optionales tatsächliches Endgewicht. Zutaten kopieren keine Nährwerte, sondern referenzieren ein eigenes Lebensmittel und optional eines seiner Haushaltsmaße.

## Berechnung und Datenqualität

Mengen in g/ml, vorhandenen Food-Maßen oder direkt an der Zutat definierten Haushaltsmaßen werden mit derselben Normalisierung wie Food Core in die Bezugsmenge des Lebensmittels überführt. Für Stück, Portion, Scheibe, Teelöffel und Esslöffel wird eine konkrete Entsprechung in g/ml gespeichert, beispielsweise `1 Stück = 120 g`; pauschale Standardgewichte werden nicht erfunden. Die Aggregation läuft bei jedem Abruf mit `Decimal`; Zwischenwerte werden nicht gerundet. Fehlende Nährwerte bleiben unbekannt und werden niemals als Null addiert. Eine gespeicherte Null bleibt dagegen ein bekannter Wert.

Jeder Nährstoff weist bekannte und relevante Zutaten, den Abdeckungsgrad, fehlende Zutaten und geschätzte Umrechnungen aus. Summen und Werte pro Portion stehen für die jeweils bekannte Abdeckung zur Verfügung. Werte pro 100 g gibt es nur mit explizitem Endgewicht oder vollständig ermittelbarem theoretischem Gewicht. Qualitätsstufe und Warnungen beschreiben Datenvollständigkeit und Umrechnung, nicht gesundheitliche Eignung oder wissenschaftliche Verifizierung.

## Lebenszyklus

Listen und Details sind dem aktuellen Profil zugeordnet. Rezepte können gesucht, nach dem versionierten Tag-Katalog gefiltert, geändert, dupliziert, skaliert, archiviert, wiederhergestellt und nach separater Warnung dauerhaft gelöscht werden. Die Rezeptlöschung entfernt Zutaten und Schritte, lässt die referenzierten Foods aber bestehen. Archivierung ist reversibel und keine Datenschutzlöschung. Ein archiviertes Lebensmittel bleibt für bestehende Rezeptberechnungen lesbar, kann aber keiner neuen oder geänderten Zutatenliste hinzugefügt werden. Eine Food-Dauerlöschung wird durch bestehende Rezeptreferenzen verhindert.

## Barcode-Übergabe

Ein über Open Food Facts bestätigtes Barcode-Produkt wird weiterhin zuerst als Food gespeichert. Die App bietet zwei bewusste Ziele: normales Lebensmittel oder „Fertiggericht“. Beim Fertiggericht entsteht ein vorbefüllter Rezeptentwurf, der das gespeicherte Food referenziert und vor dem Speichern bearbeitet werden kann. Dieselbe Aktion „Als Gericht übernehmen“ steht auch später im Detail jedes aktiven Lebensmittels zur Verfügung. Recipe Core selbst ruft keinen externen Importdienst auf.

## Datenschutz und Grenzen

Export und vollständige Profillöschung umfassen Rezepte, Zutaten und Schritte. Eine vollständige Löschung entfernt den Recipe-Graph per Datenbank-Cascade. Recipe Core vergleicht noch nicht mit persönlichen Zielwerten, importiert keine externen Rezepte, analysiert keine Allergien und verwendet keine KI. Nächster fachlicher Schritt ist `feat/recipe-target-comparison`; dafür muss eine konkrete unveränderliche Assessment-Version referenziert werden.
