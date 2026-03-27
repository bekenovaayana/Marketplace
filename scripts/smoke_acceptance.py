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


def post_json(url: str, payload: dict, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def get_json(url: str, token: str | None = None) -> tuple[int, dict | list]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
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


def upload_image(token: str) -> tuple[int, dict]:
    boundary = "----BoundarySmokeTest"
    png = b"\x89PNG\r\n\x1a\n" + b"smoke-test-image"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="image.png"\r\n',
            b"Content-Type: image/png\r\n\r\n",
            png,
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
        return resp.status, json.loads(resp.read().decode())


def upload_invalid_mime(token: str) -> tuple[int, str]:
    boundary = "----BoundaryInvalidMime"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="bad.txt"\r\n',
            b"Content-Type: text/plain\r\n\r\n",
            b"not-an-image",
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        "http://localhost:8000/uploads/images",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()
    raise RuntimeError("Expected HTTPError for invalid mime upload")


def upload_too_large(token: str) -> tuple[int, str]:
    boundary = "----BoundaryTooLarge"
    content = b"x" * (67_108_864 + 1)
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="big.png"\r\n',
            b"Content-Type: image/png\r\n\r\n",
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        "http://localhost:8000/uploads/images",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()
    raise RuntimeError("Expected HTTPError for oversized upload")


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
    email = f"apiuser{int(time.time())}@test.com"
    password = "password123"

    reg_status, _ = post_json(
        "http://localhost:8000/auth/register",
        {"full_name": "API User", "email": email, "password": password},
    )
    print("REGISTER", reg_status)

    login_status, login_payload = post_json("http://localhost:8000/auth/login", {"email": email, "password": password})
    print("LOGIN", login_status)
    token = login_payload["access_token"]

    upload_status, upload_payload = upload_image(token)
    print("UPLOAD", upload_status, upload_payload["url"])
    bad_mime_status, bad_mime_body = upload_invalid_mime(token)
    print("UPLOAD_INVALID_MIME", bad_mime_status, bad_mime_body)
    too_large_status, too_large_body = upload_too_large(token)
    print("UPLOAD_TOO_LARGE", too_large_status, too_large_body)

    listing_status, listing_payload = post_json(
        "http://localhost:8000/listings",
        {
            "category_id": category_id,
            "title": "Acer Laptop",
            "description": "Acer laptop in good condition with charger.",
            "price": 500,
            "currency": "USD",
            "city": "Bishkek",
            "contact_phone": "+996 555 00 11 22",
            "latitude": 42.8746,
            "longitude": 74.5698,
            "images": [{"url": f"http://localhost:8000{upload_payload['url']}", "sort_order": 0}],
        },
        token=token,
    )
    print("CREATE_LISTING", listing_status, listing_payload["id"])

    for query in (
        "q=acer",
        f"category_id={category_id}&city=bishkek",
        "min_price=100&max_price=2000&sort=price_desc",
    ):
        status_code, data = get_json(f"http://localhost:8000/listings?{query}")
        print("LIST", query, status_code, len(data["items"]))

    try:
        get_json("http://localhost:8000/listings?min_price=300&max_price=200")
    except urllib.error.HTTPError as exc:
        print("MINMAX", exc.code, exc.read().decode())

    categories_status, categories_payload = get_json("http://localhost:8000/categories")
    print("CATEGORIES", categories_status, len(categories_payload))

    home_status, home_payload = get_json("http://localhost:8000/home")
    print(
        "HOME",
        home_status,
        len(home_payload["categories"]),
        len(home_payload["recommended"]),
        len(home_payload["latest"]),
    )

    update_status, update_payload = put_json(
        "http://localhost:8000/users/me",
        {"city": "Bishkek", "phone": "+996 500 12 34 56"},
        token,
    )
    print("PROFILE_UPDATE", update_status, update_payload["city"], update_payload["phone"])
