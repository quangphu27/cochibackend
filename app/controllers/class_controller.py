"""Class management API controller."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.class_service import ClassService
from app.repositories.user_repo import UserRepository
from app.dto.schemas import validate_request, ClassCreateSchema
from app.middleware.auth_middleware import teacher_required

class_bp = Blueprint("classes", __name__, url_prefix="/api/classes")
class_service = ClassService()
user_repo = UserRepository()


@class_bp.route("", methods=["POST"])
@teacher_required
@validate_request(ClassCreateSchema)
def create_class(validated_data, current_user):
    result, status = class_service.create_class(current_user["id"], validated_data)
    return jsonify(result), status


@class_bp.route("/join", methods=["POST"])
@jwt_required()
def join_class():
    student_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    class_code = data.get("class_code", "").strip()
    if not class_code:
        return jsonify({"error": "Class code is required"}), 400
    result, status = class_service.join_class(student_id, class_code)
    return jsonify(result), status


@class_bp.route("", methods=["GET"])
@jwt_required()
def list_classes():
    user_id = get_jwt_identity()
    user = user_repo.find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    page = request.args.get("page", 1, type=int)
    result = class_service.get_user_classes(user_id, user.get("role", "student"), page=page)
    return jsonify(result), 200


@class_bp.route("/<class_id>", methods=["GET"])
@jwt_required()
def get_class(class_id):
    result, status = class_service.get_class_details(class_id)
    return jsonify(result), status


@class_bp.route("/<class_id>/students", methods=["POST"])
@teacher_required
def add_student(class_id, current_user):
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"error": "email is required"}), 400
    result, status = class_service.add_student_by_email(
        class_id, email, current_user["id"], current_user.get("role", "teacher")
    )
    return jsonify(result), status


@class_bp.route("/<class_id>/students/<student_id>", methods=["DELETE"])
@teacher_required
def remove_student(class_id, student_id, current_user):
    result, status = class_service.remove_student(
        class_id, student_id, current_user["id"], current_user.get("role", "teacher")
    )
    return jsonify(result), status
