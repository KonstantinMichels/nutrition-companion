# Vorratsabgleich für Verzehrdaten

`Pantry Consumption Reconciliation` verbindet einen Verzehreintrag ausschließlich nach einer
ausdrücklichen Nutzerentscheidung mit konkreten Vorratschargen. Ein erfasster Verzehr ist kein
Nachweis, dass ein Lebensmittel aus dem Haushaltsvorrat stammte; eine Bestandsbewegung beweist
keine ernährungsphysiologisch exakte Menge.

Unterstützte Herkunftsentscheidungen sind vollständig oder teilweise aus dem Vorrat, nicht aus
dem Vorrat, bereits anderweitig berücksichtigt und ungeklärt. Für Rezepte kommt die ausdrückliche
Einordnung als für diesen Eintrag zubereitet oder als bereits berücksichtigter Rest hinzu. Neue
Rezept-Verzehreinträge speichern ihre Zutaten, Einheiten, Normalisierung, Optionalität und
Rezeptversion transaktional. Der theoretische Zutatenbedarf wird proportional zur erfassten
Portionszahl berechnet. Spätere Rezeptänderungen verändern den Snapshot nicht. Alteinträge ohne
Snapshot werden nicht still rekonstruiert und bleiben prüfbedürftig.

Direkte Lebensmittel verwenden die historische normalisierte Verzehrmenge. Optionale Zutaten
werden standardmäßig nicht vorgeschlagen. Manuelle ungeklärte Einträge können nur über eine
ausdrückliche Food-ID und kanonische Menge abgeglichen werden. Dadurch entstehen weder neue
Foods noch Nährwertsnapshots.

Die Vorschau lädt aktive, nicht archivierte, nicht aufgebrauchte Chargen aktiver Lagerorte exakt
nach Food-ID. Die Reihenfolge ist deterministisch: gültig, heute, bald ablaufend, ohne Datum,
MHD überschritten und zuletzt Verbrauchsdatum überschritten; weitere stabile Felder lösen
Gleichstände auf. Ein überschrittenes Verbrauchsdatum wird nie still vorgeschlagen und erfordert
eine Bestätigung. Datumsangaben sind keine Aussage über Lebensmittelsicherheit.

Vorschläge können auf mehrere Chargen aufgeteilt, reduziert oder teilweise ungedeckt gelassen
werden. Erst Apply erzeugt in einer Transaktion unveränderliche Batches, Requirements,
Allocations und `consume`-Bewegungen über den Pantry-Core-Service. Vorgangs-IDs verhindern
Doppelbuchungen; ein Token erkennt geänderte Verzehr- oder Vorratsdaten. Entscheidungen ohne
Vorratsquelle erzeugen Requirements, aber keine Bewegung.

Rücknahmen löschen ursprüngliche Bewegungen nicht. Sie erstellen ausdrückliche positive
Gegenbewegungen und unterstützen Teilmengen. Überrücknahmen sind gesperrt. Archivierte
Originalchargen müssen zuerst bewusst wiederhergestellt oder durch eine kompatible Zielcharge
ersetzt werden. Beim Löschen verknüpfter Verzehreinträge oder Tage ist zwischen Gegenbewegung,
Beibehalten der Bewegungen und Abbruch zu entscheiden; Audit-Snapshots bleiben erhalten.

Der Abgleich verändert niemals Verzehrmengen, Nährwertsnapshots, Finalisierungsstatus,
Kalibrierungsbereitschaft, Tagespläne oder Einkaufslisten. Vorschauen und Tokens werden nicht
persistiert. Export und vollständige Profillöschung umfassen Batches, Requirements, Allocations,
Rezeptzutaten-Snapshots und Rücknahmen.

Bekannte Grenzen: Herkunft und Chargenauswahl sind manuell bestätigt; Rezeptmengen sind
theoretisch; Verluste, Batch Cooking, Reste, Substitutionen und automatische Korrekturen werden
nicht modelliert. Gleiche Namen ersetzen keine Food-ID. Nicht verfügbarer Bestand bleibt offen.
Barcode- und Belegscan sind nicht Bestandteil dieses Features.

Nächster erwarteter Branch: `feat/barcode-product-import`.
