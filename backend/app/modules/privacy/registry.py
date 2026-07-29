from __future__ import annotations

PROCESSING_PURPOSE_REGISTRY_VERSION = "mvp_v1"

PROCESSING_PURPOSES: tuple[dict[str, object], ...] = (
    {
        "code": "nutrition_profile_storage",
        "description_de": (
            "Speicherung deines Ernährungs- und Körperprofils für von dir gestartete Auswertungen."
        ),
        "data_categories": ["profile", "measurements", "preferences", "health_screening"],
        "may_include_special_category_data": True,
        "storage_location": "PostgreSQL; encrypted mobile draft only while onboarding",
        "retention_period": "Until complete profile deletion",
        "legal_basis_placeholder": "Legal basis requires qualified review before public release",
        # Technical MVP enforcement: this storage purpose is required to provide the
        # user-requested profile feature. Its legal basis remains deliberately unresolved.
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": (
            "Wird bei vollständiger Profillöschung aus der aktiven Datenbank gelöscht."
        ),
        "required": True,
    },
    {
        "code": "nutrition_assessment_calculation",
        "description_de": (
            "Berechnung transparenter, geschätzter Ernährungszielwerte aus deinen Angaben."
        ),
        "data_categories": ["profile", "activity", "goal", "health_screening", "assessment"],
        "may_include_special_category_data": True,
        "storage_location": (
            "FastAPI process memory during calculation and PostgreSQL assessment snapshot"
        ),
        "retention_period": "Assessment remains until history or profile deletion",
        "legal_basis_placeholder": (
            "Explicit-consent basis is a draft and requires qualified legal review"
        ),
        "consent_required": True,
        "recipients_or_processors": [],
        "deletion_behavior_de": (
            "Auswertungen werden über Verlaufslöschung oder Profillöschung gelöscht."
        ),
        "required": True,
    },
    {
        "code": "assessment_history",
        "description_de": "Anzeige früherer, unveränderter Auswertungen.",
        "data_categories": ["assessment snapshots", "metrics", "safety flags"],
        "may_include_special_category_data": True,
        "storage_location": "PostgreSQL and minimal encrypted latest-summary cache on device",
        "retention_period": "Until assessment-history or profile deletion",
        "legal_basis_placeholder": "Requires qualified legal review",
        # History storage is technically part of the requested service. Only calculation
        # consent is enforced in code; a qualified review must confirm the legal model.
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": "Kann getrennt vom Profil dauerhaft gelöscht werden.",
        "required": True,
    },
    {
        "code": "local_onboarding_draft",
        "description_de": (
            "Verschlüsselte Zwischenspeicherung deiner noch nicht abgeschlossenen Eingaben."
        ),
        "data_categories": ["unfinished onboarding input"],
        "may_include_special_category_data": True,
        "storage_location": "Android Keystore-backed secure storage / future iOS Keychain",
        "retention_period": "30 days after last update or until manual/profile deletion",
        "legal_basis_placeholder": "Device-storage and GDPR basis require qualified review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": "Kann in der App gelöscht werden und läuft nach 30 Tagen ab.",
        "required": True,
    },
    {
        "code": "local_assessment_cache",
        "description_de": (
            "Verschlüsselte, minimale Zusammenfassung der letzten Auswertung für Offline-Anzeige."
        ),
        "data_categories": ["latest assessment summary", "cache timestamp"],
        "may_include_special_category_data": True,
        "storage_location": "Android Keystore-backed secure storage / future iOS Keychain",
        "retention_period": "Until replacement, manual deletion, or profile deletion",
        "legal_basis_placeholder": "Requires qualified legal review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": "Kann separat gelöscht werden; wird nach Profillöschung entfernt.",
        "required": False,
    },
    {
        "code": "daily_meal_planning",
        "description_de": (
            "Manuelle oder ausdrücklich bestätigte, lokal regelbasierte beziehungsweise "
            "mathematisch optimierte Zusammenstellung geplanter Mahlzeiten und persönlicher "
            "Tagesvergleiche."
        ),
        "data_categories": [
            "plan date",
            "meal names and times",
            "food and recipe references",
            "planned quantities",
            "assessment reference",
            "automation preferences and meal slots",
            "automation application audit records",
            "optimizer constraints, weights, solver status and relaxation summaries",
        ],
        "may_include_special_category_data": True,
        "storage_location": (
            "PostgreSQL; unfinished drafts only in Android Keystore-backed secure storage"
        ),
        "retention_period": "Until complete profile deletion; drafts expire after 30 days",
        "legal_basis_placeholder": "Requires qualified legal review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": (
            "Pläne werden bei vollständiger Profillöschung entfernt; Archive sind keine Löschung."
        ),
        "required": False,
    },
    {
        "code": "pantry_management",
        "description_de": "Manuelle Verwaltung verfügbarer Lebensmittelbestände und Lagerorte.",
        "data_categories": [
            "food references",
            "stock quantities",
            "locations",
            "dates",
            "inventory movements",
            "notes",
        ],
        "may_include_special_category_data": True,
        "storage_location": "PostgreSQL; no Pantry form cache in the MVP",
        "retention_period": "Until complete profile deletion",
        "legal_basis_placeholder": "Requires qualified legal review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": (
            "Lagerorte, Bestände und Bewegungen werden bei vollständiger Profillöschung entfernt."
        ),
        "required": False,
    },
    {
        "code": "shopping_list_management",
        "description_de": (
            "Erstellung und Verwaltung manueller oder aus Plänen abgeleiteter Einkaufslisten."
        ),
        "data_categories": [
            "shopping-list metadata",
            "food references and quantities",
            "plan-source snapshots",
            "Pantry comparison snapshots",
            "Pantry-aware source identities and operation audit metadata",
            "open shopping-list commitment comparison",
            "free-text items and notes",
        ],
        "may_include_special_category_data": True,
        "storage_location": "PostgreSQL; no shopping-list form cache in the MVP",
        "retention_period": "Until complete profile deletion",
        "legal_basis_placeholder": "Requires qualified legal review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": (
            "Einkaufslisten werden bei vollständiger Profillöschung entfernt; "
            "Archivieren ist keine Löschung."
        ),
        "required": False,
    },
    {
        "code": "purchase_to_pantry_management",
        "description_de": "Ausdrücklich bestätigte Übernahme gekaufter Lebensmittel in den Vorrat.",
        "data_categories": [
            "shopping source",
            "actual purchase quantities",
            "Pantry destinations",
            "handoff linkage",
        ],
        "may_include_special_category_data": True,
        "storage_location": "PostgreSQL; preview data remains transient",
        "retention_period": "Until complete profile deletion",
        "legal_basis_placeholder": "Requires qualified legal review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": (
            "Übergaben und Verknüpfungen werden bei vollständiger Profillöschung entfernt."
        ),
        "required": False,
    },
    {
        "code": "technical_security_logging",
        "description_de": (
            "Minimierte technische Protokolle zur Fehler- und Sicherheitsanalyse ohne Inhaltsdaten."
        ),
        "data_categories": ["short-lived request ID", "endpoint template", "status", "duration"],
        "may_include_special_category_data": False,
        "storage_location": "Application standard output in local development",
        "retention_period": "14 days target; production implementation pending",
        "legal_basis_placeholder": "Requires qualified legal review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": (
            "Technische Protokolle sollen nach der konfigurierten Frist rotieren."
        ),
        "required": True,
    },
    {
        "code": "user_data_export",
        "description_de": "Erstellung eines JSON-Exports nach deiner ausdrücklichen Aktion.",
        "data_categories": [
            "all current-profile data except secrets and unrelated server metadata"
        ],
        "may_include_special_category_data": True,
        "storage_location": "Generated in memory; temporary device file only for sharing",
        "retention_period": "Only for the explicit export/share operation",
        "legal_basis_placeholder": "Requires qualified legal review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": (
            "Die App lädt den Export nicht automatisch hoch; temporäre Datei wird entfernt."
        ),
        "required": False,
    },
    {
        "code": "user_data_deletion",
        "description_de": (
            "Dauerhafte Löschung ausgewählter Auswertungen oder des vollständigen Profils."
        ),
        "data_categories": ["record identifiers", "minimal non-sensitive deletion confirmation"],
        "may_include_special_category_data": False,
        "storage_location": "PostgreSQL deletion record without former profile identifier",
        "retention_period": "Deletion confirmation retained for local MVP operation",
        "legal_basis_placeholder": "Requires qualified legal and retention review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": (
            "Inhaltsdaten werden gelöscht; nur eine nicht zuordenbare Bestätigung bleibt."
        ),
        "required": True,
    },
    {
        "code": "consent_management",
        "description_de": "Versionierte Dokumentation und Widerruf deiner Einwilligung.",
        "data_categories": ["purpose", "text version", "status", "timestamps", "source"],
        "may_include_special_category_data": False,
        "storage_location": "PostgreSQL",
        "retention_period": "Until complete profile deletion in the local MVP",
        "legal_basis_placeholder": "Requires qualified legal review",
        "consent_required": False,
        "recipients_or_processors": [],
        "deletion_behavior_de": "Wird bei vollständiger Profillöschung im lokalen MVP gelöscht.",
        "required": True,
    },
)
