# Architecture

Pantry Core depends on Food Core (`Pantry Core → Food Core`) for unit, density, and
FoodMeasure normalization. Food, Recipe, Daily Planning, and Weekly Planning do not
depend on Pantry Core. A later Shopping List Core may read plan requirements and Pantry
availability without reversing this dependency.

Weekly Meal Planning is a read-time aggregation module over seven local-date daily
plans. It introduces REST read/action endpoints but no weekly database entity or
calculation cache. See [Weekly Meal Planning](weekly_meal_planning.md).

**Status:** Implemented local-MVP architecture and production boundary  
**Last reviewed:** 2026-07-28

## System shape

Nutrition Companion is one repository and one modular-monolith deployment:

```text
Flutter Android app
  UI -> Riverpod controller -> repository/API client
            |                    |
            |                    +-- REST/JSON
            +-- secure local draft/cache
                                  |
                                  v
FastAPI modular monolith
  route -> application service -> pure Nutrition Engine
                 |
                 +-> repository -> SQLAlchemy -> PostgreSQL
```

There are no microservices, message brokers, background-job workers, remote calculation services or local mobile SQL database. Database-backed FastAPI handlers are synchronous and run in FastAPI's worker thread pool, so their SQLAlchemy I/O does not run directly on the event loop. Docker Compose is a development deployment convenience, not a production topology. Its published PostgreSQL and API ports bind to `127.0.0.1` by default; intentional physical-device/LAN testing requires overriding `API_BIND_ADDRESS` and reviewing the host firewall. The API still listens on `0.0.0.0` inside its container so the host port mapping can reach it.

## Repository components

### Flutter application

The mobile application is feature-oriented rather than split into ceremonial layers. Its responsibilities are:

- Material 3 German UI, routing and light/dark theme;
- multi-step form state, local validation and German decimal normalization;
- Riverpod controllers/providers and loading/empty/error state;
- Dio REST calls and backend error mapping;
- secure onboarding draft and minimal latest-result cache;
- profile/history/report/privacy presentation; and
- explicit export/share and local-data deletion actions.

Widgets do not own nutrition formulas. Model/repository/controller code translates typed JSON and coordinates screens; authoritative validation and calculations remain on the backend. This keeps the Flutter code compatible with a later iOS target while leaving Android-specific network/security configuration under `mobile/android`.

Sensitive local keys owned by the MVP are:

| Key | Content and lifecycle |
|---|---|
| `sensitive.onboarding_draft.v1` | Serialized unfinished draft, including its client request UUID and local consent selection; expires 30 days after update and corrupt/expired data is removed on restore |
| `sensitive.latest_assessment.v1` | Minimal latest-assessment summary and `cached_at`; marked stale after 24 hours but remains viewable with a warning until replaced/cleared/history/profile deletion |
| `sensitive.current_profile_id.v1` | Reserved development context; currently not written |
| `sensitive.consent_state.v1` | Reserved offline-display state; currently not written |

These keys use the declared `flutter_secure_storage: ^10.3.1` dependency and its Android v10 default Keystore-backed RSA-OAEP/AES-GCM path; the Android options retain the library defaults `resetOnError: true` and `migrateOnAlgorithmChange: true`. If protected local data becomes unrecoverable, the store can reset it rather than falling back to plaintext; the app does not reconstruct an unfinished onboarding draft from backend data. The Android minimum SDK is 24. `SharedPreferences` stores only `ui.theme_mode`. The app's clear-data operation deletes only its four owned sensitive keys. Android backup is disabled in the application manifest (`allowBackup=false`, `fullBackupContent=false`). The app has no camera, microphone, location or contacts permission. The iOS option is prepared with `first_unlock_this_device`, but an iOS release is outside MVP scope and needs platform review/testing.

Release Android configuration denies cleartext. At runtime HTTP is accepted only when `APP_ENV=development`, `ALLOW_INSECURE_LOCAL_HTTP=true`, and the host is localhost, loopback, `10.0.2.2` or a private IPv4 address. Staging/production require HTTPS. There is no TLS bypass or body-logging interceptor.

### FastAPI modular monolith

The backend groups cohesive code into:

- `core`: environment validation, branding, errors, safe logging, runtime security and current-profile resolution;
- `database`: one SQLAlchemy metadata/session boundary and Alembic integration;
- `profiles`: current profile, measurements, activity/sport, goal, restrictions and screening;
- `privacy`: processing-purpose registry, versioned consent, export, history/profile deletion and minimal action/deletion records;
- `reference_data`: versioned scientific reference sets/values and application rule sets;
- `nutrition_assessment`: assessment API/service/repository plus the pure calculation engine;
- `foods`: profile-owned foods, nutrient provenance, measures and barcode import; and
- `recipes`: profile-owned recipes, ordered Food references and on-demand nutrient aggregation.
- `recipe_target_comparison`: pure decimal comparison engine plus an on-demand adapter joining current Recipe Core values to one immutable assessment; no persistence or external I/O.

Routes deal with HTTP schemas and status codes. Services implement use cases and transaction boundaries. Repositories express persistence queries. This separation is deliberately lightweight: there is no interface for every class and no generic plugin architecture.

### Nutrition Engine

The engine receives immutable typed input and a calculation timestamp/reference context, and returns immutable typed results. It:

- uses `Decimal` and rejects non-finite input;
- has no FastAPI, Flutter, SQLAlchemy, database or network dependency;
- stores no hidden mutable state;
- does not log profile content or call an LLM;
- keeps raw values unrounded and isolates German display rounding; and
- attaches method IDs, inputs, source metadata, application rule IDs, limitations and confidence types.

The application service is the adapter: it loads the current persisted profile and active reference/rule-set rows, checks consent, builds engine input, invokes the engine, and persists the result transactionally. The current engine instance constructs immutable rule/reference objects from checked-in versioned seed JSON, not from a network or database call. Before persistence, the service compares every engine result identifier/version with the active database rows and fails closed on a mismatch; the assessment then stores their foreign keys and version strings. The engine never performs its own network or database fetch.

Backend ownership of calculations prevents divergent Android/iOS/web formula copies, makes source/rule upgrades auditable, and lets each client display identical historical results. It also means the MVP cannot calculate a new assessment offline.

## Request path

```text
Flutter action
  -> local validation / duplicate-submit guard
  -> Dio JSON body
  -> FastAPI request ID + sanitized logging/error boundary
  -> Pydantic validation
  -> current-profile dependency
  -> route
  -> service (authorization/consent/use-case checks)
  -> engine and/or repository
  -> SQLAlchemy transaction
  -> typed JSON or uniform error envelope
  -> controller state -> German UI
```

Sensitive values never belong in query parameters. Validation happens on both sides, but backend validation is authoritative. An outer application request boundary terminates unexpected downstream exception propagation and returns a generic German error with a random request ID; bodies and exception values are neither serialized into the response nor written by the structured request logger. Unmatched requests use the constant log endpoint `/{unmatched}` rather than the raw path. The Compose Uvicorn command disables its separate access log so that the allowlisted application log is the request log for this deployment.

## Development identity boundary

The repository uses a fixed UUID configured by `DEVELOPMENT_PROFILE_ID` and resolved through `resolve_current_profile_id`. It is intentionally labeled development-only and is **not authentication**. Profile-scoped routes—including export and deletion—depend on that resolver, so application code has one replacement seam.

Settings treat `local`, `development` and `test` as local environments. Staging/production startup rejects:

- the development resolver;
- HTTP public API configuration or insecure-local-HTTP allowance;
- wildcard CORS; and
- recognized development database hosts/credentials.

This fail-closed configuration is useful defense in depth but does not implement production identity. An exposed service with the development resolver would allow anyone who can reach it to act as the one configured profile. Public release therefore remains blocked on real authentication, object authorization, secure tokens, re-authentication for export/deletion, recovery safeguards, enumeration resistance and rate limiting.

## Persistence model

PostgreSQL is the authoritative store. Normal columns serve frequently queried fields; JSON/JSONB is used where immutable snapshots and extensible calculation metadata benefit.

```text
Profile
  |-- Measurements
  |-- ActivityProfile -- SportActivities
  |-- NutritionGoal
  |-- DietaryRestrictions
  |-- HealthScreening
  |-- ConsentRecords
  `-- Assessments
        |-- AssessmentMetrics
        `-- SafetyFlags

ReferenceSet -- ReferenceValues
ApplicationRuleSet
ProcessingPurpose
PrivacyAction / DeletionRecord (no health-data copy)
DailyMealPlan -- Meals -- MealEntries --> current Recipe/Food sources
      `-- optional immutable Assessment target reference
```

An assessment row references the concrete scientific/reference and application-rule rows, and also stores their identifiers/versions with engine version, calculation time, supported-scope status and summary. Metric rows preserve raw/lower/upper values, display value, unit, method, German explanation/limitation, calculation inputs, source metadata, application-rule identifier and confidence type.

The database uniqueness constraint on `(profile_id, client_request_id)` makes assessment submission idempotent per profile. It prevents duplicate rows when a mobile retry follows a timeout; it is not a substitute for the client-side loading guard.

## Assessment immutability

At creation time the service copies the relevant current profile state into `input_snapshot`. Subsequent profile edits update only current profile tables. A new assessment creates a new snapshot; it does not update the previous one.

Old assessments are returned from stored results, not silently recalculated under a new formula/reference/rule version. Updating seed data creates/supersedes a versioned set while referenced old sets remain available. This is why foreign keys from assessments to source/rule sets restrict deletion.

## Consent boundary

The app's consent checkbox starts false and submits the exact text version (`privacy_consent_de_mvp_v1`) with purpose `nutrition_assessment_calculation`. FastAPI stores versioned `ConsentRecord`s containing purpose, version, status, grant/withdrawal time and source. Repeating a grant while the same profile/purpose/text-version grant is active returns that record without adding another record or `consent_granted` action. A partial unique database index enforces at most one active grant for that tuple.

Before calculation, the service requires an active record for the calculation purpose **and current configured text version**. Withdrawing an owned record revokes every active row for that profile, purpose and text version with one withdrawal timestamp, including legacy duplicate rows; repeating the withdrawal makes no further change. Only `nutrition_assessment_calculation` is technically consent-gated; profile storage and history are machine-registered as required operations with `consent_required = false`, pending a qualified decision on their Article 6/9 bases and whether separate consent is needed. Withdrawal is server-side and blocks new assessments; it does not erase old data. Export, history deletion and complete-profile deletion are independent controls. The canonical German wording and legal basis are drafts requiring professional review; technical enforcement does not prove legally valid consent.

## Transaction boundaries

The service owns commits/rollbacks for multi-record use cases:

- replacing a profile subsection and its children;
- granting/withdrawing consent;
- creating an assessment, its metrics and safety flags;
- deleting assessment history and dependent rows; and
- deleting the complete profile graph and writing only any designed non-sensitive confirmation.

A failed use case rolls back rather than returning a partial success. Database cascades support ownership cleanup, but service tests must verify the complete graph whenever schema relations change.

## Privacy architecture

The primary flow and trust boundaries are detailed in [privacy/privacy_architecture.md](privacy/privacy_architecture.md). Architectural constraints include:

- collect no name, address, phone, exact location, employer, advertising ID or device fingerprint;
- no analytics, advertising, session replay, third-party crash body capture or social SDK;
- no sensitive SharedPreferences, URL parameters, logs, fixtures or seeds;
- encrypted minimal local storage and explicit cache/draft controls;
- HTTPS outside explicit local development and restrictive production CORS;
- profile-scoped JSON export only after user action;
- transactional active-data deletion plus local purge; and
- no claim of production backups, field encryption, hosting compliance or third-country transfer.

## Reference data versus application rules

Scientific data and product policy are separately versioned:

- **reference set:** sourced values/formulas and provenance such as DGE/ÖGE tables or Mifflin–St Jeor; and
- **application rule set:** goal percentages, PAL midpoint/sport mapping, selection within a sports-protein range, warnings, validation and display rounding.

The API and report expose both. A product rule must never be labeled a DGE/ÖGE reference value. Missing scientific values remain unavailable rather than falling back to invented or U.S. values.

## Daily planning orchestration

`app.modules.daily_meal_planning` follows router → service → repository/engine. The service owns
authorization, source loading and transaction boundaries; it calls Food Core conversion, Recipe
Core calculation, immutable target extraction and canonical unit conversion. The pure Decimal
aggregation engine receives typed values and never queries the database. Preview uses this same
path without persistence. The partial database index on owner/date enforces one active plan.

Flutter adds only form state and presentation. Authoritative nutrient totals and comparisons come
from FastAPI. Sensitive unsaved structure uses the shared encrypted `SensitiveStore`, not
SharedPreferences.

## Future integration

Future foods, recipes, meal plans, pantry and shopping-list capabilities should be backend modules in the same monolith/database. They consume a selected immutable assessment through an application service; they do not reach into its tables or copy engine code. A food-composition dataset has independent provenance/licensing from target reference values.

Real authentication replaces the current-profile dependency without changing calculation services. iOS reuses Flutter features/API contracts and the Keychain-compatible secure-store abstraction. An optional web dashboard would be another API client and requires its own browser-session, CORS/CSRF, storage/TDDDG and privacy design. Details are in [future_modules.md](future_modules.md).

## Production blockers

The implemented repository is suitable for local development with synthetic data. It is not a production security or compliance architecture. Before public release, complete at least:

- qualified regulatory, scientific, privacy/consent/legal-basis and DPIA review;
- real authentication/authorization and high-impact re-authentication;
- production hosting, TLS-to-database, encryption-at-rest/backups, secrets and least-privilege roles;
- administrator MFA/accounts/access review and incident organization;
- processor and third-country transfer review;
- backup restore plus deletion-reapplication tests;
- production logging/monitoring without payloads, patch management and penetration testing; and
- App Store/Play declarations and replacement of `com.example.nutrition_companion`.

The authoritative release gate is [privacy/production_privacy_checklist.md](privacy/production_privacy_checklist.md).
# Food Core module

`app.modules.foods` is a modular-monolith sibling of profiles, privacy and nutrition assessment. Router → service → repository separates HTTP, domain validation/conversions/quality, and SQLAlchemy access. The code nutrient catalog is authoritative; persisted foods reference stable codes and use `NUMERIC`/`Decimal` throughout.
# Purchase-to-Pantry-Abhängigkeit

`Purchase to Pantry → Shopping List Core → Pantry Core → Food Core` beschreibt die fachliche Orchestrierung: Das Übergabemodul verwendet die öffentlichen Normalisierungs- und Bestandsoperationen, während Shopping List, Pantry und Food Core nicht von ihm abhängen. Shopping List bleibt Quelle der Kaufabsicht, Pantry Quelle des Bestands. Abhaken mutiert Pantry nicht.
