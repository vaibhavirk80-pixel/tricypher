
import pytest
from cryptography.fernet import Fernet

from src.tricypher.core import TriCypher


@pytest.fixture
def engine(monkeypatch):
    # Give each test a fresh encryption key.
    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("TRICYPHER_VAULT_KEY", test_key)

    return TriCypher()


def test_protect_person_and_email(engine):
    original = (
        "My name is Shweta Desai "
        "and my email is shweta@example.com"
    )

    result = engine.protect(original)
    protected_text = result["protected_text"]

    assert "Shweta Desai" not in protected_text
    assert "shweta@example.com" not in protected_text
    assert "<TC_PERSON_" in protected_text
    assert "<TC_EMAIL_ADDRESS_" in protected_text


def test_restore_original_text(engine):
    original = (
        "My name is Shweta Desai "
        "and my email is shweta@example.com"
    )

    protected = engine.protect(original)
    restored = engine.restore(protected["protected_text"])

    assert restored == original


def test_reject_empty_text(engine):
    with pytest.raises(ValueError):
        engine.protect("")


def test_reject_non_string_input(engine):
    with pytest.raises(TypeError):
        engine.protect(12345)
