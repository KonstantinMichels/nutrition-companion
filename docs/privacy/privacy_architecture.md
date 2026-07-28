# Privacy architecture

**Status:** Technical design and implementation record for the local MVP  
**Last reviewed:** 2026-07-28  
**Legal status:** Draft; not legal advice, a privacy notice, a record of processing activities, or evidence of compliance.

## Scope and interpretation

Nutrition Companion handles body, activity, dietary and health-screening information. Some or all of it may be data concerning health and therefore a special category of personal data under GDPR Article 9. Voluntary entry does not make the data non-sensitive.

This architecture applies four distinct labels:

- **Implemented locally:** behavior present in the repository and intended for the single-user development MVP.
- **Configured locally:** a development choice, not a production guarantee.
- **Organizational requirement:** a policy or operational control that code alone cannot provide.
- **Production blocker:** must be completed and verified before public release.

The GDPR establishes principles such as purpose limitation, data minimization, storage limitation, integrity and confidentiality (Article 5), privacy by design/default (Article 25) and risk-appropriate security (Article 32). Article 9 requires a separate condition for special-category processing in addition to an Article 6 basis. The actual Article 6 and Article 9 bases remain legal-review placeholders in this project. See the official [GDPR text](https://eur-lex.europa.eu/eli/reg/2016/679/oj), accessed 2026-07-28.

For a future German operator, the BDSG may supplement the directly applicable GDPR within its scope; this repository does not select a BDSG permission or exception. See the official [Bundesdatenschutzgesetz](https://www.gesetze-im-internet.de/bdsg_2018/), accessed 2026-07-28. The controller, establishment, employment context and actual processing must be known before qualified counsel can decide which provisions apply.

## System and trust boundaries

```text
Android application process
  |  encrypted local draft/cache (device trust boundary)
  |  REST JSON; HTTP only in explicit local development, HTTPS otherwise
  v
FastAPI modular monolith (API/service trust boundary)
  |  validation -> current-profile resolution -> consent check -> engine
  |  SQLAlchemy transaction
  v
PostgreSQL (database trust boundary)

Explicit user export -> temporary app-controlled file -> Android share sheet
Explicit deletion   -> backend transaction + local secure-store purge
```

The phone, API process, database, development workstation, future production administrators, backup system and any selected share-sheet destination are separate trust zones. A UUID is pseudonymous, not anonymous: anyone able to link it with profile or device context can still relate the record to a person.

## Data stores

### Android secure storage

The narrow local-data budget is implemented through four owned secure-storage keys:

- `sensitive.onboarding_draft.v1`: unfinished onboarding draft, client request UUID and local consent checkbox; 30-day expiry;
- `sensitive.latest_assessment.v1`: minimal latest-assessment summary plus `cached_at`; stale warning after 24 hours;
- `sensitive.consent_state.v1`: reserved for offline display, currently not written; and
- `sensitive.current_profile_id.v1`: reserved for development context, currently not written.

Sensitive values use the declared `flutter_secure_storage: ^10.3.1` dependency with its Android v10 default Keystore-backed RSA-OAEP/AES-GCM implementation; `AndroidOptions()` retains the library defaults `resetOnError: true` and `migrateOnAlgorithmChange: true`. No key is hard-coded or committed. The app requires Android SDK 24 or later. Android describes Keystore key material as harder to extract and non-exportable from the app/device in normal operation; this is a protection mechanism, not a guarantee against a compromised, unlocked or rooted device. See [Android Keystore](https://developer.android.com/privacy-and-security/keystore), accessed 2026-07-28.

SharedPreferences currently stores only the non-sensitive `ui.theme_mode` presentation preference. It must not contain body/health data, assessment results, consent records, access-enabling identifiers or secrets; any future preference needs a data-inventory review.

**Key invalidation behavior:** if a key becomes unavailable after device/security changes, storage corruption or app reinstallation, the configured secure-store reset behavior can discard the unreadable protected payload. The app then allows a fresh server retrieval or fresh onboarding; it does not silently reconstruct an unfinished draft from backend data. It must not fall back to plaintext or embed a recovery key.

**Backup behavior:** the Android manifest sets `android:allowBackup="false"` and `android:fullBackupContent="false"`, so the MVP intends to exclude app data from Android backup/device transfer. Android's backup guidance recommends excluding particularly sensitive data or requiring end-to-end-encrypted backup when exclusion is impossible. See [Android backup security recommendations](https://developer.android.com/privacy-and-security/risks/backup-best-practices), accessed 2026-07-28. OEM/API behavior and the manifest/package configuration still require device-matrix verification before release.

### Backend database

PostgreSQL is the authoritative store for current profile sections, measurements, activity, goals, restrictions, screening, versioned consent records, immutable assessments and their version metadata. JSONB is appropriate for immutable input/calculation snapshots; normally queried attributes remain relational.

Local Docker volumes are development storage and are not an approved production control. Compose publishes the PostgreSQL and API host ports on `127.0.0.1` by default; the API's `0.0.0.0` bind is inside the container. Physical-device/LAN access therefore requires an intentional `API_BIND_ADDRESS` override and host-firewall review. Environment-based development credentials are intentionally unsuitable for public deployment. No real user health data belongs in seeds, fixtures or automated tests.

### Logs

Permitted structured fields are limited to request/correlation ID, endpoint template, method, response status, duration, technical error code, environment and timestamp. The current middleware emits only timestamp, random request ID, route template or the constant `/{unmatched}`, method, status and duration. It never substitutes the raw unmatched/error path. Request/response bodies, profile UUIDs, body/health values, consent text, result details, tokens and keys are prohibited. A short-lived correlation ID is generated independently of the profile. The Compose command disables Uvicorn's separate access log; production ingress/proxy/platform logs remain an explicit review item.

### Temporary export

Export is created only after an explicit user action. Before collecting privacy actions, the service writes and flushes an `export_requested` action, so the same export includes its own request action. The JSON contains data associated with the current profile, complete assessment data, consent records and minimal privacy actions, but not secrets or unrelated server metadata. `Decimal` values are encoded exactly as JSON strings, including in nested snapshots/metadata. If the mobile app creates a temporary file, it remains sensitive until deleted. The app opens the platform share sheet; the user-selected destination becomes a separate recipient outside Nutrition Companion's control. There is no automatic cloud upload.

## Transport and API boundary

- Sensitive data is carried in JSON request bodies, never query parameters or public URLs.
- Plain HTTP is allowed only for explicitly configured local development (for example, emulator to `10.0.2.2`).
- Non-local/production configuration must require HTTPS and normal certificate validation.
- TLS validation must never be disabled. Certificate pinning is intentionally absent until a safe rotation and recovery plan exists.
- Production CORS must be an explicit allowlist; wildcard origins are prohibited.
- Validation, unmatched/unsupported routes and unexpected errors receive sanitized envelopes. The outer application request boundary consumes unexpected downstream exceptions without serializing them or propagating their values to Uvicorn.

Android Network Security Configuration supports cleartext opt-out and narrowly scoped debug exceptions; Android warns that cleartext permits observation and manipulation in transit. See [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config) and [cleartext communication risk](https://developer.android.com/privacy-and-security/risks/cleartext-communications), accessed 2026-07-28.

## Consent boundary

Before the first assessment, the user must affirm an unselected German consent control. The grant endpoint accepts only the configured purpose and exact consent-text version (`privacy_consent_de_mvp_v1`); the backend then verifies an active record for both the required assessment purpose and current configured version. Repeating the same active grant returns the existing record without another grant action, while a partial unique database index permits at most one active row for each profile/purpose/text-version tuple. Withdrawing an owned record revokes every active matching row with one timestamp, including legacy duplicates, and repeating it is idempotent. This is the only purpose technically consent-gated in `mvp_v1`. Profile storage and history are registered as required operations with `consent_required = false`; qualified review must decide their legal bases and whether separate consent is needed. A withdrawal stops new assessments. It does not silently delete historical data; export and deletion remain separate actions.

Consent is a technical state in the MVP. Whether the proposed wording is freely given, specific, informed, unambiguous and an appropriate Article 6/Article 9 legal basis must be decided by qualified counsel before release. The controller must also define how a withdrawal affects each processing operation, retention obligation and backup.

## Current-profile and authorization boundary

The local MVP has a configured UUID-based development profile resolved through one backend dependency. This is **not authentication**. It can separate data structurally but cannot establish who is making a request. Export and deletion being routed through that dependency does not make them safe for an exposed service.

A production process must refuse to start with the development resolver or development credentials. Public release is blocked until real authentication and object-level authorization are implemented and tested, including re-authentication for export/deletion, secure token lifecycle, account recovery protection, enumeration resistance and rate limiting.

## Calculation and immutability boundary

FastAPI performs authoritative validation, supported-scope screening and consent verification before invoking the deterministic Nutrition Engine. Database-backed route handlers are synchronous and therefore execute through FastAPI's worker thread pool rather than performing blocking SQLAlchemy work directly on the event loop. The engine has no HTTP, database, logging or network access. It receives a typed snapshot and returns typed calculations and safety flags.

Each assessment stores its immutable input, formula IDs, reference/rule-set versions, selected PAL/manual overrides, explanations, warnings and calculation time. Editing the profile does not alter an old assessment; a new assessment is required. This supports transparency and reproducibility and avoids covert reuse under a new rule version.

## Export and deletion paths

### Export

```text
explicit user action -> current-profile dependency -> export service
-> add/flush export_requested action -> profile-scoped query including that action
-> exact-string Decimal JSON response -> temporary app file -> user share choice
```

Production requires authentication, authorization, re-authentication, abuse controls, secure temporary-file cleanup and a reviewed data-subject-request process.

### Assessment-history deletion

The backend deletes assessments and dependent metrics/flags in one transaction while retaining the current profile and consent state. The app then deletes any cached latest assessment. Failure must not be presented as success.

### Complete-profile deletion

The backend transaction deletes profile-related current data, measurements, activity, goals, restrictions, screening, assessments, metrics, safety flags and consent data according to the local-MVP deletion concept. Only a minimal non-sensitive confirmation/action record may remain where implemented. On confirmed server success, the app purges the onboarding draft, result cache and local current-profile context.

Production backup expiry and deletion reapplication are documented requirements, not implemented infrastructure.

## Administrative access and production controls

The repository does not deploy a production administration plane. Before public operation, the operator must implement and verify:

- individual administrator accounts, MFA and least privilege;
- separate migration/runtime/database roles where practical;
- just-in-time or approved support access and access review;
- EU/EEA hosting and subprocessors selected through due diligence;
- TLS to PostgreSQL, encrypted volumes and encrypted backups;
- managed secrets, rotation and revocation;
- security/access logs that exclude sensitive payloads;
- tested restore and deletion-reapplication procedures;
- separate development, test and production data/credentials; and
- incident response, vulnerability management and independent security testing.

Custom field-level encryption is deliberately not claimed. It should be introduced only with a documented threat model, searchable-field implications, key ownership, rotation, recovery and deletion design.

## Device access and TDDDG

The native MVP uses device storage only for the requested app functionality described above and requests no camera, microphone, location or contacts permission. It does not add a generic cookie banner. German TDDDG § 25 distinguishes consent from storage/access that is strictly necessary to provide a service expressly requested by the user; the legal characterization of each store remains a release-review question. See [TDDDG § 25](https://www.gesetze-im-internet.de/ttdsg/__25.html), accessed 2026-07-28.

Any future camera/barcode/media/social import requires just-in-time permission, a pre-prompt purpose explanation, graceful refusal, no upload without explicit action, and a separate privacy/security review.

## Production release blockers

See [production_privacy_checklist.md](production_privacy_checklist.md). In particular, this local architecture does not provide an approved legal basis, controller identity/privacy notice, processor contracts, production authentication, hosting, administrator controls, backup operation, DPIA decision, deletion verification or incident organization.
