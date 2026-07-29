# Meal-plan automation foundation

The automation module creates deterministic, reviewable daily or ISO-week drafts from recipes,
an assessment, explicit preferences, Pantry availability and existing meal plans. Generation and
recalculation are transient. Nothing is written until the user calls `apply` and confirms whether
missing daily plans may be created.

## Preferences and slots

Named preference profiles persist meal slots, assessment selection, recipe/tag exclusions,
portion ranges, preparation-time and repetition limits, Pantry/shopping behavior and versioned
decimal scoring weights. Profiles are archived rather than hard-deleted. Drafts keep only a
reference and are deliberately session-only in Flutter.

Assessment modes are `latest_usable`, `explicit` and `per_existing_daily_plan`. Blocking or
critical assessment safety flags stop automation. Manual planning remains available at all times.

## Deterministic selection

The pure engine enumerates exact Decimal portion candidates, calculates explainable components,
applies non-negative weights and uses stable recipe-ID/portion tie-breakers. Hard exclusions run
before scoring. The foundation uses an intentionally greedy day/slot pass; it does not claim a
global optimum. A temporary Pantry budget is reduced while building a draft, but no stock is
reserved or changed. Missing quantities are projections and do not alter shopping lists.

## Review and application

The Android UI exposes the feature from daily and weekly plans. Users select scope, date,
preferences and existing-plan handling, then review proposals, component explanations,
alternatives, locks, daily/weekly values, Pantry usage and missing quantities. Applying supports
all-or-nothing or conflict-free mode, checks a freshness token and uses a client operation UUID for
idempotency. Existing meals are never silently overwritten. Successful applications create an
audit record; drafts and rejected alternatives are not retained.

API routes live below `/api/v1/meal-plan-automation`, including preference CRUD/archive/restore,
generation/recalculation, slot regeneration, application and application history.

## Privacy and limitations

Preferences and application audits are included in the profile export and removed before profile
deletion. The processing-purpose registry describes these data under meal planning. Generated
drafts stay in memory and are cleared by navigation/process termination. This is planning support,
not medical advice, an intake record, an optimizer, an AI recommendation or an autonomous Pantry
or shopping mutation.

The optional CP-SAT optimizer now sits behind the same eligibility, explanation and explicit
application boundaries. The greedy foundation remains independently available as baseline and
fallback; see `meal_plan_automation_optimizer.md`.
