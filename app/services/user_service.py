"""Admin user management service."""
from app.repositories.user_repo import UserRepository
from app.utils.auth_utils import hash_password

user_repo = UserRepository()


class UserService:
    def list_users(self, role=None, page=1, limit=20):
        query = {}
        if role:
            query["role"] = role
        result = user_repo.find_all(query, page=page, limit=limit, sort=[("created_at", -1)])
        for u in result["data"]:
            u.pop("password_hash", None)
        return result, 200

    def create_teacher(self, data):
        email = data["email"].lower().strip()
        if user_repo.find_by_email(email):
            return {"error": "Email đã được sử dụng"}, 409

        user = user_repo.create({
            "email": email,
            "password_hash": hash_password(data["password"]),
            "full_name": data["full_name"].strip(),
            "role": "teacher",
            "phone": (data.get("phone") or "").strip(),
            "avatar_url": "",
            "is_verified": True,
            "is_active": True,
            "class_ids": [],
            "student_ids": [],
            "preferences": {"theme": "light", "language": "vi"},
        })
        user.pop("password_hash", None)
        return {"user": user, "message": "Tạo tài khoản giáo viên thành công"}, 201

    def delete_user(self, user_id: str, actor: dict):
        if actor.get("id") == user_id:
            return {"error": "Không thể xóa tài khoản của chính bạn"}, 400

        target = user_repo.find_by_id(user_id)
        if not target:
            return {"error": "Không tìm thấy người dùng"}, 404
        if target.get("role") == "super_admin":
            return {"error": "Không thể xóa tài khoản quản trị viên"}, 403

        user_repo.delete(user_id)
        return {"message": "Đã xóa tài khoản"}, 200
