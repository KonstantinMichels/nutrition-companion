from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.database.base import utc_now
from app.modules.daily_meal_planning import repository as plan_repository
from app.modules.foods import repository as food_repository
from app.modules.foods.models import Food
from app.modules.pantry import service as pantry_service
from app.modules.shopping_lists.models import ShoppingList, ShoppingListItem, ShoppingListItemSource
from app.modules.shopping_lists.schemas import (
    GenerationRequest,
    ItemCreate,
    ItemPatch,
    ListCreate,
    ListPatch,
)


def _error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status)


def _category(food: Food) -> str:
    value = food.category_code or "other"
    mapping = {
        "fruit": "produce",
        "vegetables": "produce",
        "dairy": "dairy",
        "beverages": "beverages",
        "meat": "meat",
        "fish": "meat",
        "bakery": "bakery",
        "frozen": "frozen",
    }
    return mapping.get(
        value,
        value
        if value
        in {"produce", "dairy", "meat", "bakery", "frozen", "beverages", "household", "other"}
        else "other",
    )


def _plans(
    session: Session, profile_id: UUID, request: GenerationRequest
) -> tuple[list[Any], date | None, date | None, str]:
    if request.daily_plan_id:
        plan = plan_repository.get(session, profile_id, request.daily_plan_id)
        if plan is None:
            raise _error("SHOPPING_SOURCE_NOT_FOUND", "Der Tagesplan wurde nicht gefunden.", 404)
        return [plan], None, None, "daily_plan"
    assert request.week_anchor_date is not None
    start = request.week_anchor_date - timedelta(days=request.week_anchor_date.weekday())
    end = start + timedelta(days=6)
    plans = [
        p
        for p in plan_repository.in_date_range(session, profile_id, start, end)
        if not p.is_archived
    ]
    if not plans:
        raise _error(
            "SHOPPING_SOURCE_EMPTY", "Für diese Woche wurden keine Tagespläne gefunden.", 409
        )
    return plans, start, end, "weekly_plan"


def calculate(session: Session, profile_id: UUID, request: GenerationRequest) -> dict[str, Any]:
    plans, week_start, week_end, source_type = _plans(session, profile_id, request)
    grouped: dict[UUID, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    meal_count = entry_count = estimated_count = archived_count = 0
    for plan in plans:
        archived_count += int(plan.is_archived)
        for meal in plan.meals:
            meal_count += 1
            for entry in meal.entries:
                entry_count += 1
                contributions: list[tuple[Food, Decimal, str, bool, UUID | None, str | None]] = []
                if (
                    entry.entry_type == "food"
                    and entry.food is not None
                    and entry.food_quantity is not None
                    and entry.food_unit_code
                ):
                    try:
                        qty, unit, estimated = pantry_service.normalize(
                            entry.food,
                            entry.food_quantity,
                            entry.food_unit_code,
                            entry.food_measure_id,
                        )
                        contributions.append((entry.food, qty, unit, estimated, None, None))
                    except ApiError as exc:
                        unresolved.append(
                            _unresolved(
                                plan.plan_date,
                                meal.custom_name or meal.meal_type,
                                None,
                                entry.food.name,
                                entry.food_quantity,
                                entry.food_unit_code,
                                exc.code,
                                exc.message,
                            )
                        )
                elif (
                    entry.entry_type == "recipe"
                    and entry.recipe is not None
                    and entry.recipe_portion_count is not None
                ):
                    recipe = entry.recipe
                    archived_count += int(recipe.is_archived)
                    factor = entry.recipe_portion_count / recipe.servings
                    for ingredient in recipe.ingredients:
                        if ingredient.food is None:
                            continue
                        contributions.append(
                            (
                                ingredient.food,
                                ingredient.normalized_quantity * factor,
                                ingredient.normalized_unit,
                                ingredient.conversion_is_estimated,
                                ingredient.id,
                                recipe.name,
                            )
                        )
                else:
                    unresolved.append(
                        _unresolved(
                            plan.plan_date,
                            meal.custom_name or meal.meal_type,
                            None,
                            None,
                            None,
                            None,
                            "SHOPPING_REQUIREMENT_UNRESOLVED",
                            "Die Planquelle ist unvollständig.",
                        )
                    )
                for food, qty, unit, estimated, ingredient_id, recipe_name in contributions:
                    estimated_count += int(estimated)
                    group = grouped.setdefault(
                        food.id, {"food": food, "required": Decimal(0), "unit": unit, "sources": []}
                    )
                    if group["unit"] != unit:
                        unresolved.append(
                            _unresolved(
                                plan.plan_date,
                                meal.custom_name or meal.meal_type,
                                recipe_name,
                                food.name,
                                qty,
                                unit,
                                "SHOPPING_UNIT_INCOMPATIBLE",
                                "Die Mengen haben inkompatible Einheiten.",
                            )
                        )
                        continue
                    group["required"] += qty
                    group["sources"].append(
                        {
                            "source_type": "recipe_ingredient" if ingredient_id else "direct_food",
                            "daily_plan_id": plan.id,
                            "plan_date": plan.plan_date,
                            "meal_id": meal.id,
                            "meal_name": meal.custom_name or meal.meal_type,
                            "meal_entry_id": entry.id,
                            "recipe_id": entry.recipe_id,
                            "recipe_name": recipe_name,
                            "recipe_ingredient_id": ingredient_id,
                            "quantity": qty,
                            "unit": unit,
                            "conversion_estimated": estimated,
                        }
                    )
    pantry = (
        {row["food_id"]: row for row in pantry_service.availability(session, profile_id)}
        if request.pantry_considered
        else {}
    )
    items = []
    for group in grouped.values():
        food = group["food"]
        available = (
            pantry.get(food.id, {}).get("available_quantity", Decimal(0))
            if request.pantry_considered
            else None
        )
        suggested = (
            max(group["required"] - (available or Decimal(0)), Decimal(0))
            if request.pantry_considered
            else group["required"]
        )
        items.append(
            {
                "food_id": food.id,
                "food_name": food.name,
                "brand": food.brand,
                "category_code": _category(food),
                "required_quantity": group["required"],
                "canonical_unit": group["unit"],
                "pantry_available_quantity": available,
                "suggested_purchase_quantity": suggested,
                "fully_covered": suggested == 0,
                "archived_food": food.is_archived,
                "sources": group["sources"],
            }
        )
    items.sort(key=lambda row: (row["category_code"], row["food_name"].casefold()))
    warnings = []
    if not request.pantry_considered:
        warnings.append(
            {
                "code": "SHOPPING_PANTRY_NOT_CONSIDERED",
                "severity": "info",
                "message": "Der Vorrat wurde nicht berücksichtigt.",
            }
        )
    if unresolved:
        warnings.append(
            {
                "code": "SHOPPING_REQUIREMENT_UNRESOLVED",
                "severity": "warning",
                "message": "Mindestens eine Anforderung muss geprüft werden.",
            }
        )
    summary = {
        "source_type": source_type,
        "source_day_count": len({p.plan_date for p in plans}),
        "planned_day_count": len(plans),
        "source_meal_count": meal_count,
        "source_entry_count": entry_count,
        "generated_food_item_count": len(items),
        "manual_item_count": 0,
        "pantry_considered": request.pantry_considered,
        "pantry_matched_item_count": sum(
            i["pantry_available_quantity"] is not None and i["pantry_available_quantity"] > 0
            for i in items
        ),
        "fully_covered_item_count": sum(i["fully_covered"] for i in items),
        "suggested_purchase_item_count": sum(i["suggested_purchase_quantity"] > 0 for i in items),
        "overridden_quantity_count": 0,
        "estimated_conversion_count": estimated_count,
        "unresolved_requirement_count": len(unresolved),
        "archived_source_count": archived_count,
        "quality_level": "requires_review"
        if unresolved
        else "partial"
        if warnings or estimated_count or archived_count
        else "complete",
    }
    return {
        "source_type": source_type,
        "source_daily_plan_id": plans[0].id if source_type == "daily_plan" else None,
        "source_week_start": week_start,
        "source_week_end": week_end,
        "source_days": [p.plan_date for p in plans],
        "items": items,
        "unresolved_requirements": unresolved,
        "warnings": warnings,
        "quality_summary": summary,
    }


def _unresolved(
    day: date,
    meal: str,
    recipe: str | None,
    food: str | None,
    quantity: Any,
    unit: str | None,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "source_date": day,
        "meal": meal,
        "recipe": recipe,
        "food": food,
        "entered_quantity": quantity,
        "entered_unit": unit,
        "reason_code": code,
        "explanation": message,
    }


LOAD = (
    selectinload(ShoppingList.items).selectinload(ShoppingListItem.sources),
    selectinload(ShoppingList.items).selectinload(ShoppingListItem.food),
)


def _get(session: Session, profile_id: UUID, list_id: UUID, *, lock: bool = False) -> ShoppingList:
    stmt = (
        select(ShoppingList)
        .where(ShoppingList.id == list_id, ShoppingList.owner_profile_id == profile_id)
        .options(*LOAD)
    )
    if lock:
        stmt = stmt.with_for_update()
    result = session.scalar(stmt)
    if result is None:
        raise _error("SHOPPING_LIST_NOT_FOUND", "Die Einkaufsliste wurde nicht gefunden.", 404)
    return result


def create(session: Session, profile_id: UUID, payload: ListCreate) -> dict[str, Any]:
    item = ShoppingList(
        owner_profile_id=profile_id,
        name=payload.name.strip(),
        notes=payload.notes,
        source_type="manual",
        source_summary={"quality_level": "manual"},
    )
    session.add(item)
    session.commit()
    return detail(session, profile_id, item.id)


def generate(session: Session, profile_id: UUID, payload: GenerationRequest) -> dict[str, Any]:
    preview = calculate(session, profile_id, payload)
    default_name = (
        f"Einkauf {preview['source_days'][0].strftime('%d.%m.%Y')}"
        if preview["source_type"] == "daily_plan"
        else f"Einkauf KW {preview['source_week_start'].isocalendar().week}"
    )
    shopping = ShoppingList(
        owner_profile_id=profile_id,
        name=(payload.name or default_name).strip(),
        source_type=preview["source_type"],
        source_daily_plan_id=preview["source_daily_plan_id"],
        source_week_start=preview["source_week_start"],
        source_week_end=preview["source_week_end"],
        pantry_considered=payload.pantry_considered,
        generated_at=utc_now(),
        source_summary=preview["quality_summary"],
        warning_codes=[w["code"] for w in preview["warnings"]],
    )
    session.add(shopping)
    session.flush()
    for position, row in enumerate(preview["items"]):
        _add_generated(session, shopping, row, position)
    session.commit()
    return detail(session, profile_id, shopping.id)


def _add_generated(
    session: Session, shopping: ShoppingList, row: dict[str, Any], position: int
) -> ShoppingListItem:
    item = ShoppingListItem(
        shopping_list=shopping,
        item_type="food",
        origin_type="generated",
        food_id=row["food_id"],
        food_name_snapshot=row["food_name"],
        category_code=row["category_code"],
        position=position,
        canonical_unit=row["canonical_unit"],
        required_quantity=row["required_quantity"],
        pantry_available_quantity=row["pantry_available_quantity"],
        suggested_purchase_quantity=row["suggested_purchase_quantity"],
        purchase_quantity=row["suggested_purchase_quantity"],
        purchase_unit_code=row["canonical_unit"],
    )
    session.add(item)
    session.flush()
    for src in row["sources"]:
        session.add(
            ShoppingListItemSource(
                shopping_list_item_id=item.id,
                source_type=src["source_type"],
                daily_plan_id=src["daily_plan_id"],
                plan_date=src["plan_date"],
                meal_id=src["meal_id"],
                meal_name_snapshot=src["meal_name"],
                meal_entry_id=src["meal_entry_id"],
                recipe_id=src["recipe_id"],
                recipe_name_snapshot=src["recipe_name"],
                recipe_ingredient_id=src["recipe_ingredient_id"],
                food_id=row["food_id"],
                quantity=src["quantity"],
                unit=src["unit"],
                conversion_estimated=src["conversion_estimated"],
            )
        )
    return item


def list_all(
    session: Session,
    profile_id: UUID,
    status: str | None,
    source_type: str | None,
    include_archived: bool,
    query: str | None,
    page: int,
    page_size: int,
    sort: str,
) -> dict[str, Any]:
    criteria = [ShoppingList.owner_profile_id == profile_id]
    if not include_archived:
        criteria.append(ShoppingList.is_archived.is_(False))
    if status:
        criteria.append(ShoppingList.status == status)
    if source_type:
        criteria.append(ShoppingList.source_type == source_type)
    if query:
        criteria.append(ShoppingList.name.ilike(f"%{query}%"))
    total = session.scalar(select(func.count()).select_from(ShoppingList).where(*criteria)) or 0
    order = ShoppingList.name if sort == "name" else ShoppingList.updated_at.desc()
    rows = list(
        session.scalars(
            select(ShoppingList)
            .where(*criteria)
            .options(selectinload(ShoppingList.items))
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return {
        "items": [_summary(x) for x in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def _summary(x: ShoppingList) -> dict[str, Any]:
    active = [i for i in x.items if i.source_status != "no_longer_required"]
    return {
        "id": x.id,
        "name": x.name,
        "status": x.status,
        "source_type": x.source_type,
        "active_item_count": len(active),
        "checked_item_count": sum(i.is_checked for i in active),
        "suggested_item_count": sum((i.purchase_quantity or 0) > 0 for i in active),
        "is_archived": x.is_archived,
        "updated_at": x.updated_at,
    }


def detail(session: Session, profile_id: UUID, list_id: UUID) -> dict[str, Any]:
    x = _get(session, profile_id, list_id)
    items = [_item_dict(i) for i in x.items]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in items:
        grouped.setdefault(row["category_code"], []).append(row)
    return {
        **_summary(x),
        "notes": x.notes,
        "pantry_considered": x.pantry_considered,
        "source_daily_plan_id": x.source_daily_plan_id,
        "source_week_start": x.source_week_start,
        "source_week_end": x.source_week_end,
        "generated_at": x.generated_at,
        "refreshed_at": x.refreshed_at,
        "completed_at": x.completed_at,
        "version": x.version,
        "quality_summary": x.source_summary,
        "warning_codes": x.warning_codes,
        "items": items,
        "grouped_items": grouped,
    }


def _item_dict(i: ShoppingListItem) -> dict[str, Any]:
    return {
        "id": i.id,
        "item_type": i.item_type,
        "origin_type": i.origin_type,
        "food_id": i.food_id,
        "name": i.food_name_snapshot or i.manual_name,
        "category_code": i.category_code,
        "position": i.position,
        "canonical_unit": i.canonical_unit,
        "required_quantity": i.required_quantity,
        "pantry_available_quantity": i.pantry_available_quantity,
        "suggested_purchase_quantity": i.suggested_purchase_quantity,
        "purchase_quantity": i.purchase_quantity,
        "purchase_unit_code": i.purchase_unit_code,
        "manual_quantity": i.manual_quantity,
        "manual_unit_label": i.manual_unit_label,
        "quantity_overridden": i.quantity_overridden,
        "is_checked": i.is_checked,
        "source_status": i.source_status,
        "warning_codes": i.warning_codes,
        "note": i.note,
        "sources": [
            {
                "source_date": s.plan_date,
                "meal": s.meal_name_snapshot,
                "recipe": s.recipe_name_snapshot,
                "quantity": s.quantity,
                "unit": s.unit,
                "conversion_estimated": s.conversion_estimated,
            }
            for s in i.sources
        ],
    }


def update(session: Session, profile_id: UUID, list_id: UUID, payload: ListPatch) -> dict[str, Any]:
    x = _get(session, profile_id, list_id)
    for field in payload.model_fields_set:
        setattr(x, field, getattr(payload, field))
    x.version += 1
    session.commit()
    return detail(session, profile_id, list_id)


def add_item(
    session: Session, profile_id: UUID, list_id: UUID, payload: ItemCreate
) -> dict[str, Any]:
    x = _get(session, profile_id, list_id)
    if x.is_archived:
        raise _error("SHOPPING_LIST_ARCHIVED", "Archivierte Listen sind schreibgeschützt.", 409)
    position = max((i.position for i in x.items), default=-1) + 1
    if payload.food_id:
        food = food_repository.get_food(session, profile_id, payload.food_id)
        if food is None:
            raise _error("SHOPPING_FOOD_NOT_FOUND", "Das Lebensmittel wurde nicht gefunden.", 404)
        if food.is_archived:
            raise _error(
                "SHOPPING_FOOD_ARCHIVED",
                "Archivierte Lebensmittel können nicht hinzugefügt werden.",
                409,
            )
        assert payload.quantity is not None and payload.unit_code is not None
        qty, unit, estimated = pantry_service.normalize(
            food, payload.quantity, payload.unit_code, payload.food_measure_id
        )
        item = ShoppingListItem(
            shopping_list=x,
            item_type="food",
            origin_type="manual",
            food_id=food.id,
            food_name_snapshot=food.name,
            category_code=payload.category_code or _category(food),
            position=position,
            canonical_unit=unit,
            purchase_quantity=qty,
            purchase_unit_code=unit,
            note=payload.note,
            warning_codes=["SHOPPING_MEASURE_ESTIMATED"] if estimated else [],
        )
    else:
        item = ShoppingListItem(
            shopping_list=x,
            item_type="manual",
            origin_type="manual",
            manual_name=payload.name.strip() if payload.name else None,
            category_code=payload.category_code,
            position=position,
            manual_quantity=payload.quantity,
            manual_unit_label=payload.unit_code,
            note=payload.note,
        )
    session.add(item)
    x.version += 1
    session.commit()
    return _item_dict(item)


def _owned_item(
    session: Session, profile_id: UUID, list_id: UUID, item_id: UUID
) -> tuple[ShoppingList, ShoppingListItem]:
    x = _get(session, profile_id, list_id)
    item = next((i for i in x.items if i.id == item_id), None)
    if item is None:
        raise _error("SHOPPING_ITEM_NOT_FOUND", "Der Eintrag wurde nicht gefunden.", 404)
    return x, item


def update_item(
    session: Session, profile_id: UUID, list_id: UUID, item_id: UUID, payload: ItemPatch
) -> dict[str, Any]:
    x, item = _owned_item(session, profile_id, list_id, item_id)
    if payload.reset_to_suggestion and item.suggested_purchase_quantity is not None:
        item.purchase_quantity = item.suggested_purchase_quantity
        item.purchase_unit_code = item.canonical_unit
        item.quantity_overridden = False
    for field in payload.model_fields_set - {"reset_to_suggestion"}:
        value = getattr(payload, field)
        if field == "is_checked":
            item.checked_at = datetime.now(UTC) if value else None
        setattr(item, field, value)
    if (
        "purchase_quantity" in payload.model_fields_set
        or "purchase_unit_code" in payload.model_fields_set
    ):
        item.quantity_overridden = True
    x.version += 1
    session.commit()
    return _item_dict(item)


def remove_item(session: Session, profile_id: UUID, list_id: UUID, item_id: UUID) -> None:
    x, item = _owned_item(session, profile_id, list_id, item_id)
    session.delete(item)
    x.version += 1
    session.commit()


def reorder(session: Session, profile_id: UUID, list_id: UUID, ids: list[UUID]) -> dict[str, Any]:
    x = _get(session, profile_id, list_id)
    if len(ids) != len(set(ids)) or set(ids) != {i.id for i in x.items}:
        raise _error(
            "SHOPPING_REORDER_INVALID", "Die Reihenfolge muss alle Einträge genau einmal enthalten."
        )
    positions = {value: index for index, value in enumerate(ids)}
    for item in x.items:
        item.position = positions[item.id]
    x.version += 1
    session.commit()
    return detail(session, profile_id, list_id)


def set_state(session: Session, profile_id: UUID, list_id: UUID, action: str) -> dict[str, Any]:
    x = _get(session, profile_id, list_id)
    now = datetime.now(UTC)
    if action == "complete":
        x.status, x.completed_at = "completed", now
    elif action == "reopen":
        x.status, x.completed_at = "open", None
    elif action == "archive":
        x.is_archived, x.archived_at = True, now
    elif action == "restore":
        x.is_archived, x.archived_at = False, None
    x.version += 1
    session.commit()
    return detail(session, profile_id, list_id)


def _refresh_request(x: ShoppingList) -> GenerationRequest:
    if x.source_type == "daily_plan" and x.source_daily_plan_id:
        return GenerationRequest(
            daily_plan_id=x.source_daily_plan_id, pantry_considered=x.pantry_considered
        )
    if x.source_type == "weekly_plan" and x.source_week_start:
        return GenerationRequest(
            week_anchor_date=x.source_week_start, pantry_considered=x.pantry_considered
        )
    raise _error(
        "SHOPPING_REFRESH_UNAVAILABLE",
        "Manuelle Listen können nicht aus einem Plan aktualisiert werden.",
        409,
    )


def refresh_preview(session: Session, profile_id: UUID, list_id: UUID) -> dict[str, Any]:
    x = _get(session, profile_id, list_id)
    preview = calculate(session, profile_id, _refresh_request(x))
    old = {i.food_id: i for i in x.items if i.origin_type == "generated"}
    new = {i["food_id"]: i for i in preview["items"]}
    changed = [
        {
            "food_id": fid,
            "name": row["food_name"],
            "old_required_quantity": old[fid].required_quantity,
            "new_required_quantity": row["required_quantity"],
        }
        for fid, row in new.items()
        if fid in old
        and (
            old[fid].required_quantity != row["required_quantity"]
            or old[fid].pantry_available_quantity != row["pantry_available_quantity"]
        )
    ]
    return {
        "preview_version": x.version,
        "new_items": [r for fid, r in new.items() if fid not in old],
        "removed_requirements": [_item_dict(i) for fid, i in old.items() if fid not in new],
        "changed_required_quantities": changed,
        "changed_pantry_quantities": changed,
        "changed_suggested_quantities": changed,
        "unchanged_items": sum(
            fid in old
            and old[fid].required_quantity == r["required_quantity"]
            and old[fid].pantry_available_quantity == r["pantry_available_quantity"]
            for fid, r in new.items()
        ),
        "unresolved_sources": preview["unresolved_requirements"],
        "quality_summary": preview["quality_summary"],
    }


def refresh(
    session: Session, profile_id: UUID, list_id: UUID, preview_version: int
) -> dict[str, Any]:
    x = _get(session, profile_id, list_id, lock=True)
    if x.version != preview_version:
        raise _error(
            "SHOPPING_REFRESH_STALE",
            "Die Liste wurde seit der Vorschau geändert. Bitte Vorschau neu laden.",
            409,
        )
    preview = calculate(session, profile_id, _refresh_request(x))
    old = {i.food_id: i for i in x.items if i.origin_type == "generated"}
    new = {r["food_id"]: r for r in preview["items"]}
    for fid, item in old.items():
        if fid not in new:
            if item.is_checked or item.quantity_overridden:
                item.source_status = "no_longer_required"
                item.warning_codes = ["SHOPPING_ITEM_NO_LONGER_REQUIRED"]
            else:
                session.delete(item)
            continue
        row = new[fid]
        item.required_quantity = row["required_quantity"]
        item.pantry_available_quantity = row["pantry_available_quantity"]
        item.suggested_purchase_quantity = row["suggested_purchase_quantity"]
        item.source_status = "current"
        if not item.quantity_overridden:
            item.purchase_quantity = row["suggested_purchase_quantity"]
        item.sources.clear()
        session.flush()
        for src in row["sources"]:
            session.add(
                ShoppingListItemSource(
                    shopping_list_item_id=item.id,
                    source_type=src["source_type"],
                    daily_plan_id=src["daily_plan_id"],
                    plan_date=src["plan_date"],
                    meal_id=src["meal_id"],
                    meal_name_snapshot=src["meal_name"],
                    meal_entry_id=src["meal_entry_id"],
                    recipe_id=src["recipe_id"],
                    recipe_name_snapshot=src["recipe_name"],
                    recipe_ingredient_id=src["recipe_ingredient_id"],
                    food_id=fid,
                    quantity=src["quantity"],
                    unit=src["unit"],
                    conversion_estimated=src["conversion_estimated"],
                )
            )
    position = max((i.position for i in x.items), default=-1) + 1
    for fid, row in new.items():
        if fid not in old:
            _add_generated(session, x, row, position)
            position += 1
    x.source_summary = preview["quality_summary"]
    x.warning_codes = [w["code"] for w in preview["warnings"]]
    x.refreshed_at = utc_now()
    x.version += 1
    session.commit()
    return detail(session, profile_id, list_id)
