# Personal-data flows

Progress-Eingabe → lokale FastAPI-Instanz → profilgebundene PostgreSQL-Beobachtung → flüchtige Trendberechnung → chartfertige Antwort. Es gibt keinen externen Empfänger und keine Analytics.

Pantry inputs flow from the Android form to the first-party FastAPI inventory service
and PostgreSQL. Food Core supplies local conversion metadata. No external service,
analytics recipient, or third-country transfer receives Pantry data.

For Weekly Meal Planning the Android client sends a local anchor date to the first-party
API. The API batch-loads profile-owned daily source records, derives the response in
memory, and returns it to the client. No external recipient or third-country transfer is
introduced.

**Status:** Local-MVP technical flow and production requirements  
**Last reviewed:** 2026-07-28

This document is not a legal approval. Field-level coverage is in [data_inventory.md](data_inventory.md), purposes in [processing_purposes.md](processing_purposes.md), and deletion behavior in [deletion_concept.md](deletion_concept.md).

## Primary assessment flow

```text
User input
  -> Flutter form state (memory)
  -> encrypted mobile onboarding draft
  -> REST JSON request body
  -> TLS in non-local environments
  -> FastAPI schema and scope validation
  -> development current-profile resolver (local MVP only)
  -> synchronous DB-backed route in FastAPI worker thread pool
  -> active-consent verification
  -> deterministic Nutrition Engine (in process, no network/DB access)
  -> transactional PostgreSQL writes
       current profile sections
       immutable assessment input snapshot
       metrics, explanations, source/rule versions and safety flags
  -> sanitized REST JSON response
  -> rendered report
  -> encrypted minimal latest-assessment cache
```

In explicitly configured local development, emulator/device traffic may use HTTP. Such traffic is observable and modifiable on the network and must contain synthetic development data only. Production must reject HTTP configuration and use verified TLS.

## Boundary table

| Crossing | Data | Protection in local MVP | Production requirement |
|---|---|---|---|
| User -> Flutter | Entered body, goal, activity, diet, screening and consent data | App process and local validation | Screen privacy/usability review; compromised-device limitations disclosed |
| Flutter memory -> local storage | Draft, minimal cache, local context | Secure-storage abstraction; SharedPreferences excluded for sensitive data | Verify package/platform configuration, backup exclusions and key-invalidation behavior |
| Device -> API | Profile and assessment request bodies | Dio; configurable local HTTP | HTTPS only, normal certificate validation, edge protections; no sensitive query strings |
| API -> service | Typed values and current profile context | Pydantic validation; request IDs separated from profile ID; synchronous DB-backed handlers dispatched to FastAPI's worker thread pool | Authenticated/authorized principal; rate limiting |
| Service -> engine | Immutable typed calculation input | In-process call; no I/O in engine | Dependency/version integrity and calculation-change governance |
| Service -> PostgreSQL | Current records, snapshots, metrics and consent | SQLAlchemy transaction, development credentials | TLS, least-privilege roles, encrypted volumes/backups and monitored access |
| API -> device | Full report/history/export | Typed JSON; body not logged | HTTPS, authorization, re-authentication for high-impact actions |
| Device -> share target | Explicit export file | Android share sheet only after user action | Explain recipient change; securely clean temporary file; test content URI permissions |

## Profile edit and new assessment

```text
edit current profile -> validate -> persist current rows
                                     |
                                     +-- old assessment unchanged

explicit "new assessment" -> copy current state into new immutable snapshot
                           -> calculate under then-current reference/rule version
                           -> append history item
```

There is no automatic recalculation of history. This prevents a reference/rule update or profile edit from silently changing a result the user previously saw.

## Consent flows

### Grant

```text
unselected checkbox -> user affirmatively selects -> submit exact purpose + text version
-> backend returns the matching active record if one exists
   or writes one timestamped ConsentRecord plus one grant action
-> partial unique active-row index enforces one active record per profile/purpose/version
-> required purpose becomes active
```

### Withdraw

```text
explicit withdrawal -> backend finds all active rows for the selected record's
   purpose + text version and marks them withdrawn with one timestamp
-> new assessment requests fail with a machine-readable consent error
-> stored profile/history remain until a separate deletion request
```

Duplicate active legacy rows are closed together; a repeated withdrawal performs no further write. Refusal or withdrawal must not be logged as health content. Consent wording and legal basis require professional review before release.

## Export flow

```text
user taps export
-> current-profile scoped GET
-> backend adds and flushes export_requested
-> backend assembles understandable JSON from all associated stores,
   including that export action
-> every Decimal is encoded exactly as a JSON string, including nested values
-> response excludes credentials/secrets and unrelated infrastructure metadata
-> app creates temporary protected file
-> user chooses a destination in Android share sheet
-> app removes its temporary copy according to the local cleanup policy
```

After the user selects a third-party app, that recipient's processing is outside this system boundary. No destination is preselected and no automatic cloud upload occurs.

## Deletion flows

### History only

```text
explicit confirmation -> profile-scoped DELETE assessments
-> one database transaction removes assessments, metrics and safety flags
-> success response contains no body/health data
-> app removes cached assessment
```

### Complete profile

```text
explicit high-friction confirmation -> profile-scoped DELETE profile/local-profile-data
-> one database transaction removes the profile graph and applicable consent rows
-> minimal non-sensitive confirmation where implemented
-> app purges draft, cache and local profile context
```

Production backups may retain encrypted copies only until ordinary expiry. A restore must reapply deletions before data becomes active. That workflow is a production requirement, not an implemented local capability.

## Technical telemetry flow

```text
request -> random short-lived request ID -> route template or /{unmatched}
        -> status/duration/error code
        -> structured application log -> short configured retention -> deletion
```

The Compose Uvicorn access log is disabled so this allowlisted application log is the request-log flow for that deployment. The outer application middleware converts unexpected downstream exceptions to a generic envelope without propagating exception values. There are no analytics, advertising, session replay, third-party crash reporting or remote body-logging flows in the MVP. Persistent profile UUIDs, raw unmatched paths and payloads are prohibited in logs. Production ingress/proxy/platform logging must be inventoried and reviewed separately.

## Prohibited flows

- Sensitive data in URL/query strings, analytics events or public links.
- Profile/request bodies in logs, traces or exception reporting.
- SharedPreferences storage of profile, health, assessment, consent or token data.
- Test/seed data copied from real people.
- Automatic export to a cloud drive or messaging service.
- Calculation calls to an LLM or external service.
- Data reuse for recipe import, marketing, research, model training or another undefined purpose.
- Third-country transfer without a documented provider and transfer review.
# Food Core

## Daily planning flow

```text
encrypted Flutter draft -> explicit preview/save -> FastAPI ownership checks
  -> current Food/Recipe Core calculation + immutable assessment targets
  -> PostgreSQL plan structure / calculated response -> Flutter display
```

Preview is memory-only. Persisted plans stay in PostgreSQL; calculated totals are not cached. No
external recipient receives plan content. Request logging records only allowlisted technical
metadata and excludes bodies, meal names/notes, targets and totals. Export reads only the current
profile graph. Complete deletion removes server plans and the app clears the encrypted draft key.

Android-App → eigene FastAPI → PostgreSQL. Lebensmitteldaten verlassen diesen lokalen/selbst betriebenen Datenfluss nicht. Der Export wird nur auf ausdrückliche Aktion erzeugt.

Beim ausdrücklich gestarteten Barcode-Scan gilt abweichend: Android-App → eigene FastAPI → Open Food Facts. Übertragen werden Barcode, technische HTTP-Metadaten und die IP-Adresse des Backendservers. Die Produktantwort wird vor dem Speichern angezeigt. Manuell eingegebene Lebensmittel und Profildaten werden nicht an Open Food Facts übertragen.

# Recipe Core

Ausgewählte profilgebundene Foods → Rezeptentwurf → eigene FastAPI → PostgreSQL. Gespeichertes Rezept und aktuelle Food-Werte → deterministische Decimal-Aggregation → App. Recipe Core hat keinen externen Netzwerkfluss. Beim Barcode-Fertiggericht wird Open Food Facts ausschließlich im getrennten Food-Vorschau-/Importfluss kontaktiert; danach wird die lokale Food-ID an einen bearbeitbaren Rezeptentwurf übergeben.

# Recipe Target Comparison

```text
eigene Rezept-ID + eigene Assessment-ID + Portionszahl
-> eigene FastAPI
-> aktuelle Recipe-Core-Berechnung + unveränderte gespeicherte Zielwerte
-> deterministischer Vergleich
-> flüchtige Flutter-Anzeige
```

Es gibt keinen externen Empfänger, keine Analyse, keinen Vergleichscache und keinen neuen persistenten Ergebnisdatensatz. Protokolliert werden weiterhin nur Route, Status, Dauer und zufällige Request-ID, nicht Rezeptname, Zielwerte oder Vergleichsantwort.
# Purchase to Pantry

Die App sendet die ausdrücklich ausgewählten Artikel zunächst zur transienten Vorschau. Erst die Bestätigung schreibt atomar Pantry-Bestände, Bewegungen und lokale Verknüpfungen. Es gibt keine externe Übertragung.

# Pantry Recipe Availability

```text
eigene Rezept-ID + Portionszahl + Anzeigeoptionen
-> eigene FastAPI -> aktuelle Recipe-Core-Zutaten + aktive Pantry-Lose
-> deterministische Decimal-Berechnung -> flüchtige Flutter-Anzeige
```

Es gibt keinen externen Empfänger, keinen Ergebnisdatensatz, keine Reservierung und keine
Bestandsbewegung. Protokolliert werden keine Rezept-, Food- oder Mengenwerte.

# Pantry-aware Shopping

```text
eigene Quelle + Optionen + Zielliste -> eigene FastAPI
-> aktuelle Quellen + Pantry + offene Listen + Handoff-Zustände
-> flüchtige Vorschau -> ausdrückliches Apply -> genau eine Zielliste + Audit
```

Andere Listen und Pantry bleiben unverändert. Logs enthalten nur Route, Status, Dauer und zufällige
Request-ID, keine Listen-, Food-, Plan- oder Mengeninhalte.

For optimization, profile-owned targets, recipes, plans, Pantry and active shopping commitments are
loaded into process memory and passed to local OR-Tools CP-SAT. No external solver or AI receives
them, no model dump is written, and only an explicitly applied compact audit persists.

## Verzehrerfassung

`Flutter → FastAPI Consumption API → Profilbesitzprüfung → Food/Recipe-Normalisierung →
historische PostgreSQL-Snapshots → abgeleitete Summen`. Es gibt keinen Pfad zu externen Diensten,
Analytics oder Werbung. Daily Plan und Assessment werden nur gelesen beziehungsweise referenziert;
Pantry und Shopping Lists werden für eine Verzehrbuchung nicht verändert.
