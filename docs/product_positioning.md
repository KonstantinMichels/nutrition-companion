# Nutrition Companion: product positioning

**Document status:** Product and regulatory boundary for the development MVP  
**Last reviewed:** 2026-07-28  
**Release status:** Draft. It has not been legally or regulatorily approved.

## Intended purpose

Nutrition Companion is a personal nutrition and lifestyle-planning application for generally healthy adults. The MVP uses information entered by the user to calculate transparent, scientifically referenced **estimates** of energy, macronutrient, fibre, hydration and available micronutrient targets. It lets the user inspect calculation inputs, methods, reference versions, limitations and previous immutable assessments.

The intended benefit is orientation and support for personal planning. The product does not diagnose, prevent, monitor, predict, prognose, treat or alleviate disease, and does not make clinical decisions. A calculation is not a medical diagnosis, an individual prescription or a guarantee of an outcome.

This boundary must be consistent in the UI, API documentation, store listing, support material and promotional statements. Under the EU Medical Device Regulation, qualification depends materially on the manufacturer's stated intended purpose. Lifestyle and wellbeing software is not automatically a medical device, while software specifically intended for one of the medical purposes in Article 2 may be one. See [Regulation (EU) 2017/745, Article 2 and recital 19](https://eur-lex.europa.eu/eli/reg/2017/745/oj) and the European Commission's [MDCG 2019-11 rev.1 software guidance (June 2025)](https://health.ec.europa.eu/latest-updates/update-mdcg-2019-11-rev1-qualification-and-classification-software-regulation-eu-2017745-and-2025-06-17_en?prefLang=en), accessed 2026-07-28. This document is a product constraint, not a legal classification opinion.

## Supported users

Automatic standard assessments are limited to people who are all of the following:

- 18 through 65 years old;
- generally healthy;
- not pregnant or breastfeeding; and
- not reporting a condition or prescribed diet that requires medical nutrition therapy.

The app may store an unsupported user's profile and return a calm, structured safety flag, but it must not return a normal weight-change target or high-protein sports target for that user. Allergies, intolerances and food exclusions may be recorded for future planning; the MVP neither diagnoses them nor evaluates food safety.

The upper boundary is inclusive: a person aged exactly 65 remains inside the configured MVP age screen. Scientific tables can use narrower source age bands, so a lookup must still match the source's exact age interval.

## Unsupported uses

The MVP must not be used for:

- people under 18 or over 65;
- pregnancy or breastfeeding;
- a diagnosed eating disorder;
- diabetes, kidney disease, liver disease or a serious metabolic condition;
- a medically prescribed diet or any other situation requiring professional nutrition care;
- diagnosing nutrient deficiencies, allergy, intolerance, malnutrition or disease;
- medical nutrition therapy, disease management or clinical monitoring;
- emergency, dehydration or electrolyte-treatment advice;
- supplement prescriptions;
- calculating a guaranteed weight trajectory or target date; or
- replacing a physician, qualified dietitian or other appropriate professional.

When a screening answer is unsupported, user-facing text should say that this version is not designed for the situation and recommend qualified individual advice. It must not say or imply that the software detected a disease.

## Claims policy

### Prohibited claims

Do not use, imply, optimize search metadata for, or permit testimonials to stand as claims such as:

- “medically proven” or “clinically validated”;
- “treats obesity” or “prevents diabetes”;
- “diagnoses deficiencies”;
- “guarantees optimal health” or a precise weekly weight change;
- “creates a medically optimal diet”;
- “personal medical recommendation”;
- “replaces professional advice”; or
- “DiGA”, “medical device” or a CE-related claim without a completed, documented regulatory pathway.

A disclaimer does not neutralize a contradictory feature or marketing claim.

### Preferred wording

| Context | Use | Avoid |
|---|---|---|
| Quantity | “geschätzter Wert”, “berechneter Zielbereich” | “exakter Bedarf” |
| Evidence | “wissenschaftlich referenzierte Schätzung” | “wissenschaftlich bewiesen für dich” |
| Recommendation | “allgemeine Ernährungsempfehlung” | “Therapieempfehlung” |
| Personalization | “auf Basis deiner Angaben berechnet” | “medizinisch personalisiert” |
| Limitation | “nicht zur Diagnose oder Behandlung bestimmt” | “ersetzt die Beratung” |
| Outcome | “der tatsächliche Bedarf kann abweichen” | “garantierter Erfolg” |

Every numerical result should identify whether it is measured, derived, estimated or a reference target. A range must not be called a clinically validated confidence interval unless such validation has actually occurred.

## UI wording

Reusable German wording for the MVP:

> Nutrition Companion berechnet wissenschaftlich referenzierte Schätzungen für allgemein gesunde Erwachsene. Die Ergebnisse dienen der persönlichen Ernährungs- und Lebensstilplanung. Sie sind keine Diagnose oder Behandlung und ersetzen keine individuelle Beratung durch qualifizierte Fachpersonen.

For an unsupported screen:

> Diese Version ist für deine angegebene Situation nicht ausgelegt. Deshalb erstellen wir keinen regulären Zielwert zur Gewichtsveränderung und kein erhöhtes Sport-Proteinziel. Deine Angabe ist keine Diagnose durch die App. Bitte besprich eine individuelle Planung mit einer dafür qualifizierten Fachperson.

For an optional free-text health note:

> Dieser Hinweis wird gespeichert, aber nicht medizinisch geprüft.

For profile edits:

> Bestehende Auswertungen bleiben unverändert. Erstelle eine neue Auswertung, um geänderte Profildaten anzuwenden.

## Future app-store description guidelines

A future store description may say that the app:

- creates explainable nutrition estimates for generally healthy adults;
- records user-entered goals, activity and dietary preferences;
- shows the formula, source version and limitations behind a result;
- keeps historical assessments separate; and
- provides export, consent and deletion controls.

It must state the supported population and non-medical purpose prominently, not only behind a “more” link. Screenshots, keywords, release notes and developer responses are part of the claim surface and must follow the same boundary. Before publication, a qualified reviewer must assess the final listing, in-app wording, onboarding, calculation rules and actual behavior together.

Illustrative draft, not approved for publication:

> Nutrition Companion unterstützt allgemein gesunde Erwachsene bei der persönlichen Ernährungs- und Lebensstilplanung. Auf Basis deiner Angaben berechnet die App nachvollziehbare Schätz- und Zielbereiche und zeigt Formeln, Quellen und Grenzen der Berechnung. Die App ist nicht zur Diagnose oder Behandlung bestimmt und ersetzt keine individuelle medizinische oder ernährungstherapeutische Beratung.

## Changes that require a fresh regulatory review

Review must occur before design or marketing approval if a change introduces or implies:

- diagnosis, screening for disease or deficiency, prediction, prognosis, monitoring, prevention, treatment or alleviation of a disease;
- patient-specific clinical decisions or recommendations used for diagnosis or therapy;
- medical nutrition therapy, a clinician workflow or integration into clinical records;
- handling of pregnancy, breastfeeding, eating disorders, diabetes, kidney/liver disease or metabolic disorders with calculated treatment targets;
- sensor-based monitoring, alerts that could influence urgent care, or automated interpretation of biomarkers;
- supplement or medication recommendations;
- a claim of clinical performance, a medical-device claim, CE marking or DiGA eligibility;
- material AI/ML-generated health recommendations;
- a changed target population, especially minors or vulnerable groups; or
- an expanded intended purpose even if the underlying code is unchanged.

A DiGA is a CE-marked medical device meeting additional German requirements and an assessment process; this MVP is not a DiGA. See the [BfArM DiGA overview](https://www.bfarm.de/DE/Medizinprodukte/Aufgaben/DiGA-und-DiPA/DiGA/_node.html), accessed 2026-07-28.

## Review and release gate

The repository implements technical guardrails and draft language only. They do not establish legal compliance, medical-device status, scientific validation or fitness for public distribution. Public release remains blocked pending documented review by qualified German/EU legal, privacy and regulatory professionals, including at least:

- final intended-purpose and regulatory classification;
- all product and store claims;
- privacy notice, consent wording and legal bases;
- safety and supported-population rules;
- scientific reference data and application-rule governance; and
- the production hosting, authentication and operations model.

