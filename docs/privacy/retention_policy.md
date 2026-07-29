# Retention policy

**Status:** Local-MVP policy with explicit production gaps  
**Last reviewed:** 2026-07-28  
**Approval:** Draft; controller and legal/privacy approval required before production

## Principles

Retention is purpose-specific. “Indefinite” is not a period. A configurable rule does not count as operating practice until jobs, monitoring and deletion verification exist. Complete-profile and assessment-history deletion are active hard-deletion operations, not hidden soft deletion.

The GDPR storage-limitation and data-minimization principles appear in Article 5; erasure rights and exceptions are in Article 17. See the official [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj), accessed 2026-07-28. How those provisions apply to an operator requires professional review.

## Retention schedule

| Data category | Local-MVP period | Trigger | Deletion process | Backup behavior | Reason/status |
|---|---|---|---|---|---|
| In-memory form/request/response data | Only for active UI/request/process lifetime | Navigation/lifecycle completion, request completion or process end | References released; never intentionally logged | Not backed up | Technical processing only |
| Abandoned encrypted onboarding draft | **Policy target: 30 days after last update**, or earlier submission/manual clear/profile deletion | TTL, successful onboarding, user clear, profile deletion | Delete all draft keys atomically/best effort; unreadable payload removed rather than downgraded | Must be excluded from Android backup or protected per reviewed backup design | Resume convenience; automatic TTL implementation must be verified before release |
| Encrypted daily-plan drafts | 30 days after last update, or earlier save/manual clear/complete profile deletion | Read-time TTL, successful save, explicit clear or profile deletion | Remove date entry or the complete app-owned draft key; no plaintext fallback | Android backup disabled; future backup design requires review | Resume manual editing only; no nutrient source snapshots |
| Minimal encrypted latest-assessment cache | Until replaced by a newer result, manual clear, history deletion or complete-profile deletion; after 24 hours it remains viewable but is visibly stale | New assessment, clear-cache/history/profile action | Delete cache key; no complete server export cached | Must be excluded/reviewed as above | Offline latest-summary display; staleness is not deletion, and a maximum production cache age still needs owner approval |
| Local development profile identifier/consent display state | Until complete-profile deletion, local-data clear or uninstall | Deletion/reset | Delete secure-storage keys | Exclude/review backup | Development routing/offline display only; not authentication |
| Current profile and child records | Until user requests complete-profile deletion | Explicit confirmed profile deletion | One DB transaction removes profile, measurements, activity, sport, goal, restrictions and screening | Local DB has no managed backup policy; production rule below | Needed for user-requested saved profile |
| Foods and recipes, including nutrients, measures, ingredients and steps | Until explicit permanent Food deletion where unreferenced, or complete-profile deletion; archive alone does not shorten retention | Permanent Food deletion or profile deletion | Referential checks protect recipe ingredients; profile cascade hard-deletes both graphs | Same | User-requested reusable nutrition data |
| Daily meal plans, meals and entries | Until complete-profile deletion; archive remains retained | Confirmed complete deletion | Delete plan graph before protected recipe/food sources in one transaction | Same | User-requested manual planning; plan is not consumption history |
| Assessments, metrics, safety flags and snapshots | Until user deletes assessment history or complete profile | Explicit confirmed history/profile deletion | One DB transaction hard-deletes assessment graph | Same | User-requested immutable history; no automatic recalculation |
| Consent records | Local MVP: until complete-profile deletion; withdrawal state retained while profile exists | Profile deletion; withdrawal updates state but is not deletion | Delete with profile under local concept | Production legal/evidentiary period unresolved | Enforce and show the user's decision; post-deletion period needs counsel |
| Privacy-action records | While profile exists unless an implemented minimal record is demonstrably needed | Profile deletion or approved TTL | Remove linked record; never retain health-data copies | Production rule unresolved | Minimal operational trace only |
| Minimal deletion confirmation (`DeletionRecord`) | Current local implementation retains scope, time, approximate record count and random confirmation code without a profile UUID; **no TTL is implemented** | Successful history/profile deletion | No automatic deletion yet | Production rule unresolved | Retention purpose/period and cleanup job are production blockers; record contains no health payload |
| Reference sets/application rules/processing-purpose definitions | Version life plus as long as an assessment refers to the version | Supersession and no remaining dependency | Do not delete versions referenced by retained assessments | Included in normal configuration/DB backup | Reproducibility; generally non-personal until linked |
| Structured technical logs | **Provisional 14 days** in any future persistent environment; local console/container logs may end sooner | Rotation/TTL | Automated rotation and deletion | Exclude from long-lived backup by default | Debug/security with minimization; production risk/necessity approval pending |
| Incident evidence hold | Only when an actual incident owner records scope, basis and review date; no default indefinite hold | Incident closure plus approved follow-up period | Restricted deletion approved by incident/legal owner | Protected consistently | Exception process, not routine retention |
| Generated server export | Request lifetime only; no server-side export archive | Response completion/error | Release temporary resources | Not backed up | User-requested generation only |
| Mobile export temporary file | Delete promptly after the share workflow; policy target no later than app's next cleanup opportunity | Share completion/cancel, startup cleanup, profile deletion | Delete app-controlled temp file/content grant | Exclude from backup | Export delivery; destination copy controlled by user-selected app |
| Automated test/seed data | Test/run lifetime; synthetic only | Test teardown/reset | Drop/rollback isolated data | No production backup | No real user health data permitted |

## Withdrawal is not deletion

Withdrawing a required consent changes future processing state and blocks new assessments. It does not automatically erase the current profile or old assessments. The UI must offer and explain three distinct controls:

1. withdraw consent and stop future assessment processing;
2. delete assessment history while keeping the current profile; and
3. delete the complete profile and local sensitive data.

The controller must decide, with counsel, whether any operation must stop or any data must be retained/erased when consent is withdrawn, especially if a different legal basis applies. The code's state transition is not that legal decision.

## Future production backups

No production backup system is implemented in this repository. Public release requires a documented schedule specifying backup frequency, maximum expiry, regions, encryption and key ownership, access, immutable/ransomware protection, restore testing and deletion handling.

Required behavior:

- deleted data may exist only temporarily in protected backups until ordinary expiration;
- backups are not queried or restored for ordinary product use;
- deletion markers or an equivalent protected ledger are reapplied before a restore is returned to active use;
- restored systems are quarantined until that reapplication and verification complete;
- expired backup objects and keys are verifiably removed under provider capability; and
- users are accurately informed of the maximum residual period.

Do not claim this process exists until it is deployed, tested and evidenced.

## Exceptions and review

Any legal hold, accounting/security requirement or contested request needs a recorded owner, exact scope, legal basis, access restriction, start date, review date and deletion date. Do not retain a full health profile merely to prove that a privacy action occurred.

Review this schedule at least annually in production and whenever a purpose, vendor, legal basis, backup, authentication model or data field changes.
# Food Core

Aktive und archivierte Lebensmittel bleiben bis zur vollständigen Profillöschung erhalten. Archivierung ist keine Datenschutzlöschung.
