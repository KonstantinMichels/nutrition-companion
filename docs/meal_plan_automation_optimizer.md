# Meal-plan automation optimizer

The optimizer jointly selects recipe/portion candidates for enabled meal slots across one day or
one ISO week. It extends, and does not replace, the deterministic greedy foundation. Users choose
`greedy`, `optimizer_strict`, or `optimizer_explainable_relaxation`; every result remains a
transient draft until explicit application through the existing Daily Meal Plan service.

## Solver isolation and reproducibility

Google OR-Tools CP-SAT is pinned to `9.14.6206` and wrapped by the application-owned
`MealPlanSolver` interface. The pure optimizer receives typed slots, candidates, nutrient bounds,
fixed-plan contributions, Pantry quantities and shopping commitments. It has no HTTP, database,
Flutter, network, LLM or persistence access. CP-SAT runs locally in the backend with one worker,
random seed 0, a 5-second day/20-second week default limit and a 2% relative-gap limit. Solver
upgrades may change solutions.

## Candidate and integer model

Foundation eligibility, tags, archive policy, data completeness, portion enumeration and component
scores run before optimization. Candidates are deterministically sorted and bounded per slot
(default 40; API range 5–80); locked/manual choices are retained. Model protection rejects more
than 35 slots or 4,000 candidate variables.

CP-SAT coefficients use a central Decimal scaling layer: energy uses whole kcal, macronutrients mg,
micronutrients µg, ingredient quantities milli-units, and scores 0–10,000. Hard lower bounds round
upward and upper bounds downward. Negative invalid values, unknown scales and coefficients above
`10^15` are rejected. Original Decimals remain in responses.

Each option has a binary variable; required slots select exactly one and optional slots at most one.
Locked choices are fixed. Existing meals contribute fixed nutrients and exact-recipe occurrences.
Exact Recipe IDs enforce daily/weekly repetition limits and minimum-day gaps. Daily preparation and
energy, protein, fiber, fat and saturated-fat limits use assessment semantics when configured
strictly.

## Pantry, shopping and objectives

Ingredient requirements are aggregated across the draft. Pantry availability and remaining active
shopping-list commitments form a temporary supply budget. Strict Pantry mode is hard; otherwise
shortage and distinct missing-food variables contribute to the objective. Partial handoffs are
subtracted and completed/archived lists excluded. Pantry and Shopping Lists are never mutated.

The bounded objective combines foundation suitability, Pantry coverage, shopping effort,
preparation time, variety or explicit meal-prep reuse, recipe preference and data quality, followed
by stable option-order tie-breaking. Returned sections show normalized weights, boundaries, model
size and structured explanations. This is not a health score.

## Status, relaxation and application

Stable statuses are `optimal`, `feasible`, `infeasible`, `unknown`, `invalid_model`, and
`time_limit_without_solution`. “Optimal” appears only for CP-SAT `OPTIMAL`; feasible results are the
best found within the limit and include a meaningful relative gap where available.

Explainable relaxation attempts strict solving first. Only configured planning constraints may be
relaxed. Ownership, safety, allergy/intolerance, explicit food/recipe exclusion, archive policy,
data validity, existing meals and locked ownership are never relaxed. Every relaxation is displayed
and needs a second confirmation. Audits persist only compact solver/objective/relaxation metadata,
not matrices, coefficients, tokens or model dumps.

Recalculation and `/optimize` preserve locks and manual choices. Apply repeats freshness checks, is
transactional/idempotent, never overwrites occupied slots, and reuses foundation conflict modes.
The optional greedy comparison reports factual model differences only.

## Privacy, performance and limitations

No external solver receives personal data and no model/result cache is written. Preferences and
compact audits are exported and deleted with the profile. Logs contain endpoint metadata only;
mobile drafts remain session-local.

Optimization uses a pruned discrete set, so valid combinations may be omitted. A proven optimum is
only optimal for this model and weights; time limits may stop early. Pantry is not reserved,
concurrent drafts can share stock, shopping lists remain unchanged, and meal-prep creates no
leftovers. Cuisine semantics, substitutions, standalone foods, prices, packages, retailers,
consumption and medical diet planning are unsupported. No external AI is used.

The next expected branch is `feat/progress-tracking-core`.
