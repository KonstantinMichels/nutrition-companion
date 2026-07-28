# Scientific source register

**Status:** Source catalogue for the MVP  
**Verification/access date:** 2026-07-28  
**Scope:** Generally healthy adults aged 18 through 65; unsupported conditions do not receive an ordinary goal/high-protein assessment

## Provenance policy

This register records sources; it is not permission to reproduce a copyrighted dataset. Seed files include only values verified against an official source and the metadata required to identify that source. Missing or insufficiently verified values stay unavailable and are recorded in [reference_data_incomplete.md](reference_data_incomplete.md).

Scientific references are separate from Nutrition Companion application rules. Weight-goal percentages, PAL midpoints/sport mapping, protein-range selection, validation bounds, display uncertainty and rounding are product rules under `nutrition_companion_mvp_v1`; they must never be attributed to DGE, ÖGE, EFSA, WHO or Mifflin et al.

IDs in the first table are the exact identifiers stored in the checked-in seed metadata. The assessment stores the source/reference-set metadata actually used at calculation time; an old assessment is not rewritten when this catalogue changes. Context-only sources in the second table are documentation aids and are not falsely presented as the numeric source of a metric.

## Persisted calculation sources

| Persisted seed ID | Organization/authors | Title / edition | Implemented use | Official/primary location | Accessed |
|---|---|---|---|---|---|
| `mvp_spec_anthropometrics` | Nutrition Companion | MVP anthropometric formulas / `nutrition_companion_mvp_v1`; rules effective 2026-07-28 | BMI, waist ratios and body-composition arithmetic specified by the product brief; deliberately recorded as an application specification rather than invented external provenance | Local application specification; WHO BMI definition is listed as context below | 2026-07-28 |
| `mifflin_st_jeor_1990` | Mifflin MD et al. | “A new predictive equation for resting energy expenditure in healthy individuals,” *AJCN* 51(2):241–247; DOI 10.1093/ajcn/51.2.241 | Coefficients for both physiological reference categories when measured REE is absent | [PubMed record, PMID 2305711](https://pubmed.ncbi.nlm.nih.gov/2305711/) | 2026-07-28 |
| `dge_pal_reference` | DGE | Energy-intake FAQ and energy reference; derivation status 2015 | PAL bands, `TDEE = REE × PAL`, and source context for the +0.3 strenuous-leisure example | [DGE energy FAQ](https://www.dge.de/gesunde-ernaehrung/faq/energiezufuhr/) and [energy reference](https://www.dge.de/wissenschaft/referenzwerte/energie/) | 2026-07-28 |
| `dge_protein_2017` | DGE/ÖGE | Protein reference, derivation status 2017; 3rd edition 2025 / erratum May 2026 | Age-specific general protein rows; 0.8 g/kg/day for healthy adults 19 to under 65 | [DGE protein reference](https://www.dge.de/wissenschaft/referenzwerte/protein/) and [protein FAQ](https://www.dge.de/gesunde-ernaehrung/faq/ausgewaehlte-fragen-und-antworten-zu-protein-und-unentbehrlichen-aminosaeuren/) | 2026-07-28 |
| `dge_sport_protein_2020` | DGE Sports Nutrition Working Group | Position paper, *Ernährungs Umschau* 67(7):132–139 | Context-dependent 1.2–2.0 g/kg/day range above five training hours/week for healthy adults | [DGE position-paper page](https://www.dge.de/presse/meldungen/2020/positionspapier-zur-proteinzufuhr-im-sport/) | 2026-07-28 |
| `dge_macronutrients` | DGE/ÖGE | Fat/carbohydrate references, 3rd edition 2025 / erratum May 2026 | 30 En% total fat, max 10 En% saturated fat, >50 En% carbohydrate guidance where compatible, and transparent 4/4/9 conversion | [Carbohydrate reference](https://www.dge.de/wissenschaft/referenzwerte/kohlenhydrate/), [DGE position](https://www.dge.de/wissenschaft/stellungnahmen-und-positionspapiere/positionen/richtwerte-fuer-die-energiezufuhr-aus-kohlenhydraten-und-fett/), [energy reference](https://www.dge.de/wissenschaft/referenzwerte/energie/) | 2026-07-28 |
| `dge_fiber_2021` | DGE/ÖGE | Fibre reference, derivation status 2021; 3rd edition 2025 / erratum May 2026 | At least 30 g/day and at least 14.6 g/1,000 kcal; engine selects the higher applicable target | [DGE fibre FAQ](https://www.dge.de/gesunde-ernaehrung/faq/ausgewaehlte-fragen-und-antworten-zu-ballaststoffen/) | 2026-07-28 |
| `dge_water_2000` | DGE/ÖGE | Water reference, derivation status 2000; 3rd edition 2025 / erratum May 2026 | Age-banded beverages, solid-food water, oxidation water and total-water rows | [DGE water reference](https://www.dge.de/wissenschaft/referenzwerte/wasser/) | 2026-07-28 |
| `dge_reference_tool_adults_2026` | DGE/ÖGE | Individualized reference tables, 3rd edition 2025 / erratum May 2026 | Verified adult subset for vitamin A, E, K, thiamin, riboflavin, niacin, pantothenic acid, B6, biotin, folate and B12 | [Official DGE/ÖGE reference-value tool](https://www.dge.de/wissenschaft/referenzwerte-tool/) | 2026-07-28 |
| `dge_vitamin_c_2015` | DGE/ÖGE | Vitamin C reference, derivation status 2015 | Verified category/age rows, including the source band covering age 18; smoker-specific values are not selected because smoking is not collected | [DGE vitamin C reference](https://www.dge.de/wissenschaft/referenzwerte/vitamin-c/) | 2026-07-28 |
| `dge_vitamin_d_2012` | DGE/ÖGE | Vitamin D reference, derivation status 2012 | 20 µg/day estimated value under the source condition of absent endogenous synthesis | [DGE vitamin D reference](https://www.dge.de/wissenschaft/referenzwerte/vitamin-d/) | 2026-07-28 |
| `dge_calcium_2013` | DGE/ÖGE | Calcium reference, derivation status 2013 | Verified age-specific recommended-intake rows | [DGE calcium reference](https://www.dge.de/wissenschaft/referenzwerte/calcium/) | 2026-07-28 |
| `dge_phosphorus_2022` | DGE/ÖGE | Phosphorus reference, derivation status 2022 | Verified age-specific estimated-value rows | [DGE phosphorus reference](https://www.dge.de/wissenschaft/referenzwerte/phosphor/) | 2026-07-28 |
| `dge_iodine_2025` | DGE/ÖGE | Iodine reference, derivation status 2025 | Verified 150 µg/day row for age 15+; pregnancy/lactation values are outside automatic MVP scope | [DGE iodine reference](https://www.dge.de/wissenschaft/referenzwerte/jod/) | 2026-07-28 |
| `dge_food_based_recommendations_2024_mvp_v1` | DGE | *Gut essen und trinken* / DGE food circle; published 2024 | Structured general food-group orientation for healthy adults 18–65 eating mixed diet at about 2,000 kcal/day | [DGE recommendations](https://www.dge.de/gesunde-ernaehrung/gut-essen-und-trinken/dge-empfehlungen/) and [food circle](https://www.dge.de/gesunde-ernaehrung/gut-essen-und-trinken/dge-ernaehrungskreis/) | 2026-07-28 |

The enclosing reference set is `dge_oege_v3_mvp_2026_05`, version `3rd-edition-2025_erratum-2026-05_subset-v1`. It is explicitly marked incomplete. DGE's [reference-values overview](https://www.dge.de/wissenschaft/referenzwerte/) identifies the 3rd edition and erratum context (accessed 2026-07-28).

## Context and interpretation sources

| Documentation ID | Source | Why it is cited | Official/primary location | Accessed |
|---|---|---|---|---|
| `WHO_BMI_CONTEXT` | WHO Regional Office for Europe; live fact sheet, publication year not stated | Corroborates the kg/m² BMI definition; it is not represented as the persisted source for all local anthropometric application rules | [WHO Europe fact sheet](https://www.who.int/europe/news-room/fact-sheets/item/nutrition---maintaining-a-healthy-lifestyle) | 2026-07-28 |
| `EFSA_DRV_TERMINOLOGY` | European Food Safety Authority; page last reviewed 5 August 2024 | Helps distinguish AR, PRI, AI, macronutrient reference-intake range and UL; no EFSA number replaces a missing DGE/ÖGE row | [EFSA DRV overview](https://www.efsa.europa.eu/en/topics/topic/dietary-reference-values) | 2026-07-28 |

## What each source does not establish

- The WHO BMI definition does not make BMI diagnostic, nor does it justify using BMI alone for a nutrition recommendation.
- The Mifflin–St Jeor paper supplies a population-derived prediction equation, not a personal measurement or guaranteed energy requirement. The UI's “reference category A/B” is an implementation abstraction needed for equation selection and must not be presented as gender identity.
- DGE PAL categories do not establish that every person's activity fits one exact factor. The MVP's chosen midpoint and double-counting prevention are application rules.
- The DGE sports-protein range does not say every person training over five hours should receive 2.0 g/kg/day. Selection within the range is a transparent application rule, and the MVP suppresses high-protein targets for unsupported medical screens.
- The DGE macro profile is a general reference profile, not proof that one distribution is optimal for all users. Protein and fat allocation can make a >50 En% carbohydrate share mathematically incompatible; the app reports rather than hides that.
- Water rows are baseline guideline values under average conditions, not sweat-loss, dehydration, electrolyte or illness treatment advice.
- DGE food-based recommendations apply to healthy adults 18–65 and, on the cited page, a mixed diet. Vegetarian/vegan adaptations need separately verified source material before specific equivalent targets are claimed.
- EFSA terminology helps preserve meaning but is not substituted for missing DGE/ÖGE numeric targets.

## Reference-value type preservation

The storage/response layer must keep source semantics such as `recommended_intake`, `estimated_value`, `guideline_value`, `adequate_intake`, `reference_intake_range` or `upper_limit`. The UI should explain these types and must not render an estimated value or guideline as an individual minimum, or a UL as a target.

## Verification procedure for a numeric seed update

1. Use the official source/table and confirm age interval boundaries, physiological category, pregnancy/breastfeeding filter, unit, value type and every footnote.
2. Record organization, title/edition, publication/derivation status, official URL, access date and internal data version.
3. Obtain a second-person scientific review; do not rely on a search-result snippet or a commercial summary.
4. Validate units and decimal precision mechanically; reject duplicate/overlapping target groups and malformed source data.
5. Add boundary and missing-value lookup tests.
6. Create a new version rather than mutating a set referenced by an old assessment.
7. Update this register and [reference_data_incomplete.md](reference_data_incomplete.md).

If source access/licensing does not permit reliable verification or redistribution, the value remains unavailable. U.S. values or plausible placeholders must not be substituted silently.
