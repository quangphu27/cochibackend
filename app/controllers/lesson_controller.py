"""Lesson builder API controller."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.middleware.auth_middleware import teacher_required
from app.repositories.user_repo import UserRepository
from app.services.lesson_service import LessonService

lesson_bp = Blueprint("lessons", __name__, url_prefix="/api/lessons")
lesson_service = LessonService()
user_repo = UserRepository()


def _role(user_id):
    user = user_repo.find_by_id(user_id)
    return user.get("role", "student") if user else "student"


@lesson_bp.route("", methods=["GET"])
@jwt_required()
def list_lessons():
    user_id = get_jwt_identity()
    role = _role(user_id)
    page = request.args.get("page", 1, type=int)
    grade = request.args.get("grade")
    skill = request.args.get("skill")
    status = request.args.get("status")
    class_id = request.args.get("class_id")
    result, status_code = lesson_service.list_lessons(user_id, role, page, grade, skill, status, class_id)
    return jsonify(result), status_code


@lesson_bp.route("", methods=["POST"])
@teacher_required
def create_lesson(current_user):
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400
    result, status = lesson_service.create_lesson(current_user["id"], data)
    return jsonify(result), status


@lesson_bp.route("/analytics", methods=["GET"])
@teacher_required
def lesson_analytics(current_user):
    result, status = lesson_service.lesson_analytics(
        current_user["id"], current_user.get("role", "teacher")
    )
    return jsonify(result), status


@lesson_bp.route("/<lesson_id>", methods=["GET"])
@jwt_required()
def get_lesson(lesson_id):
    user_id = get_jwt_identity()
    result, status = lesson_service.get_lesson(lesson_id, user_id, _role(user_id))
    return jsonify(result), status


@lesson_bp.route("/<lesson_id>", methods=["PUT"])
@teacher_required
def update_lesson(lesson_id, current_user):
    data = request.get_json(silent=True) or {}
    result, status = lesson_service.update_lesson(
        lesson_id, current_user["id"], current_user.get("role", "teacher"), data
    )
    return jsonify(result), status


@lesson_bp.route("/<lesson_id>", methods=["DELETE"])
@teacher_required
def delete_lesson(lesson_id, current_user):
    result, status = lesson_service.delete_lesson(
        lesson_id, current_user["id"], current_user.get("role", "teacher")
    )
    return jsonify(result), status


@lesson_bp.route("/<lesson_id>/publish", methods=["POST"])
@teacher_required
def publish_lesson(lesson_id, current_user):
    data = request.get_json(silent=True) or {}
    result, status = lesson_service.publish_lesson(
        lesson_id, current_user["id"], current_user.get("role", "teacher"),
        data.get("class_ids", []),
    )
    return jsonify(result), status


@lesson_bp.route("/<lesson_id>/grade", methods=["POST"])
@jwt_required()
def grade_block(lesson_id):
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    block_id = data.get("block_id")
    if not block_id:
        return jsonify({"error": "block_id is required"}), 400
    result, status = lesson_service.grade_block(lesson_id, user_id, block_id, data.get("answers", {}))
    return jsonify(result), status


@lesson_bp.route("/<lesson_id>/progress", methods=["GET"])
@jwt_required()
def get_progress(lesson_id):
    user_id = get_jwt_identity()
    student_id = request.args.get("student_id")
    role = _role(user_id)
    if student_id and role in ("teacher", "super_admin"):
        user_id = student_id
    result, status = lesson_service.get_progress(lesson_id, user_id, role)
    return jsonify(result), status


@lesson_bp.route("/<lesson_id>/progress", methods=["POST"])
@jwt_required()
def save_progress(lesson_id):
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    result, status = lesson_service.save_progress(lesson_id, user_id, data)
    return jsonify(result), status


@lesson_bp.route("/<lesson_id>/ai-generate", methods=["POST"])
@teacher_required
def ai_generate(lesson_id, current_user):
    data = request.get_json(silent=True) or {}
    result, status = lesson_service.generate_block_ai(
        lesson_id,
        current_user["id"],
        current_user.get("role", "teacher"),
        data.get("block_type", "text"),
        data.get("topic", ""),
        data.get("grade"),
        data.get("skill"),
    )
    return jsonify(result), status
