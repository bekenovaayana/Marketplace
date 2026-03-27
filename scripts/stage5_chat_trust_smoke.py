from __future__ import annotations

import json
import time
import urllib.request


def post_json(url: str, payload: dict, token: str | None = None, headers: dict | None = None) -> tuple[int, dict]:
    request_headers = {"Content-Type": "application/json"}
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=request_headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def get_json(url: str, token: str | None = None) -> tuple[int, dict]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def create_user(email_prefix: str) -> tuple[str, str]:
    email = f"{email_prefix}{int(time.time() * 1000)}@test.com"
    password = "password123"
    post_json("http://localhost:8000/auth/register", {"full_name": email_prefix, "email": email, "password": password})
    _, login = post_json("http://localhost:8000/auth/login", {"email": email, "password": password})
    return login["access_token"], email


if __name__ == "__main__":
    token_a, _ = create_user("chatA")
    token_b, _ = create_user("chatB")

    # user A sees trust fields and completeness
    me_status, me_payload = get_json("http://localhost:8000/users/me", token=token_a)
    print("ME_TRUST_FIELDS", me_status, me_payload.get("email_verified"), me_payload.get("phone_verified"), me_payload.get("trust_score"))

    comp_status, comp_payload = get_json("http://localhost:8000/users/me/completeness", token=token_a)
    print("COMPLETENESS", comp_status, comp_payload["percentage"], len(comp_payload["missing_fields"]))

    # determine user_b id by creating conversation from A with alias other_user_id after reading me of B
    _, me_b = get_json("http://localhost:8000/users/me", token=token_b)
    user_b_id = me_b["id"]
    conv_status, conv = post_json("http://localhost:8000/conversations", {"other_user_id": user_b_id}, token=token_a)
    conv_id = conv["id"]
    print("CREATE_CONVERSATION", conv_status, conv_id)

    # send message with idempotency key twice (as A)
    msg_payload = {"conversation_id": conv_id, "content": "hello from A"}
    m1_status, m1 = post_json(
        "http://localhost:8000/messages",
        msg_payload,
        token=token_a,
        headers={"Idempotency-Key": "idem-123"},
    )
    m2_status, m2 = post_json(
        "http://localhost:8000/messages",
        msg_payload,
        token=token_a,
        headers={"Idempotency-Key": "idem-123"},
    )
    print("IDEMPOTENCY", m1_status, m2_status, m1["id"], m2["id"])

    # send message from B so A gets unread
    post_json("http://localhost:8000/messages", {"conversation_id": conv_id, "text_body": "reply from B"}, token=token_b)

    # unread summary and conversation metadata for A
    unread_status, unread_payload = get_json("http://localhost:8000/chats/unread-summary", token=token_a)
    print("UNREAD_SUMMARY", unread_status, unread_payload["total_unread"], unread_payload["by_conversation"])

    convs_status, convs = get_json("http://localhost:8000/conversations?page=1&page_size=20", token=token_a)
    first = convs["items"][0]
    print(
        "CONV_METADATA",
        convs_status,
        first.get("last_message_text"),
        first.get("unread_count"),
        "listing_title" in first,
        "listing_image_url" in first,
    )

    # mark read and verify unread resets
    mark_status, mark_payload = post_json(f"http://localhost:8000/messages/{conv_id}/mark-read", {}, token=token_a)
    print("MARK_READ", mark_status, mark_payload["updated_count"])
    _, unread_after = get_json("http://localhost:8000/chats/unread-summary", token=token_a)
    print("UNREAD_AFTER", unread_after["total_unread"])
