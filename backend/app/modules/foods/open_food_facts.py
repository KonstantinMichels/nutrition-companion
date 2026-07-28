from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.errors import ApiError
from app.modules.foods.nutrient_catalog import NUTRIENT_BY_CODE

API_BASE = "https://world.openfoodfacts.org/api/v3/product"
USER_AGENT = "NutritionCompanion/0.1 (contact: local-development)"
BARCODE_FIELDS = (
    "code,product_name,product_name_de,brands,quantity,product_quantity_unit,"
    "serving_quantity_unit,nutrition_data_per,nutriments,categories_tags,"
    "image_front_small_url,last_modified_t"
)

OFF_NUTRIENT_MAP = {
    "energy-kcal": "energy_kcal",
    "fat": "fat",
    "saturated-fat": "saturated_fat",
    "carbohydrates": "carbohydrate",
    "sugars": "sugars",
    "fiber": "fiber",
    "proteins": "protein",
    "salt": "salt",
    "sodium": "sodium",
    "vitamin-a": "vitamin_a",
    "vitamin-d": "vitamin_d",
    "vitamin-e": "vitamin_e",
    "vitamin-k": "vitamin_k",
    "vitamin-c": "vitamin_c",
    "vitamin-b1": "thiamin",
    "vitamin-b2": "riboflavin",
    "vitamin-pp": "niacin",
    "pantothenic-acid": "pantothenic_acid",
    "vitamin-b6": "vitamin_b6",
    "biotin": "biotin",
    "folates": "folate",
    "vitamin-b12": "vitamin_b12",
    "calcium": "calcium",
    "magnesium": "magnesium",
    "potassium": "potassium",
    "chloride": "chloride",
    "phosphorus": "phosphorus",
    "iron": "iron",
    "zinc": "zinc",
    "iodine": "iodine",
    "selenium": "selenium",
    "copper": "copper",
    "manganese": "manganese",
}


def normalize_barcode(code: str) -> str:
    normalized = code.strip()
    if not normalized.isdigit() or len(normalized) not in {8, 12, 13, 14}:
        raise ApiError(
            code="INVALID_BARCODE",
            message="Der Barcode muss eine gültige EAN-, UPC- oder GTIN-Nummer sein.",
            status_code=422,
        )
    return normalized


def fetch_product(code: str) -> dict[str, Any]:
    barcode = normalize_barcode(code)
    url = f"{API_BASE}/{barcode}?{urlencode({'fields': BARCODE_FIELDS})}"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read())  # type: ignore[no-any-return]
    except HTTPError as error:
        if error.code == 404:
            raise ApiError(
                code="BARCODE_PRODUCT_NOT_FOUND",
                message="Zu diesem Barcode wurde kein Produkt gefunden.",
                status_code=404,
            ) from error
        raise ApiError(
            code="EXTERNAL_FOOD_SERVICE_UNAVAILABLE",
            message="Open Food Facts ist momentan nicht erreichbar.",
            status_code=503,
        ) from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ApiError(
            code="EXTERNAL_FOOD_SERVICE_UNAVAILABLE",
            message="Open Food Facts ist momentan nicht erreichbar.",
            status_code=503,
        ) from error


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() and parsed >= 0 else None


def _from_off_standard_unit(amount: Decimal, local_unit: str) -> Decimal:
    """OFF normalizes non-energy nutrient `_100g` values to grams."""

    if local_unit.startswith("mg"):
        return amount * Decimal(1000)
    if local_unit.startswith(("µg", "μg")):
        return amount * Decimal(1_000_000)
    return amount


def map_product(code: str, response: dict[str, Any]) -> dict[str, Any]:
    product_raw = response.get("product")
    if not isinstance(product_raw, dict):
        raise ApiError(
            code="BARCODE_PRODUCT_NOT_FOUND",
            message="Zu diesem Barcode wurde kein Produkt gefunden.",
            status_code=404,
        )
    product: dict[str, Any] = product_raw
    name = str(product.get("product_name_de") or product.get("product_name") or "").strip()
    if not name:
        name = f"Produkt {code}"
    quantity_unit = str(
        product.get("product_quantity_unit") or product.get("serving_quantity_unit") or ""
    ).lower()
    reference_unit = "ml" if quantity_unit in {"ml", "cl", "l"} else "g"
    nutriments = product.get("nutriments")
    nutrients: list[dict[str, str]] = []
    if isinstance(nutriments, dict):
        for off_code, local_code in OFF_NUTRIENT_MAP.items():
            amount = _decimal(nutriments.get(f"{off_code}_100g"))
            if amount is None:
                continue
            definition = NUTRIENT_BY_CODE[local_code]
            if local_code != "energy_kcal":
                amount = _from_off_standard_unit(amount, definition.canonical_unit)
            nutrients.append(
                {
                    "nutrient_code": local_code,
                    "amount": str(amount),
                    "unit": definition.canonical_unit,
                }
            )
    if any(item["nutrient_code"] == "salt" for item in nutrients):
        nutrients = [item for item in nutrients if item["nutrient_code"] != "sodium"]
    return {
        "barcode": str(product.get("code") or code),
        "name": name,
        "brand": str(product.get("brands") or "").strip() or None,
        "quantity_label": str(product.get("quantity") or "").strip() or None,
        "reference_unit": reference_unit,
        "nutrients": nutrients,
        "image_url": product.get("image_front_small_url"),
        "source_name": "Open Food Facts",
        "source_version": str(product.get("last_modified_t") or "") or None,
        "warnings": [
            "Die Angaben stammen aus einer gemeinschaftlich gepflegten "
            "Datenbank und müssen geprüft werden."
        ],
    }


def lookup_barcode(code: str) -> dict[str, Any]:
    barcode = normalize_barcode(code)
    return map_product(barcode, fetch_product(barcode))
