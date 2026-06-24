"""Community API - comments and likes."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.repositories.lms_repo import CommentRepository, LikeRepository
from app.repositories.content_repo import PostRepository
from app.repositories.user_repo import UserRepository

community_bp = Blueprint("community", __name__, url_prefix="/api/community")
comment_repo = CommentRepository()
like_repo = LikeRepository()
post_repo = PostRepository()
user_repo = UserRepository()


@community_bp.route("/posts/<post_id>/comments", methods=["GET"])
def list_comments(post_id):
    page = request.args.get("page", 1, type=int)
    result = comment_repo.find_by_post(post_id, page=page)
    for c in result["data"]:
        author = user_repo.find_by_id(c.get("author_id", ""))
        if author:
            author.pop("password_hash", None)
            c["author"] = {"id": author["id"], "full_name": author.get("full_name"), "avatar_url": author.get("avatar_url")}
    return jsonify(result), 200


@community_bp.route("/posts/<post_id>/comments", methods=["POST"])
@jwt_required()
def create_comment(post_id):
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    if not data.get("content"):
        return jsonify({"error": "content is required"}), 400
    comment = comment_repo.create({
        "post_id": post_id,
        "author_id": user_id,
        "content": data["content"],
        "parent_id": data.get("parent_id", ""),
    })
    post = post_repo.find_by_id(post_id)
    if post:
        post_repo.update(post_id, {"comments_count": post.get("comments_count", 0) + 1})
    return jsonify(comment), 201


@community_bp.route("/posts/<post_id>/like", methods=["POST"])
@jwt_required()
def toggle_like(post_id):
    user_id = get_jwt_identity()
    liked = like_repo.toggle(post_id, user_id)
    post = post_repo.find_by_id(post_id)
    if post:
        count = post.get("likes_count", 0) + (1 if liked else -1)
        post_repo.update(post_id, {"likes_count": max(0, count)})
    return jsonify({"liked": liked, "likes_count": max(0, (post or {}).get("likes_count", 0) + (1 if liked else -1))}), 200
