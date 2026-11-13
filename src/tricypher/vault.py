
import os
import time
from cryptography.fernet import Fernet, InvalidToken


class TokenVault:
    """Temporary encrypted storage for reversible anonymization."""

    def __init__(self, ttl_seconds=900):
        key = os.getenv("TRICYPHER_VAULT_KEY")

        if not key:
            raise ValueError(
                "TRICYPHER_VAULT_KEY is missing from environment"
            )

        self.cipher = Fernet(key.encode())
        self.ttl_seconds = ttl_seconds
        self.storage = {}

    def store(self, original_value, token=None):
        # Generate a token if one was not supplied.
        if token is None:
            import secrets
            token = f"<TC_{secrets.token_hex(6)}>"

        encrypted_value = self.cipher.encrypt(
            original_value.encode()
        )

        self.storage[token] = {
            "value": encrypted_value,
            "expires_at": time.time() + self.ttl_seconds,
        }

        return token

    def restore(self, token):
        entry = self.storage.get(token)

        if not entry:
            return None

        if time.time() > entry["expires_at"]:
            del self.storage[token]
            return None

        try:
            return self.cipher.decrypt(entry["value"]).decode()
        except InvalidToken:
            return None

    def delete(self, token):
        self.storage.pop(token, None)
