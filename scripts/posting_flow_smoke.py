from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from app.db.session import SessionLocal
from app.models.category import Category


def post_json(url: str, payload: dict, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def put_json(url: str, payload: dict, token: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def get_json(url: str, token: str | None = None) -> tuple[int, dict]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def upload_small_image(token: str, name: str) -> str:
    boundary = "----PostingSmokeBoundary"
    payload = b"\x89PNG\r\n\x1a\nposting"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'.encode(),
            b"Content-Type: image/png\r\n\r\n",
            payload,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        "http://localhost:8000/uploads/images",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())["url"]


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
    email = f"posting{int(time.time())}@test.com"
    password = "password123"

    post_json("http://localhost:8000/auth/register", {"full_name": "Posting User", "email": email, "password": password})
    _, login_payload = post_json("http://localhost:8000/auth/login", {"email": email, "password": password})
    token = login_payload["access_token"]

    draft_status, draft = post_json("http://localhost:8000/listings/drafts", {"currency": "USD"}, token=token)
    listing_id = draft["id"]
    print("A_CREATE_DRAFT", draft_status, draft["status"])

    upd_status, _ = put_json(
        f"http://localhost:8000/listings/drafts/{listing_id}",
        {"title": "Acer Nitro V15", "city": "Bishkek"},
        token=token,
    )
    print("B_UPDATE_DRAFT", upd_status)

    image1 = upload_small_image(token, "img1.png")
    image2 = upload_small_image(token, "img2.png")
    reorder_status, reorder_payload = put_json(
        f"http://localhost:8000/listings/{listing_id}/images/reorder",
        {"images": [{"url": f"http://localhost:8000{image2}", "sort_order": 0}, {"url": f"http://localhost:8000{image1}", "sort_order": 1}]},
        token=token,
    )
    print("C_REORDER_IMAGES", reorder_status, len(reorder_payload["images"]))

    preview_owner_status, preview_owner = get_json(f"http://localhost:8000/listings/{listing_id}/preview", token=token)
    print("D_PREVIEW_OWNER", preview_owner_status, preview_owner["status"])

    try:
        post_json(f"http://localhost:8000/listings/{listing_id}/publish", {}, token=token)
    except urllib.error.HTTPError as exc:
        print("E_PUBLISH_INCOMPLETE", exc.code, exc.read().decode())

    put_json(
        f"http://localhost:8000/listings/drafts/{listing_id}",
        {
            "category_id": category_id,
            "description": "Excellent condition laptop with charger and warranty.",
            "price": 900,
            "city": "Bishkek",
            "contact_phone": "+996 500 12 34 56",
            "latitude": 42.8746,
            "longitude": 74.5698,
            "images": [{"url": f"http://localhost:8000{image1}", "sort_order": 0}],
        },
        token=token,
    )
    pub_status, pub_payload = post_json(f"http://localhost:8000/listings/{listing_id}/publish", {}, token=token)
    print("F_PUBLISH_OK", pub_status, pub_payload["listing"]["status"])

    my_status, my_payload = get_json("http://localhost:8000/listings/me?status=active&page=1&page_size=20", token=token)
    print("G_MY_LISTINGS", my_status, len(my_payload["items"]))

    public_status, public_payload = get_json("http://localhost:8000/listings?q=nitro")
    print("H_PUBLIC_LISTINGS", public_status, len(public_payload["items"]))
