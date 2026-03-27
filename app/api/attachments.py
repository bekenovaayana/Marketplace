from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.message_attachment_repository import MessageAttachmentRepository
from app.schemas.message_attachment import MessageAttachmentRead, MessageAttachmentUploadRead
from app.services.upload_service import UploadService

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post(
    "",
    response_model=MessageAttachmentUploadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload message attachment",
    description=(
        "Upload a single message attachment file (image or PDF, max 20 MB). "
        "Use the returned `url` as `attachments[].file_url` in `POST /messages`. "
        "Accepted MIME types: image/jpeg, image/png, image/webp, application/pdf."
    ),
    responses={
        201: {
            "description": "Attachment uploaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "url": "/uploads/messages/attachments/9f4bb7f3ca6f43c49643c6de63a4bcf2.pdf",
                        "original_name": "invoice-march.pdf",
                        "content_type": "application/pdf",
                        "size_bytes": 245811,
                    }
                }
            },
        },
        413: {"description": "File too large (max 20 MB)"},
        415: {"description": "Unsupported media type"},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {"file": {"type": "string", "format": "binary"}},
                    }
                }
            },
        }
    },
)
def upload_attachment(
    file: UploadFile = File(..., description="Binary file to upload."),
    current_user: User = Depends(get_current_user),
) -> MessageAttachmentUploadRead:
    _ = current_user
    return UploadService().upload_message_attachment(upload_file=file)


@router.get(
    "/{attachment_id}",
    response_model=MessageAttachmentRead,
    summary="Get attachment details",
    description="Fetch attachment metadata. Only conversation participants can access this endpoint.",
)
def get_attachment_detail(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageAttachmentRead:
    attachment = MessageAttachmentRepository(db).get_by_id(attachment_id, with_message=True)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    message = attachment.message
    if not message or not message.conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    convo = message.conversation
    if current_user.id not in (convo.participant_a_id, convo.participant_b_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    return attachment
