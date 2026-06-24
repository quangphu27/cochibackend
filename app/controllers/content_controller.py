"""Content and resources API controller."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.repositories.content_repo import ResourceRepository, PostRepository, DocumentRepository, NotificationRepository
from app.repositories.base import BaseRepository
from app.models.collections import COLLECTIONS
from app.utils.cloudinary_utils import upload_image, upload_video, upload_audio, upload_document
from app.middleware.auth_middleware import teacher_required

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


@content_bp.route("/resources", methods=["GET"])
def list_resources():
    grade = request.args.get("grade")
    skill = request.args.get("skill")
    page = request.args.get("page", 1, type=int)
    result = resource_repo.find_by_grade_skill(grade, skill, page=page)
    return jsonify(result), 200


@content_bp.route("/resources", methods=["POST"])
@teacher_required
def create_resource(current_user):
    data = request.form.to_dict()
    file = request.files.get("file")
    upload_result = None
    if file:
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
        if ext in ("jpg", "jpeg", "png", "gif", "webp"):
            upload_result = upload_image(file)
        elif ext in ("mp4", "webm", "mov"):
            upload_result = upload_video(file)
        elif ext in ("mp3", "wav", "ogg"):
            upload_result = upload_audio(file)
        else:
            upload_result = upload_document(file)

    resource = resource_repo.create({
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "grade": data.get("grade", ""),
        "skill": data.get("skill", ""),
        "category": data.get("category", ""),
        "file_type": data.get("file_type", ""),
        "file_url": upload_result["secure_url"] if upload_result else "",
        "cloudinary_id": upload_result["public_id"] if upload_result else "",
        "thumbnail_url": upload_result.get("thumbnail_url", "") if upload_result else "",
        "uploaded_by": current_user["id"],
        "downloads": 0,
    })
    return jsonify(resource), 201


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
        result = document_repo.find_all(page=page)
    return jsonify(result), 200


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
    result = entertainment_repo.find_all(query, page=page)
    return jsonify(result), 200


@content_bp.route("/albums", methods=["GET"])
def list_albums():
    category = request.args.get("category")
    query = {"category": category} if category else {}
    page = request.args.get("page", 1, type=int)
    result = album_repo.find_all(query, page=page)
    return jsonify(result), 200


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
