from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


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


def get_json(url: str, token: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def upload_multipart(url: str, *, token: str, filename: str, content_type: str, payload: bytes) -> tuple[int, dict]:
    boundary = "----ProfileSmokeBoundary"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            payload,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


if __name__ == "__main__":
    email = f"profile{int(time.time())}@test.com"
    password = "password123"

    reg_status, _ = post_json(
        "http://localhost:8000/auth/register",
        {"full_name": "Profile User", "email": email, "password": password},
    )
    login_status, login_payload = post_json(
        "http://localhost:8000/auth/login",
        {"email": email, "password": password},
    )
    token = login_payload["access_token"]
    print("REGISTER/LOGIN", reg_status, login_status)

    me_status, me_payload = get_json("http://localhost:8000/users/me", token)
    print("ME", me_status, "avatar_url=", me_payload.get("avatar_url"))

    put_status, put_payload = put_json(
        "http://localhost:8000/users/me",
        {"full_name": "Profile Updated", "bio": "Hello", "phone": "+996 500 12 34 56"},
        token,
    )
    print("PUT_ME", put_status, put_payload["full_name"], put_payload["phone"])

    ok_upload_status, ok_upload_payload = upload_multipart(
        "http://localhost:8000/users/me/avatar",
        token=token,
        filename="avatar.png",
        content_type="image/png",
        payload=b"\x89PNG\r\n\x1a\navatar",
    )
    print("AVATAR_OK", ok_upload_status, ok_upload_payload["avatar_url"])

    try:
        upload_multipart(
            "http://localhost:8000/users/me/avatar",
            token=token,
            filename="bad.txt",
            content_type="text/plain",
            payload=b"not-image",
        )
    except urllib.error.HTTPError as exc:
        print("AVATAR_BAD_MIME", exc.code, exc.read().decode())

    try:
        upload_multipart(
            "http://localhost:8000/users/me/avatar",
            token=token,
            filename="big.png",
            content_type="image/png",
            payload=b"x" * (5_242_880 + 1),
        )
    except urllib.error.HTTPError as exc:
        print("AVATAR_TOO_LARGE", exc.code, exc.read().decode())

    try:
        post_json(
            "http://localhost:8000/users/change-password",
            {"current_password": "wrong-pass", "new_password": "newpassword123"},
            token=token,
        )
    except urllib.error.HTTPError as exc:
        print("CHANGE_PASSWORD_WRONG", exc.code, exc.read().decode())

    cp_status, cp_payload = post_json(
        "http://localhost:8000/users/change-password",
        {"current_password": password, "new_password": "newpassword123"},
        token=token,
    )
    print("CHANGE_PASSWORD_OK", cp_status, cp_payload["detail"])

    relogin_status, _ = post_json(
        "http://localhost:8000/auth/login",
        {"email": email, "password": "newpassword123"},
    )
    print("RELOGIN_NEW_PASSWORD", relogin_status)
