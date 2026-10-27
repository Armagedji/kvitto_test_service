from httpx import AsyncClient

PAYLOAD_CARD = {"tariff_id": 2, "email": "a@example.com", "method": "card"}


async def test_create_card_no_promo(client: AsyncClient) -> None:
    r = await client.post("/payments", json=PAYLOAD_CARD)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["tariff_id"] == 2
    assert body["amount"] == 1_990_000
    assert body["discount"] == 0
    assert body["method"] == "card"
    assert body["installment_months"] is None
    assert body["schedule"] is None
    assert body["email"] == "a@example.com"
    assert set(body) == {
        "id",
        "status",
        "tariff_id",
        "amount",
        "discount",
        "method",
        "installment_months",
        "schedule",
        "email",
        "created_at",
    }


async def test_promo_case_insensitive(client: AsyncClient) -> None:
    for code in ("KVITTO10", "kvitto10", "KvItTo10"):
        r = await client.post("/payments", json={**PAYLOAD_CARD, "promo_code": code})
        assert r.status_code == 201, code
        body = r.json()
        assert body["discount"] == 199_000
        assert body["amount"] == 1_791_000


async def test_promo_unknown_returns_422(client: AsyncClient) -> None:
    r = await client.post("/payments", json={**PAYLOAD_CARD, "promo_code": "WRONG"})
    assert r.status_code == 422


async def test_installment_without_months_returns_422(client: AsyncClient) -> None:
    r = await client.post("/payments", json={**PAYLOAD_CARD, "method": "installment"})
    assert r.status_code == 422


async def test_installment_bad_months_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/payments",
        json={**PAYLOAD_CARD, "method": "installment", "installment_months": 5},
    )
    assert r.status_code == 422


async def test_installment_months_for_card_returns_422(client: AsyncClient) -> None:
    r = await client.post("/payments", json={**PAYLOAD_CARD, "installment_months": 3})
    assert r.status_code == 422


async def test_installment_schedule_example_from_spec(client: AsyncClient) -> None:
    r = await client.post(
        "/payments",
        json={
            "tariff_id": 2,
            "email": "a@example.com",
            "method": "installment",
            "installment_months": 3,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["amount"] == 1_990_000
    assert body["schedule"] == [663_334, 663_333, 663_333]
    assert sum(body["schedule"]) == body["amount"]


async def test_installment_schedule_sums_exactly(client: AsyncClient) -> None:
    # тариф 3 + промокод: amount = 2_691_000, 6 месяцев, делится ровно
    r = await client.post(
        "/payments",
        json={
            "tariff_id": 3,
            "email": "a@example.com",
            "method": "installment",
            "installment_months": 6,
            "promo_code": "KVITTO10",
        },
    )
    body = r.json()
    assert body["amount"] == 2_691_000
    assert body["schedule"] == [448_500] * 6
    assert sum(body["schedule"]) == body["amount"]


async def test_unknown_tariff_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/payments",
        json={"tariff_id": 999, "email": "a@example.com", "method": "card"},
    )
    assert r.status_code == 422


async def test_invalid_email_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/payments",
        json={"tariff_id": 2, "email": "not-an-email", "method": "card"},
    )
    assert r.status_code == 422
