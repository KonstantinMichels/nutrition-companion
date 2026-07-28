# Production privacy and security checklist

**Status:** Release-blocking checklist  
**Last reviewed:** 2026-07-28

The repository is a local development MVP. Technical completion of a checkbox does not establish legal compliance. Every item below starts unresolved unless accompanied by current evidence from the actual production system and accountable approval.

## Governance and legal

- [ ] Identify the legal controller, address, contact channel, representative (if applicable), privacy lead/DPO analysis and competent supervisory authority.
- [ ] Obtain qualified German/EU legal review of every Article 6 basis and Article 9 condition by purpose.
- [ ] Approve final German privacy notice with all Articles 12–14 information, effective date and change process.
- [ ] Approve consent wording, purpose granularity, refusal, withdrawal effect, proof/retention and exact versioning.
- [ ] Approve terms of service and age/supported-user approach.
- [ ] Obtain a documented medical-device/intended-purpose and product-claims review, including store metadata and screenshots.
- [ ] Complete and sign the DPIA threshold decision; complete DPIA/prior consultation if required.
- [ ] Maintain a controller record of processing activities and map it to this purpose registry.
- [ ] Define procedures and verified identity handling for access, correction, restriction, portability/exports, objection and deletion requests.
- [ ] Assign document owners, approval dates, annual review and change triggers.

## Data and product behavior

- [ ] Reconcile [data_inventory.md](data_inventory.md) with the final schema, API models, secure-storage keys and infrastructure metadata.
- [ ] Verify every field is necessary for a defined purpose and optional fields are genuinely optional.
- [ ] Verify unsupported conditions never receive ordinary weight-change/high-protein targets and messaging makes no diagnosis.
- [ ] Obtain independent scientific review of formulas, mappings, seed provenance, missing targets, uncertainty and safety flags.
- [ ] Verify immutable assessment history and source/rule/formula version reproduction.
- [ ] Ensure reference-data updates cannot rewrite old assessments.
- [ ] Ensure no analytics, advertising, session replay, remote body logging or unrelated device access is included.
- [ ] Review any future camera/barcode/social import, food/recipe, longitudinal tracking, AI or clinician feature separately before development/release.

## Authentication and authorization

- [ ] Replace the fixed development-profile resolver with production authentication.
- [ ] Ensure production refuses to start with the development resolver or development credentials.
- [ ] Implement server-side object authorization for every read/write/export/delete operation and test cross-account isolation.
- [ ] Design secure token issuance, rotation, revocation and Android Keystore/iOS Keychain storage.
- [ ] Require appropriate re-authentication before export and destructive deletion.
- [ ] Implement rate limiting, abuse controls and account-enumeration protection.
- [ ] Review recovery/support identity proofing and prevent social-engineering takeover.

## Mobile and network

- [ ] Replace the development package identifier `com.example.nutrition_companion` before publication.
- [ ] Verify release builds deny cleartext and only development builds/config allow narrow local HTTP.
- [ ] Verify normal certificate validation; no debug CA/TLS bypass ships; document why pinning is or is not used and rotation plan if it is.
- [ ] Review `flutter_secure_storage`/equivalent current official configuration on each supported Android version and future iOS target.
- [ ] Test key invalidation/corruption, device migration, uninstall/reinstall and locked/rooted-device limitations.
- [ ] Verify sensitive secure-storage and export-temp files are excluded from backups or meet an approved encrypted-backup design.
- [ ] Test draft 30-day expiry, 24-hour cache staleness warning, clear-draft/cache and complete-profile local purge.
- [ ] Test export content URI permission is narrow and temporary file cleanup occurs after share/cancel/restart.
- [ ] Review requested Android permissions and store data-safety declaration; camera, microphone, location and contacts remain absent.
- [ ] Complete TDDDG § 25 analysis for every device-storage/access operation; do not add a generic native cookie banner.

## Hosting, database and secrets

- [ ] Select and document production hosting, database, backup, DNS/edge and support entities; prefer EU/EEA where appropriate.
- [ ] Complete vendor due diligence and Article 28 agreements; record all subprocessors and change notification.
- [ ] Complete third-country transfer review/TIA and safeguards for every transfer or remote access.
- [ ] Enforce HTTPS externally and TLS to PostgreSQL; configure restrictive CORS and network isolation.
- [ ] Use managed secrets with ownership, rotation, revocation and tested leak response.
- [ ] Use least-privilege runtime DB roles and separate migration credentials where practical.
- [ ] Encrypt storage volumes and backups; document key ownership/access/rotation.
- [ ] Separate development, test and production projects, credentials, networks and datasets.
- [ ] Prohibit real user health data in automated tests, fixtures, seeds, screenshots and support tickets.

## Administrator and operational controls

- [ ] Use individual administrator accounts, MFA and least privilege; prohibit shared production credentials.
- [ ] Establish joiner/mover/leaver access lifecycle, periodic review and emergency revocation.
- [ ] Define approved, attributable, time-limited support/database access and prohibit casual record browsing.
- [ ] Train relevant staff on sensitive-data handling, incident escalation, exports and deletion.
- [ ] Define vulnerability/patch SLAs for app, API, PostgreSQL, images, OS and dependencies.
- [ ] Produce and monitor an SBOM/dependency/container scan; resolve or accept findings with owner/expiry.
- [ ] Complete threat modeling and an independent penetration test; remediate and retest material findings.

## Logging, incidents and continuity

- [ ] Configure allowlisted production logs containing no bodies, profile UUIDs, health values, consent text, results, tokens or keys.
- [ ] Decide and enforce short log retention (14 days is provisional), access control and secure incident holds.
- [ ] Verify reverse proxy, WAF, platform, database and mobile diagnostics do not introduce sensitive logging.
- [ ] Assign incident lead, privacy/legal/security contacts and deputies; record supervisory/processor contacts.
- [ ] Exercise incident detection, credential revocation, evidence handling, notification assessment and user communication.
- [ ] Define service recovery objectives and capacity/availability controls appropriate to harm.
- [ ] Encrypt backups, restrict restore, test restoration and prove deletion reapplication before activation.

## Retention, export and deletion

- [ ] Approve every retention period and legal reason; implement monitored TTL/deletion jobs.
- [ ] Define maximum backup expiry and accurately disclose residual backup handling.
- [ ] Verify transactional history deletion covers assessments, metrics and safety flags while preserving the profile.
- [ ] Verify complete deletion covers every profile-linked table and all four owned secure-storage keys.
- [ ] Test rollback on failure, idempotency, timeout/unknown-outcome reconciliation and cross-profile resistance.
- [ ] Ensure privacy-action/deletion records contain no copies of health data and follow an approved TTL.
- [ ] Verify JSON export is complete, understandable, profile-scoped, secret-free and generated only on explicit action.
- [ ] Ensure withdrawal blocks new assessments while remaining clearly distinct from deletion.
- [ ] Add a schema-change gate: any new profile relation must update inventory, export, deletion, retention and tests.

## Store and release evidence

- [ ] Review Google Play privacy/data-safety declarations against binaries, SDKs, backend and operational flows.
- [ ] Ensure the public description uses estimated/non-medical wording and supported scope consistently.
- [ ] Publish approved support/privacy contacts and accessible user information.
- [ ] Run backend, nutrition engine, privacy, Flutter, migration/seed, analysis and release-build checks; archive results without user data.
- [ ] Record final versions/hashes of app, backend, migrations, reference/rule sets, consent text and legal documents.
- [ ] Obtain accountable release sign-off from engineering, security, privacy/legal, scientific/safety and product owners.

## Release decision

| Role | Name | Decision/date | Evidence link |
|---|---|---|---|
| Controller/product owner | `[required]` | `[required]` | `[required]` |
| Privacy/legal reviewer | `[required]` | `[required]` | `[required]` |
| Security owner | `[required]` | `[required]` | `[required]` |
| Scientific/safety reviewer | `[required]` | `[required]` | `[required]` |
| Engineering owner | `[required]` | `[required]` | `[required]` |

No unchecked blocker may be treated as implicitly waived. Any accepted residual risk requires a named owner, rationale, compensating measure and expiry/review date.

