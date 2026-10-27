from httpx import AsyncClient


async def _create(client: AsyncClient, **overrides) -> dict:
    payload = {"tariff_id": 2, "email": "r@example.com", "method": "card", **overrides}
    r = await client.post("/payments", json=payload)
    assert r.status_code == 201
    return r.json()


async def test_get_by_id_ok(client: AsyncClient) -> None:
    p = await _create(client)
    r = await client.get(f"/payments/{p['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == p["id"]


async def test_get_by_id_404(client: AsyncClient) -> None:
    r = await client.get("/payments/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_get_by_id_422_on_bad_uuid(client: AsyncClient) -> None:
    r = await client.get("/payments/not-a-uuid")
    assert r.status_code == 422


async def test_list_filter_by_email(client: AsyncClient) -> None:
    await _create(client, email="a@example.com")
    await _create(client, email="b@example.com")
    r = await client.get("/payments", params={"email": "a@example.com"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["email"] == "a@example.com"


async def test_list_filter_by_status(client: AsyncClient) -> None:
    await _create(client)
    r = await client.get("/payments", params={"status": "pending"})
    assert len(r.json()) == 1
    r2 = await client.get("/payments", params={"status": "succeeded"})
    assert r2.json() == []


async def test_list_filter_by_status_invalid_returns_422(client: AsyncClient) -> None:
    r = await client.get("/payments", params={"status": "unknown"})
    assert r.status_code == 422


async def test_list_combined_filters(client: AsyncClient) -> None:
    await _create(client, email="x@example.com")
    await _create(client, email="y@example.com")
    r = await client.get("/payments", params={"email": "x@example.com", "status": "pending"})
    assert len(r.json()) == 1
    r2 = await client.get("/payments", params={"email": "x@example.com", "status": "succeeded"})
    assert r2.json() == []
