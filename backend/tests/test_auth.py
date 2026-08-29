"""Tests for the /api/v1/auth endpoints."""


def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@test.com", "password": "password123", "full_name": "New User"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@test.com"
    assert body["full_name"] == "New User"
    assert body["is_active"] is True
    assert "id" in body
    assert "hashed_password" not in body


def test_register_duplicate_email(client, test_user):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": test_user.email, "password": "password123"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": test_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": test_user.email, "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_refresh_success(client, test_user):
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": test_user.email, "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_refresh_with_access_token_rejected(client, auth_headers):
    # An access token used as a refresh token should be rejected (wrong "type" claim).
    access_token = auth_headers["Authorization"].split(" ")[1]
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_refresh_invalid_token(client):
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401


def test_me_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_authorized(client, auth_headers, test_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == test_user.email
    assert body["id"] == test_user.id


def test_update_me(client, auth_headers):
    response = client.put("/api/v1/auth/me", json={"full_name": "Updated Name"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"

    # Confirm it persisted.
    me_response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_response.json()["full_name"] == "Updated Name"


def test_update_me_unauthorized(client):
    response = client.put("/api/v1/auth/me", json={"full_name": "Nope"})
    assert response.status_code == 401


def test_logout(client, auth_headers):
    response = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 204
