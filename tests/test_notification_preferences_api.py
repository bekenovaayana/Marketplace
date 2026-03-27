from __future__ import annotations

import io
import time

from fastapi.testclient import TestClient
from PIL import Image

from app.db.session import SessionLocal
from app.main import app
from app.models.category import Category

client = TestClient(app)


def _unique_email(prefix: str = "np") -> str:
    return f"{prefix}_{time.time_ns()}@test.com"


def _register(name: str, email: str | None = None, password: str = "Password123!") -> tuple[str, dict]:
    e = email or _unique_email()
    reg = client.post("/auth/register", json={"full_name": name, "email": e, "password": password})
    assert reg.status_code == 201, reg.text
    login = client.post("/auth/login", json={"email": e, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    return token, me.json()


def _category_id() -> int:
    db = SessionLocal()
    try:
        c = Category(name="T", slug=f"t-{time.time_ns()}", is_active=True, display_order=1)
        db.add(c)
        db.commit()
        db.refresh(c)
        return int(c.id)
    finally:
        db.close()


def _png_upload(token: str) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(200, 10, 50)).save(buf, format="PNG")
    buf.seek(0)
    r = client.post(
        "/uploads/images",
        files={"file": ("x.png", buf, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["url"]


def _publish_min_listing(token: str, *, title: str = "Item") -> int:
    cid = _category_id()
    r = client.post("/listings/drafts", json={"currency": "USD"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    lid = r.json()["id"]
    url = _png_upload(token)
    if url.startswith("/"):
        url = f"http://testserver{url}"
    body = {
        "category_id": cid,
        "title": title,
        "description": "Good condition, pickup downtown.",
        "price": 10,
        "city": "Bishkek",
        "contact_phone": "+996500123456",
    }
    u = client.put(f"/listings/drafts/{lid}", json=body, headers={"Authorization": f"Bearer {token}"})
    assert u.status_code == 200, u.text
    rep = client.put(
        f"/listings/{lid}/images/reorder",
        json=[{"url": url, "sort_order": 0}],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rep.status_code == 200, rep.text
    pub = client.post(f"/listings/{lid}/publish", headers={"Authorization": f"Bearer {token}"})
    assert pub.status_code == 200, pub.text
    return lid


def test_me_includes_theme_and_notification_flags() -> None:
    tok, _ = _register("Flags User")
    r = client.get("/users/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["theme"] == "system"
    assert body["notify_new_message"] is True
    assert body["notify_contact_request"] is True
    assert body["notify_listing_favorited"] is True


def test_patch_theme_and_notification_prefs() -> None:
    tok, _ = _register("Patch User")
    r = client.patch(
        "/users/me",
        json={"theme": "dark", "notify_new_message": False},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["theme"] == "dark"
    assert b["notify_new_message"] is False
    assert b["notify_listing_favorited"] is True


def test_new_message_skipped_when_notify_new_message_disabled() -> None:
    tok_a, a = _register("Alice N")
    tok_b, b = _register("Bob N")
    client.patch(
        "/users/me",
        json={"notify_new_message": False},
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    cr = client.post("/conversations", json={"participant_id": b["id"]}, headers={"Authorization": f"Bearer {tok_a}"})
    assert cr.status_code == 201, cr.text
    conv_id = cr.json()["id"]
    msg = client.post(
        "/messages",
        json={"conversation_id": conv_id, "text_body": "hi"},
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    assert msg.status_code == 201, msg.text
    nf = client.get("/notifications", headers={"Authorization": f"Bearer {tok_b}"})
    assert nf.status_code == 200
    assert len(nf.json()["items"]) == 0


def test_listing_favorited_notification_respects_flag() -> None:
    tok_seller, seller = _register("Seller Fav")
    tok_buyer, _ = _register("Buyer Fav")
    lid = _publish_min_listing(tok_seller, title="Bike")
    client.patch(
        "/users/me",
        json={"notify_listing_favorited": False},
        headers={"Authorization": f"Bearer {tok_seller}"},
    )
    fa = client.post(f"/favorites/{lid}", headers={"Authorization": f"Bearer {tok_buyer}"})
    assert fa.status_code == 201, fa.text
    nf = client.get("/notifications", headers={"Authorization": f"Bearer {tok_seller}"})
    assert nf.status_code == 200
    types = [i["notification_type"] for i in nf.json()["items"]]
    assert "listing_favorited" not in types

    client.patch(
        "/users/me",
        json={"notify_listing_favorited": True},
        headers={"Authorization": f"Bearer {tok_seller}"},
    )
    lid2 = _publish_min_listing(tok_seller, title="Scooter")
    fb = client.post(f"/favorites/{lid2}", headers={"Authorization": f"Bearer {tok_buyer}"})
    assert fb.status_code == 201, fb.text
    nf2 = client.get("/notifications", headers={"Authorization": f"Bearer {tok_seller}"})
    assert any(i["notification_type"] == "listing_favorited" for i in nf2.json()["items"])


def test_contact_intent_throttle_and_notification_flag() -> None:
    tok_seller, _ = _register("Seller C")
    tok_buyer, _ = _register("Buyer C")
    lid = _publish_min_listing(tok_seller, title="Desk")
    c1 = client.post(f"/listings/{lid}/contact-intent", headers={"Authorization": f"Bearer {tok_buyer}"})
    assert c1.status_code == 201, c1.text
    c2 = client.post(f"/listings/{lid}/contact-intent", headers={"Authorization": f"Bearer {tok_buyer}"})
    assert c2.status_code == 429, c2.text

    client.patch(
        "/users/me",
        json={"notify_contact_request": False},
        headers={"Authorization": f"Bearer {tok_seller}"},
    )
    tok_buyer2, _ = _register("Buyer C2")
    lid2 = _publish_min_listing(tok_seller, title="Chair")
    client.post(f"/listings/{lid2}/contact-intent", headers={"Authorization": f"Bearer {tok_buyer2}"})
    nf = client.get("/notifications", headers={"Authorization": f"Bearer {tok_seller}"})
    contact_types = [i["notification_type"] for i in nf.json()["items"] if i["notification_type"] == "contact_request"]
    assert contact_types.count("contact_request") == 1
