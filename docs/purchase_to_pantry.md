# Purchase to Pantry

Purchase to Pantry überträgt ausdrücklich bestätigte Einkäufe aus einer Einkaufslisten-Momentaufnahme in Pantry Core. Folgende Zustände bleiben unabhängig: Eintrag abgehakt, Liste abgeschlossen, Kauf bestätigt, Menge in Pantry übertragen und tatsächlich verfügbarer Bestand. Abhaken oder Abschließen verändert Pantry niemals.

## Ablauf und Berechnung

Offene und abgeschlossene, aber nicht archivierte Listen sind zulässig. Abgehakte Food-Core-Einträge sind vorausgewählt; nicht abgehakte können bewusst ergänzt werden. Freitext wird nur nach expliziter Zuordnung zu einem aktiven Food übertragen. Haushaltswaren bleiben außerhalb des Lebensmittelvorrats.

Die tatsächliche Menge darf von der geplanten Kaufmenge abweichen und wird über Pantry/Food Core ohne vorzeitige Rundung normalisiert. Unterstützt werden g, kg, ml, l und passende FoodMeasures. Ein Artikel kann auf mehrere neue oder bestehende Bestände verteilt werden; die normalisierten Zielmengen müssen exakt der tatsächlichen Gesamtmenge entsprechen. Neue Bestände sind der Standard. Ein bestehender Bestand muss aktiv, nicht aufgebraucht, demselben Food und kompatiblen Metadaten zugeordnet sein; seine Datumsfelder werden nicht überschrieben.

Kauf-, Öffnungs-, Mindesthaltbarkeits- und Verbrauchsdatum sind getrennt. Nur das Kaufdatum darf in der App mit dem lokalen heutigen Datum vorbelegt werden. Daraus wird keine Lebensmittelsicherheit abgeleitet.

## Vorschau, Anwendung und Historie

`pantry-handoff-preview` prüft Eigentum, Mengen, Einheiten, Foods, Lagerorte, Bestände, Datumsmetadaten und Splits, persistiert aber nichts. Der Token bindet die Vorschau an Shopping-List- und Pantry-Lot-Versionen. `pantry-handoff` berechnet autoritativ neu, sperrt relevante Datensätze und wendet alle Pantry-Operationen in einer Transaktion an. Ein profilweit eindeutiger `client_operation_id` verhindert Doppelbuchungen; Zieloperationen erhalten deterministische Unter-IDs.

Jede erfolgreiche Übergabe speichert Batch, Artikel und Ziele einschließlich Pantry-Bewegung. Ein Artikel ist `partial`, bis der Nutzer ihn ausdrücklich als abgeschlossen markiert; numerische Gleichheit allein schließt ihn nicht ab. Weitere Sitzungen bleiben möglich, nach Abschluss nur mit zusätzlicher Bestätigung. Checkbox und Listenabschluss bleiben unverändert.

## Datenschutz und Grenzen

Übergaben erscheinen im Profildatenexport und werden bei vollständiger Profillöschung vor den verknüpften Shopping- und Pantry-Daten entfernt. Vorschauen werden nicht gespeichert, Anfragetexte nicht geloggt und keine Daten extern übertragen. Die Verarbeitung ist Teil der ausdrücklich angeforderten Shopping-/Pantry-Funktion und erhält deshalb keine zusätzliche Einwilligungscheckbox.

Einkäufe und Daten werden manuell bestätigt. Nicht enthalten sind Beleg-/Barcode-Erkennung, Preise, Händlerabgleich, automatische Paketgrößen, automatische Übertragung, Pantry-Abzug oder Rezeptverfügbarkeit. Als Nächstes ist `feat/pantry-recipe-availability` vorgesehen.
