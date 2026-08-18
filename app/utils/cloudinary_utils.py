"""Cloudinary upload utilities."""
import os
import re
import uuid
from pathlib import Path

import cloudinary.uploader

ALLOWED_EXTS = {
    "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
    "png", "jpg", "jpeg", "gif", "webp", "mp4", "webm", "mp3", "wav", "ogg",
}


def _folder_prefix():
    try:
        from flask import current_app
        return current_app.config.get("CLOUDINARY_FOLDER_PREFIX", "cochibrightfuture")
    except RuntimeError:
        return os.getenv("CLOUDINARY_FOLDER_PREFIX", "cochibrightfuture")


def get_folder_map():
    prefix = _folder_prefix()
    return {
        "image": f"{prefix}/images",
        "video": f"{prefix}/videos",
        "audio": f"{prefix}/audio",
        "pdf": f"{prefix}/documents",
        "document": f"{prefix}/documents",
        "speaking": f"{prefix}/speaking",
    }


def _ext_from_url(url: str) -> str:
    if not url:
        return ""
    name = Path(url.split("?")[0].rstrip("/")).name
    ext = Path(name).suffix.lstrip(".").lower()
    return ext if ext in ALLOWED_EXTS else ""


def _raw_public_id(filename: str) -> str:
    """Keep original name + extension so downloads open correctly."""
    name = Path(filename or "document").name
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(name).stem)[:80].strip("_") or "file"
    ext = Path(name).suffix.lstrip(".").lower()
    unique = uuid.uuid4().hex[:8]
    if ext:
        return f"{stem}_{unique}.{ext}"
    return f"{stem}_{unique}"


def safe_download_name(
    title: str = "",
    original_filename: str = "",
    file_type: str = "",
    file_url: str = "",
) -> str:
    original = Path(original_filename or "").name
    ext = Path(original).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTS:
        ext = ""
    if not ext:
        ext = _ext_from_url(file_url)
    if not ext:
        ext = {
            "pdf": "pdf",
            "document": "pdf",
            "doc": "doc",
            "docx": "docx",
            "ppt": "ppt",
            "pptx": "pptx",
            "xls": "xls",
            "xlsx": "xlsx",
            "image": "jpg",
            "video": "mp4",
            "audio": "mp3",
        }.get((file_type or "").lower(), "pdf")
    stem_source = Path(original).stem if original else (title or "file")
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem_source)[:80].strip("_") or "file"
    return f"{stem}.{ext}"


def strip_attachment_transform(url: str) -> str:
    """Raw Cloudinary files reject fl_attachment (HTTP 400). Always use the original URL."""
    if not url:
        return url
    return re.sub(r"/upload/fl_attachment:[^/]+/", "/upload/", url)


def upload_file(file, resource_type="auto", folder=None, public_id=None, **extra):
    options = {"resource_type": resource_type, **extra}
    if folder:
        options["folder"] = folder
    if public_id:
        options["public_id"] = public_id
    return cloudinary.uploader.upload(file, **options)


def upload_image(file, folder=None):
    folders = get_folder_map()
    return upload_file(file, resource_type="image", folder=folder or folders["image"])


def upload_video(file, folder=None):
    folders = get_folder_map()
    return upload_file(file, resource_type="video", folder=folder or folders["video"])


def upload_audio(file, folder=None):
    folders = get_folder_map()
    return upload_file(file, resource_type="video", folder=folder or folders["audio"])


def upload_document(file, folder=None):
    folders = get_folder_map()
    filename = getattr(file, "filename", None) or "document"
    return upload_file(
        file,
        resource_type="raw",
        folder=folder or folders["document"],
        public_id=_raw_public_id(filename),
    )


def delete_file(public_id, resource_type="image"):
    return cloudinary.uploader.destroy(public_id, resource_type=resource_type)
