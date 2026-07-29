# Future modules

The next expected branch is `feat/shopping-list-core`. It will collect requirements
from selected daily or weekly plans, normalize quantities, compare them with Pantry
availability, calculate missing amounts, and allow manual entries while keeping planned
requirements separate from actual purchases. None of this is implemented in Pantry Core.

The next expected branch is `feat/pantry-core`. Pantry Core will introduce stored food
items, available quantities, storage locations, optional best-before dates, manual stock
adjustments, and links to Food Core. It prepares later pantry-aware planning and shopping
lists; none of those capabilities is implemented yet.

## Next: `feat/weekly-meal-planning`

Daily Meal Planning is implemented. The next branch should organize existing daily plans across a
week, provide a weekly overview, support deliberate copying/moving of meals between dates and
aggregate weekly nutrient and food-group information. It may prepare later automatic planning but
must not silently introduce recommendations or optimization. Weekly planning is not implemented.

**Status:** Architecture roadmap only  
**Last reviewed:** 2026-07-28

None of the modules below is part of the MVP unless the code and tests explicitly say otherwise. This document describes integration seams, not implemented promises.

## Extension principle

Nutrition Companion remains a modular monolith until measured operational needs justify something else. A new feature should normally add:

1. a cohesive backend module inside the existing FastAPI deployment;
2. relational tables and an Alembic migration in the same PostgreSQL database;
3. application services that call existing module APIs rather than reaching into their tables;
4. versioned REST endpoints under `/api/v1` (or a later explicit API version); and
5. one feature area in the Flutter application.

The existing Nutrition Engine remains deterministic, side-effect free and backend-owned. Meal-planning modules may consume an immutable assessment result; they must not copy its formulas into Flutter or silently reinterpret historical targets.

Every module must complete a data-minimization, purpose, retention, recipient, permission and regulatory review before implementation. “The data already exists” is not permission to reuse it for a new purpose.

## Domain evolution

| Module | Likely core records | Integration with MVP | Important boundary before implementation |
|---|---|---|---|
| Foods | `Food`, `FoodNutrient`, provenance/version | Supplies ingredients and nutrient totals; does not replace assessment references | Dataset licence, provenance, update/recall process and locale-specific units |
| Recipes | `Recipe`, `RecipeIngredient`, portions, instructions | May compare aggregate nutrients with an assessment snapshot | Allergy safety wording, recipe-source rights and deletion ownership |
| Meal plans | `MealPlan`, `MealSlot`, planned portions | Reads a selected assessment ID and its immutable target snapshot | Planning is not treatment; preserve the exact target version used |
| Weekly planning | Calendar-like aggregation around meal plans | Produces a week view without changing assessment history | Time-zone behavior, conflict model and retention |
| Pantry | `PantryItem`, quantity, expiry estimate | Can suggest availability for recipes | Household sharing and barcode/device access need separate scope |
| Shopping lists | `ShoppingList`, `ShoppingItem` | Derived from plans plus pantry; user can edit independently | External sharing is a new disclosure purpose |
| Barcode import | Product code, provider response and provenance | Creates or links a food record | Camera permission only in context; provider contract, accuracy and transfer review |
| Social-media recipe import | Source URL, extracted draft, provenance | Creates a user-reviewed recipe draft | Copyright, platform terms, third-party transfer, media upload and security review |
| Longitudinal weight tracking | Timestamped measurements and user context | Existing measurements can seed a time series | Trend wording, eating-disorder safeguards and retention controls |
| Dynamic energy calibration | Versioned calibration observations and model result | Creates a new estimate; never mutates old assessments | Scientific validation, minimum data quality, uncertainty, reset/opt-out and likely fresh regulatory review |
| iOS | Platform target using the same Flutter feature code | Uses the existing REST API and iOS Keychain-compatible storage abstraction | Keychain accessibility/backup behavior, App Store declarations and platform tests |
| Optional web dashboard | Separate presentation client only | Uses the same authenticated API and purpose boundaries | Browser storage, CSRF/CORS, cookies/TDDDG, session security and accessibility |
| Real authentication | Account, credentials/federated subject, sessions | Replaces the development-only current-profile resolver | Threat model, account recovery, enumeration, rate limiting and re-authentication for export/deletion |

## Foods and nutrient provenance

A food database is different from the DGE/ÖGE target-reference set. Food nutrient composition needs its own source records, licence fields, locale, sampling/method metadata, effective dates and import checks. It must never be stored as if it were a user target. Imported values remain attributable to a dataset version; corrected data should not silently rewrite a historical meal-plan calculation.

## Planning flow

The realistic dependency path is:

```text
versioned foods -> recipe ingredients -> recipes -> meal-plan slots
                                         |             |
pantry quantities -----------------------+             +-> shopping-list draft
immutable assessment target ---------------------------> comparison/explanation
```

Recipe and plan services should receive a selected `assessment_id`, not simply read the latest mutable profile. A plan can then explain which historical target it used. Creating a new assessment does not silently rewrite existing plans.

## Import flows

Barcode or social-media import should be a staged workflow:

1. user explicitly invokes the feature and sees the purpose;
2. permission is requested only when required;
3. external content is retrieved through an isolated importer with timeouts, size/content limits and allowlists where appropriate;
4. provenance and licence/terms metadata are retained;
5. parsed content is an untrusted draft;
6. the user reviews and confirms it before it becomes a recipe or food; and
7. temporary media and raw payloads are deleted according to a specific retention rule.

No importer may feed an LLM result directly into authoritative nutrition calculations. If AI extraction is ever proposed, it requires explicit uncertainty labeling, a new processing purpose, processor/transfer review, human confirmation and a separate product/regulatory assessment.

## Longitudinal calibration

Future calibration must be a new, versioned engine capability rather than a mutation of the Mifflin/PAL calculation. At minimum it would need:

- sufficient dated weight observations and a documented quality threshold;
- declared or measured intake/behavior inputs of known uncertainty;
- a deterministic model version and immutable calibration input snapshot;
- separation of observed data from inferred energy requirements;
- bounds, drift detection and an easy reset;
- clear “estimated, not measured” explanations; and
- prospective scientific and safety evaluation.

Historical assessments remain as originally produced. A calibrated value creates a new assessment or separately versioned calibration result.

## Authentication migration

The MVP's fixed development-profile resolver is deliberately one small dependency. Production authentication should replace it with an authenticated principal-to-profile resolution step while application services continue to accept only an authorized profile context. The migration must add:

- secure token storage in Android Keystore/iOS Keychain;
- server-side authorization on every profile-scoped object;
- token rotation/revocation and rate limiting;
- re-authentication before export and destructive deletion;
- recovery safeguards and account-enumeration protection; and
- tests proving cross-account isolation.

Production must never fall back to the development resolver.

## When to reconsider deployment topology

Separate services are not a roadmap goal. Reconsider only if there is evidence of an independently scaling workload, materially different security isolation, a separately operated team or a hard availability boundary. Even then, first define ownership, transaction changes, failure behavior and privacy impact. A queue, cache, generic plugin framework or additional database should not be introduced merely because a future feature could use one.
# Implementiert: `feat/recipe-core`

Recipe Core referenziert Lebensmittel per ID, normalisiert g/ml und vorhandene Haushaltsmaße und aggregiert bekannte Nährwerte dezimalgenau mit sichtbarer Abdeckung. Barcode-Produkte können nach dem Food-Import als Fertiggericht in einen Rezeptentwurf übernommen werden.

# Implementiert: `feat/recipe-target-comparison`

Ein einzelnes Rezept kann mit einer gewählten unveränderlichen Einschätzung und einer frei gewählten Portionszahl verglichen werden. `feat/daily-meal-planning` ist ebenfalls implementiert: mehrere Foods und Rezepte lassen sich manuell zu Mahlzeiten und einem Tag kombinieren. Nächster erwarteter Branch ist `feat/weekly-meal-planning`.
