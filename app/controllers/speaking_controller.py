"""Speaking and writing evaluation API."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.repositories.lms_repo import SpeakingRepository, WritingRepository
from app.services.ai_service import AIService
from app.utils.cloudinary_utils import upload_audio
from app.middleware.auth_middleware import teacher_required

speaking_bp = Blueprint("speaking", __name__, url_prefix="/api/speaking")
writing_bp = Blueprint("writing", __name__, url_prefix="/api/writing")
speaking_repo = SpeakingRepository()
writing_repo = WritingRepository()
ai_service = AIService()


@speaking_bp.route("/submit", methods=["POST"])
@jwt_required()
def submit_speaking():
    student_id = get_jwt_identity()
    audio_file = request.files.get("audio")
    data = request.form.to_dict()

    audio_url = ""
    if audio_file:
        result = upload_audio(audio_file)
        audio_url = result.get("secure_url", "")

    transcript = data.get("transcript", "")
    ai_eval = {}
    if transcript:
        ai_eval = ai_service.generate("speaking_evaluation", {"content": transcript})

    record = speaking_repo.create({
        "student_id": student_id,
        "exam_id": data.get("exam_id", ""),
        "assignment_id": data.get("assignment_id", ""),
        "audio_url": audio_url,
        "transcript": transcript,
        "ai_evaluation": ai_eval.get("response", ""),
        "teacher_feedback": "",
        "pronunciation_score": 0,
        "fluency_score": 0,
        "vocabulary_score": 0,
    })
    return jsonify(record), 201


@speaking_bp.route("/records", methods=["GET"])
@jwt_required()
def list_speaking():
    student_id = request.args.get("student_id") or get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    return jsonify(speaking_repo.find_all({"student_id": student_id}, page=page)), 200


@speaking_bp.route("/records/<record_id>/feedback", methods=["PUT"])
@teacher_required
def speaking_feedback(record_id, current_user):
    data = request.get_json(silent=True) or {}
    updated = speaking_repo.update(record_id, {
        "teacher_feedback": data.get("teacher_feedback", ""),
        "pronunciation_score": data.get("pronunciation_score", 0),
        "fluency_score": data.get("fluency_score", 0),
        "vocabulary_score": data.get("vocabulary_score", 0),
    })
    if not updated:
        return jsonify({"error": "Record not found"}), 404
    return jsonify(updated), 200


@writing_bp.route("/submit", methods=["POST"])
@jwt_required()
def submit_writing():
    student_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return jsonify({"error": "content is required"}), 400

    ai_eval = ai_service.generate("writing_evaluation", {"content": content})

    record = writing_repo.create({
        "student_id": student_id,
        "exam_id": data.get("exam_id", ""),
        "assignment_id": data.get("assignment_id", ""),
        "content": content,
        "ai_evaluation": ai_eval.get("response", ""),
        "teacher_feedback": "",
        "rubric_scores": {},
        "final_score": 0,
    })
    return jsonify(record), 201


@writing_bp.route("/records", methods=["GET"])
@jwt_required()
def list_writing():
    student_id = request.args.get("student_id") or get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    return jsonify(writing_repo.find_all({"student_id": student_id}, page=page)), 200


@writing_bp.route("/records/<record_id>/grade", methods=["PUT"])
@teacher_required
def grade_writing(record_id, current_user):
    data = request.get_json(silent=True) or {}
    updated = writing_repo.update(record_id, {
        "teacher_feedback": data.get("teacher_feedback", ""),
        "rubric_scores": data.get("rubric_scores", {}),
        "final_score": data.get("final_score", 0),
    })
    if not updated:
        return jsonify({"error": "Record not found"}), 404
    return jsonify(updated), 200
