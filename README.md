# Nutrition Companion

Der Funktionsumfang enthält einen ausdrücklich bestätigten Vorratsabgleich für Verzehreinträge.
Er erzeugt beim Erfassen oder Finalisieren niemals automatisch Bestandsbewegungen. Details:
[Vorratsabgleich für Verzehrdaten](docs/pantry_consumption_reconciliation.md).

Enthält ein datenschutzorientiertes [Progress Tracking](docs/progress_tracking_core.md) für manuelle Messungen, transparente Trends und explizite Ziele.

Meal planning supports a fast deterministic greedy draft and an optional local-backend OR-Tools
CP-SAT optimizer. Both produce review-only drafts and require explicit application.

Pantry-aware Shopping gleicht Rezept-, Tages- und Wochenbedarf ausdrücklich mit aktuellem Vorrat
und offenen Einkaufslisten ab, bevor genau eine Zielliste aktualisiert wird. Bestände werden nicht
reserviert oder verändert; siehe [Pantry-aware Shopping](docs/pantry_aware_shopping.md).

Rezepte zeigen ihre aktuelle Verfügbarkeit aus aktiven Vorratslosen, einschließlich Fehlmengen und
maximal möglicher Portionen. Die Berechnung verändert oder reserviert keinen Bestand. Details:
[Pantry Recipe Availability](docs/pantry_recipe_availability.md).

Purchase to Pantry ermöglicht die ausdrücklich bestätigte, nachvollziehbare Übernahme gekaufter Einkaufslistenartikel in den Vorrat. Abhaken allein verändert keinen Bestand; Details stehen in `docs/purchase_to_pantry.md`.

**Vorrat** provides manual Pantry Core inventory with storage locations, separate stock
lots, decimal-safe quantities, date information, traceable movements, and availability
grouping. See [Pantry Core](docs/pantry_core.md).

The Android application includes manual ISO-week planning as a derived overview of
Daily Meal Planning. Open **Wochenplan** to review Monday through Sunday, open or create
daily plans, copy days, transfer meals, and inspect weekly totals and target coverage.
See [Weekly Meal Planning](docs/weekly_meal_planning.md).

Daily Meal Planning kombiniert Rezepte und Lebensmittel manuell zu Mahlzeiten eines lokalen
Kalendertags, berechnet Tageswerte und vergleicht sie neutral mit einem ausgewählten unveränderlichen
Assessment. Es ist keine Verzehrserfassung und erzeugt weder Empfehlungen noch Scores. Siehe
[docs/daily_meal_planning.md](docs/daily_meal_planning.md).

Nutrition Companion is an Android-first, German-language nutrition-assessment MVP for
generally healthy adults. It collects a deliberately limited profile, creates a transparent
and reproducible assessment on the backend, and explains every returned result. It is not a
diagnostic or treatment product and is not presented as a medical device.

The repository contains one Flutter client and one FastAPI modular monolith backed by
PostgreSQL. The authoritative Nutrition Engine is pure Python: Flutter contains presentation
and form validation, but no second copy of the professional calculation rules.

## Repository map

```text
.
├── backend/                  FastAPI, SQLAlchemy, Alembic and pure Nutrition Engine
│   ├── alembic/              explicit initial migration
│   ├── app/core/             branding, configuration, errors, logging, security boundary
│   ├── app/database/         shared SQLAlchemy metadata and sessions
│   ├── app/modules/          profiles, privacy, reference data and assessment modules
│   ├── app/seed/             versioned checked-in reference/rule data
│   └── tests/                engine, API, privacy and transaction tests
├── mobile/                   Flutter app with Android and future-compatible iOS projects
│   ├── lib/core/             API, configuration, formatting and secure storage
│   ├── lib/features/         onboarding, report, history, profile, privacy and settings
│   └── test/                 unit and widget tests
├── docs/                     architecture, API, scientific and privacy documentation
├── docker-compose.yml        local FastAPI/PostgreSQL stack
└── .env.example              development-only configuration template
```

See [architecture](docs/architecture.md), [API](docs/api.md),
[nutrition methodology](docs/nutrition_methodology.md), and
[privacy architecture](docs/privacy/privacy_architecture.md) for the detailed design.

## Local backend and database

Prerequisites are Docker Engine with Compose v2 and ports 8000/5432 available. The bundled
credentials and fixed profile UUID are conspicuous development defaults; do not expose or
reuse them in staging or production.

```sh
cp .env.example .env
docker compose up --build
```

The API container waits for PostgreSQL, runs `alembic upgrade head`, performs the idempotent
seed, and starts Uvicorn. In another terminal:

```sh
curl http://localhost:8000/health
```

OpenAPI is available locally at `http://localhost:8000/docs`. Useful lifecycle commands are:

```sh
docker compose logs -f api
docker compose exec api alembic current
docker compose exec api python -m app.modules.reference_data.seed
docker compose down
```

`docker compose down` keeps the named PostgreSQL volume. Do not add `--volumes` unless the
local database is intentionally being destroyed.

### Backend without Docker

Python 3.12 and a reachable PostgreSQL database are required. From the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -e './backend[dev]'
cp .env.example .env
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.modules.reference_data.seed
../.venv/bin/uvicorn app.main:app --reload --no-access-log
```

When running outside Compose, change `DATABASE_URL` from host `db` to `localhost` (or another
actual PostgreSQL host). Never put health/profile values in environment variables, URLs or
query parameters.

## Android development

Install Flutter 3.44 stable (Dart 3.12), a compatible Android SDK, Java 17 or newer, and an
Android API 24+ emulator/device. Then run:

```sh
flutter doctor
flutter doctor --android-licenses
cd mobile
flutter pub get
flutter devices
```

An Android emulator reaches the host through `10.0.2.2`:

```sh
flutter run \
  --dart-define=APP_ENV=development \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000 \
  --dart-define=ALLOW_INSECURE_LOCAL_HTTP=true
```

For a USB-connected physical Android device, keep the backend bound to loopback and forward
the API port through ADB:

```sh
adb devices
adb -s <device-id> reverse tcp:8000 tcp:8000
flutter run -d <device-id> \
  --dart-define=APP_ENV=development \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000 \
  --dart-define=ALLOW_INSECURE_LOCAL_HTTP=true
```

The alternative private-LAN setup requires deliberately setting `API_BIND_ADDRESS=0.0.0.0`,
restricting firewall access and using the host's private IPv4 address in `API_BASE_URL`.
PostgreSQL remains loopback-only. Plain HTTP is accepted only in development with the explicit
opt-in and a loopback, emulator or private-network host. Staging and production require HTTPS.

The current development identifier is `com.example.nutrition_companion`. **It must be
replaced before publication.** Update Android `namespace`/`applicationId`, the Kotlin package
and directory, `AppBranding.packageIdentifier`, and the iOS bundle identifiers. Product copy
is centralized separately from nutrition domain names, database tables and engine identifiers;
do not rename those domain identifiers as part of branding.

The release Android variant is intentionally unsigned. Add a protected release keystore and
CI signing configuration before distribution, without committing secrets.

## Quality commands

```sh
cd backend
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv/bin/pytest -q
../.venv/bin/ruff check .
../.venv/bin/ruff format --check .
../.venv/bin/mypy app

cd ../mobile
flutter analyze
flutter test
flutter build apk --debug
```

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` makes the test run independent of unrelated globally
installed pytest plugins. It does not disable this project's own fixtures or tests.

Verification on 2026-07-29: all 118 backend tests and all 44 mobile tests passed, together with
Ruff, Ruff formatting, strict mypy, Dart formatting and Flutter static analysis. The Android
debug APK also built successfully. Use the commands above to reproduce the checks. iOS
compilation was not attempted because the development host runs Linux.

For a clean migration/seed check against a disposable database, set `DATABASE_URL` explicitly,
run `alembic upgrade head`, and run the seed command twice; the second seed must insert no new
reference/rule rows. Never point a destructive test at production data.

## Scientific and rule versions

The checked-in scientific subset is reference set `dge_oege_v3_mvp_2026_05`, version
`3rd-edition-2025_erratum-2026-05_subset-v1`. It contains the verified MVP subset of DGE/ÖGE
micronutrient values plus documented hydration metadata; provenance and access dates are in
[nutrition sources](docs/nutrition_sources.md). It is intentionally incomplete. Missing age,
pregnancy/breastfeeding, physiological reference-table category, or nutrient combinations are
returned as unavailable, never filled with invented or unrelated values.

Product policy is separately versioned as application-rule set
`nutrition_companion_mvp_v1`, version `v1`. It contains PAL/sport mapping, goal adjustment,
macro/protein selection, validation, warnings and display rules. Product rules are not labeled
as official DGE/ÖGE values. The engine version is `nutrition_engine_v1`.

## Data and privacy boundaries

PostgreSQL is authoritative for the profile UUID, birth date and physiological category,
anthropometrics, optional measurements, activity/sport, goal, dietary restrictions, health
screening, versioned consent, immutable assessments, Food/Recipe Core and manual daily plans. Minimal
privacy/deletion action records intentionally contain no copied health values.

On-device sensitive state is limited to unfinished onboarding/daily-plan drafts (30-day expiry),
the assessment idempotency UUID, and a minimal latest-assessment cache. These use
`flutter_secure_storage` with Android Keystore-backed encryption. SharedPreferences stores only
`ui.theme_mode`; Android backup is disabled. A requested JSON export exists only in the app
temporary directory while it is handed to the system share sheet and is then deleted.

The assessment-consent checkbox starts unselected. A valid record for purpose
`nutrition_assessment_calculation` and exact text version `privacy_consent_de_mvp_v1` is required
for a new calculation. Refusal prevents calculation. Withdrawal blocks new calculations but
does not silently erase old assessments; export, history deletion and full-profile deletion are
separate controls. History/profile deletion also clears the corresponding owned local cache or
all owned sensitive keys in the app.

The local MVP includes no analytics, advertising, tracking, hosted AI, external crash reporting,
social SDK or other configured recipient. Normal network traffic is only between the app and the
configured API, and between that API and PostgreSQL. Any production host, processor, monitoring,
support or distribution service changes that statement and requires an updated processor and
third-country-transfer review.

## Public-release blockers

This is development infrastructure, not production security. The fixed current-profile resolver
is explicitly not authentication and is rejected by non-local configuration. Before public
release, at minimum provide real authentication/object authorization and re-authentication for
export/deletion; production TLS, secrets, database roles, encryption, backup/restore and deletion
reapplication; rate limits and privacy-safe monitoring; dependency/security testing; protected
signing; Play/iOS declarations; qualified scientific/regulatory review; and professional review
of legal bases, consent text, notices, retention, DPIA and processor/transfer arrangements.

The full release gate is [production privacy checklist](docs/privacy/production_privacy_checklist.md),
and known reference gaps are listed in
[reference data incomplete](docs/reference_data_incomplete.md).

The MVP implements technical and architectural measures designed to support German and European
data-protection requirements. Legal, organizational and production compliance must be reviewed
before public release.
# Food Core

Die App unterstützt jetzt profilgebundene, manuell eingegebene Lebensmittel mit Nährwerten pro 100 g/ml, Suche, Qualitätsanzeige, Haushaltsmaßen sowie Archivierung und Wiederherstellung. Details und ehrliche Einschränkungen: [docs/food_core.md](docs/food_core.md).

# Verzehrerfassung

Die App trennt geplante Mahlzeiten von ausdrücklich gemeldetem tatsächlichem Verzehr. „Verzehr“
unterstützt Foods, Recipes, manuelle Einträge, Planabgleich, historische Nährwertsnapshots,
Tagesabschluss und Wochenübersichten, ohne Vorrat automatisch zu verändern. Details:
[Consumption Tracking Core](docs/consumption_tracking_core.md).
