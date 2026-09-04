from app.audit.redaction import redact_text, redact_value


def test_redacts_email():
    assert "[REDACTED_EMAIL]" in redact_text("contact me at alice@example.com please")


def test_redacts_card_number():
    assert "[REDACTED_CARD_NUMBER]" in redact_text("card: 4111111111111111 exp 12/29")


def test_redacts_phone():
    assert "[REDACTED_PHONE]" in redact_text("call 555-123-4567 now")


def test_redacts_api_key():
    assert "[REDACTED_API_KEY]" in redact_text("key=sk-abcdefghijklmnop123")


def test_redact_value_recurses_into_nested_structures():
    payload = {"user": {"email": "bob@example.com"}, "notes": ["call 555-987-6543"]}
    redacted = redact_value(payload)
    assert redacted["user"]["email"] == "[REDACTED_EMAIL]"
    assert "[REDACTED_PHONE]" in redacted["notes"][0]


def test_redact_value_passes_through_non_string_scalars():
    assert redact_value(42) == 42
    assert redact_value(True) is True
    assert redact_value(None) is None
