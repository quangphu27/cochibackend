"""Password hashing and JWT utilities."""
import bcrypt
import secrets
import string
from itsdangerous import URLSafeTimedSerializer
from flask import current_app


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def generate_class_code(length=6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_verification_token(email: str) -> str:
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(email, salt="email-verify")


def verify_token(token: str, salt: str, max_age=3600) -> str | None:
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        return serializer.loads(token, salt=salt, max_age=max_age)
    except Exception:
        return None
