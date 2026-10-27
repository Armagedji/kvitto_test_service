import hashlib
import hmac

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"succeeded", "failed"},
    "succeeded": {"refunded"},
    "failed": set(),
    "refunded": set(),
}


def verify_signature(raw_body: bytes, signature_hex: str | None, secret: str) -> bool:
    if signature_hex is None:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_hex)


def is_transition_allowed(current: str, new: str) -> bool:
    return new in ALLOWED_TRANSITIONS.get(current, set())