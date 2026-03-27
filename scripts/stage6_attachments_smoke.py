from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL = "http://localhost:8000"
MAX_ATTACHMENT_BYTES = 20_971_520


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
    request_headers = {}
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=request_headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())


def post_multipart_file(
    url: str,
    *,
    token: str,
    filename: str,
    content_type: str,
    payload: bytes,
) -> tuple[int, dict]:
    boundary = "----Stage6AttachmentBoundary"
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


def post_multipart_expect_error(
    url: str,
    *,
    token: str,
    filename: str,
    content_type: str,
    payload: bytes,
) -> tuple[int, str]:
    boundary = "----Stage6AttachmentErrorBoundary"
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
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()
    raise RuntimeError("Expected HTTPError")


def assert_true(condition: bool, label: str) -> None:
    if not condition:
        raise RuntimeError(f"FAILED: {label}")
    print(f"PASS: {label}")


def create_user(email_prefix: str) -> tuple[str, dict]:
    email = f"{email_prefix}{int(time.time() * 1000)}@test.com"
    password = "password123"
    post_json(
        f"{BASE_URL}/auth/register",
        {"full_name": email_prefix, "email": email, "password": password},
    )
    _, login_payload = post_json(f"{BASE_URL}/auth/login", {"email": email, "password": password})
    token = login_payload["access_token"]
    _, me = get_json(f"{BASE_URL}/users/me", token=token)
    return token, me


if __name__ == "__main__":
    # Three users to verify participant vs non-participant attachment access.
    token_a, user_a = create_user("stage6A")
    token_b, user_b = create_user("stage6B")
    token_c, _ = create_user("stage6C")

    conv_status, conv = post_json(
        f"{BASE_URL}/conversations",
        {"participant_id": user_b["id"]},
        token=token_a,
    )
    assert_true(conv_status == 201, "conversation created for A <-> B")
    conversation_id = conv["id"]

    # A) Valid image attachment upload <=20MB.
    image_status, image_upload = post_multipart_file(
        f"{BASE_URL}/attachments",
        token=token_a,
        filename="receipt.png",
        content_type="image/png",
        payload=b"\x89PNG\r\n\x1a\nstage6-image",
    )
    assert_true(image_status == 201, "A: image upload succeeds")
    assert_true(all(k in image_upload for k in ("url", "original_name", "content_type", "size_bytes")), "A: upload response shape")

    # B) Valid PDF attachment upload <=20MB.
    pdf_status, pdf_upload = post_multipart_file(
        f"{BASE_URL}/attachments",
        token=token_a,
        filename="proof.pdf",
        content_type="application/pdf",
        payload=b"%PDF-1.7\n%stage6",
    )
    assert_true(pdf_status == 201, "B: pdf upload succeeds")

    # C) Attachment >20MB should return 413.
    too_large_status, too_large_body = post_multipart_expect_error(
        f"{BASE_URL}/attachments",
        token=token_a,
        filename="too-big.pdf",
        content_type="application/pdf",
        payload=b"x" * (MAX_ATTACHMENT_BYTES + 1),
    )
    assert_true(too_large_status == 413, "C: oversized attachment rejected with 413")
    assert_true("File too large" in too_large_body, "C: oversized response detail present")

    # D) Unsupported mime should return 415.
    bad_mime_status, bad_mime_body = post_multipart_expect_error(
        f"{BASE_URL}/attachments",
        token=token_a,
        filename="malware.exe",
        content_type="application/octet-stream",
        payload=b"MZstage6",
    )
    assert_true(bad_mime_status == 415, "D: invalid mime rejected with 415")
    assert_true("Unsupported media type" in bad_mime_body, "D: invalid mime response detail present")

    # E) Send message with attachment only (no text body).
    file_name = Path(pdf_upload["url"]).name
    send_status, sent_message = post_json(
        f"{BASE_URL}/messages",
        {
            "conversation_id": conversation_id,
            "text_body": None,
            "attachments": [
                {
                    "file_name": file_name,
                    "original_name": pdf_upload["original_name"],
                    "mime_type": pdf_upload["content_type"],
                    "file_size": pdf_upload["size_bytes"],
                    "file_url": pdf_upload["url"],
                }
            ],
            "client_message_id": f"stage6-{int(time.time() * 1000)}",
        },
        token=token_a,
    )
    assert_true(send_status == 201, "E: message with attachment and no text succeeds")
    assert_true(len(sent_message.get("attachments", [])) == 1, "E: message returns one attachment")
    attachment_id = sent_message["attachments"][0]["id"]

    # F) List messages returns attachments populated.
    list_status, list_payload = get_json(f"{BASE_URL}/messages/{conversation_id}?page=1&page_size=50", token=token_b)
    assert_true(list_status == 200, "F: list messages succeeds")
    attachment_count = sum(len(item.get("attachments", [])) for item in list_payload.get("items", []))
    assert_true(attachment_count >= 1, "F: list messages includes attachments")

    # G) Participant can access attachment detail.
    detail_status, detail_payload = get_json(f"{BASE_URL}/attachments/{attachment_id}", token=token_b)
    assert_true(detail_status == 200, "G: participant can read attachment detail")
    assert_true(detail_payload["id"] == attachment_id, "G: fetched expected attachment")

    # H) Non-participant gets 403.
    try:
        get_json(f"{BASE_URL}/attachments/{attachment_id}", token=token_c)
        raise RuntimeError("FAILED: H expected 403 for non-participant")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        assert_true(exc.code == 403, "H: non-participant blocked with 403")
        assert_true("Not allowed" in body, "H: non-participant response detail present")

    # I) Existing send/list message flow still works with text-only payload.
    text_send_status, _ = post_json(
        f"{BASE_URL}/messages",
        {"conversation_id": conversation_id, "content": "text-only still works"},
        token=token_b,
        headers={"Idempotency-Key": f"stage6-text-{int(time.time() * 1000)}"},
    )
    assert_true(text_send_status == 201, "I: text-only messaging flow unchanged")

    # J) Existing listing image upload endpoint still works.
    listing_upload_status, listing_upload = post_multipart_file(
        f"{BASE_URL}/uploads/images",
        token=token_a,
        filename="listing.png",
        content_type="image/png",
        payload=b"\x89PNG\r\n\x1a\nlisting-image",
    )
    assert_true(listing_upload_status == 200, "J: /uploads/images endpoint still works")
    assert_true("url" in listing_upload and listing_upload["url"], "J: listing upload returns url")

    print("STAGE6_SMOKE_COMPLETE")
