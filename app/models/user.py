"""User and role schemas."""
from datetime import datetime

ROLES = ["super_admin", "teacher", "student", "parent"]

USER_SCHEMA = {
    "email": str,
    "password_hash": str,
    "full_name": str,
    "role": str,
    "avatar_url": str,
    "phone": str,
    "is_verified": bool,
    "is_active": bool,
    "google_id": str,
    "parent_id": str,
    "student_ids": list,
    "class_ids": list,
    "preferences": dict,
    "created_at": datetime,
    "updated_at": datetime,
}

ROLE_SCHEMA = {
    "name": str,
    "permissions": list,
    "description": str,
}

TEACHER_PROFILE = {
    "user_id": str,
    "biography": str,
    "philosophy": str,
    "certifications": list,
    "experience_years": int,
    "specializations": list,
    "achievements": list,
    "subjects": list,
}
