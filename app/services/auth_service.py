"""Authentication service."""
from app.repositories.user_repo import UserRepository
from app.utils.auth_utils import hash_password, verify_password, generate_verification_token, verify_token
from app.utils.email_utils import send_verification_email, send_password_reset_email

user_repo = UserRepository()


class AuthService:
    def register(self, data):
        if user_repo.find_by_email(data["email"]):
            return {"error": "Email already registered"}, 409

        user = user_repo.create({
            "email": data["email"].lower(),
            "password_hash": hash_password(data["password"]),
            "full_name": data["full_name"],
            "role": "student",
            "phone": data.get("phone", ""),
            "avatar_url": "",
            "is_verified": False,
            "is_active": True,
            "class_ids": [],
            "student_ids": [],
            "preferences": {"theme": "light", "language": "vi"},
        })

        token = generate_verification_token(user["email"])
        send_verification_email(user["email"], token)

        user.pop("password_hash", None)
        return {"user": user, "message": "Registration successful. Please verify your email."}, 201

    def login(self, email, password):
        user = user_repo.find_by_email(email)
        if not user or not verify_password(password, user["password_hash"]):
            return {"error": "Invalid email or password"}, 401
        if not user.get("is_active", True):
            return {"error": "Account is deactivated"}, 403

        user.pop("password_hash", None)
        return {"user": user}, 200

    def verify_email(self, token):
        email = verify_token(token, "email-verify", max_age=86400)
        if not email:
            return {"error": "Invalid or expired token"}, 400
        user = user_repo.find_by_email(email)
        if not user:
            return {"error": "User not found"}, 404
        user_repo.update(user["id"], {"is_verified": True})
        return {"message": "Email verified successfully"}, 200

    def forgot_password(self, email):
        user = user_repo.find_by_email(email)
        if not user:
            return {"message": "If email exists, reset link has been sent"}, 200
        token = generate_verification_token(email)
        send_password_reset_email(email, token)
        return {"message": "If email exists, reset link has been sent"}, 200

    def reset_password(self, token, new_password):
        email = verify_token(token, "email-verify", max_age=3600)
        if not email:
            return {"error": "Invalid or expired token"}, 400
        user = user_repo.find_by_email(email)
        if not user:
            return {"error": "User not found"}, 404
        user_repo.update(user["id"], {"password_hash": hash_password(new_password)})
        return {"message": "Password reset successful"}, 200

    def update_profile(self, user_id, data):
        allowed = {"full_name", "phone", "avatar_url"}
        updates = {k: v.strip() if isinstance(v, str) else v for k, v in data.items() if k in allowed and v is not None}
        if not updates:
            return {"error": "Không có thông tin hợp lệ để cập nhật"}, 400
        if "full_name" in updates and not updates["full_name"]:
            return {"error": "Họ tên không được để trống"}, 400
        user_repo.update(user_id, updates)
        user = user_repo.find_by_id(user_id)
        if not user:
            return {"error": "User not found"}, 404
        user.pop("password_hash", None)
        return {"user": user, "message": "Cập nhật thông tin thành công"}, 200

    def change_password(self, user_id, current_password, new_password):
        user = user_repo.find_by_id(user_id)
        if not user:
            return {"error": "User not found"}, 404
        if not verify_password(current_password, user["password_hash"]):
            return {"error": "Mật khẩu hiện tại không đúng"}, 400
        if not new_password or len(new_password) < 6:
            return {"error": "Mật khẩu mới phải có ít nhất 6 ký tự"}, 400
        user_repo.update(user_id, {"password_hash": hash_password(new_password)})
        return {"message": "Đổi mật khẩu thành công"}, 200
