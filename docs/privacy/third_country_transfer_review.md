# Third-country transfer review

**Status:** No third-country transfer intended or configured for the local MVP  
**Last reviewed:** 2026-07-28  
**Production decision owner:** `[to be assigned]`

## Current finding

The local MVP is designed to run on a developer-controlled Android device/emulator, FastAPI process and PostgreSQL instance. No analytics, advertising, hosted AI, external crash reporting, remote support, cloud production platform or other external recipient is configured to receive profile/health data. Accordingly, this repository introduces no intended transfer of personal data outside the EU/EEA.

This is a statement about the local architecture, not a legal conclusion about a future operator's devices, source-control service, backups, development tools, app-distribution telemetry or chosen export destination. Public deployment is blocked until actual vendors, legal entities, subprocessors, support access and regions are inventoried.

## Trigger for review

Review before enabling any service that can receive or access personal data from outside the EU/EEA, including:

- hosting, database, storage, backup, CDN, WAF or DNS-layer request logging;
- monitoring, logs, traces, crash reports, support or ticketing;
- authentication, email, push notification or analytics;
- source-control/CI artifacts containing data (which are prohibited regardless);
- barcode, food, recipe or social-media import providers;
- AI/LLM or transcription providers;
- remote administrator or vendor support access; and
- a processor's subprocessor or parent-company access.

## Required assessment record

For each transfer or possible remote access, document:

1. exporter, importer, roles and processing purposes;
2. precise data fields, volume, frequency and special-category status;
3. all storage, transit, support and backup countries;
4. onward transfers and current subprocessors;
5. whether an EU adequacy decision applies to the exact recipient/context;
6. otherwise, the selected Article 46 safeguard (for example, the applicable standard contractual clauses);
7. a transfer impact assessment of local law and practical access risks;
8. supplementary technical/contractual/organizational measures, including who controls encryption keys;
9. data-subject information, rights handling, retention and deletion verification;
10. processor agreement and audit evidence;
11. DPIA and purpose-registry consequences; and
12. owner, approval date, review cadence and change trigger.

An EU data-center selection alone is insufficient if support, telemetry, subprocessors, backups or legal access create another data path. Pseudonymization reduces risk but does not make linkable profile data anonymous.

## Decision states

| State | Meaning |
|---|---|
| `not_present_local_mvp` | No external recipient/data path is configured in the local build |
| `review_required` | A proposed service or remote-access path has been identified; it must not receive personal data |
| `approved_with_conditions` | Qualified review documents a lawful mechanism and required safeguards/configuration |
| `rejected` | Transfer must not be enabled |
| `suspended` | Previously approved transfer is disabled pending reassessment |

## Legal source and release gate

GDPR Chapter V requires conditions for transfers to third countries or international organizations; the relevant route depends on actual facts. See the official [Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj), accessed 2026-07-28.

Before production, qualified EU/German privacy counsel must review the data map, contracts, transfer mechanism and assessment. Update [processor_register.md](processor_register.md), [data_flow.md](data_flow.md), [dpia_screening.md](dpia_screening.md) and the user-facing privacy notice before any activation.

