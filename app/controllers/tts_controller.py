"""Text-to-speech API — generate MP3 + history."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.dto.schemas import TtsGenerateSchema, validate_request
from app.services.tts_service import TtsService, MAX_CHARS

tts_bp = Blueprint("tts", __name__, url_prefix="/api/tts")
service = TtsService()


@tts_bp.route("/voices", methods=["GET"])
def voices():
    return jsonify({"voices": service.voices(), "max_chars": MAX_CHARS}), 200


@tts_bp.route("/generate", methods=["POST"])
@jwt_required()
@validate_request(TtsGenerateSchema)
def generate(validated_data):
    user_id = get_jwt_identity()
    result, status = service.generate(
        user_id,
        validated_data.get("text", ""),
        validated_data.get("voice", "en-US"),
        validated_data.get("slow", False),
    )
    return jsonify(result), status


@tts_bp.route("/history", methods=["GET"])
@jwt_required()
def history():
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    result, status = service.history(user_id, page=page)
    return jsonify(result), status


@tts_bp.route("/<item_id>", methods=["DELETE"])
@jwt_required()
def delete_item(item_id):
    user_id = get_jwt_identity()
    result, status = service.delete(user_id, item_id)
    return jsonify(result), status
