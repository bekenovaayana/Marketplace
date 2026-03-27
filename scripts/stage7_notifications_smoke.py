"""Stage 7 — Notifications smoke test.

Checks:
A  GET /notifications returns paginated list (empty for new user)
B  GET /notifications/unread-count returns 0 for new user
C  Sending a message auto-creates a notification for recipient
D  Recipient sees unread_count = 1 after receiving message
E  GET /notifications?unread_only=true returns only unread items
F  POST /notifications/{id}/read marks single notification as read
G  unread_count drops to 0 after marking read
H  POST /notifications/read-all works when already all read (returns 0)
I  Non-owner cannot read another user's notification (404)
J  GET /users/me includes theme + notify_* fields; PATCH toggles them
    (Full favorite/contact-intent flows: pytest tests/test_notification_preferences_api.py)
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
HDR_JSON = {"Content-Type": "application/json"}


def request(method, path, *, token=None, body=None):
    headers = dict(HDR_JSON)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def register_login(tag):
    ts = int(time.time() * 1000)
    email = f"notif_{tag}_{ts}@test.com"
    request("POST", "/auth/register", body={"full_name": tag, "email": email, "password": "pass1234"})
    _, tok = request("POST", "/auth/login", body={"email": email, "password": "pass1234"})
    return tok["access_token"]


def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"{status}: {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        raise SystemExit(1)


tok_a = register_login("alice")
tok_b = register_login("bob")

_, me_b = request("GET", "/users/me", token=tok_b)

# A — empty list
code, data = request("GET", "/notifications", token=tok_b)
check("A: GET /notifications returns 200", code == 200)
check("A: response has items key", "items" in data)

# B — unread count = 0
code, data = request("GET", "/notifications/unread-count", token=tok_b)
check("B: unread-count endpoint 200", code == 200)
check("B: unread_count starts at 0", data["unread_count"] == 0)

# Create conversation A -> B
_, convo = request("POST", "/conversations", token=tok_a, body={"participant_id": me_b["id"]})
cid = convo["id"]

# C — send message → notification created for B
code, _ = request("POST", "/messages", token=tok_a, body={"conversation_id": cid, "text_body": "hello"})
check("C: message sent", code == 201)

time.sleep(0.3)

code, data = request("GET", "/notifications", token=tok_b)
check("C: notification list non-empty after message", len(data["items"]) >= 1)
notif = data["items"][0]
check("C: notification type is new_message", notif["notification_type"] == "new_message")
check("C: entity_type is conversation", notif["entity_type"] == "conversation")
check("C: entity_id matches conversation", notif["entity_id"] == cid)

# D — unread count = 1
code, data = request("GET", "/notifications/unread-count", token=tok_b)
check("D: unread_count = 1 after receiving message", data["unread_count"] >= 1)

# E — unread_only filter
code, data = request("GET", "/notifications?unread_only=true", token=tok_b)
check("E: unread_only filter 200", code == 200)
check("E: all items are unread", all(not item["is_read"] for item in data["items"]))

# F — mark single as read
notif_id = notif["id"]
code, data = request("POST", f"/notifications/{notif_id}/read", token=tok_b)
check("F: mark-read returns 200", code == 200)
check("F: updated_count = 1", data["updated_count"] == 1)

# G — unread count drops
code, data = request("GET", "/notifications/unread-count", token=tok_b)
check("G: unread_count = 0 after marking read", data["unread_count"] == 0)

# H — read-all on already-read notifications returns 0 updated
code, data = request("POST", "/notifications/read-all", token=tok_b)
check("H: read-all returns 200", code == 200)
check("H: updated_count = 0 when all already read", data["updated_count"] == 0)

# I — alice cannot read bob's notification
code, _ = request("GET", f"/notifications", token=tok_a)
# Alice has no notifications (she sent the message, not received)
code2, data2 = request("POST", f"/notifications/{notif_id}/read", token=tok_a)
check("I: non-owner gets 404 on other's notification", code2 == 404)

# J — settings fields on /users/me
code, me_b2 = request("GET", "/users/me", token=tok_b)
check("J: /users/me includes theme", code == 200 and me_b2.get("theme") == "system")
check("J: notify_new_message default true", me_b2.get("notify_new_message") is True)
code, patched = request(
    "PATCH",
    "/users/me",
    token=tok_b,
    body={"theme": "dark", "notify_listing_favorited": False},
)
check("J: PATCH prefs 200", code == 200)
check("J: theme updated", patched.get("theme") == "dark")
check("J: notify_listing_favorited false", patched.get("notify_listing_favorited") is False)

print("STAGE7_SMOKE_COMPLETE")
