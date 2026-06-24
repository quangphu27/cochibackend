"""Role-based access control middleware."""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

ROLE_HIERARCHY = {
    "super_admin": 4,
    "teacher": 3,
    "parent": 2,
    "student": 1,
}


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            from app.repositories.user_repo import UserRepository
            user = UserRepository().find_by_id(get_jwt_identity())
            if not user or user.get("role") not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return fn(*args, **kwargs, current_user=user)
        return wrapper
    return decorator


def admin_required(fn):
    return role_required("super_admin")(fn)


def teacher_required(fn):
    return role_required("super_admin", "teacher")(fn)
