from httpx import AsyncClient

PAYLOAD = {"tariff_id": 2, "email": "i@example.com", "method": "card"}
HEADERS = {"Idempotency-Key": "test-key-1"}


async def test_repeat_returns_same_payment_and_200(client: AsyncClient) -> None:
    r1 = await client.post("/payments", json=PAYLOAD, headers=HEADERS)
    r2 = await client.post("/payments", json=PAYLOAD, headers=HEADERS)
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


async def test_no_key_creates_new_payments(client: AsyncClient) -> None:
    r1 = await client.post("/payments", json=PAYLOAD)
    r2 = await client.post("/payments", json=PAYLOAD)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]


async def test_different_keys_create_different_payments(client: AsyncClient) -> None:
    r1 = await client.post("/payments", json=PAYLOAD, headers={"Idempotency-Key": "k1"})
    r2 = await client.post("/payments", json=PAYLOAD, headers={"Idempotency-Key": "k2"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]


async def test_invalid_request_does_not_burn_key(client: AsyncClient) -> None:
    # 422 — платёж не создан, ключ не «сожжён»
    bad = {"tariff_id": 999, "email": "x@example.com", "method": "card"}
    r_bad = await client.post("/payments", json=bad, headers=HEADERS)
    assert r_bad.status_code == 422

    r_ok = await client.post("/payments", json=PAYLOAD, headers=HEADERS)
    assert r_ok.status_code == 201  # ключ всё ещё свободен
