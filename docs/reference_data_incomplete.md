# Incomplete scientific reference data

**Status:** Required transparency record for reference set `dge_oege_v3_mvp_2026_05`  
**Internal version:** `3rd-edition-2025_erratum-2026-05_subset-v1`  
**Verified:** 2026-07-28  
**Seed declaration:** `is_complete: false`

The application remains runnable with a deliberately incomplete micronutrient subset. An unavailable result is correct behavior; a plausible placeholder, U.S. value or silently reused neighboring age/category value is not.

The official DGE page identifies the current work as DGE/ÖGE *Referenzwerte für die Nährstoffzufuhr*, 3rd edition, first issue 2025, with erratum status May 2026. The implemented subset was checked against official DGE pages/tool on the access date. See [nutrition_sources.md](nutrition_sources.md).

## Catalog coverage

The generic catalog contains all 27 requested nutrient codes. Sixteen have at least one verified numeric row; eleven are catalog-only and unavailable for every MVP user.

### No numeric row in the seed

| Code | Display name | Reason omitted | Affected output | Official source needed / next verification step |
|---|---|---|---|---|
| `magnesium` | Magnesium | Complete supported-age/category rows and footnotes were not independently verified during implementation | Target reported unavailable | Verify all 18–65 DGE/ÖGE age/category rows, value type, unit and footnotes in the [official reference tool](https://www.dge.de/wissenschaft/referenzwerte-tool/); second-person review, then add a new reference-set version |
| `potassium` | Kalium | Same | Unavailable | Verify current DGE/ÖGE rows and `estimated_value`/other type; test every boundary |
| `sodium` | Natrium | Same | Unavailable | Verify current rows, type and whether value is a guideline/estimate rather than a minimum |
| `chloride` | Chlorid | Same | Unavailable | Verify current rows, type, unit and coupled footnotes |
| `iron` | Eisen | Current 2024-era category/age detail was not fully transcribed and reviewed | Unavailable | Verify official current table for every MVP reference category/age band and preserve category/footnotes; do not infer menstruation or another uncollected characteristic |
| `zinc` | Zink | Official targets depend on dietary phytate context; MVP does not collect a reliable phytate estimate and no honest selection rule is implemented | Unavailable | Decide with scientific review whether to return the complete official range/context explanation or add a justified input; never select a midpoint without labeling it an application rule |
| `selenium` | Selen | Complete rows/footnotes not independently verified | Unavailable | Verify official rows, value type, units and applicable category boundaries |
| `copper` | Kupfer | Complete rows/footnotes not independently verified | Unavailable | Verify official source and preserve value type/range rather than collapsing it |
| `manganese` | Mangan | Complete rows/footnotes not independently verified | Unavailable | Verify official source and whether it is a range/estimated value |
| `chromium` | Chrom | Complete rows/footnotes not independently verified | Unavailable | Confirm whether a current DGE/ÖGE value exists in the cited edition and can be represented; absence must remain absence |
| `molybdenum` | Molybdän | Complete rows/footnotes not independently verified | Unavailable | Verify official source, range/type/unit and supported age boundaries |

### Age 18 coverage gaps in otherwise seeded nutrients

The supported product scope begins at 18, while many implemented adult rows start at 19. At exactly age 18, only `vitamin_c`, `vitamin_d`, `calcium`, `phosphorus` and `iodine` currently have matching verified rows. The following 11 seeded nutrients therefore remain unavailable at age 18:

| Codes | Reason | Needed completion |
|---|---|---|
| `vitamin_a`, `vitamin_e`, `vitamin_k`, `thiamin`, `riboflavin`, `niacin`, `pantothenic_acid`, `vitamin_b6`, `biotin`, `folate`, `vitamin_b12` | Implemented rows begin at age 19; substituting the 19+ value for an 18-year-old would erase a source age boundary | Verify and seed the official 15-to-under-19 rows (including both applicable table categories, value types and footnotes) in a new set |

Together with the 11 catalog-only nutrients above, an 18-year-old currently sees 22 of 27 micronutrient codes as unavailable. This is intentional and should be stated in the report rather than presented as a server error.

## Unsupported physiological states

No pregnancy or breastfeeding micronutrient/water target rows are used for automatic assessment. Those states are outside the MVP supported scope. The profile can be saved, but calculation returns structured unsupported-scope flags and suppresses ordinary goal/high-protein recommendations.

Adding official pregnancy/lactation values alone would not make those users supported. It would require new safety, product, scientific, privacy and regulatory review.

## Upper limits and therapeutic interpretation

The data model supports `lower_value`, `upper_value` and different reference-value categories, but this subset does not claim a complete set of tolerable upper intake levels. Do not:

- use a recommended intake as an upper limit;
- infer an upper limit from the highest displayed target;
- combine a DGE/ÖGE target silently with a U.S. limit;
- present an estimated value as an individual deficiency threshold; or
- use this assessment to recommend supplements or diagnose deficiency.

If EFSA upper levels are added, they require their own official source/version, target-group mapping, unit/form conversion, applicability notes and review. They must not overwrite the DGE/ÖGE reference-value type.

## Known source-context limitations in available rows

| Area | Limitation | Current honest behavior |
|---|---|---|
| Vitamin C | Official guidance contains smoking-related context; smoking status is not collected | Source note says the smoking-specific increase is not selected; do not infer smoking status |
| Vitamin D | The 20 µg/day estimated value applies when endogenous synthesis is absent | Preserve `estimated_value` and its source note; do not present it as a universal measured requirement |
| Category-dependent tables | `reference_category_a/b` map only to the source table's two physiological columns | Explain that this calculation/reference input is not gender identity |
| DGE food-based recommendations | Cited structured amounts apply to healthy adults 18–65 with mixed diet and approximately 2,000 kcal/day | Present as general orientation, not a personalized compliance score; no unverified vegan equivalence |
| Water | Baseline assumes average conditions/adequate energy and includes oxidation water in total | Show beverage, food and total/oxidation components separately; no sweat/electrolyte or illness treatment |
| Protein | The MVP multiplies the configured g/kg rule by current body weight and does not establish an individual measured need | Label reference/estimated target and limitations; unsupported medical screens suppress athletic targets |

## How unavailability propagates

For every catalog nutrient the lookup returns either a matching typed reference row or an unavailable reason. Missing rows do not abort other calculations. The assessment/report:

- keeps the nutrient code/display name/unit in the known catalog;
- marks the target unavailable with a German explanation;
- records unavailable codes in assessment summary metadata for the client;
- does not emit `0`, `null` disguised as zero, a neighboring category value or a fabricated range; and
- preserves the incomplete reference-set identifier/version on the assessment.

The Android result view must say “Nicht verfügbar” rather than imply the user has a zero target or a deficiency.

## Completion workflow

1. Select the exact official DGE/ÖGE table/edition/erratum and confirm reproduction/usage terms.
2. Capture age minimum, exclusive maximum, physiological table category, pregnancy/lactation state, value/range, unit, value category and every applicability footnote.
3. Obtain a second-person qualified scientific verification against the official source—not a search snippet or commercial page.
4. Run overlap/gap/unit validation and boundary tests at ages 18, 19, 25, 51, 65 and any source-specific split.
5. Add lookup and unavailable regression tests.
6. Create a new immutable reference-set identifier/version and seed idempotently; do not edit a set used by old assessments.
7. Update [nutrition_sources.md](nutrition_sources.md), this file and report wording.

Do not mark `is_complete` true until every catalog code and every supported target-group combination is verified, source types/footnotes are preserved, and an independent review is recorded.

