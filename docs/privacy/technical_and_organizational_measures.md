# Technical and organizational measures

**Status:** MVP controls and production control requirements  
**Last reviewed:** 2026-07-28  
**Approval:** Draft; the future controller must select measures appropriate to the real risk under GDPR Article 32.

Code can implement some safeguards. It cannot establish administrator discipline, contracts, hosting security, monitoring coverage or legal compliance. “Required” below is a release gate until an accountable production owner supplies evidence.

## Control matrix

| Area | Local-MVP technical measure | Production/organizational requirement and evidence |
|---|---|---|
| Data minimization | No name/address/phone/location/advertising ID; limited screening; minimal local cache | Field/purpose review for every release; owner-approved inventory and privacy notice diff |
| Purpose limitation | Stable purpose codes; no analytics/ads/tracking; engine has no network | Change-control gate; record of processing; prohibit secondary use without review |
| Access control | Profile-scoped service dependency with development UUID | Real authentication and object authorization; cross-account tests; re-auth for export/delete |
| Administrator access | No production admin plane | Individual accounts, phishing-resistant MFA where practical, least privilege, approvals, periodic access review, rapid revocation |
| Mobile storage | Sensitive draft/cache through secure-storage abstraction; no hard-coded key; SharedPreferences limited | Verify Android/iOS package config, device/API matrix, backup rules, key invalidation and rooted-device threat statement |
| Transport | Local HTTP only by explicit development config; Compose publishes DB/API to host loopback by default; production intended to reject HTTP; normal TLS validation | TLS termination/config scan, HSTS where web-appropriate, certificate renewal, restricted CORS, no debug trust anchors; explicit firewall review for any LAN bind |
| Database | SQLAlchemy parameterization/transactions; environment credentials | TLS to PostgreSQL, least-privilege runtime/migration roles, encrypted volumes, network isolation, credential rotation |
| Backups | No production backup is claimed | Encrypted backups, separate access, key ownership, immutable protection, declared expiry, restore and deletion-reapplication tests |
| Secrets | `.env` excluded; `.env.example` contains development placeholders | Managed secret store, no shared accounts, rotation/revocation runbook, leak scanning and incident procedure |
| Logging | Structured technical metadata; unmatched route logged only as `/{unmatched}`; bodies/profile UUIDs/secrets prohibited; Compose Uvicorn access log disabled | Central access controls, field allowlist/redaction tests, ingress/platform-log review, 14-day provisional TTL, alerting and incident evidence handling |
| Error handling | Consistent sanitized API errors/request IDs for validation, 404/405 and unexpected failures; outer middleware terminates exception propagation without serializing values | Edge/proxy error review and monitoring that does not capture payloads |
| Integrity/reproducibility | Immutable assessment snapshots with formula/reference/rule versions; deterministic engine | Signed/reviewed releases, dependency and seed provenance, controlled reference updates, rollback procedure |
| Availability | Local Docker Compose and tests; synchronous DB routes execute in FastAPI's worker thread pool rather than blocking the event loop directly | Capacity/thread-pool/rate limits, health monitoring, redundancy objective, disaster recovery and recovery-time/data-loss decisions |
| Deletion | Transactional history/profile deletion; mobile local purge | Authorization, support process, backup expiry/reapplication, sampled verification and schema-change gate |
| Export | On-demand JSON; no automatic upload | Re-authentication, temporary-file/URI tests, abuse limits, rights-request procedure |
| Development separation | Synthetic tests/seeds; environment configuration | Separate accounts/projects/networks/keys; prohibit production dumps; documented sanitized debugging path |
| Dependency security | Locked project manifests and automated tests where configured | Patch owner/cadence, SBOM/dependency scanning, supported-version policy, urgent vulnerability response |
| Security testing | Unit/API/mobile tests within repository scope | Threat model, SAST/dependency checks, independent penetration test and remediation evidence before release |
| Incident handling | Runbook in [incident_response.md](incident_response.md) | Named on-call/decision makers, contacts, exercises, processor notification terms, legal assessment capability |

## Access and least privilege

- Application code receives the minimum database permissions it needs; migration rights should be separate where practical.
- Production access is individual, attributable, time-limited where possible and reviewed periodically.
- Support personnel do not browse health records for convenience. Access requires an approved need and is logged without copying data into tickets.
- Development and tests use synthetic records. Production exports/dumps are prohibited on developer laptops unless a separately approved incident procedure requires a narrowly scoped artifact.
- Departures and role changes trigger prompt revocation from source, CI, hosting, database, secrets, logs and backups.

The local development resolver is not an access control. An exposed deployment using it is prohibited.

## Encryption and key management

- Device-side key material is delegated to Android Keystore via the maintained secure-storage library; no application key is hard-coded.
- Production API traffic and database connections require TLS; certificate validation remains enabled.
- Production data volumes and backups require encryption at rest with documented provider/key boundary.
- Secret and encryption keys require ownership, creation, access, rotation, revocation, recovery and destruction procedures.
- Do not add home-grown field encryption without a threat model and lifecycle design. Encryption that stores the key beside the ciphertext does not solve the stated threat.

Android's official documentation describes Keystore's non-exportable key handling, while GDPR Article 32 names encryption/pseudonymization, confidentiality/integrity/availability/resilience, restoration and regular testing as measures to consider according to risk. See [Android Keystore](https://developer.android.com/privacy-and-security/keystore) and [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj), accessed 2026-07-28.

## Logging and monitoring

Use an allowlist, not ad-hoc redaction after logging. Allowed fields are request ID, endpoint template, status, duration, error code, environment and timestamp. Never log:

- request/response bodies or form fields;
- profile IDs, full URLs with parameters or persistent device identifiers;
- weight, measurements, screening, allergies, disease, goals or results;
- consent text or secure-store contents; or
- credentials, access tokens, database URLs, encryption keys or stack traces sent to clients.

Unexpected downstream exceptions are consumed by the outer application request middleware and converted to a generic response before reaching Uvicorn. The structured logger uses the matched route template or `/{unmatched}`, never a raw unmatched/error path. Compose disables Uvicorn's separate access log; a production ingress, platform or alternative server command may add another access-log flow and must be reviewed. A production log pipeline is a processor/data flow and must be added to the inventory/register before activation.

## Patch and vulnerability management

Assign owners for Python, Dart/Flutter, Android build tooling, database images and base OS. At minimum:

1. review supported/stable versions on a defined cadence;
2. scan direct/transitive dependencies and container images;
3. triage findings by exploitability and sensitivity of affected data;
4. use an expedited path for critical exposed vulnerabilities;
5. run calculation, API, privacy, Flutter and build tests after updates; and
6. record accepted risks with owner and expiry rather than silently suppressing alerts.

## Restore, deletion and continuity testing

Production must test restoration regularly with a documented recovery objective. A successful byte restore is insufficient: authorization, secrets, application/reference versions, auditability and deletion reapplication must also be verified. The exercise uses synthetic or properly controlled data, records start/end, findings and remediation owner, and never turns an unreviewed restored copy into a parallel production database.

## Developer rules

- Never place real health data in tests, screenshots, issue trackers, chat, source control, fixtures or seeds.
- Do not inspect user records through raw SQL for ordinary debugging.
- Do not disable TLS/certificate validation or production safeguards to resolve connectivity.
- Do not copy request bodies into exception messages.
- Use least-privilege, separate development credentials; never commit `.env`.
- Treat generated exports and screenshots as sensitive even when the user created them.
- Report suspected exposure immediately through the incident process; do not privately investigate beyond authorized containment.

## Review cadence

Review measures before production, at least annually thereafter, after a material incident, and whenever authentication, hosting, processors, transfers, permissions, data categories, calculations or future modules change. Record reviewer, evidence, residual risk and next date. This document alone is not proof that a measure operates.
