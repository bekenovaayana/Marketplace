from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


BASE = "http://127.0.0.1:8000"


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


def upload_avatar(token: str, *, content_type: str, payload: bytes) -> tuple[int, str]:
    boundary = "----BoundaryAvatarValidation"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="avatar"\r\n',
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            payload,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        f"{BASE}/users/me/avatar",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def register_and_login() -> str:
    email = f"val{int(time.time())}@test.com"
    password = "password123"
    st, _ = post_json("/auth/register", {"full_name": "Val User", "email": email, "password": password, "preferred_language": "en"})
    assert st == 201, st
    st, login = post_json("/auth/login", {"email": email, "password": password})
    assert st == 200, st
    return str(login["access_token"])


if __name__ == "__main__":
    token = register_and_login()

    # language validation
    try:
        patch_json("/users/me", {"preferred_language": "kg"}, token)
        raise RuntimeError("expected 422 for preferred_language")
    except urllib.error.HTTPError as exc:
        print("LANG_INVALID", exc.code, exc.read().decode())

    st, ok = patch_json("/users/me", {"preferred_language": "ru"}, token)
    print("LANG_OK", st, ok["preferred_language"])

    # phone validation
    try:
        patch_json("/users/me", {"phone": "+123"}, token)
        raise RuntimeError("expected 422 for phone")
    except urllib.error.HTTPError as exc:
        print("PHONE_INVALID", exc.code, exc.read().decode())

    st, ok = patch_json("/users/me", {"phone": "+996500123456"}, token)
    print("PHONE_OK", st, ok["phone"])

    # avatar type validation (only jpeg/png)
    st, body = upload_avatar(token, content_type="image/webp", payload=b"RIFFxxxxWEBP")
    print("AVATAR_WEBP", st, body)

    png = b"\x89PNG\r\n\x1a\n" + b"ok"
    st, body = upload_avatar(token, content_type="image/png", payload=png)
    print("AVATAR_PNG", st, body)

    # avatar size validation (5MB)
    too_big = b"x" * (5_242_880 + 1)
    st, body = upload_avatar(token, content_type="image/png", payload=too_big)
    print("AVATAR_TOO_BIG", st, body)

