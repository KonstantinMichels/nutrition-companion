# Security and personal-data incident response

**Status:** Draft operating runbook; no production organization is established  
**Last reviewed:** 2026-07-28  
**Owner/on-call/legal/privacy contacts:** `[must be assigned before production]`

## Purpose

This runbook covers suspected compromise, loss, unauthorized access/disclosure, integrity loss or unavailability involving Nutrition Companion systems or personal data. Examples include a leaked database credential, exposed export, sensitive payload in logs, authorization bypass, stolen administrator device, malicious dependency, backup exposure or deletion failure.

Do not wait for certainty before recording and escalating a credible signal. Preserve evidence without broadly copying health data.

## Severity and immediate priorities

| Severity | Example | Initial handling |
|---|---|---|
| Critical | Active unauthorized production access, public database/export, cross-profile access, destructive compromise | Page incident lead; contain immediately; involve security/privacy/legal decision makers |
| High | Leaked usable credential, sensitive logs accessible to unauthorized party, backup exposure | Revoke/isolate; begin formal assessment urgently |
| Medium | Attempted access blocked, limited internal misdelivery, deletion workflow defect without known disclosure | Record, scope and remediate; reassess if facts change |
| Low | Benign operational failure with no confidentiality/integrity/availability impact | Normal ticket with security review if uncertain |

Severity does not decide GDPR notification by itself. The competent authority and affected-person decisions depend on actual likelihood/severity of risk and require qualified review.

## Response sequence

### 1. Detect and open a record

Create an incident ID and record discovery time, reporter, affected environment/component, observable facts and immediate owner. Do not paste entire profiles, exports, tokens or secrets into the ticket. Store necessary evidence in a restricted location and reference it.

Possible signals include authentication/access anomalies, integrity checks, unexpected exports/deletions, secret scanning, dependency alerts, user reports and processor notices. The MVP has no third-party analytics or crash reporting; adding monitoring changes the processor/data-flow inventory.

### 2. Contain safely

Depending on the event:

- revoke/rotate the exact compromised credential or token;
- isolate a host, route, endpoint, account or deployment;
- disable export or write operations if needed to prevent harm;
- preserve relevant minimized logs and system state;
- prevent backup rotation from destroying essential evidence under an approved narrow hold; and
- do not delete attacker evidence or perform broad destructive actions without incident-lead authorization.

Containment must not silently weaken TLS, authentication or logging safeguards.

### 3. Investigate and scope

Determine with evidence:

- what happened, entry point and timeline;
- affected controller/processor and system versions;
- data subjects and approximate number, without unnecessary re-identification;
- exact data categories, special-category content, volume and time range;
- whether data was viewed, altered, exported, deleted, encrypted or merely exposed;
- recipients/countries and whether access remains possible;
- effect on calculation integrity, consent, deletion and availability;
- whether credentials/keys or backups were involved; and
- confidence, unknowns and further actions.

Query logs using short-lived request IDs where possible; do not create a new sensitive log dataset.

### 4. Escalate and assess notification

Notify the assigned incident lead, controller/privacy lead, security lead, relevant product/engineering owner and qualified legal counsel. Contact processors under contractual incident terms if present.

GDPR Article 33 provides for supervisory-authority notification without undue delay and, where feasible, within 72 hours after the controller becomes aware **when the breach is likely to result in a risk** to people's rights and freedoms; reasons for delay must accompany a late notification. Article 34 addresses communication to affected people **when likely high risk**, subject to its conditions/exceptions. Every breach must be documented under Article 33(5). See the official [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj), accessed 2026-07-28.

This runbook does not predetermine notification. Qualified decision makers must record:

- awareness time and deadline tracking;
- competent supervisory authority analysis;
- likelihood/severity of consequences;
- protective measures such as effective encryption and key exposure status;
- notification/communication decision and reasons;
- content, sender, recipients and time if made; and
- follow-up facts and supplemental notifications.

### 5. Eradicate, recover and validate

- remove the root cause and persistence;
- patch/rebuild from trusted artifacts rather than editing a compromised host in place;
- rotate affected secrets and invalidate sessions;
- restore from a verified point if necessary;
- reapply deletions before restored data becomes active;
- verify authentication/authorization, data integrity and calculation/reference versions;
- increase narrowly scoped monitoring without capturing health payloads; and
- obtain incident-lead approval before normal service resumes.

### 6. Communicate

Only designated personnel communicate externally. Messages must be factual, calm, accessible and updated as knowledge changes. Do not minimize uncertainty, speculate, expose another person, make unverified legal claims or promise impossible deletion from a recipient's systems.

Where user communication is approved, cover the nature of the breach, contact point, likely consequences and measures taken/proposed, as applicable. Use a channel appropriate to the risk and verify that the contact dataset itself is authorized—the MVP intentionally does not collect email/phone numbers.

### 7. Close and learn

Closure requires documented containment, root cause, affected versions/data, notification decisions, remediation owner/deadline, verification, residual risk and an after-action review. Update threat model, tests, TOMs, data inventory, processors/transfers and DPIA when implicated.

## Incident record minimum

```text
incident_id
discovered_at / controller_awareness_at
reporter and accountable lead
facts and timeline
systems, versions and environments
data categories / subject count estimate
confidentiality, integrity and availability effects
containment and evidence locations
risk assessment and unknowns
authority notification decision/time
data-subject communication decision/time
root cause, recovery and validation
actions, owners, due dates and closure approval
```

The incident record itself is access-restricted and follows an approved retention rule. It must reference sensitive evidence rather than duplicate it.

## Readiness blockers

Before production: assign named deputies and 24/7 escalation expectations appropriate to the service; identify supervisory authority/legal contacts; execute a tabletop exercise; configure detection without body logging; agree processor notification terms; define secure evidence storage; and test credential revocation, rebuild, restore and deletion reapplication.

