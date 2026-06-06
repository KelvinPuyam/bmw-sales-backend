"""
Integration tests for /auth/* endpoints.
These hit the real FastAPI router via TestClient.
"""

import pytest


SIGNUP_PAYLOAD = {
    "username": "routeuser",
    "password": "securepass",
    "first_name": "Route",
    "last_name": "User",
    "email": "routeuser@example.com",
}


class TestSignupEndpoint:
    def test_successful_signup_returns_201(self, client):
        resp = client.post("/auth/signup", json=SIGNUP_PAYLOAD)
        assert resp.status_code == 201

    def test_signup_response_contains_user_fields(self, client):
        payload = {**SIGNUP_PAYLOAD, "username": "routeuser2", "email": "routeuser2@example.com"}
        resp = client.post("/auth/signup", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "routeuser2"
        assert data["email"] == "routeuser2@example.com"
        assert "id" in data
        assert "hashed_password" not in data  # never expose this

    def test_duplicate_username_returns_409(self, client):
        client.post("/auth/signup", json=SIGNUP_PAYLOAD)
        resp = client.post("/auth/signup", json=SIGNUP_PAYLOAD)
        assert resp.status_code == 409

    def test_duplicate_email_returns_409(self, client):
        client.post("/auth/signup", json=SIGNUP_PAYLOAD)
        different_username = {**SIGNUP_PAYLOAD, "username": "another"}
        resp = client.post("/auth/signup", json=different_username)
        assert resp.status_code == 409

    def test_username_with_spaces_returns_422(self, client):
        bad = {**SIGNUP_PAYLOAD, "username": "bad user"}
        resp = client.post("/auth/signup", json=bad)
        assert resp.status_code == 422

    def test_short_password_returns_422(self, client):
        bad = {**SIGNUP_PAYLOAD, "username": "newguy", "password": "ab"}
        resp = client.post("/auth/signup", json=bad)
        assert resp.status_code == 422

    def test_invalid_email_returns_422(self, client):
        bad = {**SIGNUP_PAYLOAD, "username": "newguy2", "email": "notanemail"}
        resp = client.post("/auth/signup", json=bad)
        assert resp.status_code == 422

    def test_missing_required_fields_returns_422(self, client):
        resp = client.post("/auth/signup", json={"username": "incomplete"})
        assert resp.status_code == 422


class TestLoginEndpoint:
    def test_valid_login_returns_token(self, client):
        client.post("/auth/signup", json=SIGNUP_PAYLOAD)
        resp = client.post("/auth/login", json={
            "username": "routeuser",
            "password": "securepass",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_wrong_password_returns_401(self, client):
        client.post("/auth/signup", json=SIGNUP_PAYLOAD)
        resp = client.post("/auth/login", json={
            "username": "routeuser",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_unknown_user_returns_401(self, client):
        resp = client.post("/auth/login", json={
            "username": "ghost",
            "password": "pass123",
        })
        assert resp.status_code == 401

    def test_missing_credentials_returns_422(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 422


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["message"] == "BMW Sales API is running"