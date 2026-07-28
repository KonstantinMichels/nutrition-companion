# Processor register

**Status:** Local-MVP register; empty by design  
**Last reviewed:** 2026-07-28  
**Owner/reviewer:** `[to be assigned before production]`

## Current register

| Processor | Service | Personal data | Location/transfer | Agreement | Status |
|---|---|---|---|---|---|
| _None_ | No external service receives Nutrition Companion personal data in the local MVP | — | — | — | Local development only |

Docker, PostgreSQL, FastAPI and Flutter dependencies running on the developer's own local systems are software components, not by themselves external recipients. The Android share sheet exposes only an export the user explicitly directs to a chosen recipient; Nutrition Companion neither preselects nor operates that recipient. This does not remove the need to explain the boundary to the user.

No analytics, advertising, session-replay, third-party crash-reporting, hosted LLM, Firebase, Supabase, cloud-production host, email or customer-support processor is configured for the MVP.

## Before adding a processor

The controller must complete and approve a record containing:

- legal entity, service, purpose and accountable owner;
- exact data fields and whether special-category data is possible;
- controller/processor role analysis and any joint-controller issue;
- processing and support locations, subprocessors and remote-access locations;
- retention, deletion/return, backup and portability behavior;
- security controls, incident terms, audit evidence and access model;
- GDPR Article 28 agreement status;
- third-country mechanism and transfer impact assessment where relevant;
- production configuration and data-flow changes;
- privacy notice, purpose registry and DPIA updates; and
- exit/migration plan, including deletion evidence.

No vendor may receive production data merely because it offers an EU region. Contractual entity, support access, subprocessors and actual data paths still require review. GDPR processor obligations and contractual elements are set out in Article 28; international transfers are governed by Chapter V. See the official [GDPR text](https://eur-lex.europa.eu/eli/reg/2016/679/oj), accessed 2026-07-28.

## Register template

| Field | Entry |
|---|---|
| Processor legal name | `[required]` |
| Service/product | `[required]` |
| Processing purpose code(s) | `[required]` |
| Data categories | `[required]` |
| Special-category data | `yes/no and detail` |
| Data subjects | `[required]` |
| Primary region | `[required]` |
| Remote/support locations | `[required]` |
| Subprocessor list/version | `[required]` |
| Article 28 DPA | `owner, version, signed date` |
| Transfer mechanism/TIA | `[if applicable]` |
| Retention/deletion | `[required]` |
| Security assessment | `owner, date, evidence` |
| Incident contact/SLA | `[required]` |
| Exit verification | `[required]` |
| Next review | `[required]` |

