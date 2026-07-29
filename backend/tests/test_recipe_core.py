from decimal import Decimal


def create_food(
    client,
    name: str = "Haferflocken",
    *,
    unit: str = "g",
    nutrients=None,
    measures=None,
    density=None,
):
    values = nutrients or {
        "energy_kcal": ("370", "kcal"),
        "fat": ("7", "g"),
        "carbohydrate": ("60", "g"),
        "protein": ("13", "g"),
        "fiber": ("10", "g"),
    }
    response = client.post(
        "/api/v1/foods",
        json={
            "name": name,
            "reference_unit": unit,
            "density_g_per_ml": density,
            "nutrients": [
                {"nutrient_code": code, "amount": amount, "unit": value_unit}
                for code, (amount, value_unit) in values.items()
            ],
            "measures": measures or [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def recipe_payload(food_id: str, **updates):
    result = {
        "name": "Porridge",
        "servings": "2.5",
        "tags": ["breakfast", "vegetarian"],
        "ingredients": [
            {"food_id": food_id, "quantity": "250", "unit_type": "base", "unit_code": "g"}
        ],
        "steps": [{"instruction": "Alles verrühren.", "optional_duration_minutes": 5}],
    }
    result.update(updates)
    return result


def test_recipe_lifecycle_calculation_and_scaling(client, saved_profile):
    food = create_food(client)
    created = client.post("/api/v1/recipes", json=recipe_payload(food["id"]))
    assert created.status_code == 201, created.text
    body = created.json()
    protein = next(item for item in body["nutrients"] if item["nutrient_code"] == "protein")
    assert Decimal(protein["amount_total"]) == Decimal("32.5")
    assert Decimal(protein["amount_per_serving"]) == Decimal("13")
    assert body["weight"]["status"] == "theoretical_complete"
    assert Decimal(protein["amount_per_100g"]) == Decimal("13")
    recipe_id = body["id"]
    scaled = client.get(f"/api/v1/recipes/{recipe_id}/scale?servings=5").json()
    assert Decimal(scaled["ingredients"][0]["quantity"]) == Decimal("500")
    assert client.get(f"/api/v1/recipes/{recipe_id}").json()["servings"] == "2.500000"
    duplicate = client.post(f"/api/v1/recipes/{recipe_id}/duplicate")
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] != recipe_id
    assert client.delete(f"/api/v1/recipes/{recipe_id}").status_code == 200
    assert client.get("/api/v1/recipes").json()["total"] == 1
    assert client.get("/api/v1/recipes?include_archived=true").json()["total"] == 2
    assert client.post(f"/api/v1/recipes/{recipe_id}/restore").status_code == 200
    referenced_delete = client.delete(f"/api/v1/foods/{food['id']}/permanent")
    assert referenced_delete.status_code == 409
    assert referenced_delete.json()["error"]["code"] == "FOOD_REFERENCED_BY_RECIPE"
    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200
    assert any(recipe["id"] == recipe_id for recipe in exported.json()["data"]["recipes"])
    permanently_deleted = client.delete(f"/api/v1/recipes/{recipe_id}/permanent")
    assert permanently_deleted.status_code == 200
    assert permanently_deleted.json()["deleted"] is True
    assert client.get(f"/api/v1/recipes/{recipe_id}").status_code == 404
    assert client.get(f"/api/v1/foods/{food['id']}").status_code == 200


def test_unknown_zero_and_coverage(client, saved_profile):
    food = create_food(
        client,
        nutrients={
            "energy_kcal": ("0", "kcal"),
            "fat": ("0", "g"),
            "carbohydrate": ("0", "g"),
            "protein": ("0", "g"),
        },
    )
    body = client.post(
        "/api/v1/recipes",
        json=recipe_payload(food["id"], name="Nullrezept", servings="1", steps=[]),
    ).json()
    protein = next(item for item in body["nutrients"] if item["nutrient_code"] == "protein")
    fiber = (
        next(item for item in body["nutrients"] if item["nutrient_code"] == "fiber")
        if any(item["nutrient_code"] == "fiber" for item in body["nutrients"])
        else None
    )
    assert Decimal(protein["amount_total"]) == 0
    assert protein["is_complete"] is True
    assert fiber is None


def test_measure_normalization_and_estimated_quality(client, saved_profile):
    food = create_food(
        client,
        name="Ei",
        measures=[
            {
                "name": "Stück",
                "quantity": "1",
                "unit_code": "piece",
                "equivalent_quantity": "58",
                "equivalent_unit": "g",
                "is_estimated": True,
            }
        ],
    )
    measure_id = food["measures"][0]["id"]
    payload = recipe_payload(
        food["id"],
        name="Eier",
        servings="1",
        ingredients=[
            {
                "food_id": food["id"],
                "quantity": "2",
                "unit_type": "measure",
                "unit_code": "piece",
                "food_measure_id": measure_id,
            }
        ],
    )
    body = client.post("/api/v1/recipes", json=payload).json()
    assert Decimal(body["ingredients"][0]["normalized_quantity"]) == Decimal("116")
    assert body["quality"]["estimated_conversion_count"] == 1


def test_custom_household_measure_normalization(client, saved_profile):
    food = create_food(client, name="Kartoffelpuffer")
    payload = recipe_payload(
        food["id"],
        name="Puffergericht",
        servings="1",
        ingredients=[
            {
                "food_id": food["id"],
                "quantity": "3",
                "unit_type": "custom_measure",
                "unit_code": "piece",
                "equivalent_quantity": "120",
                "equivalent_unit": "g",
            }
        ],
    )
    body = client.post("/api/v1/recipes", json=payload).json()
    ingredient = body["ingredients"][0]
    assert ingredient["unit_name"] == "Stück"
    assert Decimal(ingredient["normalized_quantity"]) == Decimal("360")
    assert Decimal(ingredient["equivalent_quantity"]) == Decimal("120")


def test_validation_duplicate_update_and_search(client, saved_profile):
    food = create_food(client)
    payload = recipe_payload(food["id"])
    first = client.post("/api/v1/recipes", json=payload)
    assert first.status_code == 201
    assert client.post("/api/v1/recipes", json=payload).status_code == 409
    assert (
        client.post(
            "/api/v1/recipes", json={**payload, "name": "Leer", "ingredients": []}
        ).status_code
        == 422
    )
    assert client.get("/api/v1/recipes?query=PORR").json()["total"] == 1
    updated = client.put(
        f"/api/v1/recipes/{first.json()['id']}", json={**payload, "name": "Neuer Porridge"}
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == first.json()["id"]


def test_profile_reset_preserves_food_and_recipe_but_all_data_removes_everything(
    client, saved_profile
):
    food = create_food(client, name="Bibliotheksfood")
    recipe = client.post(
        "/api/v1/recipes", json=recipe_payload(food["id"], name="Bibliotheksrezept")
    ).json()
    reset = client.request(
        "DELETE", "/api/v1/privacy/profile-and-assessments", json={"confirm": True}
    )
    assert reset.status_code == 200
    assert client.get("/api/v1/profile").status_code == 404
    assert client.get(f"/api/v1/foods/{food['id']}").status_code == 200
    assert client.get(f"/api/v1/recipes/{recipe['id']}").status_code == 200
    deleted = client.request("DELETE", "/api/v1/privacy/all-data", json={"confirm": True})
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/foods/{food['id']}").status_code == 404
    assert client.get(f"/api/v1/recipes/{recipe['id']}").status_code == 404


def test_library_bulk_deletion_requires_recipes_before_foods(client, saved_profile):
    food = create_food(client, name="Verknüpftes Food")
    client.post("/api/v1/recipes", json=recipe_payload(food["id"], name="Verknüpft"))
    blocked = client.request("DELETE", "/api/v1/privacy/foods", json={"confirm": True})
    assert blocked.status_code == 409
    assert (
        client.request("DELETE", "/api/v1/privacy/recipes", json={"confirm": True}).status_code
        == 200
    )
    assert (
        client.request("DELETE", "/api/v1/privacy/foods", json={"confirm": True}).status_code == 200
    )
    assert client.get("/api/v1/profile").status_code == 200
