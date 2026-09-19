from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token


def register_user(client: TestClient, email: str, password: str = "password123"):
    return client.post(
        "/api/v1/register",
        json={"email": email, "password": password},
    )


def login_user(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post(
        "/api/v1/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_duplicate_registration_returns_conflict(client: TestClient):
    email = "duplicate@example.com"

    first_response = register_user(client, email)
    duplicate_response = register_user(client, email)

    assert first_response.status_code == 201, first_response.text
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "Email already registered"


@pytest.mark.parametrize("token_kind", ["invalid", "expired"])
def test_invalid_or_expired_jwt_is_rejected_on_protected_route(
    client: TestClient, token_kind: str
):
    email = "protected@example.com"
    register_response = register_user(client, email)
    assert register_response.status_code == 201, register_response.text

    if token_kind == "expired":
        token = create_access_token(
            {"sub": email}, expires_delta=timedelta(seconds=-1)
        )
    else:
        token = "not-a-valid-jwt"

    response = client.get("/api/v1/users/me", headers=bearer(token))

    assert response.status_code == 401


def test_user_cannot_read_update_or_delete_another_users_bookmark(
    client: TestClient,
):
    owner_email = "owner@example.com"
    other_email = "other@example.com"
    assert register_user(client, owner_email).status_code == 201
    assert register_user(client, other_email).status_code == 201

    owner_token = login_user(client, owner_email)
    other_token = login_user(client, other_email)
    create_response = client.post(
        "/api/v1/bookmarks",
        json={
            "title": "Private bookmark",
            "url": "https://example.com/private",
            "description": "Owner-only bookmark",
        },
        headers=bearer(owner_token),
    )
    assert create_response.status_code == 201, create_response.text
    bookmark_id = create_response.json()["id"]

    other_headers = bearer(other_token)
    read_response = client.get(
        f"/api/v1/bookmarks/{bookmark_id}", headers=other_headers
    )
    update_response = client.patch(
        f"/api/v1/bookmarks/{bookmark_id}",
        json={"title": "Unauthorized update"},
        headers=other_headers,
    )
    delete_response = client.delete(
        f"/api/v1/bookmarks/{bookmark_id}", headers=other_headers
    )

    assert read_response.status_code == 404
    assert update_response.status_code == 404
    assert delete_response.status_code == 404

    owner_read_response = client.get(
        f"/api/v1/bookmarks/{bookmark_id}", headers=bearer(owner_token)
    )
    assert owner_read_response.status_code == 200
    assert owner_read_response.json()["title"] == "Private bookmark"