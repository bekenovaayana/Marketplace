from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.category import Category


BASE = "http://localhost:8000"


def post_json(path: str, payload: dict, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def patch_json(path: str, payload: dict, token: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="PATCH",
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def get_json(path: str, token: str | None = None) -> tuple[int, dict | list]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def upload_avatar(token: str) -> tuple[int, dict]:
    boundary = "----BoundaryAvatarSmoke"
    png = b"\x89PNG\r\n\x1a\n" + b"avatar-smoke"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="avatar.png"\r\n',
            b"Content-Type: image/png\r\n\r\n",
            png,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        f"{BASE}/users/me/avatar",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


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


def register_and_login(label: str) -> str:
    email = f"{label}{int(time.time())}@test.com"
    password = "password123"
    post_json("/auth/register", {"full_name": label, "email": email, "password": password})
    _, login = post_json("/auth/login", {"email": email, "password": password})
    return str(login["access_token"])


def expect_http_error(fn, expected_code: int) -> str:
    try:
        fn()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        assert exc.code == expected_code, (exc.code, body)
        return body
    raise RuntimeError(f"Expected HTTP {expected_code}")


if __name__ == "__main__":
    category_id = ensure_category()

    token_owner = register_and_login("Owner User")
    token_other = register_and_login("Other User")

    # profile update + avatar upload
    st, me0 = get_json("/users/me", token_owner)
    print("ME", st, me0["id"])

    st, updated = patch_json("/users/me", {"first_name": "Owner", "last_name": "User", "phone": "+1 555 000 1111"}, token_owner)
    print("PROFILE_PATCH", st, updated["first_name"], updated["last_name"], updated["phone"])

    st, avatar = upload_avatar(token_owner)
    print("AVATAR_UPLOAD", st, avatar["avatar_url"])

    # create an active listing
    st, listing = post_json(
        "/listings",
        {
            "category_id": category_id,
            "title": "Promo Test Listing",
            "description": "Promotion smoke test",
            "price": 10,
            "currency": "USD",
            "city": "Bishkek",
            "contact_phone": "+996 555 00 11 22",
            "latitude": 42.8746,
            "longitude": 74.5698,
            "images": [{"url": f"{BASE}/uploads/listings/placeholder.png", "sort_order": 0}],
        },
        token=token_owner,
    )
    listing_id = int(listing["id"])
    print("CREATE_LISTING", st, listing_id)

    # listing ownership check: other user cannot promote owner's listing
    body = expect_http_error(lambda: post_json("/promotions/checkout", {"listing_id": listing_id, "days": 7}, token_other), 403)
    print("PROMO_OWNERSHIP_403", body)

    # checkout + webhook activation
    st, options = get_json("/promotions/options", token_owner)
    print("PROMO_OPTIONS", st, options["options"])

    st, checkout = post_json("/promotions/checkout", {"listing_id": listing_id, "days": 7}, token_owner)
    print("PROMO_CHECKOUT", st, checkout["promotion_id"], checkout["payment_intent_id"], checkout["amount"])

    st, payment = post_json("/payments/webhook", {"provider_reference": checkout["payment_intent_id"], "event": "payment_succeeded"})
    print("WEBHOOK", st, payment["status"])

    st, promos = get_json("/promotions", token_owner)
    latest = promos["items"][0] if promos["items"] else None
    print("PROMOS", st, len(promos["items"]), latest["status"] if latest else None)

