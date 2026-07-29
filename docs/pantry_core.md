# Pantry Core

Pantry Core stores manually reported food availability. `PantryLocation` identifies a
profile-owned storage place. `PantryStockLot` represents a distinguishable quantity of
one Food Core food, and multiple lots per food and location are supported. Pantry Core
depends on Food Core for base units, density conversion, and household measures;
planning modules do not depend on Pantry Core.

Every lot stores its current canonical balance in `g` or `ml`, its initial entered
quantity/unit or FoodMeasure, and whether conversion was estimated. `kg` normalizes to
`g`, `l` to `ml`; mass/volume conversion needs Food Core density, and ambiguous piece or
package units need a matching FoodMeasure. Decimal/NUMERIC arithmetic is retained
without intermediate rounding.

Quantity changes happen only through the inventory service. Creation writes an
`initial_stock` movement. Add, consume, discard, correction, transfer, and restore keep
immutable before/after records. Operations lock the lot row and use a mobile-generated
UUID for idempotency. Duplicate submissions return the previously affected lot. A
balance cannot become negative. Depleted lots remain in history.

Full transfer keeps the lot ID and changes its location with a transfer movement.
Partial transfer reduces the locked source, creates a new target lot with copied date
metadata, and writes linked transfer-out/transfer-in movements in one transaction.
Lots are never merged automatically.

Purchase, opened, best-before, and use-by dates remain separate. The display rule
`expiring_soon_days` is currently versioned in code at three days. Use-by has display
priority. Date states never delete stock or claim whether food is safe. Both date types
may coexist and produce a visible plausibility warning.

Archived lots are excluded from availability without being treated as consumed or
discarded. Non-depleted archive requires confirmation. Archived locations cannot accept
stock or be restored as a lot target; non-empty locations cannot be archived. Default
locations are created once per profile.

Availability sums active, non-depleted, non-archived lots by food and location. No
nutritional score, shortage, shopping list, or recipe-availability decision is made.

Pantry locations, lots, and movements are included in profile export and removed during
complete profile deletion. Requests are logged only by endpoint template/status; stock
names, quantities, dates, notes, and request bodies are not logged. No Pantry form cache
or external service is used.

Known limitations: inventory is manual and may differ from reality; no meal-plan
deduction, consumption synchronization, barcode stocking, receipt scanning, price
tracking, reminder, notification, shared household, safety assessment, shopping list,
or recipe recommendation exists. The next expected feature is
`feat/shopping-list-core`.
# Herkunft aus Einkaufslisten

Bestände aus ausdrücklich bestätigten Übergaben verwenden die generische Bewegungsquelle `shopping_list_purchase`. Pantry bleibt für Mengen und Bewegungen autoritativ; Listenhaken oder Listenabschluss erzeugen keine Bewegung.
