from __future__ import annotations

import io
import time

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


client = TestClient(app)


def _unique_email(prefix: str = "guestflow") -> str:
    return f"{prefix}_{int(time.time() * 1000)}@test.com"


def _register_and_login() -> tuple[str, str]:
    email = _unique_email()
    password = "Password123!"

    register_resp = client.post(
        "/auth/register",
        json={"full_name": "Guest Flow User", "email": email, "password": password},
    )
    assert register_resp.status_code == 201, register_resp.text

    login_resp = client.post("/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return email, token


def test_guest_can_access_public_endpoints() -> None:
    for path in ("/home", "/listings", "/categories"):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}: {resp.text}"


def test_guest_gets_401_on_protected_endpoints() -> None:
    protected_checks = [
        ("get", "/users/me"),
        ("patch", "/users/me"),
        ("post", "/users/me/avatar"),
        ("get", "/favorites"),
        ("get", "/conversations"),
        ("get", "/messages/1"),
        ("post", "/promotions/checkout"),
        ("post", "/payments"),
    ]
    for method, path in protected_checks:
        if method == "get":
            resp = client.get(path)
        elif method == "patch":
            resp = client.patch(path, json={"bio": "guest"})
        else:
            resp = client.post(path, json={})
        assert resp.status_code == 401, f"{method.upper()} {path} -> {resp.status_code}: {resp.text}"


def test_register_duplicate_email_returns_409() -> None:
    email = _unique_email("dup")
    payload = {"full_name": "Dup User", "email": email, "password": "Password123!"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201, first.text

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json().get("detail") == "Email already registered"


def test_login_invalid_credentials_returns_401() -> None:
    email = _unique_email("invalid")
    register = client.post(
        "/auth/register",
        json={"full_name": "Invalid Login User", "email": email, "password": "Password123!"},
    )
    assert register.status_code == 201, register.text

    login = client.post("/auth/login", json={"email": email, "password": "WrongPassword123!"})
    assert login.status_code == 401
    assert login.json().get("detail") == "Invalid credentials"


def test_refresh_success_and_invalid_token_failure() -> None:
    email = _unique_email("refresh")
    password = "Password123!"
    register = client.post("/auth/register", json={"full_name": "Refresh User", "email": email, "password": password})
    assert register.status_code == 201, register.text
    login_ok = client.post("/auth/login", json={"email": email, "password": password})
    assert login_ok.status_code == 200, login_ok.text
    refresh_token = login_ok.json().get("refresh_token")
    assert refresh_token

    refresh = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 200, refresh.text
    assert "access_token" in refresh.json()

    invalid = client.post("/auth/refresh", json={"refresh_token": "bad.token.value"})
    assert invalid.status_code == 401


def test_profile_patch_validation_errors_are_structured() -> None:
    _, token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.patch(
        "/users/me",
        json={"preferred_language": "de", "phone": "0555123456"},
        headers=headers,
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "errors" in body or "detail" in body


def test_avatar_upload_supports_png_and_crop_metadata() -> None:
    _, token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    image = Image.new("RGB", (4, 4), (10, 120, 220))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    files = {"file": ("avatar.png", io.BytesIO(png_bytes), "image/png")}
    data = {
        "crop_x": "0",
        "crop_y": "0",
        "crop_width": "1",
        "crop_height": "1",
        "crop_rotation": "0",
    }
    resp = client.post("/users/me/avatar", headers=headers, files=files, data=data)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["content_type"] == "image/jpeg"
    assert body["avatar_url"].endswith("_512.jpg")
    assert body["size_bytes"] > 0
