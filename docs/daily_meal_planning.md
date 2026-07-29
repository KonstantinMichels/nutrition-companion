# Daily Meal Planning

## Scope and product boundary

Daily Meal Planning is a manual planning tool. A profile can create meals for a local calendar
date, add current recipes or foods, inspect meal/day totals and compare the planned day with one
selected immutable Nutrition Assessment. A plan is intent, not evidence of consumption. The
module creates no automatic recommendation, optimization, score, diary or weekly schedule.

## Persistence and date behavior

`daily_meal_plans.plan_date` is a PostgreSQL `DATE`; meal times are local `TIME` values without
timezone conversion. A partial unique index permits at most one non-archived plan per profile and
date. Archived plans remain readable. A new active plan may coexist with archived plans for that
date; restore is rejected while another active plan exists.

```text
DailyMealPlan (owner, DATE, optional assessment, metadata, archive state)
  `-- Meal (type, custom name, local time, position, notes)
        `-- MealEntry (recipe portions OR food quantity/unit/measure, position, note)
```

Pydantic and database constraints require positive quantities and exactly one entry source.
Deleting a plan graph cascades to meals and entries. Assessment deletion uses `ON DELETE SET
NULL`; plans and nutrient totals remain usable without personal comparison.

## Assessment selection

Creation selects the newest supported assessment with comparable targets unless the client
explicitly requests a plan without assessment. Historical usable assessments can be selected.
Targets remain the immutable stored assessment values. A missing/deleted/unsupported assessment
does not erase plan structure and never creates a hidden target snapshot.

## Entry calculation and normalization

Recipe entries use Recipe Core's current per-serving calculation multiplied with the decimal
`recipe_portion_count`. Each unique recipe is calculated once per request. Direct food entries use
Food Core density, base-unit and household-measure conversions; g/ml conversion without density
is rejected. Selected measures must belong to the food. Estimated measures retain an explicit
quality marker. Calculations use `Decimal` without intermediate display rounding.

Archived foods/recipes remain calculated in already saved plans and receive warnings. They are
excluded from new selection and rejected when newly submitted. Current source values are used:
later food or recipe edits may change current plan totals. This feature deliberately stores no
historical food/recipe nutrient snapshot.

## Aggregation and coverage

The pure backend engine receives typed meals and entry nutrient results and performs no HTTP,
database, Flutter, network or LLM work. It aggregates canonical nutrients per meal and day. For
every nutrient it retains the known amount, known/relevant source-component counts, missing source
names, coverage ratio and completeness. Recipe ingredients remain components where Recipe Core
provides them; a direct food entry is one component. Coverage is data availability, not statistical
confidence. Unknown values remain `null`; a known true zero remains zero.

Quality levels are `empty`, `incomplete`, `basic_complete` and `extended`. Structured warnings
cover empty plans, missing assessments, incomplete basics, archived references, estimated
conversions and definite target/limit exceedance.

## Daily target and remaining semantics

Target extraction, kinds and canonical conversion are reused from Recipe Target Comparison:

- minimum: complete gaps are exact; with incomplete data a known gap is only an upper bound;
- maximum: complete remaining allowance is exact; incomplete allowance is indeterminate unless
  the known lower bound already exceeds the maximum;
- range: complete values are below/within/above; incomplete values are indeterminate unless the
  known value is already above the upper bound;
- reference: a neutral difference/contribution, never a mandatory medical target.

No unavailable amount is rendered as zero and no relation is described as a deficiency diagnosis.

## API and preview

`/api/v1/daily-meal-plans` supports lightweight date lists, transactional create/update, detail,
active lookup by date, archive, restore and duplication with new graph IDs. Duplication never
overwrites a target date and optionally copies the assessment reference.

`POST /api/v1/daily-meal-plans/preview` validates ownership and quantities and returns the same
authoritative calculation shape without persisting or modifying any plan, food or recipe.

## Flutter and drafts

The navigation drawer exposes **Tagesplan**. The Android-first overview provides previous/next day,
native date picker, empty/error/loading states, compact totals, meal cards, detailed comparison,
duplicate, archive and restore. The editor supports meal/entry add/remove/edit and accessible
up/down ordering, assessment selection, German decimal input and explicit server preview.

Unsaved plan structure is stored in the existing Keystore/Keychain-backed `SensitiveStore`, keyed
by date inside one app-owned encrypted value, expires after 30 days, can be manually removed and is
cleared with complete local profile deletion. It does not contain complete nutrient source records.

## Privacy and deletion

Plans contain sensitive behavioral nutrition data. Ownership is enforced for plans, assessments,
recipes and foods. Bodies, notes, target values and daily totals are not logged. No analytics,
advertising or external service is added. Privacy export contains the persisted plan graph, not
on-demand comparisons. Complete profile deletion removes plans first, then protected recipes,
foods and the remaining profile graph; app-local deletion clears encrypted drafts.

## Known limitations and next feature

Planning is manual and does not prove consumption. There is one active plan per date, no historical
source snapshot, and incomplete Food Core data limits totals. There are no suggestions, automatic
gap filling, weekly overview, pantry/inventory, shopping list, budget, training-calendar adjustment,
Health Score or medical interpretation.

The next planned branch is `feat/weekly-meal-planning`: week organization and overview, copying or
moving meals between dates, and weekly aggregation. It is not implemented here.
