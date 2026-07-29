# Pantry Recipe Availability

Die Rezeptverfügbarkeit vergleicht auf ausdrücklichen Abruf die aktuellen Zutaten eines
profilgebundenen Rezepts mit den aktiven Vorratslosen desselben Profils. Das Ergebnis ist eine
Live-Berechnung: Es wird weder gespeichert noch reserviert, abgezogen oder als Bewegung gebucht.

Zutaten werden mit `gewünschte Portionen / gespeicherte Rezeptportionen` skaliert und ausschließlich
über ihre Food-ID zusammengefasst. Optionale Zutaten sind standardmäßig ausgeschlossen. Für jede
Zutat zeigt die Antwort Bedarf, verfügbaren Bestand, Fehlmenge, einen rein hypothetischen Rest,
Abdeckung und die beitragenden Lose. Archivierte Foods und geschätzte Einheitenumrechnungen bleiben
sichtbar. Ein unbekannter oder nicht kompatibler Wert wird nicht als Null interpretiert.

Auf Rezeptebene werden vollständige, teilweise, fehlende und nicht berechenbare Verfügbarkeit,
maximal mögliche Portionen, vollständige ganze Portionen und alle gleichauf begrenzenden Zutaten
ausgewiesen. Die Berechnung verwendet `Decimal`; Rundung findet nur für die deutsche Anzeige statt.

Aktive Lose können in drei Datumsmodi betrachtet werden: alle einschließen, überschrittene
Verbrauchsdaten ausschließen oder alle überschrittenen Datumsfelder ausschließen. Die Datumssortierung
hilft bei der transparenten Darstellung, ist aber keine Aussage zur Lebensmittelsicherheit. Nutzer
entscheiden selbst über Verwendung und Entsorgung.

Die API bietet die Detailberechnung unter
`GET /api/v1/recipes/{recipe_id}/pantry-availability` und filterbare Listenübersichten unter
`GET /api/v1/recipes/pantry-availability`. Beide Endpunkte erzwingen die Profilzugehörigkeit. Es gibt
keine neue Tabelle, Migration, Exportentität oder Löschreihenfolge. Der nächste Ausbau ist
`feat/pantry-aware-shopping`.

Dieser Folgeausbau verwendet dieselbe Rezeptskalierung und Datumssemantik, ergänzt aber offene
Einkaufslisten und aktualisiert nach ausdrücklicher Vorschau genau eine Zielliste.

The optimizer aggregates the same canonical ingredient requirements across its transient draft.
This is a temporary calculation only: availability is never reserved or deducted.
