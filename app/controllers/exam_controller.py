"""Examination API controller."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.exam_service import ExamService, create_question_set
from app.repositories.exam_repo import QuestionRepository
from app.repositories.question_set_repo import QuestionSetRepository
from app.dto.schemas import validate_request, ExamCreateSchema, QuestionCreateSchema, QuestionSetCreateSchema
from app.middleware.auth_middleware import teacher_required

exam_bp = Blueprint("exams", __name__, url_prefix="/api/exams")
exam_service = ExamService()
question_repo = QuestionRepository()
set_repo = QuestionSetRepository()


@exam_bp.route("", methods=["GET"])
@jwt_required()
def list_exams():
    class_id = request.args.get("class_id")
    page = request.args.get("page", 1, type=int)
    if not class_id:
        return jsonify({"error": "class_id is required"}), 400
    result = exam_service.list_by_class(class_id, page=page)
    return jsonify(result), 200


@exam_bp.route("", methods=["POST"])
@teacher_required
@validate_request(ExamCreateSchema)
def create_exam(validated_data, current_user):
    result, status = exam_service.create_exam(current_user["id"], validated_data)
    return jsonify(result), status


@exam_bp.route("/<exam_id>", methods=["GET"])
@jwt_required()
def get_exam(exam_id):
    from app.repositories.user_repo import UserRepository
    user = UserRepository().find_by_id(get_jwt_identity())
    include_answers = user and user.get("role") in ("teacher", "super_admin")
    result, status = exam_service.get_exam(exam_id, include_answers=include_answers)
    return jsonify(result), status


@exam_bp.route("/<exam_id>/submit", methods=["POST"])
@jwt_required()
def submit_exam(exam_id):
    student_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    answers = data.get("answers", [])
    result, status = exam_service.submit_exam(student_id, exam_id, answers)
    return jsonify(result), status


@exam_bp.route("/<exam_id>/results", methods=["GET"])
@teacher_required
def get_results(exam_id, current_user):
    result = exam_service.get_class_results(exam_id)
    return jsonify(result), 200


@exam_bp.route("/results/<result_id>/grade", methods=["PUT"])
@teacher_required
def grade_result(result_id, current_user):
    data = request.get_json(silent=True) or {}
    result, status = exam_service.grade_result(result_id, data)
    return jsonify(result), status


@exam_bp.route("/<exam_id>/my-result", methods=["GET"])
@jwt_required()
def my_exam_result(exam_id):
    student_id = get_jwt_identity()
    result, status = exam_service.get_my_exam_result(student_id, exam_id)
    return jsonify(result), status


@exam_bp.route("/my-results", methods=["GET"])
@jwt_required()
def my_results():
    student_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    result = exam_service.get_student_results(student_id, page=page)
    return jsonify(result), 200


@exam_bp.route("/questions", methods=["POST"])
@teacher_required
@validate_request(QuestionCreateSchema)
def create_question(validated_data, current_user):
    manual_types = {
        "rewrite", "essay", "letter", "image_description", "open_ended",
        "read_aloud", "speaking_topic", "image_speaking",
    }
    if validated_data.get("type") not in manual_types and validated_data.get("correct_answer") is None:
        return jsonify({"error": "correct_answer is required for auto-graded questions"}), 400
    validated_data["created_by"] = current_user["id"]
    result = question_repo.create(validated_data)
    return jsonify(result), 201


@exam_bp.route("/question-sets", methods=["POST"])
@teacher_required
@validate_request(QuestionSetCreateSchema)
def create_question_set_endpoint(validated_data, current_user):
    if not validated_data.get("questions"):
        return jsonify({"error": "At least one sub-question is required"}), 400
    result = create_question_set(current_user["id"], validated_data)
    return jsonify(result), 201


@exam_bp.route("/question-sets", methods=["GET"])
@jwt_required()
def list_question_sets():
    filters = {
        "skill": request.args.get("skill"),
        "grade": request.args.get("grade"),
        "difficulty": request.args.get("difficulty"),
        "topic": request.args.get("topic"),
        "search": request.args.get("search"),
    }
    page = request.args.get("page", 1, type=int)
    result = set_repo.find_by_filters(filters, page=page)
    return jsonify(result), 200


@exam_bp.route("/question-sets/<set_id>", methods=["GET"])
@jwt_required()
def get_question_set(set_id):
    qset = set_repo.find_by_id(set_id)
    if not qset:
        return jsonify({"error": "Question set not found"}), 404
    return jsonify(qset), 200


@exam_bp.route("/questions", methods=["GET"])
@jwt_required()
def list_questions():
    filters = {
        "category": request.args.get("category"),
        "skill": request.args.get("skill"),
        "grade": request.args.get("grade"),
        "difficulty": request.args.get("difficulty"),
        "type": request.args.get("type"),
        "search": request.args.get("search"),
    }
    page = request.args.get("page", 1, type=int)
    result = question_repo.find_by_filters(filters, page=page)
    return jsonify(result), 200
