import json

from httpx import AsyncClient

from tests.conftest import sign


async def _create(client: AsyncClient) -> str:
    r = await client.post(
        "/payments",
        json={"tariff_id": 2, "email": "w@example.com", "method": "card"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def _body(payment_id: str, status: str) -> bytes:
    return json.dumps(
        {"payment_id": payment_id, "status": status}, separators=(",", ":")
    ).encode()


async def _post_webhook(client: AsyncClient, body: bytes, signature: str | None) -> object:
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Signature"] = signature
    return await client.post("/webhooks/bank", content=body, headers=headers)


async def test_pending_to_succeeded_ok(client: AsyncClient) -> None:
    pid = await _create(client)
    body = _body(pid, "succeeded")
    r = await _post_webhook(client, body, sign(body))
    assert r.status_code == 200
    assert r.json() == {"result": "ok"}

    r2 = await client.get(f"/payments/{pid}")
    assert r2.json()["status"] == "succeeded"


async def test_bad_signature_returns_401(client: AsyncClient) -> None:
    pid = await _create(client)
    body = _body(pid, "succeeded")
    r = await _post_webhook(client, body, "deadbeef")
    assert r.status_code == 401

    r2 = await client.get(f"/payments/{pid}")
    assert r2.json()["status"] == "pending"


async def test_missing_signature_returns_401(client: AsyncClient) -> None:
    pid = await _create(client)
    body = _body(pid, "succeeded")
    r = await _post_webhook(client, body, None)
    assert r.status_code == 401


async def test_unknown_payment_returns_404(client: AsyncClient) -> None:
    body = _body("00000000-0000-0000-0000-000000000000", "succeeded")
    r = await _post_webhook(client, body, sign(body))
    assert r.status_code == 404


async def test_forbidden_transition_succeeded_to_pending(client: AsyncClient) -> None:
    pid = await _create(client)
    body1 = _body(pid, "succeeded")
    await _post_webhook(client, body1, sign(body1))

    body2 = _body(pid, "pending")
    r = await _post_webhook(client, body2, sign(body2))
    assert r.status_code == 409
    assert r.json() == {"error": "invalid_transition"}

    r2 = await client.get(f"/payments/{pid}")
    assert r2.json()["status"] == "succeeded"


async def test_succeeded_to_refunded_ok(client: AsyncClient) -> None:
    pid = await _create(client)
    b1 = _body(pid, "succeeded")
    await _post_webhook(client, b1, sign(b1))

    b2 = _body(pid, "refunded")
    r = await _post_webhook(client, b2, sign(b2))
    assert r.status_code == 200

    r2 = await client.get(f"/payments/{pid}")
    assert r2.json()["status"] == "refunded"


async def test_failed_to_succeeded_forbidden(client: AsyncClient) -> None:
    pid = await _create(client)
    b1 = _body(pid, "failed")
    await _post_webhook(client, b1, sign(b1))

    b2 = _body(pid, "succeeded")
    r = await _post_webhook(client, b2, sign(b2))
    assert r.status_code == 409

    r2 = await client.get(f"/payments/{pid}")
    assert r2.json()["status"] == "failed"


async def test_refunded_to_refunded_forbidden(client: AsyncClient) -> None:
    pid = await _create(client)
    for status in ("succeeded", "refunded"):
        b = _body(pid, status)
        await _post_webhook(client, b, sign(b))
    # повтор refunded -> refunded
    b = _body(pid, "refunded")
    r = await _post_webhook(client, b, sign(b))
    assert r.status_code == 409


async def test_signature_is_over_raw_body(client: AsyncClient) -> None:
    pid = await _create(client)
    compact = _body(pid, "succeeded")
    spaced = (
        '{ "payment_id" : "' + pid + '" , "status" : "succeeded" }'
    ).encode()
    # подпись от compact, отправляем spaced
    r = await _post_webhook(client, spaced, sign(compact))
    assert r.status_code == 401