# Pantry-aware Shopping

Pantry-aware Shopping gleicht einen aktuellen Rezept-, Tagesplan- oder Wochenbedarf oder die
Quellen einer bestehenden Einkaufsliste mit aktivem Vorrat und offenen Einkaufslisten ab. Die
Funktion plant zusätzliche Einkaufsmengen; sie bestätigt weder Kauf noch Verzehr und reserviert,
verändert oder reduziert keinen Vorrat.

## Quellen und Identität

Direkte Planeinträge verwenden `daily_plan:{plan}:meal_entry:{entry}`, Rezeptzutaten innerhalb eines
Planeintrags ergänzen `:recipe_ingredient:{ingredient}`. Wochenquellen behalten diese zugrunde
liegenden Tagesplanidentitäten. Direkte Rezeptvorgänge verwenden
`recipe:{recipe}:request:{occurrence}:ingredient:{ingredient}`. Dadurch ist ein Vorgang idempotent,
während ein späterer bewusster Vorgang eine neue Occurrence-ID erhält. Gleiche Food-IDs werden
aggregiert; gleichnamige verschiedene Foods bleiben getrennt.

Eine bereits auf einer offenen Liste repräsentierte Identität wird standardmäßig ausgelassen und
mit ihrer Liste angezeigt. Bewusste Duplikate benötigen eine ausdrückliche Bestätigung. Gespeicherte
Source-Snapshots bleiben erhalten, auch wenn eine Quelle später nicht mehr verfügbar ist.

## Berechnung

```text
combined_requirement = existing_open_linked_requirement + new_selected_requirement
global_additional_need = max(combined_requirement - pantry - all_open_commitments, 0)
desired_target_commitment = max(combined_requirement - pantry - other_open_commitments, 0)
suggested_target_change = desired_target_commitment - target_existing_commitment
```

Checked-Zustände allein entfernen kein Commitment. Bei partieller Purchase-to-Pantry-Übergabe gilt
`max(purchase_quantity - transferred_quantity, 0)`; ein ausdrücklich abgeschlossener Handoff zählt
als null. Abgeschlossene oder archivierte Listen zählen nicht. Freitextartikel nehmen an keiner
Food-Berechnung teil.

Die Pantry-Datumsmodi schließen wahlweise nichts, überschrittene Verbrauchsdaten oder alle
überschrittenen Datumsfelder aus. Datumshinweise sind keine Aussage zur Lebensmittelsicherheit.

## Vorschau und Übernahme

Die Vorschau persistiert nichts und zeigt Bedarf, Pantry, andere Listen, Zielliste, Vorschlag,
Änderung, Annahmen, Duplikate und Konflikte. Manuelle Food-Treffer werden nicht stillschweigend
zusammengeführt; mehrere Treffer benötigen eine Entscheidung. Manuell überschriebene Mengen bleiben
erhalten, bis „Auf aktuellen Vorschlag setzen“ ausdrücklich gewählt wird. Freitext und manuelle
Artikel bleiben unverändert.

Apply prüft den opaken Vorschau-Token erneut und schreibt genau eine Zielliste, Source-Links und einen
Audit-/Idempotenzdatensatz in einer Transaktion. Eine profilweit eindeutige Client-Operations-ID
verhindert Doppelbuchungen. Änderungen an Quellen, Pantry, Handoffs oder relevanten Listen machen die
Vorschau ungültig. Andere Einkaufslisten und Pantry werden nie verändert.

## Datenschutz und Grenzen

Die Verarbeitung bleibt in Flutter, eigener FastAPI und PostgreSQL; es gibt keinen externen
Empfänger, keine Analyse und keine zusätzliche Einwilligungscheckbox. Persistierte Operationen und
Source-Metadaten erscheinen im Export und werden mit dem vollständigen Profil gelöscht. Vorschauen
und Tokens werden nicht gespeichert oder exportiert.

Pantry ist nicht reserviert; parallele Vorschauen können veralten. Offene Listen sind
Planungsannahmen, checked bedeutet nicht gekauft, und bestätigte Handoffs hängen von Nutzereingaben
ab. Nicht unterstützt sind Ersatzprodukte, Paketgrößen, Preise, Händler, Freitextberechnung,
Pantry-Abzug oder automatische Planung. Der nächste Ausbau ist
`feat/progress-tracking-core`.

Optimization reads remaining active canonical shopping commitments after partial Pantry handoffs to
estimate additional shortages. It never updates, completes or creates a Shopping List.
