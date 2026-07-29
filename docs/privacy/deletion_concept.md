# Deletion concept

**Status:** Local-MVP behavior and production design requirements  
**Last reviewed:** 2026-07-28  
**Legal status:** Draft; legal obligations and exceptions require professional review.

## User controls and semantics

| Control | Stops future assessments | Deletes server profile | Deletes old assessments | Deletes local sensitive data |
|---|---:|---:|---:|---:|
| Withdraw consent | Yes | No | No | No, except refreshed consent display state as needed |
| Delete assessment history | No, if consent remains active | No | Yes | Latest-assessment cache yes |
| Delete onboarding draft | No | No | No | Draft only |
| Delete local assessment cache | No | No | No | Cache only |
| Delete complete profile | Yes because profile/consent cease to exist | Yes | Yes | Draft, cache and local profile/consent context |
| Delete profile and assessments | Stops until a new profile is configured | Personal profile content only; internal library-owner anchor remains | Yes | Draft and assessment cache |
| Delete all recipes | No | No | No | No |
| Delete all foods | No | No | No | No |

Foods cannot be bulk-deleted while recipes reference them. The UI instructs the user to delete recipes first. “Delete all data” performs that dependency-safe ordering automatically. The internal owner anchor retained by a profile-only reset contains placeholder values and is not returned as an existing configured profile; it exists solely so Foods and Recipes remain assigned to the same local development identity.

The German UI must explain these differences and require explicit confirmation for destructive operations. A successful response must not contain the former profile ID or any body/health values.

## Assessment-history deletion

Preconditions:

- explicit user action and confirmation;
- resolution of the current profile through the backend dependency;
- in production, authenticated authorization and re-authentication policy as approved; and
- idempotent behavior that does not expose whether another user's assessment exists.

Database transaction:

1. identify only assessments owned by the current profile;
2. delete dependent assessment metrics;
3. delete dependent safety flags;
4. delete assessment rows and immutable snapshots;
5. record only a minimal privacy action if the approved implementation does so; and
6. commit as one transaction or roll back completely.

After confirmed server success, Flutter removes the minimal latest-assessment cache and refreshes history. A network timeout after submission is an unknown outcome: the client must re-query state rather than claim failure or success without evidence.

Current profile, measurements, activity, goal, restrictions, screening and consent remain. A later assessment creates a new snapshot from the then-current profile.

## Complete-profile deletion

Database transaction removes, in dependency-safe order or through verified cascades:

- assessment metrics and safety flags;
- assessments and immutable snapshots;
- sport activities and activity profile;
- measurements;
- nutrition goal;
- dietary restrictions;
- health screening;
- foods, food nutrients and food measures;
- recipes, recipe ingredients and recipe steps;
- daily meal plans, meals and meal entries before their protected source records;
- consent records as appropriate for the local MVP;
- privacy-action records that are linked and not covered by an approved minimal exception; and
- the profile.

The transaction must use current-profile scope throughout. It must not be a UI hide, status flag or unprocessed soft delete. On any database error, roll back the whole transaction and return a sanitized machine-readable error.

Only after server confirmation, Flutter deletes:

- unfinished onboarding draft;
- all encrypted daily-plan drafts;
- latest-assessment cache;
- local consent display state;
- development current-profile context where present; and
- app-controlled temporary export files.

If local cleanup partially fails, the app reports a local-cleanup error without resubmitting or recreating the server profile, retries only local removal, and treats unreadable secure-storage payloads as data to discard. No plaintext fallback is permitted.

## Deletion confirmation

Preferred local response:

```json
{
  "deleted": true,
  "scope": "profile",
  "request_id": "short-lived-random-id"
}
```

Do not include the deleted UUID, values, assessment summary, consent text or free-text notes. If a minimal server deletion record is implemented, it contains only a random confirmation ID, scope and timestamp, has no recoverable link to the deleted profile, and follows the approved short TTL in [retention_policy.md](retention_policy.md).

## Local database and development volumes

API deletion removes active rows. A developer who destroys a local Docker volume is performing environment cleanup, not exercising the product's profile-deletion flow. Local snapshots or manual database dumps containing synthetic data must also be removed when no longer needed; real user data must never be used for development.

## Production backup behavior

Production backups do not exist in the MVP. Required future process:

```text
active deletion
  -> append minimal protected deletion marker (without health payload)
  -> backup copies age out under declared maximum period
  -> any restore enters quarantine
  -> reapply every deletion after the restored backup's point-in-time
  -> verify referential deletion
  -> only then release restored service
```

The operator must define maximum backup retention, encryption/key control, authorized restore roles, test cadence and evidence. A restore test must prove both recoverability and reapplication of deletion. This repository must not claim that outcome.

## Verification tests

Before production, automated and operational tests must verify:

- all profile-owned tables are covered;
- deleting history preserves current profile/consent but removes metrics/flags/cache;
- complete deletion removes every profile-owned active record and local secure-storage object;
- forced failure rolls back the whole database transaction;
- repeated deletion is safe and non-revealing;
- cross-profile identifiers cannot delete another profile's records;
- logs and minimal action records contain no former body/health data;
- temporary export content and URI grants are cleaned up; and
- a production restore reapplies deletion before activation.

Schema changes that add profile-linked data must update this concept, the export, inventory, cascade/transaction and deletion tests in the same change.

Assessment-history deletion leaves daily plans intact. Their `assessment_id` becomes `NULL` through
the foreign key, daily totals remain calculable, and comparison stays unavailable until another
assessment is selected. Archiving a plan, food or recipe is not privacy deletion. Existing archived
source references remain structurally present and visibly warned; archived sources cannot be added
to a new entry.
# Food Core

Die vollständige Profillöschung löscht eigene Lebensmittel sowie Nährwerte und Maße dauerhaft per Datenbank-Cascade. Die App muss anschließend lokale verschlüsselte Profildaten leeren. `DELETE /foods/{id}` archiviert dagegen nur. Die getrennte, in der App ausdrücklich bestätigte Aktion `DELETE /foods/{id}/permanent` löscht ein einzelnes eigenes Lebensmittel samt abhängigen Werten unwiderruflich.
