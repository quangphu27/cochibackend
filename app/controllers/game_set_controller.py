"""Interactive game sets — save / list / update / delete."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.dto.schemas import GameSetUpsertSchema, validate_request
from app.services.game_set_service import GameSetService, VALID_TYPES

game_sets_bp = Blueprint("game_sets", __name__, url_prefix="/api/game-sets")
service = GameSetService()


@game_sets_bp.route("", methods=["GET"])
@jwt_required()
def list_sets():
    user_id = get_jwt_identity()
    game_type = request.args.get("type")
    if game_type and game_type not in VALID_TYPES:
        return jsonify({"error": "Loại trò chơi không hợp lệ"}), 400
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    result, status = service.list(user_id, game_type=game_type, page=page, limit=limit)
    return jsonify(result), status


@game_sets_bp.route("/<item_id>", methods=["GET"])
@jwt_required()
def get_set(item_id):
    user_id = get_jwt_identity()
    result, status = service.get(user_id, item_id)
    return jsonify(result), status


@game_sets_bp.route("", methods=["POST"])
@jwt_required()
@validate_request(GameSetUpsertSchema)
def create_set(validated_data):
    user_id = get_jwt_identity()
    result, status = service.create(user_id, validated_data)
    return jsonify(result), status


@game_sets_bp.route("/<item_id>", methods=["PUT"])
@jwt_required()
@validate_request(GameSetUpsertSchema)
def update_set(item_id, validated_data):
    user_id = get_jwt_identity()
    result, status = service.update(user_id, item_id, validated_data)
    return jsonify(result), status


@game_sets_bp.route("/<item_id>", methods=["DELETE"])
@jwt_required()
def delete_set(item_id):
    user_id = get_jwt_identity()
    result, status = service.delete(user_id, item_id)
    return jsonify(result), status
