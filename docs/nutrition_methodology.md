# Nutrition methodology

## Fortschrittsmessungen

Messwerte sind Nutzereingaben. Kurzfristige Gewichtsänderungen können viele Ursachen haben. Rolling Averages reduzieren sichtbare Tagesvariabilität, zeigen aber weder Ursache noch Körperzusammensetzung. Lineare Trends sind beschreibend; Messmethoden sind nur eingeschränkt vergleichbar. Es erfolgen keine Diagnose und keine automatische Zieländerung.

## Weekly planning interpretation

Weekly totals represent planned quantities from available active daily plans. Missing
daily plans are not treated as zero intake. Averages use planned days. Weekly targets
sum only compatible targets from planned days with usable selected assessments, so a
five-day plan is never compared with seven daily targets. Different immutable
assessments may contribute their stored daily values. Incomplete nutrient data makes
weekly amounts lower bounds and restricts remaining/range statements. The comparison
does not diagnose deficiency or excess and generates no automatic recommendation.

## Vergleich eines Rezepts mit persönlichen Tageswerten

Recipe Target Comparison skaliert die bekannte Nährstoffmenge einer ausgewählten Rezeptportionenzahl und stellt sie den gespeicherten Tageswerten einer unveränderten Einschätzung gegenüber. Das ist keine Bewertung der gesamten Tagesernährung und diagnostiziert weder Mangel noch Überschuss. Ein geringer Beitrag einer einzelnen Mahlzeit ist nicht grundsätzlich negativ. Fehlende Food-Core-Werte begrenzen den Vergleich und werden als bekannte Untergrenze beziehungsweise unbestimmte Höchstwert-/Bereichslage ausgewiesen.

**Engine:** `nutrition_engine_v1`  
**Scientific subset:** `dge_oege_v3_mvp_2026_05` / `3rd-edition-2025_erratum-2026-05_subset-v1`  
**Application rules:** `nutrition_companion_mvp_v1` / `v1`  
**Rules effective date:** 2026-07-28  
**Document reviewed:** 2026-07-28

This document describes the implemented deterministic MVP, not a clinical protocol. References and access dates are in [nutrition_sources.md](nutrition_sources.md); deliberate gaps are in [reference_data_incomplete.md](reference_data_incomplete.md).

## Purpose and supported scope

The engine produces transparent estimates and general reference targets for generally healthy adults aged 18 through 65. It is not intended to diagnose, prevent, monitor or treat disease and does not infer a nutrient deficiency. All values can differ from an individual's measured requirement.

An input is outside the automatic supported scope when:

- age is below 18 or above 65;
- pregnancy or breastfeeding is reported;
- a diagnosed eating disorder, diabetes, kidney disease, liver disease or serious metabolic condition is reported;
- a medically prescribed diet is reported; or
- the user reports another condition requiring professional nutrition care.

The engine returns `supported_scope_status = unsupported` plus one blocking, calm, non-diagnostic flag for each applicable screen. It withholds the ordinary goal-adjusted energy range and sport-elevated protein target. The current base protein reference may still be displayed with an explicit limitation; it is not a medical recommendation. The profile itself can be stored.

## Determinism and reproducibility

One assessment receives:

- age on the calculation date, height, current weight and physiological equation/reference-table category;
- optional dated/source-labeled body-fat, waist, hip and measured-REE values;
- current activity category, optional manual PAL and sport entries;
- current goal and optional weight-change preferences;
- relevant screening flags and dietary preference;
- one calculation timestamp; and
- immutable reference/rule objects.

The engine performs no network, HTTP or database access and keeps no hidden mutable state. For identical typed input, reference/rule versions and timestamp, output is deterministic. The service persists the complete relevant input snapshot, raw results, method/source/rule IDs and timestamp. Profile edits never recalculate an old assessment.

All arithmetic uses Python `Decimal`. No intermediate result is rounded. German display strings use `ROUND_HALF_UP` only after calculation; raw values are persisted with available precision (database numeric columns currently store up to six fractional places).

## Input validation

Validation occurs in Flutter, Pydantic and again at the engine boundary. Invalid values are rejected, never silently clamped.

Configured engine limits are:

| Input | Accepted range |
|---|---|
| Stored/profile age | 13–120 years; 18–65 is the supported assessment scope |
| Height | >100 through 250 cm |
| Current/target weight | >25 through 350 kg |
| Body-fat percentage | 2–75% |
| Waist/hip circumference | 30–250 cm |
| Measured REE | 500–5,000 kcal/day |
| Manual PAL | 1.2–2.4 |
| Sport sessions | 0–14/week |
| Minutes/session | 0–600 |
| Requested weekly weight-change magnitude | >0 through 2 kg/week |
| Measurement date | No more than one day after the calculation date; profile API also rejects implausibly old dates |

NaN, infinity, malformed decimals, wrong units and duplicate current measurement types are rejected. German comma input is normalized at the boundary, but calculation input is a typed decimal.

These plausibility limits are application rules, not diagnostic ranges and not DGE reference values.

## Calculation order

```text
validate -> supported-scope flags
         -> anthropometrics
         -> select measured or estimated REE
         -> PAL range / manual override
         -> maintenance-energy range
         -> goal-energy adjustment and safety floor
         -> protein target/range
         -> macro distribution
         -> fibre target
         -> age-banded hydration
         -> micronutrient lookups/unavailable reasons
         -> structured food-group orientation
         -> explanations, summary and safety/information flags
```

## Anthropometrics

### BMI

```text
height_m = height_cm / 100
BMI = weight_kg / height_m²
```

Metric code: `anthropometrics.bmi`. Method identifier: `bmi_weight_divided_by_height_squared`. BMI is a derived ratio, shown to one decimal place. It is not used alone to produce a nutrition target and is not rendered as a diagnosis.

### Waist ratios

When the required measurements exist:

```text
waist_to_height_ratio = waist_cm / height_cm
waist_to_hip_ratio = waist_cm / hip_cm
```

Both are derived and displayed to two decimals. The MVP reports no disease-risk cutoff or diagnosis from them.

### Body composition

When body-fat percentage exists:

```text
body_fat_fraction = body_fat_percentage / 100
fat_mass_kg = weight_kg × body_fat_fraction
fat_free_mass_kg = weight_kg - fat_mass_kg
```

Masses display to one decimal. If body-fat input is a device/user estimate, derived values remain labeled estimates; the arithmetic does not improve source quality.

## Resting energy expenditure

If a measured REE is supplied, it is selected as the authoritative resting-energy input under method `measured_resting_energy_expenditure_override`, with measurement date/source retained. The Mifflin–St Jeor estimate is still calculated and retained as comparison metadata; it does not replace the measured value.

Otherwise:

```text
reference category A (male physiological table column):
REE = 10 × weight_kg + 6.25 × height_cm - 5 × age_years + 5

reference category B (female physiological table column):
REE = 10 × weight_kg + 6.25 × height_cm - 5 × age_years - 161
```

Formula IDs are `mifflin_st_jeor_1990_reference_category_a` and `mifflin_st_jeor_1990_reference_category_b`. Category A maps to the male physiological table column and category B to the female physiological table column. The category is a physiological equation/reference-table input, not gender identity. Predicted REE is an estimate from a population equation, not an individual measurement.

## PAL mapping and sport

The selected usual daily-activity category maps to a DGE-based band. Midpoints are transparent application choices:

| Input category | Base minimum | Midpoint | Maximum |
|---|---:|---:|---:|
| `mostly_seated` | 1.40 | 1.45 | 1.50 |
| `seated_with_walking` | 1.60 | 1.65 | 1.70 |
| `mostly_standing_walking` | 1.80 | 1.85 | 1.90 |
| `physically_demanding` | 2.00 | 2.20 | 2.40 |

### Logged-sport rule

The base categories are configured as excluding logged sport. A +0.3 adjustment is added to all three band points only when the logged schedule contains at least four sessions per week where each qualifying session is at least 30 minutes and has `moderate` or `vigorous` intensity. Sessions and minutes outside that pattern still contribute to total weekly exercise duration but do not receive a fabricated partial PAL increment.

Method: `dge_pal_band_plus_documented_sport_adjustment`; application rule: `pal_sport_plus_0_3_when_dge_pattern_met`. Each final point is capped visibly at 2.4, so a physically demanding base range plus sport can collapse partly or entirely at the cap.

The official DGE example describes 30–60 minutes of strenuous leisure activity on 4–5 days/week. The MVP operationalizes that as qualifying logged **sessions**, because session day distribution is not collected. Multiple sessions on one day can therefore satisfy the counter; this is an explicit application simplification and uncertainty.

### Manual override

A validated manual value (1.2–2.4) is treated as the final whole-day PAL and collapses minimum/midpoint/maximum to that value. Logged sport is not added again. Method: `manual_pal_override_including_sport`. The report shows the override, selected base category and explanation.

## Maintenance energy

For the selected REE:

```text
maintenance_lower    = REE × PAL_lower
maintenance_midpoint = REE × PAL_midpoint
maintenance_upper    = REE × PAL_upper
```

This is an estimated range, not a statistically validated confidence interval. Variation in movement, body composition, measurement conditions, intake reporting and metabolic adaptation is not modeled.

## Goal-adjusted energy

The following are Nutrition Companion product rules, not scientific DGE values:

| Goal | Mild | Moderate/default |
|---|---:|---:|
| Maintain weight | 0% | 0% |
| General health | 0% | 0% |
| Athletic performance | 0% | 0% |
| Weight loss | −10% | −15% |
| Weight gain | +5% | +10% |

Each maintenance bound is multiplied by `1 + applied_percent / 100`. The engine can accept a service-supplied requested percentage, but any deficit is capped at −20%. The public MVP request currently selects only the configured mild/moderate rule.

If any adjusted bound is below selected REE, that bound is raised to REE and a visible warning records that the floor was applied. This is a product safety guard, not proof that consuming exactly REE is suitable for every person. For unsupported scope, the target range is unavailable.

A requested weekly rate is stored but is not converted into energy, a guaranteed rate or target date. A magnitude over 1.0 kg/week creates an aggressive-request warning under the MVP rule even though the requested rate does not drive the calculation.

Method: `maintenance_range_times_goal_adjustment_with_ree_floor`, or `goal_energy_withheld_unsupported_scope`.

## Protein

### Base reference by exact supported age

| Age | Category A | Category B | Interpretation |
|---:|---:|---:|---|
| 18 | 0.9 g/kg/day | 0.8 g/kg/day | Configured age-specific DGE/ÖGE rows |
| 19–64 | 0.8 g/kg/day | 0.8 g/kg/day | Recommended intake for healthy adults 19 to under 65 |
| 65 | 1.0 g/kg/day | 1.0 g/kg/day | Configured older-adult estimated value at the inclusive product boundary |

Daily grams equal selected g/kg multiplied by current body weight. This is a reference target calculation, not a measured individual requirement.

At no more than five total logged training hours per week, sport alone does not increase the base target. More than five hours makes a supported, generally healthy user eligible for a 1.2–2.0 g/kg/day athletic range. The default inside that range is an application rule:

| Deterministic selection (first applicable) | Default g/kg/day | Rule key |
|---|---:|---|
| Weight-loss goal | 1.8 | `weight_loss_with_substantial_training` |
| Weight-gain goal or strength is dominant training focus | 1.7 | `strength_or_weight_gain` |
| Athletic-performance goal | 1.6 | `athletic_performance` |
| Mixed/team focus | 1.5 | `mixed_or_team` |
| Endurance focus with maintenance/general context | 1.4 | `endurance_maintenance` |
| Other athletic pattern | 1.4 | `other_athletic` |

Training focus is the category with greatest weekly minutes. Strength, mixed, endurance and other form the deterministic tie-break order. Cycling, running, swimming and endurance training enter the endurance bucket; team/mixed enter mixed; mobility/recovery and `other` enter other.

Every eligible result reports 1.2 minimum, the selected default, and 2.0 optional upper bound with grams/day. The upper bound is not always selected. Unsupported medical scope suppresses the athletic range and, when kidney disease coincides with an otherwise eligible elevated target, returns `HIGH_PROTEIN_KIDNEY_CONDITION` in addition to the unsupported kidney flag.

## Fat, saturated fat and carbohydrate

The standard profile uses the selected goal-energy range when available:

```text
protein_energy_kcal = selected_protein_g × 4
fat_energy_kcal     = energy_kcal × 0.30
fat_g               = fat_energy_kcal / 9
carbohydrate_kcal   = energy_kcal - protein_energy_kcal - fat_energy_kcal
carbohydrate_g      = carbohydrate_kcal / 4
```

The same default protein grams/day is used across the energy range; fat is 30% of each bound and carbohydrate is the remainder. At the midpoint:

```text
saturated_fat_max_g = midpoint_energy × 0.10 / 9
```

Macro energy uses 4 kcal/g protein, 4 kcal/g carbohydrate and 9 kcal/g fat. The midpoint energy sum is checked from unrounded values. Negative remaining carbohydrate is an error, not silently clamped.

The report returns grams and energy percentages. When the calculated carbohydrate share is at or below 50%, it adds a non-critical information flag explaining that the combination is below the standard “over 50%” mixed-diet guidance; it does not force an impossible total or call another distribution optimal.

Therapeutic or ketogenic profiles are not implemented.

## Fibre

For every point in the selected energy range:

```text
energy_relative_g = 14.6 × energy_kcal / 1000
fibre_target_g = max(30, energy_relative_g)
```

The midpoint report explains whether the absolute or energy-relative rule governs; lower/upper values correspond to their unrounded energy bounds. Method: `higher_of_30_g_or_14_6_g_per_1000_kcal`. This is a guideline/reference target, not a diagnosis.

## Hydration

The MVP performs an age-band lookup of DGE baseline guideline values; it does not scale by body weight, PAL or estimated sweat. Total includes beverages, water in solid food and oxidation water:

| Age | Beverages | Food | Oxidation | Total water |
|---:|---:|---:|---:|---:|
| 18 (source band 15–<19) | 1,530 ml | 920 ml | 350 ml | 2,800 ml |
| 19–24 | 1,470 ml | 890 ml | 340 ml | 2,700 ml |
| 25–50 | 1,410 ml | 860 ml | 330 ml | 2,600 ml |
| 51–64 | 1,230 ml | 740 ml | 280 ml | 2,250 ml |
| 65 | 1,310 ml | 680 ml | 260 ml | 2,250 ml |

Method: `dge_age_banded_baseline_water_reference`. The UI must not confuse total water with beverage-only volume. Heat, exercise, dry/cold air, illness and individual sweat loss can change needs; the engine does not prescribe dehydration/electrolyte treatment or unsupported pregnancy/lactation values.

## Micronutrient lookup

The engine iterates the fixed 27-code catalog and matches by:

- `age_min_years <= age < age_max_years_exclusive` (or open maximum);
- physiological reference-table category where the row is category-specific;
- pregnancy state; and
- breastfeeding state.

An exact category row is preferred over a category-independent row. Duplicate/overlapping equally specific rows fail loading. Each available target retains value/range, unit, reference-value category, source identifier/note and reference-set metadata.

No matching row produces a structured unavailable reason, not zero or a substituted value. The current subset has significant gaps, especially at age 18; see [reference_data_incomplete.md](reference_data_incomplete.md). A reference target is not a strict individual daily threshold and cannot diagnose intake/deficiency because the MVP has no food diary or biomarker data.

## Food-group recommendations

The engine returns structured DGE 2024 general orientation for:

- water/calorie-free beverages;
- vegetables and fruit (combined minimum five portions/day);
- legumes (at least weekly) and nuts/seeds (daily);
- whole-grain choices;
- plant oils;
- dairy or suitable alternatives;
- fish;
- meat/processed meat; and
- highly processed discretionary foods.

Source amounts are orientation for healthy 18–65-year-old adults eating mixed diet at about 2,000 kcal/day. The MVP does not scale them, score compliance or claim specific vegan equivalents because it has no food consumption data. Dietary preferences/restrictions are stored but do not alter this general list in v1.

## Presentation rounding

Only `display_value` is rounded; calculation inputs, stored raw values and comparisons use unrounded decimals.

| Kind | Display places |
|---|---:|
| BMI | 1 |
| Ratios | 2 |
| Mass (kg) | 1 |
| Energy (kcal) | 0 |
| PAL | 2 |
| Protein g/kg | 1 |
| Grams | 1 |
| Percent | 1 |
| Water (ml) | 0 |
| Micronutrients | 2 |

German presentation replaces the decimal point with comma and uses `ROUND_HALF_UP`. Ranges are rounded only after both endpoints have been computed.

## Persisted metric catalogue

The assessment persists the following stable metric-code families. Optional anthropometric metrics appear only when their required measurement exists. Macro and fibre rows are still present with `raw_value = null` and `display_value = "Nicht verfügbar"` when the supported goal-energy target is withheld. Every one of the 27 micronutrient catalogue entries is present; a missing verified row is represented explicitly as unavailable.

| Metric code | Method code or selection rule |
|---|---|
| `anthropometrics.bmi` | `bmi_weight_divided_by_height_squared` |
| `anthropometrics.waist_to_height_ratio` | `waist_cm_divided_by_height_cm` |
| `anthropometrics.waist_to_hip_ratio` | `waist_cm_divided_by_hip_cm` |
| `body_composition.fat_mass_kg` | `weight_times_body_fat_fraction` |
| `body_composition.fat_free_mass_kg` | `weight_minus_fat_mass` |
| `energy.resting_energy` | measured override or category-specific Mifflin method |
| `energy.resting_energy_formula_comparison` | category-specific Mifflin method; present with measured REE |
| `activity.pal` | documented-sport band or manual-override method |
| `energy.maintenance` | `resting_energy_times_pal_range` |
| `energy.goal_target` | goal-adjustment method or unsupported-scope withholding method |
| `protein.grams_per_kg` | exact protein selection-rule ID |
| `protein.grams_per_day` | `protein_g_per_kg_times_body_weight` |
| `macros.protein_grams`, `macros.protein_energy_percent` | `macro_energy_balance_4_4_9` |
| `macros.fat_grams`, `macros.fat_energy_percent` | `macro_energy_balance_4_4_9` |
| `macros.saturated_fat_max_grams`, `macros.saturated_fat_max_energy_percent` | `macro_energy_balance_4_4_9` |
| `macros.carbohydrate_grams`, `macros.carbohydrate_energy_percent` | `macro_energy_balance_4_4_9` |
| `macros.energy_sum` | `macro_energy_balance_4_4_9` |
| `fiber.target` | `higher_of_30_g_or_14_6_g_per_1000_kcal` |
| `hydration.total_water`, `hydration.beverages`, `hydration.food`, `hydration.oxidation_water` | `dge_age_banded_baseline_water_reference` or unavailable method |
| `micronutrients.<catalogue_code>` | `versioned_reference_value_lookup` or `reference_value_unavailable` |

For withheld macro/fibre rows, the method is `target_withheld_without_supported_energy_target`. Food-group recommendations live in the assessment summary and top-level engine result rather than masquerading as calculated nutrient metrics.

## Confidence labels

| Label | Meaning/examples |
|---|---|
| `measured` | User-supplied measured REE, with source/date |
| `derived` | Exact arithmetic from supplied measurements: BMI, ratios, fat/fat-free mass |
| `estimated` | Mifflin REE, PAL/TDEE and model-derived targets |
| `reference_target` | DGE/ÖGE-based protein, fibre, water or nutrient target |

An estimate derived from estimated body-fat data remains limited by that source even if its arithmetic is exact.

## Safety and information flags

Blocking scope flags are stable machine codes:

- `UNSUPPORTED_AGE`
- `UNSUPPORTED_PREGNANCY`
- `UNSUPPORTED_BREASTFEEDING`
- `UNSUPPORTED_EATING_DISORDER`
- `UNSUPPORTED_DIABETES`
- `UNSUPPORTED_KIDNEY_DISEASE`
- `UNSUPPORTED_LIVER_DISEASE`
- `UNSUPPORTED_PRESCRIBED_DIET`
- `UNSUPPORTED_METABOLIC_CONDITION`
- `UNSUPPORTED_PROFESSIONAL_CARE_CONDITION`
- `HIGH_PROTEIN_KIDNEY_CONDITION` where relevant

Other exact application flags are:

- `PAL_RANGE_CAPPED`
- `ENERGY_DEFICIT_CAPPED`
- `ENERGY_TARGET_BELOW_REE`
- `AGGRESSIVE_REQUESTED_WEIGHT_CHANGE`
- `REQUESTED_WEEKLY_RATE_NOT_MODELED`
- `CARBOHYDRATE_SHARE_BELOW_STANDARD_GUIDANCE`

These warning/information messages are product behavior, not diagnoses.

## Known limitations

- Mifflin–St Jeor has individual prediction error and uses a binary physiological equation category.
- PAL is a broad self-selected range; the +0.3 session rule cannot verify distinct exercise days, energy intensity or double counting beyond configured assumptions.
- Measured REE is trusted within plausibility bounds; the MVP cannot verify protocol/device quality or recency beyond the supplied metadata.
- Goal percentages and REE floor are conservative product rules, not validated prescriptions or guarantees.
- Current weight is used for g/kg protein; body-size/reference-weight nuances are not modeled.
- There is no energy adaptation, thermic-effect detail, longitudinal calibration, food intake, nutrient bioavailability, laboratory value or supplement model.
- Hydration is a static age baseline; weather, sweat, altitude, illness and electrolyte loss are not calculated.
- Many micronutrient rows are deliberately unavailable; no upper-limit system is complete.
- Food-group recommendations are mixed-diet general orientation and are not personalized from consumption data.
- Screening relies on truthful self-report and is not a clinical assessment.
- The output has not been clinically validated and must not be used for medical nutrition therapy.

## Planned day interpretation

A daily plan describes intended food quantities, not confirmed consumption. Its comparison uses
immutable targets from the selected assessment with current food and recipe values. Missing source
nutrients remain unknown and can make relations or remaining amounts indeterminate; known amounts
are lower bounds. Minimums, maximums, ranges and reference values retain distinct semantics. The
wording does not diagnose deficiency or excess, and the system generates no automatic diet
recommendation, optimization or medical interpretation.
# Automated meal-plan drafts

Automation reuses stored assessment targets and recipe calculations. It presents target fit as a
planning aid, preserves target kinds (range, minimum, maximum or reference) and never converts a
reference value into a medical limit. Safety-blocked assessments cannot be automated. Candidate
scores are explainable suitability signals, not health claims or guarantees of nutritional
optimality.

The optional optimizer uses a discrete mathematical model reflecting selected constraints and
weights. `Optimal` means optimal only for that model—not medically optimal. Deviations are planning
heuristics; maximums are not goals, incomplete recipe data limits reliability, and allergy,
intolerance and explicit exclusions are never relaxed.
