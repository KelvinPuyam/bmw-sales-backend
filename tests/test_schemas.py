"""
Unit tests for Pydantic schema validators in app/schemas.py
"""

import pytest
from pydantic import ValidationError

from app.schemas import SignupRequest, LoginRequest, ChangePasswordRequest


class TestSignupRequest:
    def _valid_payload(self, **overrides):
        base = {
            "username": "johndoe",
            "password": "securepass",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
        }
        base.update(overrides)
        return base

    def test_valid_signup(self):
        req = SignupRequest(**self._valid_payload())
        assert req.username == "johndoe"

    def test_username_is_lowercased(self):
        req = SignupRequest(**self._valid_payload(username="JohnDoe"))
        assert req.username == "johndoe"

    def test_username_with_spaces_raises(self):
        with pytest.raises(ValidationError, match="spaces"):
            SignupRequest(**self._valid_payload(username="john doe"))

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError, match="6 characters"):
            SignupRequest(**self._valid_payload(password="abc"))

    def test_password_exactly_six_chars_ok(self):
        req = SignupRequest(**self._valid_payload(password="123456"))
        assert req.password == "123456"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            SignupRequest(**self._valid_payload(email="not-an-email"))

    def test_optional_phone_defaults_to_none(self):
        req = SignupRequest(**self._valid_payload())
        assert req.phone is None

    def test_optional_dob_defaults_to_none(self):
        req = SignupRequest(**self._valid_payload())
        assert req.dob is None


class TestLoginRequest:
    def test_valid_login(self):
        req = LoginRequest(username="alice", password="pass123")
        assert req.username == "alice"

    def test_missing_username_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="pass123")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="alice")


class TestChangePasswordRequest:
    def test_valid_change_password(self):
        req = ChangePasswordRequest(old_password="old123", new_password="new456")
        assert req.old_password == "old123"
        assert req.new_password == "new456"

    def test_missing_old_password_raises(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(new_password="new456")