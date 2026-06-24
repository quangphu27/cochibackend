"""AI tools API controller."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.ai_service import AIService
from app.dto.schemas import validate_request, AIGenerateSchema
from app.repositories.base import BaseRepository
from app.models.collections import COLLECTIONS

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")
ai_service = AIService()


class AIHistoryRepo(BaseRepository):
    collection_name = COLLECTIONS["ai_history"]


history_repo = AIHistoryRepo()


@ai_bp.route("/generate", methods=["POST"])
@jwt_required()
@validate_request(AIGenerateSchema)
def generate(validated_data):
    user_id = get_jwt_identity()
    result = ai_service.generate(
        validated_data["tool_type"],
        validated_data.get("params", {}),
        validated_data.get("provider", "openai"),
    )

    history_repo.create({
        "user_id": user_id,
        "tool_type": validated_data["tool_type"],
        "prompt": str(validated_data.get("params", {})),
        "response": result.get("response", ""),
        "provider": result.get("provider", ""),
        "tokens_used": result.get("tokens_used", 0),
    })

    return jsonify(result), 200


@ai_bp.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    result = history_repo.find_all({"user_id": user_id}, page=page, sort=[("created_at", -1)])
    return jsonify(result), 200


@ai_bp.route("/tools", methods=["GET"])
def list_tools():
    from app.services.ai_service import AI_TOOLS
    tools = [
        {"id": k, "name": k.replace("_", " ").title(), "description": v[:80]}
        for k, v in AI_TOOLS.items()
    ]
    return jsonify({"tools": tools}), 200
