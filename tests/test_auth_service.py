"""
Unit tests for app/services/auth_service.py
Tests user creation and authentication logic directly against the DB.
"""

import pytest

from app.services.auth_service import create_user, authenticate_user
from app.schemas import SignupRequest
from app.exceptions.base import UsernameTakenError, EmailTakenError, InvalidCredentialsError


def _signup_payload(**overrides) -> SignupRequest:
    base = {
        "username": "newuser",
        "password": "password123",
        "first_name": "New",
        "last_name": "User",
        "email": "newuser@example.com",
    }
    base.update(overrides)
    return SignupRequest(**base)


class TestCreateUser:
    def test_creates_user_successfully(self, db):
        payload = _signup_payload()
        user = create_user(payload, db)
        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"

    def test_password_is_hashed(self, db):
        payload = _signup_payload()
        user = create_user(payload, db)
        assert user.hashed_password != "password123"
        assert len(user.hashed_password) > 20

    def test_default_role_is_user(self, db):
        from app.models import RoleEnum
        user = create_user(_signup_payload(), db)
        assert user.role == RoleEnum.user

    def test_duplicate_username_raises(self, db):
        create_user(_signup_payload(), db)
        with pytest.raises(UsernameTakenError):
            create_user(_signup_payload(), db)

    def test_duplicate_email_raises(self, db):
        create_user(_signup_payload(username="user1"), db)
        with pytest.raises(EmailTakenError):
            create_user(_signup_payload(username="user2"), db)

    def test_username_stored_lowercase(self, db):
        # Validator lowercases before it hits the service
        payload = _signup_payload(username="MyUser")
        user = create_user(payload, db)
        assert user.username == "myuser"


class TestAuthenticateUser:
    def test_valid_credentials_returns_token(self, db):
        create_user(_signup_payload(), db)
        token = authenticate_user("newuser", "password123", db)
        assert isinstance(token, str)
        assert len(token) > 10

    def test_wrong_password_raises(self, db):
        create_user(_signup_payload(), db)
        with pytest.raises(InvalidCredentialsError):
            authenticate_user("newuser", "wrongpass", db)

    def test_nonexistent_user_raises(self, db):
        with pytest.raises(InvalidCredentialsError):
            authenticate_user("ghost", "pass123", db)

    def test_token_contains_username(self, db):
        from app.security import decode_access_token
        create_user(_signup_payload(), db)
        token = authenticate_user("newuser", "password123", db)
        payload = decode_access_token(token)
        assert payload["sub"] == "newuser"