from __future__ import annotations


PHONE_KEY_LENGTH = 10


def normalize_phone_last10(value: str | None) -> str:
    """Return a stable last-10 digit lookup key, or empty for invalid input."""
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) < PHONE_KEY_LENGTH:
        return ""
    return digits[-PHONE_KEY_LENGTH:]
