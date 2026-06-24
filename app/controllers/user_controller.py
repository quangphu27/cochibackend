"""User management API controller."""
from flask import Blueprint, request, jsonify
from app.repositories.user_repo import UserRepository
from app.middleware.auth_middleware import admin_required, role_required

user_bp = Blueprint("users", __name__, url_prefix="/api/users")
user_repo = UserRepository()


@user_bp.route("/teacher-profile", methods=["GET"])
def get_teacher_profile():
    teacher = user_repo.find_one({"email": "giaovien@gmail.com"})
    if not teacher:
        teacher = {
            "full_name": "Nguyễn Thị Kim Chi",
            "email": "giaovien@gmail.com",
            "phone": "0901549899",
            "role": "teacher",
            "avatar_url": "",
            "profile": {
                "biography": "Experienced English teacher specializing in high school English education.",
                "philosophy": "Learning English should be engaging, practical, and confidence-building.",
                "certifications": ["CELTA", "TEFL"],
                "experience_years": 15,
                "specializations": ["English for Teens", "Speaking Skills", "Writing Skills"],
                "achievements": ["Outstanding Teacher Award 2023"],
                "subjects": ["High School English"],
            },
        }
    else:
        teacher.pop("password_hash", None)
        teacher.setdefault("profile", {
            "biography": "Experienced English teacher with 15+ years of dedication.",
            "philosophy": "Learning English should be engaging and confidence-building.",
            "certifications": ["CELTA", "TEFL"],
            "experience_years": 15,
            "specializations": ["English for Teens", "Speaking Skills", "Writing Skills"],
            "achievements": ["Outstanding Teacher Award 2023"],
            "subjects": ["High School English"],
        })
    return jsonify(teacher), 200


@user_bp.route("", methods=["GET"])
@admin_required
def list_users(current_user):
    role = request.args.get("role")
    page = request.args.get("page", 1, type=int)
    if role:
        result = user_repo.find_by_role(role, page=page)
    else:
        result = user_repo.find_all(page=page)
    for u in result["data"]:
        u.pop("password_hash", None)
    return jsonify(result), 200


@user_bp.route("/<user_id>", methods=["GET"])
@role_required("super_admin", "teacher")
def get_user(user_id, current_user):
    user = user_repo.find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.pop("password_hash", None)
    return jsonify(user), 200
