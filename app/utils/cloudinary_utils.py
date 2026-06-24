"""Cloudinary upload utilities."""
import os
import cloudinary.uploader


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


def upload_file(file, resource_type="auto", folder=None, public_id=None):
    options = {"resource_type": resource_type}
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
    return upload_file(file, resource_type="raw", folder=folder or folders["document"])


def delete_file(public_id, resource_type="image"):
    return cloudinary.uploader.destroy(public_id, resource_type=resource_type)
