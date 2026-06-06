"""
Unit tests for app/security.py
Tests password hashing and JWT token creation/decoding.
"""

import pytest
import time
from jose import JWTError

from app.security import hash_password, verify_password, create_access_token, decode_access_token


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"

    def test_verify_correct_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("wrongpassword", hashed) is False

    def test_same_password_produces_different_hashes(self):
        """bcrypt uses a random salt each time."""
        h1 = hash_password("mysecret")
        h2 = hash_password("mysecret")
        assert h1 != h2

    def test_empty_password_hashes_and_verifies(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True


class TestJWT:
    def test_token_is_string(self):
        token = create_access_token({"sub": "alice", "role": "user"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_returns_correct_sub(self):
        token = create_access_token({"sub": "alice", "role": "user"})
        payload = decode_access_token(token)
        assert payload["sub"] == "alice"

    def test_decode_returns_correct_role(self):
        token = create_access_token({"sub": "alice", "role": "admin"})
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_tampered_token_raises(self):
        token = create_access_token({"sub": "alice"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_token_contains_exp(self):
        token = create_access_token({"sub": "alice"})
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_extra_claims_are_preserved(self):
        token = create_access_token({"sub": "alice", "custom": "value123"})
        payload = decode_access_token(token)
        assert payload["custom"] == "value123"