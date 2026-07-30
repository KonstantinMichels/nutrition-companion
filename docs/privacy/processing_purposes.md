# Processing-purpose registry

`progress_tracking` dient freiwilliger Speicherung und Darstellung sensibler Messungen und Ziele sowie transparenter Trendberechnung. Die bestehende Gesundheitsdaten-Einwilligungsarchitektur wird ohne unnötige wiederholte Prompts genutzt; rechtliche Prüfung bleibt erforderlich.

`pantry_management` covers user-requested storage, organization, and traceability of
manual food stock. It is optional service storage and introduces no new consent checkbox
in this architecture; the legal basis still requires qualified review.

The same purpose includes the user-requested, transient comparison of current recipe requirements
with current Pantry stock. Derived availability is not persisted, exported, shared externally, or
used for automated food-safety decisions and introduces no additional consent checkbox.

`shopping_list_management` umfasst außerdem den ausdrücklich gestarteten Abgleich aktueller
Rezept-/Planbedarfe mit Pantry und offenen Listen sowie persistierte Source-Identitäten und
Apply-Auditmetadaten. Vorschauen bleiben transient; es gibt keine neue Einwilligungscheckbox.

The existing `daily_meal_planning` purpose includes manual weekly organization and the
on-demand aggregation of daily plans. This adds no automated decision and needs no
redundant consent.

**Status:** Technical MVP registry and German user-text draft  
**Last reviewed:** 2026-07-28  
**Legal status:** All legal-basis entries are placeholders requiring qualified German/EU review before public release.

## Rules

- A purpose code is stable and machine-readable. A material purpose change requires a new/revised registry entry and privacy review.
- Data may not be reused for a purpose that is not defined here.
- “Required” means required to provide the named user-requested feature, not that a legal basis has been established.
- A technical consent check does not by itself prove valid GDPR consent or resolve the legal basis.
- Article 9 data needs both an Article 6 legal basis and an Article 9 exception/condition. Those decisions are intentionally not made in this repository.
- Recipients listed as “local components” are Flutter, the FastAPI modular monolith, the in-process Nutrition Engine where needed, and local PostgreSQL. There is no external processor in the MVP.

## Registry

### `nutrition_profile_storage`

| Attribute | Value |
|---|---|
| German description | „Speicherung deiner eingegebenen Profil-, Körper-, Aktivitäts-, Ziel-, Ernährungs- und Screeningangaben, damit du dein Profil ansehen, bearbeiten und für eine Auswertung verwenden kannst.“ |
| Data categories | Pseudonymous profile ID; birth date/age; calculation category; height, weight and optional measurements; activity/sport; goals; diet preferences/restrictions; minimal screening answers; timestamps |
| Special-category data possible | Yes; expected in this context |
| Storage | PostgreSQL; encrypted mobile draft before submission; immutable subset in an assessment snapshot |
| Retention | Current profile until complete-profile deletion; snapshot until history/profile deletion |
| Legal-basis placeholder | `[Article 6 basis: legal review]` + `[Article 9 condition: legal review]` |
| Consent | Not technically consent-gated in `mvp_v1`; the registry returns `consent_required = false`. Counsel must determine the Article 6/9 model and whether separate consent is required before public release |
| Recipients/processors | Local components only; no external processor |
| Deletion | Complete-profile deletion removes current rows; history deletion removes snapshot copies only; local draft/cache separately purgeable |
| Required/optional | Required to save a server profile; optional measurements and free text remain optional |

### `nutrition_assessment_calculation`

Die nutzerinitiierte Recipe-Target-Comparison verwendet eine bereits gespeicherte unveränderliche Einschätzung für den transparenten Vergleich mit einem eigenen Rezept. Sie berechnet keine neue Einschätzung, persistiert kein Ergebnis und übermittelt keine Werte an Dritte. Diese kompatible abgeleitete Nutzung ist in der Produkt-/Datenschutzinformation transparent auszuweisen; die rechtliche Einordnung bleibt vor Produktion professionell zu prüfen.

| Attribute | Value |
|---|---|
| German description | „Verarbeitung deiner Angaben, um geschätzte Ernährungszielbereiche, Erklärungen und Sicherheits-Hinweise zu berechnen. Die Auswertung ist keine Diagnose oder Behandlung.“ |
| Data categories | Profile/measurement/activity/goal inputs; screening flags; selected references/rules; derived body, energy, macro, fibre, hydration and available micronutrient values; safety flags |
| Special-category data possible | Yes |
| Storage | Request memory, in-process engine, PostgreSQL assessment/metrics/flags, API response |
| Retention | Assessment until history or complete-profile deletion |
| Legal-basis placeholder | `[Article 6 basis: legal review]` + `[Article 9 condition: likely explicit-consent candidate; legal review required]` |
| Consent | Required by the technical MVP; exact active purpose and consent-text version checked server-side; withdrawal blocks new assessments |
| Recipients/processors | Local API, engine and DB only |
| Deletion | History deletion or complete-profile deletion; no hidden soft-delete-only behavior |
| Required/optional | Required only when the user requests an assessment; refusal leaves assessment unavailable |

### `assessment_history`

| Attribute | Value |
|---|---|
| German description | „Speicherung früherer Auswertungen als unveränderliche Momentaufnahmen, damit du Ergebnisse, damalige Eingaben und verwendete Versionen später nachvollziehen kannst.“ |
| Data categories | Assessment ID/date; immutable input snapshot; result metrics; explanations; formula/reference/rule versions; warnings/safety flags |
| Special-category data possible | Yes |
| Storage | PostgreSQL; minimal latest summary may also be in encrypted mobile cache |
| Retention | Until assessment-history deletion or complete-profile deletion |
| Legal-basis placeholder | `[Article 6 basis: legal review]` + `[Article 9 condition: legal review]` |
| Consent | Not separately consent-gated in `mvp_v1`; the registry returns `consent_required = false`. Only calculation is technically gated. Whether history can share that legal model or needs separate consent/granularity requires qualified review |
| Recipients/processors | Local components only |
| Deletion | User can delete all history without deleting current profile; dependent metrics/flags removed transactionally; cache purged |
| Required/optional | Required for the MVP's reproducible assessment record; user can delete later |

### `local_onboarding_draft`

| Attribute | Value |
|---|---|
| German description | „Verschlüsselte Zwischenspeicherung deiner noch nicht abgesendeten Eingaben auf diesem Gerät, damit du die Eingabe später fortsetzen kannst.“ |
| Data categories | Any onboarding fields entered so far; no server consent record until submitted |
| Special-category data possible | Yes |
| Storage | Android secure storage only |
| Retention | Until submission, manual clear, complete-profile local purge or configured abandoned-draft expiry—whichever occurs first |
| Legal-basis placeholder | `[Article 6 basis: legal review]`; `[TDDDG § 25(2)(2) strictly-necessary assessment: legal review]`; Article 9 analysis required |
| Consent | No preselected optional consent; clear user explanation and deletion control; final legal approach pending |
| Recipients/processors | Flutter/device only |
| Deletion | “Lokale Entwurfsdaten löschen”, automatic expiry, uninstall/platform behavior, confirmed profile deletion |
| Required/optional | Registry marks this processing required for the implemented resumable-onboarding behavior; the user can clear the draft and restart without it |

### `local_assessment_cache`

| Attribute | Value |
|---|---|
| German description | „Verschlüsselte Speicherung einer kleinen Zusammenfassung der neuesten Auswertung auf diesem Gerät, damit sie ohne Netzwerkverbindung angezeigt werden kann.“ |
| Data categories | Assessment ID/time, minimal energy/macro summary, key warnings and staleness metadata; not a complete backend record |
| Special-category data possible | Yes |
| Storage | Android secure storage only |
| Retention | Replaced by newer cache; manual clear; profile deletion; stale-cache rule |
| Legal-basis placeholder | `[Article 6 basis: legal review]`; `[TDDDG § 25 strictly-necessary assessment: legal review]`; Article 9 analysis required |
| Consent | No unrelated optional tracking consent; cache purpose disclosed and independently clearable |
| Recipients/processors | Flutter/device only |
| Deletion | “Lokalen Auswertungs-Cache löschen”, confirmed profile deletion or uninstall/platform behavior |
| Required/optional | Optional offline-display feature |

### `technical_security_logging`

| Attribute | Value |
|---|---|
| German description | „Kurzzeitige Verarbeitung minimierter technischer Ereignisdaten, um Fehler und Sicherheitsvorfälle zu erkennen und den Dienst zu schützen. Profil- und Gesundheitsinhalte werden nicht protokolliert.“ |
| Data categories | Random request ID; endpoint template/method; status; duration; technical error code; environment; timestamp |
| Special-category data possible | No by design; any payload/profile UUID is a logging defect and potential incident |
| Storage | Local application/container logs in MVP |
| Retention | Short configurable period; production value pending (provisional target: 14 days, subject to risk/legal review) |
| Legal-basis placeholder | `[Article 6 basis, commonly legitimate-interest candidate: legal review and balancing test]` |
| Consent | Not designed as consent-based; no analytics/tracking |
| Recipients/processors | Authorized local developer; future operators/vendors must be registered |
| Deletion | Rotation/TTL; incident evidence may require a documented restricted hold |
| Required/optional | Required for secure/reliable operation; payload logging prohibited |

### `user_data_export`

| Attribute | Value |
|---|---|
| German description | „Zusammenstellung und Bereitstellung deiner gespeicherten Daten als verständliche JSON-Datei, wenn du den Export selbst anforderst.“ |
| Data categories | All profile-associated stored records, complete assessment data, consent records and minimal privacy actions—including the current `export_requested` action; excludes secrets/unrelated server metadata |
| Special-category data possible | Yes |
| Storage | Generated response with every `Decimal` encoded exactly as a JSON string; temporary app-controlled file; then any user-selected share destination |
| Retention | Generated on demand; temporary app copy deleted promptly after share workflow |
| Legal-basis placeholder | `[Article 6/Article 9 analysis and data-subject-right procedure: legal review]` |
| Consent | Explicit user action, not an ongoing optional consent |
| Recipients/processors | User; destination chosen by user in Android share sheet |
| Deletion | Temporary app file cleanup; receiving app controls its copy |
| Required/optional | Optional user control; production requires authentication/re-authentication |

### `user_data_deletion`

| Attribute | Value |
|---|---|
| German description | „Verarbeitung deiner ausdrücklichen Löschanfrage, um entweder den Auswertungsverlauf oder das vollständige Profil und zugehörige lokale Daten zu entfernen.“ |
| Data categories | Profile scope; selected deletion scope; transaction status; minimal non-sensitive confirmation; no copied health payload |
| Special-category data possible | The deletion touches special data; action record must not copy it |
| Storage | Request memory; DB transaction; minimal confirmation where implemented; mobile secure-store purge |
| Retention | Deleted data removed immediately from active local stores; production backup expiry pending; minimal confirmation period pending |
| Legal-basis placeholder | `[Article 6 basis/legal obligation/right handling: legal review]` |
| Consent | Explicit confirmed action; separate from consent withdrawal |
| Recipients/processors | Local components only |
| Deletion | Transactional hard deletion; future backups expire and deletion must be reapplied after restore |
| Required/optional | Optional user control; production requires authentication/re-authentication |

### `consent_management`

| Attribute | Value |
|---|---|
| German description | „Speicherung, Anzeige und Widerruf deiner Einwilligungsentscheidung einschließlich Zweck, Textversion und Zeitpunkten.“ |
| Data categories | Consent ID/profile ID; purpose; exact text version; status; granted/withdrawn time; source; creation time |
| Special-category data possible | The decision relates to special-category processing; do not copy health content |
| Storage | PostgreSQL; minimal encrypted local state if needed for offline display |
| Retention | Local MVP: profile life; production retention after withdrawal/deletion requires legal decision |
| Legal-basis placeholder | `[Article 6 basis for consent evidence/management: legal review]`; underlying Article 9 condition separately reviewed |
| Consent | This purpose records consent; an active duplicate grant is idempotently reused, a partial unique index enforces one active profile/purpose/text-version row, and withdrawal closes all matching active rows including legacy duplicates. It is not justified circularly by another hidden checkbox |
| Recipients/processors | Local components only |
| Deletion | Local MVP removes with complete profile where appropriate; production proof/defense retention must be defined and minimized |
| Required/optional | Required to remember and enforce the user's decision; refusal prevents new assessment processing |

## Deutscher Informationstext — Entwurf

## `daily_meal_planning`

| Attribute | Value |
|---|---|
| Purpose | Manuelle Speicherung und Berechnung selbst zusammengestellter Tagespläne |
| Data | Date, meal names/times/notes, recipe/food references, quantities, optional assessment reference |
| Special-category possibility | Yes; nutrition behavior and target linkage can be sensitive |
| Storage | PostgreSQL; unfinished structure in Keystore/Keychain-backed secure storage |
| Retention | Plans until complete profile deletion; encrypted drafts 30 days or earlier save/manual/profile deletion |
| Recipients | Local app, FastAPI and PostgreSQL only; none configured externally |
| Deletion | Complete profile deletion hard-deletes graph and clears app-owned drafts; archive is not deletion |
| Legal status | Placeholder; Article 6/9 and information duties require qualified review |

**Nicht rechtlich freigegeben. Vor einer Veröffentlichung müssen Verantwortlicher, Kontaktdaten, Datenschutzbeauftragte, Rechtsgrundlagen, Empfänger, konkrete Speicherfristen, Beschwerdestelle und alle Pflichtinformationen ergänzt und professionell geprüft werden.**

> ### Datenschutz-Kurzinformation
>
> Nutrition Companion verarbeitet die Angaben, die du im Ernährungsprofil machst. Dazu können Körpermaße, Aktivitäten, Ernährungsziele, Unverträglichkeiten und wenige Angaben zur gesundheitlichen Eignung dieser App-Version gehören. Wir verwenden sie, um auf deine ausdrückliche Anforderung geschätzte Ernährungszielbereiche zu berechnen, die Berechnung zu erklären und frühere Auswertungen unverändert anzuzeigen.
>
> Ein noch nicht abgesendeter Entwurf und eine kleine Zusammenfassung der neuesten Auswertung können verschlüsselt auf deinem Gerät gespeichert werden. Du kannst beide lokalen Speicherungen löschen. Die vollständigen Profildaten und Auswertungen werden in der lokalen Entwicklungsfassung in der zugehörigen Datenbank gespeichert. Es gibt keine Werbung, Analyse-SDKs oder automatische Weitergabe an soziale Netzwerke.
>
> Die Ergebnisse sind Schätzungen zur persönlichen Ernährungs- und Lebensstilplanung. Die App stellt keine Diagnose, behandelt keine Erkrankung und ersetzt keine qualifizierte Beratung.
>
> Du kannst deine Einwilligungsdatensätze ansehen, die Einwilligung für künftige Auswertungen widerrufen, deine Daten als JSON exportieren, den Auswertungsverlauf löschen oder das vollständige Profil löschen. Ein Widerruf stoppt neue Auswertungen, löscht aber nicht automatisch bereits gespeicherte Daten. Eine Löschung ist eine separate Aktion.

## Deutscher Einwilligungstext — Entwurf

**Nicht vorselektieren. Die kanonische Textversion muss zentral versioniert und in App, API und gespeicherten `ConsentRecord`s identisch sein. Die aktuelle Implementierungskennung ist `privacy_consent_de_mvp_v1`. Jede Textänderung braucht eine neue Kennung und erneute rechtliche Prüfung.**

> Ich willige ausdrücklich ein, dass meine eingegebenen Profil-, Körper-, Aktivitäts-, Ernährungs- und Screeningangaben — einschließlich möglicher Gesundheitsdaten — verarbeitet werden, um die von mir angeforderte, geschätzte Ernährungsauswertung zu berechnen und als nachvollziehbaren Verlauf zu speichern. Mir ist bekannt, dass die Auswertung keine Diagnose oder Behandlung ist. Ich kann die Einwilligung für die Zukunft widerrufen. Der Widerruf verhindert neue Auswertungen; die Löschung bereits gespeicherter Daten muss ich getrennt auslösen. Ich habe die Datenschutzinformationen gelesen.

Refusal must remain possible. Do not bundle analytics, marketing, research, model training or another optional purpose into this control.

### Technical enforcement versus unresolved legal model

The current API accepts and enforces only `nutrition_assessment_calculation` consent. `nutrition_profile_storage` and `assessment_history` are required product operations but are marked `consent_required = false` in the machine registry because the code does not separately gate them. That is a description of implementation, **not** a conclusion that consent is unnecessary. Qualified review must assign an Article 6 basis and, where applicable, an Article 9 condition to each purpose, then decide whether to change the controls, wording or registry flags.
# Purchase to Pantry

`purchase_to_pantry_management` deckt die vom Nutzer gestartete Übernahme von Kaufmengen und Zielen ab. Sie benötigt keine zusätzliche Einwilligungscheckbox und endet mit vollständiger Profillöschung.

`daily_meal_planning` also covers explicitly requested local deterministic/CP-SAT draft generation,
preference profiles and compact application audits. Existing coverage is reused; no separate
optimizer consent checkbox is introduced.
