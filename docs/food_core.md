# Food Core

Food Core verwaltet manuell angelegte und ausdrücklich aus Open Food Facts importierte, profilgebundene Lebensmittel. Der Barcode-Import ist keine Herstellerprüfung. Rezepte, Vorräte und Mahlzeitenplanung sind noch nicht implementiert.

## Modell und Katalog

`Food` speichert Metadaten, Quelle, Eigentümer, Archivstatus und genau eine Bezugsbasis (100 g oder 100 ml). `FoodNutrient` speichert bekannte Werte dezimalgenau und eindeutig je Lebensmittel/Nährstoffcode. `FoodMeasure` bildet Stück, Portion, Scheibe, Tee- und Esslöffel auf g oder ml ab. Die Dichte ist optional. Ohne Dichte findet keine g/ml-Umrechnung statt.

Der versionierte Codekatalog in `app.modules.foods.nutrient_catalog` ist die autoritative Definition für Nährstoffcodes, deutsche Namen, Einheiten, Kategorien, Reihenfolge und Plausibilitätsmetadaten. Er verwendet dieselben Mikronährstoffcodes wie die Nutrition Assessment. Kategorien und unterstützte Maße sind kleine, versionierte Codekataloge; es werden keine realen Lebensmittel oder erfundenen Werte ausgesät.

## Semantik und Berechnungen

Ein fehlender Datensatz bedeutet „Nicht angegeben“; ein gespeicherter Wert `0` ist eine echte Null. kcal ist die Eingabequelle, kJ wird mit `kcal × 4,184` als `system_derived` ausgegeben. Salz und Natrium sind getrennte Codes; der jeweils fehlende Wert wird mit Faktor 2,5 abgeleitet. Widersprüchliche Doppelteingaben werden abgelehnt.

Die Qualitätsstufen `incomplete`, `basic_complete` und `extended` beschreiben Vollständigkeit, nicht wissenschaftliche Verifizierung. Herkunft (`user_entered` bzw. `system_derived`) bleibt separat sichtbar. Skalierung nutzt `amount × quantity / 100` mit `Decimal` und rundet keine Zwischenwerte.

## Eigentum, Archiv und Datenschutz

Alle manuellen Lebensmittel gehören zum aktuellen Profil. Listen, Detail, Änderung, Archivierung und Wiederherstellung sind profilisoliert. `DELETE /foods/{id}` archiviert als sichere Standardaktion. Nach einer gesonderten Warnung kann `DELETE /foods/{id}/permanent` ein eigenes Lebensmittel einschließlich Nährwerten und Maßen unwiderruflich löschen. Die vollständige Profillöschung entfernt ebenfalls Lebensmittel und abhängige Werte dauerhaft über Cascades. Der Datenschutzexport enthält Metadaten, Quellen, Werte, Maße und Archivstatus.

## Recipe Core

Das spätere Recipe Core kann Food-IDs referenzieren und `scale_nutrients` sowie `convert_measure_to_base_quantity` wiederverwenden. Unbekannte Werte bleiben dabei unbekannt. Historische Snapshots sind bewusst noch nicht implementiert.

## Barcode und Open Food Facts

Die Android-App scannt EAN/UPC/GTIN lokal mit ML Kit. Nur der erkannte Zahlencode wird über das eigene Backend an Open Food Facts übertragen. Name, Marke, Bild und bekannte Werte pro 100 g/ml erscheinen zuerst als Vorschau. Der Nutzer muss den Import bestätigen; unvollständige Grundwerte erfordern eine zusätzliche Bestätigung. Fehlende Werte erzeugen keine Nullwerte. Gespeichert werden `source_type=open_food_facts`, Barcode, Quellname und Änderungsstand. Open Food Facts ist gemeinschaftlich gepflegt; Vollständigkeit, Aktualität und Richtigkeit sind nicht garantiert.
