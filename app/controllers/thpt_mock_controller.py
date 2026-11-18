"""THPT mock exam API — generate, share link, student attempts."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.middleware.auth_middleware import teacher_required
from app.repositories.user_repo import UserRepository
from app.services.thpt_mock_service import ThptMockService, LEVELS

thpt_mock_bp = Blueprint("thpt_mock", __name__, url_prefix="/api/thpt-mock")
service = ThptMockService()
user_repo = UserRepository()


@thpt_mock_bp.route("/levels", methods=["GET"])
def list_levels():
    return jsonify({
        "levels": [
            {"value": k, "label": v["label"], "question_count": v["question_count"]}
            for k, v in LEVELS.items()
        ]
    }), 200


@thpt_mock_bp.route("/generate", methods=["POST"])
@teacher_required
def generate_paper(current_user):
    data = request.get_json() or {}
    result, status = service.generate_paper(
        current_user["id"],
        data.get("source_text", ""),
        data.get("level", "B12"),
        data.get("provider", "gemini"),
    )
    return jsonify(result), status


@thpt_mock_bp.route("/mine", methods=["GET"])
@teacher_required
def my_papers(current_user):
    page = request.args.get("page", 1, type=int)
    return jsonify(service.list_my_papers(current_user["id"], page=page)), 200


@thpt_mock_bp.route("/public/<share_code>", methods=["GET"])
def get_public_paper(share_code):
    result, status = service.get_by_share_code(share_code, include_answers=False)
    return jsonify(result), status


@thpt_mock_bp.route("/public/<share_code>/submit", methods=["POST"])
@jwt_required()
def submit_public_paper(share_code):
    user = user_repo.find_by_id(get_jwt_identity())
    if not user:
        return jsonify({"error": "Người dùng không tồn tại"}), 404
    data = request.get_json() or {}
    result, status = service.submit_attempt(
        share_code,
        user["id"],
        user.get("full_name", ""),
        data.get("answers", []),
    )
    return jsonify(result), status


@thpt_mock_bp.route("/<paper_id>/attempts", methods=["GET"])
@teacher_required
def paper_attempts(paper_id, current_user):
    result, status = service.list_attempts(paper_id, current_user["id"])
    return jsonify(result), status