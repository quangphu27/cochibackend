"""Content and resources API controller."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.repositories.content_repo import ResourceRepository, PostRepository, DocumentRepository, NotificationRepository
from app.repositories.base import BaseRepository
from app.models.collections import COLLECTIONS
from app.utils.cloudinary_utils import upload_image, upload_video, upload_audio, upload_document
from app.middleware.auth_middleware import admin_required

content_bp = Blueprint("content", __name__, url_prefix="/api")
resource_repo = ResourceRepository()
post_repo = PostRepository()
document_repo = DocumentRepository()
notification_repo = NotificationRepository()


class MediaRepo(BaseRepository):
    collection_name = COLLECTIONS["media"]


class AlbumRepo(BaseRepository):
    collection_name = COLLECTIONS["albums"]


class EntertainmentRepo(BaseRepository):
    collection_name = COLLECTIONS["entertainment"]


media_repo = MediaRepo()
album_repo = AlbumRepo()
entertainment_repo = EntertainmentRepo()


def _upload_file(file):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext in ("jpg", "jpeg", "png", "gif", "webp"):
        return upload_image(file)
    if ext in ("mp4", "webm", "mov"):
        return upload_video(file)
    if ext in ("mp3", "wav", "ogg"):
        return upload_audio(file)
    return upload_document(file)


def _file_type_from_name(filename: str) -> str:
    if not filename:
        return "document"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in ("jpg", "jpeg", "png", "gif", "webp"):
        return "image"
    if ext in ("mp4", "webm", "mov"):
        return "video"
    if ext in ("mp3", "wav", "ogg"):
        return "audio"
    if ext == "pdf":
        return "pdf"
    return "document"


@content_bp.route("/resources", methods=["GET"])
def list_resources():
    grade = request.args.get("grade")
    skill = request.args.get("skill")
    page = request.args.get("page", 1, type=int)
    result = resource_repo.find_by_grade_skill(grade, skill, page=page)
    return jsonify(result), 200


@content_bp.route("/resources", methods=["POST"])
@admin_required
def create_resource(current_user):
    data = request.form.to_dict()
    file = request.files.get("file")
    upload_result = _upload_file(file)

    resource = resource_repo.create({
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "grade": data.get("grade", ""),
        "skill": data.get("skill", ""),
        "category": data.get("category", ""),
        "file_type": data.get("file_type") or _file_type_from_name(file.filename if file else ""),
        "file_url": upload_result["secure_url"] if upload_result else data.get("file_url", ""),
        "cloudinary_id": upload_result["public_id"] if upload_result else "",
        "thumbnail_url": upload_result.get("thumbnail_url", "") if upload_result else "",
        "uploaded_by": current_user["id"],
        "downloads": 0,
    })
    return jsonify(resource), 201


@content_bp.route("/resources/<resource_id>", methods=["DELETE"])
@admin_required
def delete_resource(resource_id, current_user):
    if not resource_repo.delete(resource_id):
        return jsonify({"error": "Không tìm thấy tài nguyên"}), 404
    return jsonify({"message": "Đã xóa tài nguyên"}), 200


@content_bp.route("/posts", methods=["GET"])
def list_posts():
    category = request.args.get("category")
    page = request.args.get("page", 1, type=int)
    if category:
        result = post_repo.find_by_category(category, page=page)
    else:
        result = post_repo.find_all(page=page, sort=[("created_at", -1)])
    return jsonify(result), 200


@content_bp.route("/posts", methods=["POST"])
@jwt_required()
def create_post():
    user_id = get_jwt_identity()
    data = request.get_json()
    post = post_repo.create({
        "author_id": user_id,
        "title": data["title"],
        "content": data["content"],
        "category": data.get("category", "general"),
        "tags": data.get("tags", []),
        "attachments": data.get("attachments", []),
        "likes_count": 0,
        "comments_count": 0,
    })
    return jsonify(post), 201


@content_bp.route("/documents", methods=["GET"])
def list_documents():
    category = request.args.get("category")
    page = request.args.get("page", 1, type=int)
    if category:
        result = document_repo.find_by_category(category, page=page)
    else:
        result = document_repo.find_all(page=page, sort=[("created_at", -1)])
    return jsonify(result), 200


@content_bp.route("/documents", methods=["POST"])
@admin_required
def create_document(current_user):
    data = request.form.to_dict()
    file = request.files.get("file")
    upload_result = _upload_file(file)
    doc = document_repo.create({
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "category": data.get("category", ""),
        "file_url": upload_result["secure_url"] if upload_result else data.get("file_url", ""),
        "file_type": _file_type_from_name(file.filename if file else ""),
        "uploaded_by": current_user["id"],
    })
    return jsonify(doc), 201


@content_bp.route("/documents/<doc_id>", methods=["DELETE"])
@admin_required
def delete_document(doc_id, current_user):
    if not document_repo.delete(doc_id):
        return jsonify({"error": "Không tìm thấy tài liệu"}), 404
    return jsonify({"message": "Đã xóa tài liệu"}), 200


@content_bp.route("/notifications", methods=["GET"])
@jwt_required()
def list_notifications():
    user_id = get_jwt_identity()
    unread = request.args.get("unread") == "true"
    page = request.args.get("page", 1, type=int)
    result = notification_repo.find_by_user(user_id, unread_only=unread, page=page)
    return jsonify(result), 200


@content_bp.route("/notifications/read-all", methods=["PUT"])
@jwt_required()
def mark_all_notifications_read():
    user_id = get_jwt_identity()
    notification_repo.mark_all_read(user_id)
    return jsonify({"message": "All notifications marked as read"}), 200


@content_bp.route("/notifications/<notif_id>/read", methods=["PUT"])
@jwt_required()
def mark_notification_read(notif_id):
    result = notification_repo.mark_read(notif_id)
    return jsonify(result), 200


@content_bp.route("/entertainment", methods=["GET"])
def list_entertainment():
    category = request.args.get("category")
    query = {"category": category} if category else {}
    page = request.args.get("page", 1, type=int)
    result = entertainment_repo.find_all(query, page=page, sort=[("created_at", -1)])
    return jsonify(result), 200


@content_bp.route("/entertainment", methods=["POST"])
@admin_required
def create_entertainment(current_user):
    data = request.form.to_dict()
    file = request.files.get("file")
    upload_result = _upload_file(file)
    cover = request.files.get("cover")
    cover_result = _upload_file(cover) if cover else None
    item = entertainment_repo.create({
        "title": data.get("title", ""),
        "category": data.get("category", ""),
        "description": data.get("description", ""),
        "media_url": upload_result["secure_url"] if upload_result else data.get("media_url", ""),
        "thumbnail_url": cover_result["secure_url"] if cover_result else "",
        "duration": int(data.get("duration") or 0),
        "uploaded_by": current_user["id"],
    })
    return jsonify(item), 201


@content_bp.route("/entertainment/<item_id>", methods=["DELETE"])
@admin_required
def delete_entertainment(item_id, current_user):
    if not entertainment_repo.delete(item_id):
        return jsonify({"error": "Không tìm thấy nội dung"}), 404
    return jsonify({"message": "Đã xóa nội dung giải trí"}), 200


@content_bp.route("/albums", methods=["GET"])
def list_albums():
    category = request.args.get("category")
    query = {"category": category} if category else {}
    page = request.args.get("page", 1, type=int)
    result = album_repo.find_all(query, page=page, sort=[("created_at", -1)])
    return jsonify(result), 200


@content_bp.route("/albums", methods=["POST"])
@admin_required
def create_album(current_user):
    data = request.form.to_dict()
    cover = request.files.get("file") or request.files.get("cover")
    upload_result = _upload_file(cover)
    album = album_repo.create({
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "category": data.get("category", ""),
        "cover_url": upload_result["secure_url"] if upload_result else data.get("cover_url", ""),
        "media_ids": [],
        "created_by": current_user["id"],
    })
    return jsonify(album), 201


@content_bp.route("/albums/<album_id>", methods=["DELETE"])
@admin_required
def delete_album(album_id, current_user):
    if not album_repo.delete(album_id):
        return jsonify({"error": "Không tìm thấy album"}), 404
    return jsonify({"message": "Đã xóa album"}), 200


@content_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_media():
    file = request.files.get("file")
    media_type = request.form.get("type", "image")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    uploaders = {"image": upload_image, "video": upload_video, "audio": upload_audio}
    uploader = uploaders.get(media_type, upload_document)
    result = uploader(file)

    media = media_repo.create({
        "title": request.form.get("title", file.filename),
        "type": media_type,
        "url": result["secure_url"],
        "cloudinary_id": result["public_id"],
        "album_id": request.form.get("album_id", ""),
        "category": request.form.get("category", ""),
        "uploaded_by": get_jwt_identity(),
    })
    return jsonify(media), 201
