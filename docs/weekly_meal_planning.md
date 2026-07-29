# Weekly Meal Planning

## Scope and architecture

The weekly planner is a derived orchestration layer over `DailyMealPlan`, `Meal`, and
`MealEntry`. It has no weekly persistence table and stores no weekly totals,
percentages, explanations, quality level, or history. `anchor_date` is normalized by
the API to the ISO Monday; the response always covers Monday through Sunday and
returns ISO week number and ISO week year. Calendar `DATE` values are not converted
through UTC.

Day states are `no_plan`, `empty_plan`, `planned`, and `archived_only`. Archived plans
are metadata only and never contribute to totals. Missing plans are unknown planning
days, not zero intake.

## Calculation

The weekly service batch-loads the seven-day range and calls the existing daily-plan
calculation for every active plan. Known nutrient amounts are summed without early
rounding. The displayed average is divided by `planned_day_count`, never implicitly by
seven. True zero remains zero; unavailable values remain unavailable.

Coverage combines daily component counts and retains date, meal, entry, and source
context for missing values (bounded to 50 items per nutrient in the mobile response).
Coverage describes data availability, not statistical confidence.

Daily assessment targets are summed only for planned days with usable, semantically
compatible descriptors and units. `minimum`, `maximum`, `range`, and `reference`
targets remain distinct. Different immutable assessments may be combined when their
semantics match; their IDs and reference/rule versions remain visible in the API.
Incompatible target kinds are not combined. Remaining values preserve the daily
uncertainty rules: known incomplete amounts are lower bounds, a known maximum
exceedance is definite, and a range cannot be called satisfied when data is incomplete.

## Organization operations

Complete days use the existing daily duplication endpoint and never overwrite an
active target date. Meal copy/move supports a new target meal or appending entries to
an existing target meal. Quantities, portions, measures, notes, and order are copied
without deduplication. A missing target plan is created with the source, latest, or no
assessment as requested. Move performs target creation/insertion and source removal in
one database transaction; validation failures leave the source unchanged.

All plan, meal, target, source, and assessment lookups are scoped to the current
profile. Weekly response bodies, meal names, totals, and target values are not logged.
No cache, analytics, external API, additional consent, or separate privacy-export
record is introduced. Profile deletion already removes the daily source records, so no
derived weekly record remains.

## Limitations

Planning is manual. Missing days are not populated. Totals use current food and recipe
data; historical source snapshots do not exist. Incomplete nutrient data limits the
interpretation. There is no automatic optimization, recommendation, pantry link,
shopping list, price/budget calculation, leftover handling, consumed-meal tracking,
recurring template, Health Score, or medical interpretation.

The next expected feature is `feat/pantry-core`.

Die Wochenansicht ist inzwischen ein Einstieg für Pantry-aware Shopping. Dabei bleiben die stabilen
Identitäten der zugrunde liegenden Tagesplaneinträge erhalten; es wird kein eigener Wochenbedarf
persistiert.
