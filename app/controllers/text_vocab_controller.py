"""Text vocabulary lab — analyze passage & generate practice."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.dto.schemas import TextVocabAnalyzeSchema, TextVocabPracticeSchema, TextVocabFeedbackSchema, validate_request
from app.services.text_vocab_service import TextVocabService, PRACTICE_MODES

text_vocab_bp = Blueprint("text_vocab", __name__, url_prefix="/api/text-vocab")
service = TextVocabService()


@text_vocab_bp.route("/levels", methods=["GET"])
def levels():
    return jsonify({
        "levels": [
            {"value": "A1", "label": "A1 — Sơ cấp"},
            {"value": "A2", "label": "A2 — Cơ bản"},
            {"value": "B1", "label": "B1 — Trung cấp (≈ lớp 10)"},
            {"value": "B2", "label": "B2 — Khá (≈ lớp 11)"},
            {"value": "C1", "label": "C1 — Nâng cao (≈ lớp 12)"},
            {"value": "C2", "label": "C2 — Thành thạo"},
        ],
        "practice_modes": list(PRACTICE_MODES),
    }), 200


@text_vocab_bp.route("/analyze", methods=["POST"])
@jwt_required()
@validate_request(TextVocabAnalyzeSchema)
def analyze(validated_data):
    result, status = service.analyze(
        validated_data.get("content", ""),
        validated_data.get("level", "B1"),
        validated_data.get("provider", "gemini"),
    )
    return jsonify(result), status


@text_vocab_bp.route("/practice", methods=["POST"])
@jwt_required()
@validate_request(TextVocabPracticeSchema)
def practice(validated_data):
    result, status = service.practice(
        validated_data.get("content", ""),
        validated_data.get("level", "B1"),
        validated_data.get("mode", "fill_gaps"),
        validated_data.get("words") or [],
        validated_data.get("provider", "gemini"),
    )
    return jsonify(result), status


@text_vocab_bp.route("/discussion-feedback", methods=["POST"])
@jwt_required()
@validate_request(TextVocabFeedbackSchema)
def discussion_feedback(validated_data):
    result, status = service.discussion_feedback(
        validated_data.get("content", ""),
        validated_data.get("level", "B1"),
        validated_data.get("question", ""),
        validated_data.get("answer", ""),
        validated_data.get("provider", "gemini"),
    )
    return jsonify(result), status