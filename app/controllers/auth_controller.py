"""Authentication API controller."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app.services.auth_service import AuthService
from app.dto.schemas import validate_request, RegisterSchema, LoginSchema

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
auth_service = AuthService()


@auth_bp.route("/register", methods=["POST"])
@validate_request(RegisterSchema)
def register(validated_data):
    result, status = auth_service.register(validated_data)
    if status == 201:
        access = create_access_token(identity=result["user"]["id"])
        refresh = create_refresh_token(identity=result["user"]["id"])
        result["access_token"] = access
        result["refresh_token"] = refresh
    return jsonify(result), status


@auth_bp.route("/login", methods=["POST"])
@validate_request(LoginSchema)
def login(validated_data):
    result, status = auth_service.login(validated_data["email"], validated_data["password"])
    if status == 200:
        access = create_access_token(identity=result["user"]["id"])
        refresh = create_refresh_token(identity=result["user"]["id"])
        result["access_token"] = access
        result["refresh_token"] = refresh
    return jsonify(result), status


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    return jsonify({"access_token": create_access_token(identity=identity)}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    from app.repositories.user_repo import UserRepository
    user = UserRepository().find_by_id(get_jwt_identity())
    if user:
        user.pop("password_hash", None)
    return jsonify({"user": user}), 200


@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_me():
    user_id = get_jwt_identity()
    result, status = auth_service.update_profile(user_id, request.json or {})
    return jsonify(result), status


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    body = request.json or {}
    result, status = auth_service.change_password(
        user_id,
        body.get("current_password", ""),
        body.get("new_password", ""),
    )
    return jsonify(result), status


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    token = request.json.get("token")
    result, status = auth_service.verify_email(token)
    return jsonify(result), status


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    email = request.json.get("email")
    result, status = auth_service.forgot_password(email)
    return jsonify(result), status


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    token = request.json.get("token")
    password = request.json.get("password")
    result, status = auth_service.reset_password(token, password)
    return jsonify(result), status
