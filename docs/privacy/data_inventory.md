# Personal-data inventory

Progress Tracking umfasst Original- und normalisierte Gewichte, lokale Tage/Uhrzeiten, Messsituationen, private Notizen, getrennte Körperumfänge, Körperzusammensetzung samt Methode und historische Ziele. Trends sind flüchtige Ableitungen.

Pantry data includes profile-owned storage locations, Food references, current and
entered quantities, dates, free-text notes, archive/depletion state, and immutable
movement history with before/after balances and operation identifiers.

Weekly views are sensitive derived planning data calculated from daily plans,
assessments, foods, and recipes. No weekly record, history, local cache, or export copy
is persisted.

**Status:** MVP design/implementation inventory  
**Last reviewed:** 2026-07-28  
**Legal review:** Required before production

## Reading the inventory

This inventory is field-oriented. “Special” means the field is health data or is likely to reveal health information in this context; the final Article 9 classification is a legal-review item. Identifiers and timestamps are personal data when linkable to a profile even if they are not independently health data. A UUID is pseudonymous, not anonymous.

Purpose abbreviations below refer to [processing_purposes.md](processing_purposes.md):

- `NPS` — `nutrition_profile_storage`
- `NAC` — `nutrition_assessment_calculation`
- `AH` — `assessment_history`
- `LOD` — `local_onboarding_draft`
- `LAC` — `local_assessment_cache`
- `TSL` — `technical_security_logging`
- `UDE` — `user_data_export`
- `UDD` — `user_data_deletion`
- `CM` — `consent_management`

Retention shorthand: **profile life** means until complete-profile deletion; **assessment life** means until history or profile deletion; **draft TTL** means the configured abandoned-draft expiry; **log TTL** means the short configured log window. Exact production periods require controller approval in [retention_policy.md](retention_policy.md).

Recipients are “app/API/DB” unless noted: Flutter displays/collects the value, FastAPI validates or orchestrates it, and PostgreSQL stores it. The Nutrition Engine receives only fields needed for assessment. No external processor receives MVP data.

## Profile and measurements

| Field | Source | Purpose | Sensitivity | Location | Retention | Recipient/use | Deletion |
|---|---|---|---|---|---|---|---|
| `profile.id` | Generated UUID | NPS, all profile-scoped actions | Personal/pseudonymous | DB; reserved mobile key exists but is currently not written | Profile life | API/DB; not persistent logs | Profile deletion; reserved local-key purge |
| `profile.birth_date` and derived age at calculation | User/system | NPS, NAC | Special in context | Draft, request, DB; birth date and derived age in assessment snapshot | Profile life; snapshot assessment life | API/engine/DB | Draft/profile/history deletion as applicable |
| `profile.physiological_category` | User | NPS, NAC | Special/sensitive | Draft, request, DB, assessment snapshot | Profile life; snapshot assessment life | Equation/reference lookup | Same |
| `profile.height_cm` | User | NPS, NAC | Special in context | Draft, request, DB, assessment snapshot | Profile life; snapshot assessment life | Body/REE calculations | Same |
| `profile.current_weight_kg` | User | NPS, NAC | Special | Draft, request, DB, assessment snapshot | Profile life; snapshot assessment life | Body/energy/protein calculations | Same |
| `profile.dietary_preference` | User | NPS | Sensitive; beliefs may sometimes be inferable | Draft, request, DB, snapshot | Profile life; snapshot assessment life | Display/future planning; not used to diagnose | Same |
| `profile.preferred_meals_per_day` | User | NPS | Sensitive lifestyle | Draft, request, DB, snapshot | Profile life; snapshot assessment life | Storage/display | Same |
| `profile.preferred_meal_timing` | User | NPS | Sensitive lifestyle | Draft, request, DB, snapshot | Profile life; snapshot assessment life | Storage/display | Same |
| `profile.created_at`, `updated_at` | System | NPS | Personal metadata | DB/export | Profile life | Integrity/export | Profile deletion |
| `measurement.id` | Generated UUID | NPS | Personal/pseudonymous | DB/export; snapshot does not copy this row ID | Profile life | Current-record linkage | Profile deletion |
| `measurement.profile_id` | System | NPS | Pseudonymous | DB only; export nesting conveys ownership without repeating the ID | Profile life | Parent relation | Profile deletion |
| `measurement.measurement_type` | User/app | NPS, NAC where used | Special | Draft/request/DB/export; calculation-relevant types become named snapshot fields | Profile life; copied optional value has assessment life | Selects storage/calculation handling | Draft/profile/history deletion as applicable |
| `measurement.value` (`weight`) | User/device estimate | NPS | Special | Draft/request/DB/export; currently not copied into engine input because `profile.current_weight_kg` is authoritative | Profile life | Stored measurement/future longitudinal context; not used by v1 calculation | Draft/profile deletion |
| `measurement.value` (body-fat %) | User/device estimate | NPS, NAC | Special | Draft/request/DB/snapshot | Profile life; snapshot assessment life | Composition estimate | Same |
| `measurement.value` (waist cm) | User/device estimate | NPS, NAC | Special | Draft/request/DB/snapshot | Profile life; snapshot assessment life | Waist ratios | Same |
| `measurement.value` (hip cm) | User/device estimate | NPS, NAC | Special | Draft/request/DB/snapshot | Profile life; snapshot assessment life | Waist-to-hip ratio | Same |
| `measurement.value` (measured REE) | User/measurement | NPS, NAC | Special | Draft/request/DB/snapshot | Profile life; snapshot assessment life | Measured-REE override | Same |
| `measurement.unit` | User/app | NPS, NAC where used | Personal when linked | Draft/request/DB/export; copied with optional calculation measurement | Same as measurement/copy | Interpretation/validation | Same |
| `measurement.measured_at` | User | NPS, NAC where used | Personal metadata | Draft/request/DB/export; copied with optional calculation measurement | Same as measurement/copy | Recency/provenance | Same |
| `measurement.source_type` | User (`measured`, `device_estimate`, `user_estimate`) | NPS, NAC where used | Sensitive provenance | Draft/request/DB/export; copied with optional calculation measurement | Same as measurement/copy | Confidence/explanation | Same |
| `measurement.created_at` | System | NPS | Personal metadata | DB/export; not copied into assessment snapshot | Profile life | Integrity/export | Profile deletion |

## Activity, sport and goals

| Field | Source | Purpose | Sensitivity | Location | Retention | Recipient/use | Deletion |
|---|---|---|---|---|---|---|---|
| `activity_profile.profile_id` | System | NPS, NAC | Pseudonymous | DB only; snapshot/export nest activity under the profile without copying this ID | Profile life | Relation | Profile deletion |
| `activity_profile.occupational_activity_category` | User | NPS, NAC | Special/sensitive lifestyle | Draft/request/DB/snapshot | Profile/assessment life | PAL selection | Same |
| `activity_profile.average_daily_steps` | User | NPS, NAC | Special activity | Draft/request/DB/snapshot | Profile/assessment life | Activity context/rule | Same |
| `activity_profile.active_commuting` | User | NPS, NAC | Sensitive activity | Draft/request/DB/snapshot | Profile/assessment life | Activity context/rule | Same |
| `activity_profile.movement_notes` | User | NPS, NAC | Special may be included | Draft/request/DB/snapshot | Profile/assessment life | Limited context; not medically reviewed | Same |
| `activity_profile.manual_pal_override` | User | NPS, NAC | Special derived target input | Draft/request/DB/snapshot | Profile/assessment life | Overrides configured PAL after validation | Same |
| `activity_profile.created_at`, `updated_at` | System | NPS | Personal metadata | DB/export | Profile life | Integrity/export | Profile deletion |
| `sport_activity.id` | Generated UUID | NPS | Pseudonymous | DB/export; not copied into assessment snapshot | Profile life | Current-record linkage | Profile deletion |
| `sport_activity.activity_profile_id` | System | NPS, NAC | Pseudonymous | DB only; nesting conveys ownership in export/snapshot | Profile life | Parent relation | Profile deletion |
| `sport_activity.sport_type` | User | NPS, NAC | Special activity | Draft/request/DB/snapshot | Profile/assessment life | Sport/protein rules | Same |
| `sport_activity.sessions_per_week` | User | NPS, NAC | Special activity | Draft/request/DB/snapshot | Profile/assessment life | Weekly duration/rules | Same |
| `sport_activity.minutes_per_session` | User | NPS, NAC | Special activity | Draft/request/DB/snapshot | Profile/assessment life | Weekly duration/rules | Same |
| `sport_activity.intensity` | User | NPS, NAC | Special activity | Draft/request/DB/snapshot | Profile/assessment life | Adjustment/explanation | Same |
| `sport_activity.note` | User | NPS | Special may be included | Draft/request/DB/snapshot | Profile/assessment life | Display/context only | Same |
| `nutrition_goal.profile_id` | System | NPS, NAC | Pseudonymous | DB only; goal content but not this ID is copied/exported | Profile life | Relation | Profile deletion |
| `nutrition_goal.goal_type` | User | NPS, NAC | Special/sensitive | Draft/request/DB/snapshot | Profile/assessment life | Goal adjustment | Same |
| `nutrition_goal.target_weight_kg` | User, optional | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Context; no guaranteed date | Same |
| `nutrition_goal.desired_intensity` | User, optional | NPS, NAC | Special/sensitive | Draft/request/DB/snapshot | Profile/assessment life | Adjustment-rule selection | Same |
| `nutrition_goal.requested_weekly_rate_kg` | User, optional | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Warning/context; no guarantee | Same |
| `nutrition_goal.created_at`, `updated_at` | System | NPS | Personal metadata | DB/export | Profile life | Integrity/export | Profile deletion |

## Dietary restrictions and health screening

| Field | Source | Purpose | Sensitivity | Location | Retention | Recipient/use | Deletion |
|---|---|---|---|---|---|---|---|
| `dietary_restriction.id` | Generated UUID | NPS | Pseudonymous | DB/export; not copied into assessment snapshot | Profile life | Current-record linkage | Profile deletion |
| `dietary_restriction.profile_id` | System | NPS | Pseudonymous | DB only; nesting conveys ownership in export/snapshot | Profile life | Parent relation | Profile deletion |
| `dietary_restriction.restriction_type` (`allergy`, `intolerance`, `excluded_food`, `disliked_food`) | User | NPS | Special when health-related | Draft/request/DB/snapshot | Profile/assessment life | Storage/display; future planning only | Same |
| `dietary_restriction.value` | User | NPS | Special when health-related | Draft/request/DB/snapshot | Profile/assessment life | Storage/display; no diagnosis | Same |
| `dietary_restriction.hard_exclusion` | User | NPS | Special | Draft/request/DB/snapshot | Profile/assessment life | Storage/display; boolean exclusion choice, not a clinical severity score | Same |
| `dietary_restriction.note` | User | NPS | Special may be included | Draft/request/DB/snapshot | Profile/assessment life | Context; not medically reviewed | Same |
| `health_screening.profile_id` | System | NPS, NAC | Pseudonymous | DB/export; not copied as an identifier into engine snapshot | Profile life | Relation | Profile deletion |
| Derived age/supported-scope result | Derived from birth date and calculation time | NAC | Special inference | Engine memory, assessment snapshot/status, response/export | Assessment life | Scope check; no separate `age_outside_scope` database field | History/profile deletion |
| `health_screening.pregnant` | User | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Unsupported-scope flag | Same |
| `health_screening.breastfeeding` | User | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Unsupported-scope flag | Same |
| `health_screening.diagnosed_eating_disorder` | User | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Unsupported-scope flag; no detail sought | Same |
| `health_screening.diabetes` | User | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Unsupported-scope flag | Same |
| `health_screening.kidney_disease` | User | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Scope/high-protein safety | Same |
| `health_screening.liver_disease` | User | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Unsupported-scope flag | Same |
| `health_screening.medically_prescribed_diet` | User | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Unsupported-scope flag | Same |
| `health_screening.serious_metabolic_condition` | User | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Unsupported-scope flag | Same |
| `health_screening.other_professional_nutrition_condition` | User | NPS, NAC | Special | Draft/request/DB/snapshot | Profile/assessment life | Unsupported-scope flag | Same |
| `health_screening.user_note` | User, optional | NPS | Special; free text may contain excess data | Draft/request/DB/snapshot | Profile/assessment life | Stored, not medically reviewed or used for diagnosis | Same |
| `health_screening.screened_at` | System on create/update | NPS | Personal metadata | DB/export; not copied into assessment snapshot | Profile life | Latest/current screening provenance | Profile deletion |

## Consent and privacy actions

| Field | Source | Purpose | Sensitivity | Location | Retention | Recipient/use | Deletion |
|---|---|---|---|---|---|---|---|
| `consent_record.id` | Generated UUID | CM, NAC | Pseudonymous | DB/export; copied into the assessment's consent snapshot | Profile life; snapshot assessment life | Consent relation/provenance | Profile deletion; copied snapshot via history/profile deletion |
| `consent_record.profile_id` | System | CM | Pseudonymous | DB only; export nesting conveys ownership | Profile life in local MVP; production decision pending | Parent relation | Profile deletion under local concept |
| `consent_record.purpose_code` | UI/system | CM | Reveals processing context | Request/DB/export | Same as consent record | Consent enforcement | Same |
| `consent_record.consent_text_version` | UI/system | CM | Personal metadata when linked | Request/DB/export | Same | Reproduce what was accepted | Same; canonical text itself is non-personal config |
| `consent_record.status` | User/system | CM | Personal choice | DB/export | Same | Permit/block new assessment | Same |
| `consent_record.granted_at` | System | CM | Personal metadata | DB/export | Same | Evidence/state | Same |
| `consent_record.withdrawn_at` | User/system | CM | Personal metadata | DB/export | Same | Stops future assessment | Same |
| `consent_record.source` | System (for example, mobile onboarding/settings) | CM | Personal metadata | DB/export | Same | Provenance | Same |
| `consent_record.created_at` | System | CM | Personal metadata | DB/export | Same | Integrity/export | Same |
| `privacy_action.id`, `action_type` | System after user action | UDE, UDD, CM | Personal metadata | ID in DB only; action type in DB/export | No TTL implemented; production period required | Minimal audit; an export includes its own newly written `export_requested` action; never copy health data | Profile FK becomes null on profile deletion; record remains until a future approved TTL |
| `privacy_action.profile_id` | System | UDE, UDD, CM | Pseudonymous link while profile exists | DB | No TTL implemented | Links export/withdraw/history-deletion action; complete-profile deletion action is written with `null` | `SET NULL` on profile deletion; future approved TTL |
| `privacy_action.occurred_at`, `outcome` | System | UDE, UDD, CM | Personal metadata | DB/export | Same | Minimal action time/result | Same |
| `deletion_record.id` | Generated UUID | UDD | Non-profile-derived action identifier | DB | No TTL implemented | Internal relation only; no health/profile link | Future approved TTL required |
| `deletion_record.confirmation_code` | System random | UDD | Minimal non-profile-derived value | DB | No TTL implemented; controller decision required | Confirmation without profile details | Future approved TTL required |
| `deletion_record.deleted_at`, `deletion_scope`, `deleted_record_count` | System | UDD | Action metadata without profile UUID/health content | DB | No TTL implemented | Minimal technical deletion record; count is approximate for complete profile | Future approved TTL required |

Privacy-action and deletion records must not contain profile snapshots, body/health values, assessment summaries, consent text or free-text notes. A grant retry reuses an existing active consent record; the database's partial unique index prevents more than one active row per profile/purpose/text version. Withdrawal closes all active matching rows, including legacy duplicates.

## Assessments, metrics and safety flags

| Field | Source | Purpose | Sensitivity | Location | Retention | Recipient/use | Deletion |
|---|---|---|---|---|---|---|---|
| `assessment.id` | Generated UUID | NAC, AH | Pseudonymous | DB/response/cache/export | Assessment life | Retrieval/history | History or profile deletion; cache purge |
| `assessment.profile_id` | System | NAC, AH | Pseudonymous | DB only; API/export scope conveys ownership without returning it | Assessment life | Ownership enforcement | History or profile deletion |
| `assessment.client_request_id` | Mobile-generated UUID | NAC | Pseudonymous request metadata | Draft/request/DB/export; omitted from normal assessment response | Draft lifetime; then assessment life | Idempotency per profile | Draft/history/profile deletion |
| `assessment.input_snapshot` | Profile copied at creation | NAC, AH | Special | DB/export; selected cache fields only | Assessment life | Reproducibility/engine | History/profile deletion |
| `assessment.supported_scope_status` | Engine | NAC, AH | Special inference | DB/response/cache/export | Assessment life | Safety/result display | Same |
| `assessment.reference_set_id`, `reference_set_identifier`, `reference_set_version` | System/config | NAC, AH | Personal metadata when linked | DB/response/export | Assessment life | Reproducibility | Same |
| `assessment.application_rule_set_id`, `application_rule_set_identifier`, `application_rule_set_version` | System/config | NAC, AH | Personal metadata when linked | DB/response/export | Assessment life | Reproducibility | Same |
| `assessment.engine_version` | System/config | NAC, AH | Personal metadata when linked | DB/response/export | Assessment life | Reproducibility | Same |
| `assessment.calculated_at` | System | NAC, AH | Personal metadata | DB/response/cache/export | Assessment life | Calculation provenance/history ordering | Same |
| `assessment.summary` | Engine | NAC, AH | Special inferred nutrition data | DB/response/cache/export | Assessment life; minimal cache until purge/expiry | Report/history | Same |
| `assessment_metric.id`, `assessment_id` | System | NAC, AH | Pseudonymous | DB only; current response/export nest metric content without row IDs | Assessment life | Relation | Parent deletion |
| `assessment_metric.metric_code` | Engine | NAC, AH | Special when linked | DB/response/export | Assessment life | Result identity | Same |
| `assessment_metric.raw_value`, `lower_value`, `upper_value` | Engine | NAC, AH | Special inferred | DB/response/export | Assessment life | Unrounded reproducibility | Same |
| `assessment_metric.display_value`, `unit` | Engine/presentation rule | NAC, AH | Special inferred | DB/response/cache/export | Assessment life | User display | Same |
| `assessment_metric.method_code` | Engine | NAC, AH | Personal metadata when linked | DB/response/export | Assessment life | Explanation/reproducibility | Same |
| `assessment_metric.explanation_de`, `limitations_de` | Engine config | NAC, AH | May contain user-specific context | DB/response/export | Assessment life | Transparency | Same |
| `assessment_metric.calculation_inputs` | Engine snapshot subset | NAC, AH | Special | DB/response/export | Assessment life | Reproducibility | Same |
| `assessment_metric.source_metadata` | Reference/config | NAC, AH | Non-personal alone; linked metadata | DB/response/export | Assessment life | Provenance | Parent deletion |
| `assessment_metric.confidence_type` | Engine (`measured`, `derived`, `estimated`, `reference_target`) | NAC, AH | Special inference | DB/response/export | Assessment life | Correct interpretation | Same |
| `safety_flag.id`, `assessment_id` | System | NAC, AH | Pseudonymous | DB only; current response/export nest flag content without row IDs | Assessment life | Relation | Parent deletion |
| `safety_flag.code`, `severity` | Engine | NAC, AH | Special inference | DB/response/cache/export | Assessment life | Calm warning/scope control | Same |
| `safety_flag.explanation_de`, `recommended_action_de` | Engine | NAC, AH | Special context; no diagnosis | DB/response/export | Assessment life | User safety explanation | Same |

Micronutrient targets and food-group recommendations become personal assessment data when returned for a profile even though their source tables are public/non-personal reference data.

## Mobile-only and transient data

| Field/object | Source | Purpose | Sensitivity | Location | Retention | Recipient/use | Deletion |
|---|---|---|---|---|---|---|---|
| Full onboarding draft (all not-yet-submitted fields above, client request UUID and unsubmitted consent-checkbox state) | User/app | LOD | Special | Memory + `sensitive.onboarding_draft.v1` | 30 days after update or submission/manual/profile deletion | Flutter only until submission | Clear-draft action, expiry/corruption cleanup, confirmed profile deletion |
| Latest assessment cache (minimal summary and `cached_at`) | API | LAC | Special | `sensitive.latest_assessment.v1` | Replaced by latest; manual/history/profile deletion; displayed stale after 24 hours | Offline Flutter display | Clear-cache/history/profile action |
| Reserved local consent display state/version | API/user | CM | Sensitive metadata | `sensitive.consent_state.v1` reserved, currently not written | If enabled: until refresh/withdrawal/profile deletion | Offline status display only, never authoritative server permission | Profile/local-data deletion |
| Reserved development current-profile ID | Configuration/app | NPS | Access-enabling context if used | `sensitive.current_profile_id.v1` reserved, currently not written | If enabled: local profile lifetime | Development routing only; not authentication | Profile/local-data deletion |
| `ui.theme_mode` | User | UI only | Non-sensitive presentation preference | SharedPreferences | Until reset/uninstall | Flutter | Settings reset/uninstall |
| Export JSON temporary file/content URI | API/user action | UDE | Special | App cache/temp + receiving app after user choice; all `Decimal` values encoded exactly as JSON strings | Delete app copy promptly after share workflow | User-selected share target | App cleanup; recipient controls its copy |
| Form/API payload in memory | User/API | NPS/NAC/CM/UDE/UDD | Special | Device/API process memory | Request/session lifetime | Relevant component only | Process/lifecycle release; no logging |

## Technical logs

| Field | Source | Purpose | Sensitivity | Location | Retention | Recipient/use | Deletion |
|---|---|---|---|---|---|---|---|
| Random `request_id`/correlation ID | API | TSL | Indirect/short-lived | Structured application log; response error envelope | Log TTL | Authorized developers/operators | TTL deletion |
| Endpoint template or constant `/{unmatched}`, and method | API | TSL | Low alone; usage metadata | Log | Log TTL | Operations/security; raw unmatched/error path is not emitted | TTL deletion |
| Status code and technical error code | API | TSL | Low alone; may infer action | Log | Log TTL | Operations/security | TTL deletion |
| Duration and timestamp | API | TSL | Usage metadata | Log | Log TTL | Operations/security | TTL deletion |

Logs must never contain request/response bodies, raw URLs with query data, profile IDs, IP addresses by default, body/health values, assessment details, allergy/disease answers, consent text, access tokens, secure-storage values or encryption keys. If production infrastructure unavoidably generates IP/access metadata, it must be newly inventoried with a purpose, legal basis, access limit and retention rule.

## Explicitly not collected

The MVP does not collect legal name, postal address, phone number, email address, exact location, employer, government identifiers, contact list, advertising ID, device fingerprint, camera/microphone content or payment data. Adding any of these requires a new purpose and privacy review.
# Food Core

## Daily meal plans

Persisted per-profile data includes plan UUID/date/name/notes/archive timestamps/optional assessment
reference; meal type/custom name/local time/notes/position/timestamps; and entry recipe/food
references, decimal quantities, units/measures, notes, positions and timestamps. Meal/day totals,
coverage and target comparisons are generated on demand and are not separate records. Unsaved plan
structure may exist for 30 days in encrypted device storage; it contains no complete nutrient source
record. This is sensitive nutrition and behavioral planning data.

Profilgebundene, manuell eingegebene Lebensmittelnamen, Marken, Beschreibungen, Bezugsbasis, optionale Dichte, Nährwerte und Haushaltsmaße einschließlich Quellen- und Archivmetadaten. Manuell eingegebene Lebensmittel werden nicht an externe Dienste übermittelt.

Bei Barcode-Importen zusätzlich: Barcode, Open-Food-Facts-Quellstand und importierte Produktdaten. Der Barcode wird für die vom Nutzer ausgelöste Suche an Open Food Facts übertragen; Profil- und Bewertungsdaten werden nicht mitgesendet.

# Recipe Core

Rezepte speichern profilgebundene Metadaten, Portionen, optionale Zeiten/Quelle/Notizen/Endgewicht, Tags, geordnete Food- und optionale FoodMeasure-Referenzen, Mengen, Zubereitungshinweise und Schritte. Berechnete Nährwertsummen und Qualitätsangaben entstehen beim Abruf und werden nicht als eigener Snapshot gespeichert. Der Export enthält den Recipe-Graph; die vollständige Profillöschung entfernt ihn dauerhaft. Archivierung bewahrt ihn bis dahin auf.

# Recipe Target Comparison

Verarbeitet auf ausdrückliches Öffnen eine eigene Rezept-ID, eine eigene unveränderliche Assessment-Version, eine sitzungsbezogene Portionszahl sowie daraus abgeleitete bekannte Mengen, Prozente, Datenabdeckung und neutrale Erklärungen. Vergleichsergebnisse und Auswahlzustand werden weder serverseitig noch lokal persistiert und bilden deshalb keinen zusätzlichen Export- oder Löschdatensatz.
# Purchase to Pantry

Gespeichert werden Übergabe-Batches, Shopping- und Food-Referenzen, geplante und tatsächliche Mengen, Ziel-Lagerorte, Pantry-Lot-/Bewegungsreferenzen, getrennte Datumsangaben, Notizen und die ausdrückliche Abschlussentscheidung.

# Pantry Recipe Availability

Transient verarbeitet werden eine eigene Rezept-ID, gewünschte Portionszahl, optionale
Darstellungsfilter sowie aktuelle Zutaten- und Vorratsmengen. Abgeleitete Fehlmengen, hypothetische
Reste, maximal mögliche Portionen und begrenzende Zutaten werden weder serverseitig noch lokal als
eigene Datensätze persistiert und erzeugen daher keinen zusätzlichen Export- oder Löschdatensatz.

# Pantry-aware Shopping

Persistiert werden stabile Source-Identität und -Version, angewandter Mengensnapshot,
Ziellistenreferenz, Datumsmodus, Other-List-Option, Client-Operations-ID, Ergebniszählwerte und
Zeitpunkte. Vorschau-Token, aktuelle Pantry-Ableitungen und globale Zusatzbedarfe werden nicht als
dauerhafte Wahrheit gespeichert. Export und vollständige Löschung umfassen die persistierten Daten.

Optimizer preferences contain engine, bounded solver settings, strict toggles, relaxation priorities
and objective weights. Applied audits contain compact engine/status/version, objective/gap and
relaxation summaries. Solver models, candidate matrices, coefficients, temporary budgets and
preview tokens are transient and excluded from export.

## Consumption Tracking Core

| Daten | Herkunft | Sensitivität | Speicherung | Löschung |
|---|---|---|---|---|
| Verzehrtag, Datum, Status, Vollständigkeits-Selbstauskunft, Notiz | Nutzer/System | Gesundheits-/Verhaltensdaten | PostgreSQL | Einzelner Tag, alle Verzehrdaten oder Profil |
| Mahlzeit, optionale lokale Uhrzeit und Notiz | Nutzer | Gesundheits-/Verhaltensdaten | PostgreSQL | Kaskade mit Tag |
| Food-/Recipe-/manueller Eintrag, tatsächliche Menge, Quelle und Version | Nutzer/System | Gesundheits-/Verhaltensdaten | PostgreSQL | Einzelner Eintrag oder Kaskade |
| Relationale Nährwertsnapshots mit Unknown/True-Zero | Berechnung | Gesundheitsdaten | PostgreSQL | Kaskade mit Eintrag |
| Planeintragsentscheidung und Ersatzverknüpfungen | Nutzer | Gesundheits-/Verhaltensdaten | PostgreSQL | Entscheidung/Tag/Profil |

Transiente Vorschauen, Tokens und Servercaches werden nicht exportiert. Vorrat und Einkaufslisten
sind getrennte Datenbestände.
