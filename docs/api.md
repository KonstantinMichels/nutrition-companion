# REST API

**API title:** Nutrition Companion API  
**Implemented version prefix:** `/api/v1`  
**Document reviewed:** 2026-07-28  
**Security status:** Local single-user development API; not safe for public exposure

FastAPI publishes the executable OpenAPI schema at `/openapi.json` and interactive documentation at `/docs` when the standard documentation route is enabled. This file explains behavior and boundaries that schema types alone do not capture.

## Authentication boundary

There is no production authentication in the MVP. Every profile-scoped endpoint calls a small development-only current-profile dependency, which returns the UUID from `DEVELOPMENT_PROFILE_ID`. No client-provided profile ID or auth header selects the profile.

This is **not authentication or authorization**. Anyone able to reach a development server can act as that one profile. The settings model refuses staging/production startup while the development resolver is enabled and returns `503 AUTHENTICATION_NOT_CONFIGURED` if no replacement resolver exists. Public exposure is prohibited.

Future authentication should replace only this dependency, then enforce an authenticated principal-to-profile relation and object authorization in every service. It must add secure token lifecycle, rate limiting, enumeration protection, account recovery safeguards and re-authentication for export/deletion.

## Protocol conventions

- JSON requests use `Content-Type: application/json`; responses are JSON.
- Dates are `YYYY-MM-DD`; timestamps are timezone-aware ISO 8601; identifiers are UUIDs.
- Decimal fields accept JSON numbers or strings. A string may use one decimal separator, including German comma (`"82,5"`). Mixed comma and point, malformed, NaN and infinity are rejected.
- Sensitive data belongs only in request bodies. The only query parameters are non-sensitive pagination controls.
- Plain HTTP is allowed only in explicit local development. Staging/production configuration requires HTTPS and normal certificate validation.
- Repeating profile-section `PUT`s replaces that current section. Old assessment snapshots remain unchanged.
- `POST /assessments` is idempotent per `(current profile, client_request_id)` so a safe retry after a lost response returns/uses the one logical assessment rather than creating duplicates.
- Repeating a consent grant for an already active `(current profile, purpose, consent-text version)` returns the existing record and creates neither a duplicate row nor another grant action.
- Assessment raw numeric values retain calculation precision; `display_value` is rounded/formatted for German presentation.

## Error envelope

Every application, validation and unexpected error uses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Die Eingaben konnten nicht verarbeitet werden.",
    "field_errors": [
      {
        "field": "height_cm",
        "code": "OUT_OF_RANGE",
        "message": "Bitte gib einen plausiblen Wert ein."
      }
    ]
  },
  "request_id": "short-lived-random-id"
}
```

`field_errors` is always an array and may be empty. Validation paths can contain list indexes, for example `measurements.0.value`. The API never returns a stack trace or submitted value. Generic, sanitized envelopes also cover unmatched paths (`404`), unsupported methods (`405`) and unexpected downstream exceptions; the outer request middleware consumes the latter rather than allowing an unsanitized exception to propagate to Uvicorn. A caller can give the non-profile-derived `request_id` to a developer for troubleshooting.

Common statuses:

| Status | Meaning |
|---:|---|
| 200 | Successful read/update/action |
| 201 | Consent created/idempotently returned, or assessment created/idempotently returned |
| 403 | Required active assessment consent is missing/withdrawn |
| 404 | Current profile, subsection, consent or assessment not found |
| 409 | Version/idempotency/reference-state conflict |
| 422 | JSON/schema/domain validation failed or consent was not affirmatively granted |
| 503 | Reference data/authentication not configured or unsafe runtime boundary |
| 500 | Sanitized unexpected error; transaction is rolled back where applicable |

## Endpoint overview

| Method | Path | Current-profile scoped | Body/query | Result |
|---|---|---:|---|---|
| GET | `/health` | No | — | Technical liveness response |
| GET | `/api/v1/profile` | Yes | — | Current profile with measurements |
| PUT | `/api/v1/profile` | Yes | `ProfileUpdate` | Create/update current profile and replace measurements |
| GET | `/api/v1/profile/activity` | Yes | — | Current activity and sports |
| PUT | `/api/v1/profile/activity` | Yes | `ActivityUpdate` | Create/update activity and replace sports |
| GET | `/api/v1/profile/goal` | Yes | — | Current nutrition goal |
| PUT | `/api/v1/profile/goal` | Yes | `GoalUpdate` | Create/update goal |
| GET | `/api/v1/profile/restrictions` | Yes | — | Current restrictions |
| PUT | `/api/v1/profile/restrictions` | Yes | `RestrictionsUpdate` | Replace restrictions |
| GET | `/api/v1/profile/health-screening` | Yes | — | Current health screen |
| PUT | `/api/v1/profile/health-screening` | Yes | `HealthScreeningUpdate` | Create/update screen |
| POST | `/api/v1/assessments` | Yes | `AssessmentCreateRequest` | Validate consent/scope, calculate and persist one immutable assessment |
| GET | `/api/v1/assessments` | Yes | `limit`, `offset` | Pagination-ready history envelope |
| GET | `/api/v1/assessments/latest` | Yes | — | Latest full assessment |
| GET | `/api/v1/assessments/{assessment_id}` | Yes | Path UUID | One owned historical assessment |
| DELETE | `/api/v1/assessments` | Yes | `DeletionConfirmation` | Hard-delete all assessment history |
| GET | `/api/v1/reference-sets/current` | No profile data | — | Active scientific and application rule-set metadata |
| GET | `/api/v1/privacy/purposes` | No profile data | — | Versioned processing-purpose registry |
| GET | `/api/v1/privacy/consents` | Yes | — | Consent records, newest first |
| POST | `/api/v1/privacy/consents` | Yes | `ConsentCreate` | Create or idempotently return an active affirmative versioned record |
| POST | `/api/v1/privacy/consents/{consent_id}/withdraw` | Yes | — | Withdraw all matching active grants; repeat is idempotent |
| GET | `/api/v1/privacy/export` | Yes | — | On-demand complete JSON export |
| DELETE | `/api/v1/profile` | Yes | `DeletionConfirmation` | Hard-delete current profile graph |
| DELETE | `/api/v1/privacy/local-profile-data` | Yes | `DeletionConfirmation` | Alias for complete-profile server deletion; mobile then purges local keys |
| DELETE | `/api/v1/privacy/profile-and-assessments` | Yes | `DeletionConfirmation` | Reset personal profile/assessment data while preserving Foods and Recipes |
| DELETE | `/api/v1/privacy/recipes` | Yes | `DeletionConfirmation` | Permanently delete all owned recipes |
| DELETE | `/api/v1/privacy/foods` | Yes | `DeletionConfirmation` | Permanently delete all owned Foods when no recipes reference them |
| DELETE | `/api/v1/privacy/all-data` | Yes | `DeletionConfirmation` | Permanently delete profile, assessments, recipes, Foods and consents |
| GET | `/api/v1/recipes` | Yes | `query`, `tag`, `include_archived`, `page`, `page_size` | Searchable, paginated recipe list with current aggregates |
| POST | `/api/v1/recipes` | Yes | `RecipeWrite` | Create a recipe from owned active Food references |
| GET | `/api/v1/recipes/{recipe_id}` | Yes | Path UUID | Recipe, ingredients, steps, coverage, totals and quality |
| PUT | `/api/v1/recipes/{recipe_id}` | Yes | `RecipeWrite` | Replace editable recipe content atomically |
| GET | `/api/v1/recipes/{recipe_id}/scale` | Yes | `servings` | Non-persistent scaled ingredient preview |
| POST | `/api/v1/recipes/{recipe_id}/duplicate` | Yes | — | Create an editable owned copy |
| DELETE | `/api/v1/recipes/{recipe_id}` | Yes | — | Archive, but do not erase, a recipe |
| DELETE | `/api/v1/recipes/{recipe_id}/permanent` | Yes | — | Permanently delete the owned recipe graph |
| POST | `/api/v1/recipes/{recipe_id}/restore` | Yes | — | Restore an archived recipe |

## Recipe Core

`RecipeWrite` requires a name, positive `servings` and at least one ingredient. Each ingredient references an owned active `food_id`, a positive quantity and either a direct base unit (`g`/`ml`) or an existing `food_measure_id`. Steps are ordered by array position. Tags come from the versioned Recipe Core catalog; `confirm_duplicate` explicitly permits a normalized same-name duplicate.

Responses calculate nutrients on demand from the current referenced Food values. Each nutrient reports total, per-serving and—when recipe weight is available—per-100-g amounts plus known/relevant counts, coverage, missing ingredients and derived-input status. Missing values remain missing; a known zero remains zero. `weight.status` explains whether per-100-g calculation uses entered finished weight, complete theoretical weight or is unavailable. `quality` reports coverage and estimated conversions without claiming verification or medical suitability.

Archived recipes are hidden by default and become read-only until restored. Archived Foods remain readable for an existing recipe but cannot be newly attached. All routes enforce current-profile ownership. Archive is reversible; the separately confirmed permanent-delete action removes only that recipe and its ingredients/steps, not the referenced Foods. Complete profile deletion removes all recipes through the privacy deletion flow.

## Health

`GET /health` returns no database/profile values:

```json
{
  "status": "ok",
  "service": "nutrition-companion-api",
  "environment": "development"
}
```

It proves only that the application process can answer. It is not a deep production-readiness or database-integrity check.

## Profile models

### `ProfileUpdate`

```json
{
  "birth_date": "1991-04-12",
  "physiological_category": "reference_category_a",
  "height_cm": "178,0",
  "current_weight_kg": "82,5",
  "dietary_preference": "mixed",
  "preferred_meals_per_day": 3,
  "preferred_meal_timing": "Frühstück, Mittag, Abend",
  "measurements": [
    {
      "measurement_type": "waist_circumference",
      "value": "91,0",
      "unit": "cm",
      "measured_at": "2026-07-27",
      "source_type": "measured"
    }
  ]
}
```

Allowed categories:

- `physiological_category`: `reference_category_a`, `reference_category_b`. This is an equation/reference-table category, not gender identity.
- `dietary_preference`: `mixed`, `vegetarian`, `vegan`, `other`.
- `measurement_type`: `weight`, `body_fat_percentage`, `waist_circumference`, `hip_circumference`, `measured_resting_energy_expenditure`.
- `source_type`: `measured`, `device_estimate`, `user_estimate`.

Type-specific units are exact: `kg`, `%`, `cm`, or `kcal/day`. A profile accepts at most one current measurement per type; `PUT` replaces the measurement collection. Plausibility validation currently includes height >100 through 250 cm, current weight >25 through 350 kg, profile age 13–120 for storage, and measurement-specific bounds. Automatic assessment scope is narrower (18–65).

The response adds profile `id`, `created_at`, `updated_at`; each measurement adds `id` and `created_at`.

### `ActivityUpdate`

```json
{
  "occupational_activity_category": "seated_with_walking",
  "average_daily_steps": 7500,
  "active_commuting": true,
  "movement_notes": null,
  "manual_pal_override": null,
  "sports": [
    {
      "sport_type": "strength_training",
      "sessions_per_week": "3",
      "minutes_per_session": 60,
      "intensity": "moderate",
      "note": null
    }
  ]
}
```

Activity categories: `mostly_seated`, `seated_with_walking`, `mostly_standing_walking`, `physically_demanding`. Sport categories are `strength_training`, `cycling`, `running`, `swimming`, `endurance_training`, `team_sport`, `mixed_training`, `mobility_recovery`, `other`; intensity is `light`, `moderate`, `vigorous`. Manual PAL is optional and validated from 1.2 through 2.4. `PUT` replaces the complete sports list.

The response adds `profile_id`, timestamps and an `id` per sport.

### `GoalUpdate`

```json
{
  "goal_type": "lose_weight",
  "target_weight_kg": "78,0",
  "desired_intensity": "mild",
  "requested_weekly_rate_kg": "0,25"
}
```

Goal types: `maintain_weight`, `lose_weight`, `gain_weight`, `general_health`, `athletic_performance`. `desired_intensity` (`mild`/`moderate`) is required only for weight-change goals; weight-change options are rejected for other goals. Requested rate is stored/contextual and does not promise an outcome or date.

### `RestrictionsUpdate`

```json
{
  "restrictions": [
    {
      "restriction_type": "allergy",
      "value": "Erdnuss",
      "hard_exclusion": true,
      "note": null
    }
  ]
}
```

Types: `allergy`, `intolerance`, `excluded_food`, `disliked_food`. The MVP stores these for future planning; it does not diagnose or calculate recipe safety. `PUT` replaces the list.

### `HealthScreeningUpdate`

```json
{
  "pregnant": false,
  "breastfeeding": false,
  "diagnosed_eating_disorder": false,
  "diabetes": false,
  "kidney_disease": false,
  "liver_disease": false,
  "medically_prescribed_diet": false,
  "serious_metabolic_condition": false,
  "other_professional_nutrition_condition": false,
  "user_note": null
}
```

The note is stored but not medically reviewed. A true flag does not cause an API validation error: the profile can be saved, and assessment creation returns `supported_scope_status: "unsupported"`, structured flags and no ordinary goal/high-protein target.

## Consent

The configured required purpose is `nutrition_assessment_calculation`. The current canonical mobile/backend consent text version is `privacy_consent_de_mvp_v1`.

```json
POST /api/v1/privacy/consents
{
  "purpose_code": "nutrition_assessment_calculation",
  "consent_text_version": "privacy_consent_de_mvp_v1",
  "affirmed": true,
  "source": "android_onboarding"
}
```

`affirmed: false` produces `422 CONSENT_NOT_GRANTED`. A stale/unknown text version produces `409 CONSENT_TEXT_VERSION_MISMATCH`. `source` is `android_onboarding` or `android_privacy_settings`. A successful `201` response contains:

```json
{
  "id": "7a074227-d35f-4a56-b55f-823736752a09",
  "purpose_code": "nutrition_assessment_calculation",
  "consent_text_version": "privacy_consent_de_mvp_v1",
  "status": "granted",
  "granted_at": "2026-07-28T10:30:00Z",
  "withdrawn_at": null,
  "source": "android_onboarding",
  "created_at": "2026-07-28T10:30:00Z"
}
```

A successful grant returns `201`. If that profile already has an active grant for the same purpose and text version, the response contains the existing record—even if the submitted `source` differs—and no duplicate record or `consent_granted` action is written. A partial unique database index on profile, purpose and text version for non-withdrawn `granted` rows also prevents multiple active records.

Withdrawal resolves the selected owned record's purpose and text version, then changes **all** active grants for that same profile/purpose/version to `withdrawn` using one `withdrawn_at` timestamp. This also closes any legacy duplicate active grants. If none remain active, the selected record is returned without another state change or withdrawal action. Assessment creation requires an active grant for both the configured purpose and current consent-text version, so a later text-version change requires a matching new grant. Withdrawal stops future assessment creation; it does not delete current/history data.

The processing-purpose response exposes `code`, German description, data categories, special-category flag, storage, retention, legal-basis placeholder, consent requirement, recipients/processors, German deletion behavior, required/optional flag and `registry_version` (`mvp_v1`). Only `nutrition_assessment_calculation` is technically consent-gated. Profile storage and assessment history return `consent_required: false`; that reflects current enforcement, not a legal conclusion. Their Article 6/9 bases and any need for separate consent remain release blockers.

## Assessment creation and immutability

The app first saves the five current profile sections and consent, then calls:

```json
POST /api/v1/assessments
{
  "client_request_id": "e3df2ab8-fb96-465d-b29c-72882cb640bb"
}
```

The backend requires a profile, activity, goal, screening, active consent and seeded current reference/rule sets. It computes age at assessment time, copies all relevant inputs into an immutable snapshot, invokes the deterministic engine and persists assessment/metrics/flags in one transaction.

Creation outcomes are intentionally distinct:

- no current profile: `404 PROFILE_NOT_FOUND`;
- missing activity, goal or health screening: `409 PROFILE_INCOMPLETE` with field errors;
- no active current-version calculation consent: `403 CONSENT_REQUIRED`;
- seed rows missing or not matching the engine's checked-in versions: `503 REFERENCE_DATA_NOT_SEEDED` or `503 REFERENCE_VERSION_MISMATCH`;
- invalid engine-domain input: `422 VALIDATION_ERROR`; and
- unsupported age/health scope: still `201`, but with `supported_scope_status: "unsupported"`, blocking flags and withheld dependent target metrics.

A repeated `(profile, client_request_id)` returns the previously stored assessment and does not recalculate it. This also means an idempotent retry is retrieval of the already completed action, not authorization to create a new assessment after consent withdrawal or profile changes.

A successful `AssessmentResponse` has the following shape (values and repeated lists are abbreviated here):

```json
{
  "id": "85e4fc58-20bc-4978-a983-3e0e2283eebd",
  "supported_scope_status": "supported",
  "reference_set_identifier": "...",
  "reference_set_version": "...",
  "application_rule_set_identifier": "nutrition_companion_mvp_v1",
  "application_rule_set_version": "...",
  "engine_version": "...",
  "calculated_at": "2026-07-28T10:31:00Z",
  "summary": {
    "goal_type": "maintain_weight",
    "supported_scope": true,
    "total_weekly_exercise_minutes": "180",
    "energy_target": {
      "available": true,
      "lower": "2200.00",
      "midpoint": "2280.00",
      "upper": "2360.00",
      "unit": "kcal/Tag"
    },
    "protein_target": {
      "available": true,
      "minimum": "66.00",
      "default": "66.00",
      "upper": null,
      "unit": "g/Tag"
    },
    "micronutrients": {
      "available_codes": ["vitamin_a", "vitamin_d"],
      "unavailable_codes": ["magnesium"],
      "reference_set_complete": false
    },
    "food_groups": [
      {
        "code": "water_calorie_free_beverages",
        "display_name_de": "Wasser und kalorienfreie Getränke",
        "recommendation_de": "...",
        "amount": "1.5",
        "unit": "Liter",
        "frequency": "daily",
        "minimum": null,
        "maximum": null,
        "combined_group_code": null,
        "source_metadata": {}
      }
    ]
  },
  "metrics": [
    {
      "metric_code": "anthropometrics.bmi",
      "raw_value": "26.038378...",
      "display_value": "26,0",
      "lower_value": null,
      "upper_value": null,
      "unit": "kg/m²",
      "method_code": "bmi_weight_divided_by_height_squared",
      "explanation_de": "...",
      "limitations_de": "...",
      "calculation_inputs": {},
      "source_metadata": {},
      "application_rule_identifier": null,
      "confidence_type": "derived"
    }
  ],
  "safety_flags": []
}
```

Exact summary and metric codes are documented in [nutrition_methodology.md](nutrition_methodology.md); consumers should tolerate additive keys. The normal assessment response does not include the top-level persisted `input_snapshot` or `client_request_id`; per-metric `calculation_inputs` support the report, while the complete user export includes both stored fields. Typed `Decimal` response fields and decimal values embedded by the engine currently serialize as JSON strings (for example, `"26.038378"`), preserving decimal semantics. Requests accept JSON numbers or normalized decimal strings as described above; clients should not convert raw values through binary floating point when reproducibility matters.

`GET /api/v1/assessments?limit=20&offset=0` returns:

```json
{
  "items": [
    {
      "id": "...",
      "calculated_at": "...",
      "supported_scope_status": "supported",
      "goal_type": "maintain_weight",
      "energy_target_summary": "...",
      "warning_codes": []
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

The full latest/by-ID responses are stored historical output; they are not recalculated. An ID belonging to no current-profile assessment returns a non-revealing 404.

If pagination parameters are omitted, `limit` defaults to 25 and `offset` to 0; the maximum limit is 100.

## Reference-set metadata

`GET /api/v1/reference-sets/current` returns the active reference and rule set:

```json
{
  "reference_set_identifier": "dge_oege_v3_mvp_2026_05",
  "reference_set_version": "3rd-edition-2025_erratum-2026-05_subset-v1",
  "source_organization": "Deutsche Gesellschaft für Ernährung (DGE) und Österreichische Gesellschaft für Ernährung (ÖGE)",
  "edition": "Referenzwerte für die Nährstoffzufuhr, 3. Auflage, 1. Ausgabe 2025; Erratum Stand Mai 2026",
  "publication_date": null,
  "effective_date": "2026-07-28",
  "application_rule_set_identifier": "nutrition_companion_mvp_v1",
  "application_rule_set_version": "v1",
  "application_rule_set_effective_date": "2026-07-28",
  "metadata": {
    "reference_set": {},
    "application_rule_set": {}
  }
}
```

If seeding has not created both active sets, the endpoint returns `503 REFERENCE_DATA_NOT_SEEDED`. The nested metadata contains the seed's complete reference-set declaration and application-rule-set document.

## Export

`GET /api/v1/privacy/export` is generated on demand. It first writes a minimal `export_requested` privacy action, so the response's `privacy_actions` array includes the action for that very export. Response:

```json
{
  "export_format": "nutrition_companion_json_v1",
  "generated_at": "2026-07-28T10:35:00Z",
  "notice_de": "Dieser Export wurde auf deine ausdrückliche Aktion erstellt ...",
  "data": {
    "profile": {},
    "measurements": [],
    "activity": {},
    "goal": {},
    "dietary_restrictions": [],
    "health_screening": {},
    "consent_records": [],
    "privacy_actions": [],
    "assessments": []
  }
}
```

It includes current profile sections and timestamps, measurement/sport/restriction IDs, consent records, minimal privacy actions, and complete assessments including their `client_request_id`, input snapshot, metrics and flags. Every Python `Decimal`, including values nested inside assessment snapshots and calculation metadata, is encoded directly as an exact JSON string rather than converted through binary floating point. It excludes application secrets and unrelated server metadata. The Android app creates a temporary JSON file only for an explicit share action and deletes its app-controlled copy after the share workflow. Production requires authentication and re-authentication.

## Deletion

Both deletion scopes require an explicit JSON body:

```json
{ "confirm": true }
```

Any other/missing value fails validation. History deletion removes all owned assessments and dependent metrics/flags while retaining the profile. Complete deletion removes the profile graph and applicable consent rows. Both are transactional and return:

```json
{
  "deleted": true,
  "scope": "assessment_history",
  "confirmation_code": "non-profile-derived-code",
  "message_de": "..."
}
```

The server retains a minimal `DeletionRecord` containing scope, timestamp, approximate deleted-record count and random confirmation code, without the former profile UUID or health data. The current implementation does not yet apply a TTL to that minimal record; production retention is a documented blocker. After server success, the mobile app clears the corresponding encrypted cache or all owned sensitive keys.

## CORS, logs and production use

Configured CORS allows only listed origins, credentials are disabled, and methods are limited to GET/POST/PUT/DELETE/OPTIONS. Wildcard origins are rejected outside local environments.

The current structured request middleware emits timestamp, random request ID, route template (or the constant `/{unmatched}` when no route matched), HTTP method, status and duration only. It does not emit a raw unmatched/error path, request/response bodies, profile UUIDs, body values, health answers, result details, tokens, environment secrets or secure-storage content. Database-backed route functions are synchronous, so FastAPI dispatches their blocking SQLAlchemy work to its worker thread pool instead of running it directly on the event loop.

Docker Compose publishes both PostgreSQL and the API on host loopback by default. Set `API_BIND_ADDRESS` only when intentional device/LAN reachability is required; this development resolver is not safe for public exposure. The Compose Uvicorn command disables Uvicorn's access log, preventing a second default request log from recording raw paths. Any production ingress, proxy, platform or alternative Uvicorn command needs its own field and retention review.

The API is not production-ready until the blockers in [privacy/production_privacy_checklist.md](privacy/production_privacy_checklist.md) are completed and verified.
# Food Core

- `GET /api/v1/nutrients` – Katalog; Filter `category`, `basic_only`, `active_only`
- `GET /api/v1/nutrients/{code}` – Katalogeintrag
- `GET /api/v1/foods` – eigene Lebensmittel; Suche, Kategorie, Archivfilter und Pagination
- `GET /api/v1/foods/duplicates` – mögliche Namens-/Markendubletten
- `POST /api/v1/foods` – Lebensmittel, bekannte Nährwerte und Maße transaktional anlegen
- `GET /api/v1/foods/{id}` – vollständige Details einschließlich Ableitungen und Qualität
- `PUT /api/v1/foods/{id}` – eigenes aktives Lebensmittel ersetzen
- `DELETE /api/v1/foods/{id}` – archivieren, nicht dauerhaft löschen
- `POST /api/v1/foods/{id}/restore` – wiederherstellen
- `DELETE /api/v1/foods/{id}/permanent` – eigenes Lebensmittel und abhängige Werte nach ausdrücklicher Bestätigung endgültig löschen
- `GET /api/v1/foods/barcode/{code}` – Produktvorschau von Open Food Facts laden; überträgt den Barcode an den externen Dienst
- `POST /api/v1/foods/barcode/{code}/import` – bestätigte Vorschau als profilgebundenes Lebensmittel speichern

Relevante Fehlercodes sind `FOOD_NOT_FOUND`, `FOOD_ARCHIVED`, `FOOD_DUPLICATE_WARNING`, `INCOMPLETE_BASIC_NUTRITION`, `NUTRIENT_NOT_FOUND`, `NUTRIENT_UNIT_MISMATCH`, `INCONSISTENT_SALT_SODIUM`, `INVALID_REFERENCE_BASIS` und `INVALID_MEASURE_CONVERSION`.

Barcodefehler: `INVALID_BARCODE`, `BARCODE_PRODUCT_NOT_FOUND` und `EXTERNAL_FOOD_SERVICE_UNAVAILABLE`.
