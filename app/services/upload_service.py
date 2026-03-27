from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.message_attachment import MessageAttachmentUploadRead
from app.schemas.upload import UploadedImageRead

ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_AVATAR_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 67_108_864
MAX_AVATAR_SIZE_BYTES = 10_485_760
MAX_MESSAGE_ATTACHMENT_SIZE_BYTES = 20_971_520
ALLOWED_MESSAGE_ATTACHMENT_MIME_TYPES = ALLOWED_IMAGE_MIME_TYPES | {"application/pdf"}
MIME_DEFAULT_SUFFIX = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}


class UploadService:
    @staticmethod
    def _require_pillow():
        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
        except Exception as exc:  # pragma: no cover - environment specific
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Image processing dependency is unavailable. Install Pillow.",
            ) from exc
        return Image, ImageOps, UnidentifiedImageError

    def upload_listing_image(self, *, upload_file: UploadFile) -> UploadedImageRead:
        return self._upload_image(
            upload_file=upload_file,
            target_subdir="listings",
            max_size_bytes=MAX_IMAGE_SIZE_BYTES,
            max_size_label="64 MB",
        )

    def upload_avatar_image(self, *, upload_file: UploadFile) -> UploadedImageRead:
        return self.upload_avatar_image_with_optional_crop(
            upload_file=upload_file,
            crop_x=None,
            crop_y=None,
            crop_width=None,
            crop_height=None,
            crop_rotation=None,
        )

    def upload_avatar_image_with_optional_crop(
        self,
        *,
        upload_file: UploadFile,
        crop_x: int | None,
        crop_y: int | None,
        crop_width: int | None,
        crop_height: int | None,
        crop_rotation: float | None,
    ) -> UploadedImageRead:
        Image, ImageOps, _ = self._require_pillow()
        allowed_mime_types_set = set(ALLOWED_AVATAR_MIME_TYPES)
        if upload_file.content_type not in allowed_mime_types_set:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported media type. Allowed: {', '.join(sorted(allowed_mime_types_set))}",
            )

        raw_payload = upload_file.file.read(MAX_AVATAR_SIZE_BYTES + 1)
        if len(raw_payload) > MAX_AVATAR_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum size is 10 MB",
            )

        source_image = self._load_and_validate_image(
            payload=raw_payload,
            expected_mime=upload_file.content_type or "",
        )
        source_image = ImageOps.exif_transpose(source_image)
        source_image = source_image.convert("RGBA")

        has_crop = any(v is not None for v in (crop_x, crop_y, crop_width, crop_height, crop_rotation))
        if has_crop:
            if None in (crop_x, crop_y, crop_width, crop_height):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="crop_x, crop_y, crop_width and crop_height must all be provided together",
                )
            if crop_width is not None and crop_width <= 0:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="crop_width must be > 0")
            if crop_height is not None and crop_height <= 0:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="crop_height must be > 0")
            if crop_rotation:
                source_image = source_image.rotate(-float(crop_rotation), expand=True, resample=Image.Resampling.BICUBIC)
            source_image = self._crop_with_bounds(
                source_image,
                x=crop_x or 0,
                y=crop_y or 0,
                width=crop_width or source_image.width,
                height=crop_height or source_image.height,
            )

        # Strip metadata by re-encoding and do not persist source EXIF.
        main_image = self._to_rgb(source_image)
        main_payload = self._encode_jpeg(main_image)

        target_subdir = "users/avatars"
        target_dir = Path(settings.UPLOADS_DIR) / target_subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        base_id = uuid.uuid4().hex
        main_filename = f"{base_id}.jpg"
        thumb_128_filename = f"{base_id}_128.jpg"
        thumb_512_filename = f"{base_id}_512.jpg"

        main_path = (target_dir / main_filename).resolve()
        thumb_128_path = (target_dir / thumb_128_filename).resolve()
        thumb_512_path = (target_dir / thumb_512_filename).resolve()

        if target_dir.resolve() not in main_path.parents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload path")

        main_path.write_bytes(main_payload)

        square = self._center_square_crop(main_image)
        thumb_128_path.write_bytes(self._encode_jpeg(square.resize((128, 128), Image.Resampling.LANCZOS)))
        thumb_512_payload = self._encode_jpeg(square.resize((512, 512), Image.Resampling.LANCZOS))
        thumb_512_path.write_bytes(thumb_512_payload)

        return UploadedImageRead(
            url=f"{settings.UPLOADS_URL_PREFIX}/{target_subdir}/{thumb_512_filename}",
            content_type="image/jpeg",
            size_bytes=len(thumb_512_payload),
        )

    def upload_message_attachment(self, *, upload_file: UploadFile) -> MessageAttachmentUploadRead:
        uploaded = self._upload_file(
            upload_file=upload_file,
            target_subdir="messages/attachments",
            max_size_bytes=MAX_MESSAGE_ATTACHMENT_SIZE_BYTES,
            max_size_label="20 MB",
            allowed_mime_types=ALLOWED_MESSAGE_ATTACHMENT_MIME_TYPES,
            default_suffix=".bin",
        )
        return MessageAttachmentUploadRead(
            url=uploaded["url"],
            original_name=uploaded["original_name"],
            content_type=uploaded["content_type"],
            size_bytes=uploaded["size_bytes"],
        )

    def _upload_image(
        self,
        *,
        upload_file: UploadFile,
        target_subdir: str,
        max_size_bytes: int,
        max_size_label: str,
        allowed_mime_types: Iterable[str] = ALLOWED_IMAGE_MIME_TYPES,
    ) -> UploadedImageRead:
        uploaded = self._upload_file(
            upload_file=upload_file,
            target_subdir=target_subdir,
            max_size_bytes=max_size_bytes,
            max_size_label=max_size_label,
            allowed_mime_types=allowed_mime_types,
            default_suffix=".jpg",
        )
        return UploadedImageRead(
            url=uploaded["url"],
            content_type=uploaded["content_type"],
            size_bytes=uploaded["size_bytes"],
        )

    def _load_and_validate_image(self, *, payload: bytes, expected_mime: str):
        _, _, UnidentifiedImageError = self._require_pillow()
        from PIL import Image

        try:
            with Image.open(io.BytesIO(payload)) as candidate:
                candidate.verify()
            image = Image.open(io.BytesIO(payload))
            actual_format = (image.format or "").upper()
        except (UnidentifiedImageError, OSError, SyntaxError):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Uploaded file is not a valid image")

        mime_by_format = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }
        actual_mime = mime_by_format.get(actual_format)
        if actual_mime is None or actual_mime != expected_mime:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File signature does not match content type",
            )
        return image

    def _crop_with_bounds(self, image, *, x: int, y: int, width: int, height: int):
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(image.width, x1 + width)
        y2 = min(image.height, y1 + height)
        if x1 >= x2 or y1 >= y2:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid crop rectangle")
        return image.crop((x1, y1, x2, y2))

    def _center_square_crop(self, image):
        side = min(image.width, image.height)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        return image.crop((left, top, left + side, top + side))

    def _to_rgb(self, image):
        if image.mode in ("RGBA", "LA"):
            from PIL import Image

            background = Image.new("RGB", image.size, (255, 255, 255))
            alpha = image.getchannel("A") if "A" in image.getbands() else None
            background.paste(image, mask=alpha)
            return background
        if image.mode != "RGB":
            return image.convert("RGB")
        return image

    def _encode_jpeg(self, image) -> bytes:
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=88, optimize=True)
        return output.getvalue()

    def _upload_file(
        self,
        *,
        upload_file: UploadFile,
        target_subdir: str,
        max_size_bytes: int,
        max_size_label: str,
        allowed_mime_types: Iterable[str],
        default_suffix: str,
    ) -> dict[str, str | int]:
        allowed_mime_types_set = set(allowed_mime_types)
        if upload_file.content_type not in allowed_mime_types_set:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported media type. Allowed: {', '.join(sorted(allowed_mime_types_set))}",
            )

        payload = upload_file.file.read(max_size_bytes + 1)
        if len(payload) > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {max_size_label}",
            )

        suffix = MIME_DEFAULT_SUFFIX.get(upload_file.content_type or "", default_suffix)

        safe_name = f"{uuid.uuid4().hex}{suffix}"
        target_dir = Path(settings.UPLOADS_DIR) / target_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = (target_dir / safe_name).resolve()

        # Ensure writes stay under configured upload root.
        if target_dir.resolve() not in target_path.parents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload path")

        target_path.write_bytes(payload)
        return {
            "url": f"{settings.UPLOADS_URL_PREFIX}/{target_subdir}/{safe_name}",
            "content_type": upload_file.content_type or "",
            "size_bytes": len(payload),
            "original_name": Path(upload_file.filename or "upload").name,
        }
