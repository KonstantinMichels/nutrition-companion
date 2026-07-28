# DPIA threshold screening

**Status:** Preliminary engineering screening, not a completed Data Protection Impact Assessment  
**Screening date:** 2026-07-28  
**Reviewer:** `[qualified privacy reviewer required]`  
**Next review date:** `[before any public production release]`

## Preliminary decision

**Production release is blocked until a qualified reviewer decides and documents whether a formal DPIA is required.**

The local single-user development instance, using synthetic data and no external processors, does not establish the scale or operational context of a public service. For the intended product, a formal DPIA is a credible requirement and should be planned for: the system deliberately processes health-related/special-category information and systematically evaluates personal body/activity data to generate individualized nutrition targets and safety flags. The absence of medical claims, AI or legal effects reduces some risks but does not remove the confidentiality, autonomy or harmful-reliance risks.

This screening neither concludes “DPIA required” nor “DPIA unnecessary.” Only the future controller, advised by qualified privacy professionals and using the final facts and competent-authority list, can make that determination.

GDPR Article 35 requires a DPIA where processing is likely to result in a high risk, and identifies systematic/comprehensive evaluation with significant effects, large-scale special-category processing and large-scale public monitoring as examples. The BfDI explains the threshold and links the German DSK list for non-public bodies. See [BfDI: Datenschutz-Folgenabschätzungen und Listen](https://www.bfdi.bund.de/DE/Fachthemen/Inhalte/Technik/Datenschutz-Folgenabschaetzungen.html), the [DSK Article 35(4) list (version 1.1)](https://www.datenschutzkonferenz-online.de/media/ah/20181017_ah_DSK_DSFA_Muss-Liste_Version_1.1_Deutsch.pdf), and the official [GDPR Article 35](https://eur-lex.europa.eu/eli/reg/2016/679/oj), accessed 2026-07-28.

## Processing screened

The prospective operation would collect and retain a pseudonymous adult profile containing body measurements, activity/sport, goals, dietary restrictions and binary health screening; calculate deterministic individualized energy/nutrient estimates and safety flags; preserve immutable history; cache a small result locally; and provide consent, export and deletion controls.

Excluded from this screening because it is not implemented: food diary, recipes, meal plans, wearables/sensors, continuous monitoring, location, camera/barcode, social-media import, AI/LLM, clinician access, minors, production authentication, production hosting and an optional web dashboard. Each inclusion would trigger a rescreen.

## Criteria assessment

| Criterion | Preliminary result | Reasoning / missing fact |
|---|---|---|
| Evaluation or scoring | **Present** | Deterministic formulas and rules evaluate personal body/activity data and generate individualized estimates, warnings and supported-scope status |
| Automated decisions with legal or similarly significant effect | **Not intended; verify** | Output is advisory lifestyle planning, no access to healthcare/employment/insurance and no treatment decision. Potential behavioral influence remains meaningful; final claims and integrations matter |
| Systematic monitoring | **Not present in MVP** | No passive sensor collection, location, background sync, diary or public-space monitoring |
| Sensitive/highly personal data | **Present** | Body/health screening and inferred nutrition requirements are sensitive and may be Article 9 health data |
| Large-scale processing | **Unknown** | Local MVP is one development profile; public user count, geographic reach, record depth, duration and operator are undecided |
| Matching/combining datasets | **Not present** | User-entered MVP data is not matched with advertising, social, clinical, insurer, wearable or purchased datasets |
| Vulnerable people | **Reduced, not absent** | Minors and medically unsupported groups are screened out of normal targets, but users concerned about weight/eating behavior may be vulnerable; no robust age identity check exists |
| Innovative/new technology or organizational solution | **Limited** | Conventional mobile/API/database and deterministic formulas; no AI. Sensitive inference and secure local cache still require careful validation |
| Processing that prevents exercise of a right/use of a service | **Limited** | Refusal/withdrawal prevents an assessment but not an essential/public service. Deletion/export must remain accessible; final business model could change this |

The WP29/EDPB criteria are indicators, not a substitute for Article 35's fact-specific high-risk test or the applicable supervisory-authority list.

## Potential harm

| Harm scenario | Impact | Existing/design mitigation | Residual/unresolved issue |
|---|---|---|---|
| Unauthorized disclosure of body/disease/eating-disorder answers | Dignitary harm, stigma, discrimination, distress | Data minimization, secure mobile storage, TLS requirement, no payload logs, no external processors | Production auth, hosting, admin access, backup and monitoring absent |
| Cross-profile access/export/deletion | Disclosure or irreversible loss | Profile-scoped dependency and transactional operations | Development resolver is not authentication; public use prohibited until object authorization tested |
| Over-reliance on estimated energy/weight targets | Undereating, harmful behavior or delayed professional advice | Non-medical language, ranges/uncertainty, unsupported screens, no targets for flagged cases, target-below-REE warning | Human-factors/safety validation and eating-disorder review incomplete |
| Incorrect reference/rule/calculation | Misleading targets | Deterministic engine, provenance/versioning, immutable snapshots, tests, missing values shown unavailable | Independent scientific review and reference-update governance needed |
| Consent not valid/informed | Loss of autonomy/unlawful processing | Unselected checkbox, purpose/text version, refusal/withdrawal, separate deletion | Legal basis and final German wording undecided |
| Excess retention or deletion failure | Persistent exposure/loss of control | User history/profile deletion, draft TTL, no soft-delete-only design | Production backups, verification jobs and support process absent |
| Device loss/compromise or backup leak | Local draft/cache disclosure | Minimal encrypted storage and key-store abstraction; clear controls | Rooted/unlocked device limitations and backup config need platform testing |
| Re-identification of UUID data | Unexpected linkage | No names/contact IDs, avoid UUID in logs | Small profile combinations remain identifying; pseudonymization is not anonymity |

## Existing risk-reduction design

- supported population limited to adults 18–65 who report being generally healthy;
- calm safety flags and no ordinary weight/high-protein targets for unsupported screens;
- no medical diagnosis/treatment claims, AI, sensors, analytics, advertising or third-party tracking;
- minimal binary screening rather than detailed diagnoses;
- deterministic engine isolated from network/HTTP/database;
- immutable versioned assessment snapshots and visible uncertainty;
- explicit versioned consent with refusal/withdrawal and separate export/deletion;
- encrypted minimal device storage, no sensitive SharedPreferences, local draft expiry;
- body/request/result logging prohibition and short technical log retention; and
- transactional active-data deletion and documented future backup requirements.

These mitigations reduce risk; they do not prove low residual risk or compliance.

## Unresolved questions for the reviewer

1. Who is the controller, where is it established and which supervisory authority/list applies?
2. What is the expected user count, geography, assessment frequency, retention and record depth?
3. Are the profile and derived targets “data concerning health” in each processing context (working assumption: likely yes)?
4. What Article 6 basis and Article 9 condition apply to each purpose? Is proposed consent sufficiently granular and freely given?
5. Does the systematic evaluation or any future integration create legal/similarly significant effects or Article 22 implications?
6. Are people with eating disorders or weight-related vulnerability adequately protected despite self-screening?
7. Which hosting, identity, logging, support, backup and distribution providers/regions will be used?
8. What production security, authentication, administrator, deletion and recovery evidence exists?
9. Are controller-scale and DSK-list combinations sufficient to make a DPIA mandatory?
10. If residual high risk remains after a DPIA, is prior supervisory consultation required under Article 36?

## Required next action

Before any real-user pilot or public release, the accountable controller must provide final processing facts to a qualified reviewer, complete the applicable DSK/authority-list analysis, document the signed threshold decision, and—if required or chosen as prudent—complete a DPIA covering necessity/proportionality, risks, safeguards, residual risks and consultation. Record review name/date/version here and link the approved assessment from a restricted governance location (do not commit sensitive threat details or real user data).

A new screen is mandatory if data categories, claims, users, scale, vendors/transfers, sensors, AI, clinician integration, authentication, meal/weight tracking or monetization changes.

