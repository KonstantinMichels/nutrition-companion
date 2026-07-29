# Shopping List Core

Einkaufslisten können manuell oder als unveränderliche Momentaufnahme eines Tagesplans beziehungsweise einer ISO-Kalenderwoche erstellt werden. Rezeptzutaten werden mit `geplante Portionen / Rezeptportionen` skaliert, direkte Lebensmittel normalisiert und anschließend ausschließlich über die Food-ID aggregiert.

Der optionale Vorratsvergleich berechnet `Vorschlag = max(Bedarf - verfügbar, 0)`. Er reserviert und verändert keinen Bestand. Mehrere Listen dürfen daher denselben Vorrat berücksichtigen. Die Werte „benötigt“, „im Vorrat“, „vorgeschlagen“ und „geplant zu kaufen“ bleiben getrennt.

## Aktualisierung

Planänderungen verändern eine bestehende Liste nicht automatisch. `refresh-preview` liefert zunächst eine Differenz und eine Listenversion. Erst `refresh` mit dieser Version berechnet serverseitig neu. IDs, Sortierung, Kategorie, Notiz, Abhakstatus und manuell überschriebene Kaufmengen bleiben erhalten. Nicht mehr benötigte, unberührte Einträge werden beim bestätigten Refresh entfernt; abgehakte oder überschriebene Einträge bleiben mit dem Hinweis `no_longer_required` erhalten. Manuelle Einträge werden nie durch Refresh entfernt.

## Kategorien und Grenzen

Die MVP-Kategorien sind Obst & Gemüse, Milchprodukte, Fleisch & Fisch, Backwaren, Tiefkühl, Getränke, Haushalt und Sonstiges. Freitext ist ausdrücklich erlaubt und wird nicht mit Food Core zusammengeführt.

Abschließen bedeutet nur, dass die Liste organisatorisch erledigt ist. Es bestätigt weder Kauf noch Verzehr und erzeugt keine Pantry-Bewegung. Preise, Händler, Reservierungen, automatische Pantry-Verbuchung und wiederkehrende Listen sind nicht Teil dieses Features.

Eine Pantry-Übernahme ist ausschließlich über den separaten, bestätigten Purchase-to-Pantry-Ablauf möglich. Dabei bleiben Haken, Abschlussstatus und geplante Einkaufsmenge unverändert; die tatsächlich übertragene Menge und der Übergabestatus werden zusätzlich angezeigt.

## API

Die API liegt unter `/api/v1/shopping-lists` und unterstützt Übersicht, Detail, manuelle Erstellung, `generation-preview`, `generate`, Item-CRUD, Sortierung, Abhaken, zweistufigen Refresh, Abschluss/Wiederöffnung sowie Archivierung/Wiederherstellung. Alle Zugriffe sind auf das aktive Profil beschränkt. Shopping-Listen sind im Datenschutzexport enthalten und werden bei vollständiger Profillöschung vor ihren referenzierten Plänen, Rezepten und Lebensmitteln gelöscht.
