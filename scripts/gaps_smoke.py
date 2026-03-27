from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from app.db.session import SessionLocal
from app.models.category import Category

BASE_URL = "http://localhost:8000"


def _request(method: str, path: str, payload: dict | None = None, token: str | None = None) -> tuple[int, dict | list | str]:
    headers: dict[str, str] = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else ""
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        parsed: dict | str
        try:
            parsed = json.loads(raw) if raw else ""
        except Exception:
            parsed = raw
        return exc.code, parsed


def ensure_category() -> int:
    db = SessionLocal()
    try:
        category = db.query(Category).filter(Category.slug == "electronics").first()
        if not category:
            category = Category(name="Electronics", slug="electronics", is_active=True, display_order=1)
            db.add(category)
            db.commit()
            db.refresh(category)
        return int(category.id)
    finally:
        db.close()


if __name__ == "__main__":
    category_id = ensure_category()
    now = int(time.time())
    email = f"gap{now}@test.com"
    password = "password123"
    new_password = "password456"

    # Register + login
    register_status, register_body = _request(
        "POST",
        "/auth/register",
        {"full_name": "Gap User", "email": email, "password": password},
    )
    assert register_status == 201, f"register failed: {register_status}, {register_body}"
    user_id = int(register_body["id"])

    login_status, login_body = _request("POST", "/auth/login", {"email": email, "password": password})
    assert login_status == 200, f"login failed: {login_status}, {login_body}"
    access_token = login_body["access_token"]
    refresh_token = login_body["refresh_token"]

    # Create listing
    listing_status, listing_body = _request(
        "POST",
        "/listings",
        {
            "category_id": category_id,
            "title": "Gap Listing",
            "description": "Gap smoke listing description with enough length.",
            "price": 100,
            "currency": "USD",
            "city": "Bishkek",
            "contact_phone": "+996 555 00 11 22",
            "images": [],
        },
        token=access_token,
    )
    assert listing_status == 201, f"create listing failed: {listing_status}, {listing_body}"
    listing_id = int(listing_body["id"])

    # A, B, C: public profile + listings + missing user
    profile_status, profile_body = _request("GET", f"/users/{user_id}")
    assert profile_status == 200, f"profile failed: {profile_status}, {profile_body}"
    assert "avatar_url" in profile_body and "bio" in profile_body and "active_listings_count" in profile_body
    assert profile_body["active_listings_count"] >= 1

    user_listings_status, user_listings_body = _request("GET", f"/users/{user_id}/listings?page=1&page_size=20")
    assert user_listings_status == 200, f"user listings failed: {user_listings_status}, {user_listings_body}"
    assert "items" in user_listings_body and "meta" in user_listings_body

    missing_user_status, _ = _request("GET", "/users/999999")
    assert missing_user_status == 404, f"missing user should be 404, got {missing_user_status}"

    # D, E: refresh
    refresh_status, refresh_body = _request("POST", "/auth/refresh", {"refresh_token": refresh_token})
    assert refresh_status == 200 and "access_token" in refresh_body, f"refresh failed: {refresh_status}, {refresh_body}"
    invalid_refresh_status, _ = _request("POST", "/auth/refresh", {"refresh_token": "not-a-token"})
    assert invalid_refresh_status == 401, f"invalid refresh should be 401, got {invalid_refresh_status}"

    # F, G: forgot/reset password
    forgot_status, forgot_body = _request("POST", "/auth/forgot-password", {"email": email})
    assert forgot_status == 200 and forgot_body.get("reset_token"), f"forgot password failed: {forgot_status}, {forgot_body}"
    reset_token = forgot_body["reset_token"]

    reset_status, reset_body = _request(
        "POST",
        "/auth/reset-password",
        {"reset_token": reset_token, "new_password": new_password},
    )
    assert reset_status == 200, f"reset password failed: {reset_status}, {reset_body}"

    old_login_status, _ = _request("POST", "/auth/login", {"email": email, "password": password})
    assert old_login_status == 401, f"old password should fail, got {old_login_status}"
    new_login_status, new_login_body = _request("POST", "/auth/login", {"email": email, "password": new_password})
    assert new_login_status == 200, f"new password login failed: {new_login_status}, {new_login_body}"
    access_token = new_login_body["access_token"]

    # H: listing view count increments for public non-owner call
    first_status, first_body = _request("GET", f"/listings/{listing_id}")
    assert first_status == 200, f"first listing fetch failed: {first_status}, {first_body}"
    second_status, second_body = _request("GET", f"/listings/{listing_id}")
    assert second_status == 200, f"second listing fetch failed: {second_status}, {second_body}"
    assert int(second_body["view_count"]) >= int(first_body["view_count"]), "view_count did not increase"

    # I: soft delete + token invalidation
    delete_status, _ = _request("DELETE", "/users/me", token=access_token)
    assert delete_status == 204, f"delete me failed: {delete_status}"
    me_status, _ = _request("GET", "/users/me", token=access_token)
    assert me_status == 401, f"deleted user token should be invalid, got {me_status}"

    print("GAPS_SMOKE_OK")
