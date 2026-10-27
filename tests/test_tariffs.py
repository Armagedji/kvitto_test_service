from httpx import AsyncClient


async def test_list_tariffs(client: AsyncClient) -> None:
    r = await client.get("/tariffs")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    by_title = {t["title"]: t["price"] for t in data}
    assert by_title == {
        "basic": 990_000,
        "standard": 1_990_000,
        "premium": 2_990_000,
    }
    for t in data:
        assert set(t) == {"id", "title", "price"}
        assert isinstance(t["price"], int)  # копейки, не float
