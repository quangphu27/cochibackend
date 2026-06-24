"""LMS API - assignments, attendance, announcements."""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.middleware.auth_middleware import teacher_required
from app.repositories.lms_repo import (
    AssignmentRepository, SubmissionRepository,
    AttendanceRepository, AnnouncementRepository,
)
from app.repositories.content_repo import NotificationRepository
from app.repositories.class_repo import ClassRepository
from app.repositories.user_repo import UserRepository

lms_bp = Blueprint("lms", __name__, url_prefix="/api/lms")
assignment_repo = AssignmentRepository()
submission_repo = SubmissionRepository()
attendance_repo = AttendanceRepository()
announcement_repo = AnnouncementRepository()
notification_repo = NotificationRepository()
class_repo = ClassRepository()
user_repo = UserRepository()


def _teacher_owns_assignment(assignment_id, user_id, role):
    assignment = assignment_repo.find_by_id(assignment_id)
    if not assignment:
        return None, ({"error": "Assignment not found"}, 404)
    cls = class_repo.find_by_id(assignment.get("class_id", ""))
    if not cls:
        return None, ({"error": "Class not found"}, 404)
    if role != "super_admin" and cls.get("teacher_id") != user_id:
        return None, ({"error": "Insufficient permissions"}, 403)
    return assignment, None


@lms_bp.route("/assignments", methods=["GET"])
@jwt_required()
def list_assignments():
    class_id = request.args.get("class_id")
    if not class_id:
        return jsonify({"error": "class_id is required"}), 400
    page = request.args.get("page", 1, type=int)
    return jsonify(assignment_repo.find_by_class(class_id, page=page)), 200


@lms_bp.route("/assignments", methods=["POST"])
@teacher_required
def create_assignment(current_user):
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("class_id"):
        return jsonify({"error": "title and class_id are required"}), 400
    assignment = assignment_repo.create({
        "class_id": data["class_id"],
        "title": data["title"],
        "description": data.get("description", ""),
        "type": data.get("type", "homework"),
        "due_date": data.get("due_date"),
        "max_score": data.get("max_score", 10),
        "question_ids": data.get("question_ids", []),
        "question_set_ids": data.get("question_set_ids", []),
        "attachments": data.get("attachments", []),
        "rubric": data.get("rubric", {}),
        "created_by": current_user["id"],
    })
    cls = class_repo.find_by_id(data["class_id"])
    if cls:
        for sid in cls.get("student_ids", []):
            notification_repo.create({
                "user_id": sid,
                "title": "Bài tập mới",
                "message": data["title"],
                "type": "assignment",
                "read": False,
                "link": f"/classes/{data['class_id']}",
            })
    return jsonify(assignment), 201


@lms_bp.route("/assignments/<assignment_id>", methods=["GET"])
@jwt_required()
def get_assignment(assignment_id):
    from app.utils.question_resolver import resolve_question_refs, SET_PREFIX
    assignment = assignment_repo.find_by_id(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    user = user_repo.find_by_id(get_jwt_identity())
    include_answers = user and user.get("role") in ("teacher", "super_admin")
    refs = list(assignment.get("question_ids") or [])
    for sid in assignment.get("question_set_ids") or []:
        refs.append(f"{SET_PREFIX}{sid}")
    question_details = resolve_question_refs(refs)
    if not include_answers:
        for q in question_details:
            q.pop("correct_answer", None)
            q.pop("explanation", None)
            q.pop("alternative_answers", None)
    assignment["question_details"] = question_details
    return jsonify(assignment), 200


@lms_bp.route("/assignments/<assignment_id>", methods=["PUT"])
@teacher_required
def update_assignment(assignment_id, current_user):
    _, err = _teacher_owns_assignment(assignment_id, current_user["id"], current_user.get("role", "teacher"))
    if err:
        return jsonify(err[0]), err[1]

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    update_fields = {}
    for key in (
        "title", "description", "type", "due_date", "max_score",
        "question_ids", "question_set_ids", "attachments", "rubric",
    ):
        if key in data:
            update_fields[key] = data[key]

    updated = assignment_repo.update(assignment_id, update_fields)
    return jsonify(updated), 200


@lms_bp.route("/assignments/<assignment_id>", methods=["DELETE"])
@teacher_required
def delete_assignment(assignment_id, current_user):
    _, err = _teacher_owns_assignment(assignment_id, current_user["id"], current_user.get("role", "teacher"))
    if err:
        return jsonify(err[0]), err[1]

    submission_repo.delete_by_assignment(assignment_id)
    assignment_repo.delete(assignment_id)
    return jsonify({"message": "Assignment deleted"}), 200


@lms_bp.route("/assignments/<assignment_id>/submit", methods=["POST"])
@jwt_required()
def submit_assignment(assignment_id):
    from app.utils.grading import grade_question, MANUAL_TYPES
    from app.utils.question_resolver import resolve_question_refs, SET_PREFIX
    student_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    assignment = assignment_repo.find_by_id(assignment_id)
    existing = submission_repo.find_by_student_assignment(assignment_id, student_id)
    payload = {
        "content": data.get("content", ""),
        "attachments": data.get("attachments", []),
        "status": "submitted",
        "submitted_at": datetime.utcnow(),
    }

    answers = data.get("answers", [])
    if answers and assignment:
        refs = list(assignment.get("question_ids") or [])
        for sid in assignment.get("question_set_ids") or []:
            refs.append(f"{SET_PREFIX}{sid}")
        all_questions = {q["id"]: q for q in resolve_question_refs(refs)}
        graded = []
        auto_score = 0.0
        max_score = 0.0
        has_manual = False
        for ans in answers:
            qid = ans.get("question_id")
            q = all_questions.get(qid)
            if not q:
                continue
            points = q.get("points", 1)
            max_score += points
            qtype = q.get("type", "mcq")
            if qtype in MANUAL_TYPES:
                has_manual = True
                graded.append({"question_id": qid, "answer": ans.get("answer"), "score": None, "max": points})
                continue
            ratio = grade_question(qtype, ans.get("answer"), q.get("correct_answer"), q)
            earned = (ratio or 0) * points
            auto_score += earned
            graded.append({"question_id": qid, "answer": ans.get("answer"), "score": earned, "max": points})
        payload["answers"] = graded
        payload["auto_score"] = auto_score
        payload["max_score"] = max_score
        if max_score > 0 and not has_manual and not data.get("content"):
            payload["status"] = "graded"
            payload["score"] = round(auto_score / max_score * (assignment.get("max_score", 10)), 2)
            payload["graded_at"] = datetime.utcnow()

    if existing:
        submission = submission_repo.update(existing["id"], payload)
    else:
        submission = submission_repo.create({
            "assignment_id": assignment_id,
            "student_id": student_id,
            **payload,
        })
    return jsonify(submission), 200


@lms_bp.route("/assignments/<assignment_id>/submissions", methods=["GET"])
@teacher_required
def list_submissions(assignment_id, current_user):
    _, err = _teacher_owns_assignment(assignment_id, current_user["id"], current_user.get("role", "teacher"))
    if err:
        return jsonify(err[0]), err[1]
    result = submission_repo.find_by_assignment(assignment_id)
    for s in result.get("data", []):
        student = user_repo.find_by_id(s.get("student_id", ""))
        if student:
            s["student_name"] = student.get("full_name", "")
            s["student_email"] = student.get("email", "")
    return jsonify(result), 200


@lms_bp.route("/assignments/<assignment_id>/my-submission", methods=["GET"])
@jwt_required()
def my_submission(assignment_id):
    student_id = get_jwt_identity()
    submission = submission_repo.find_by_student_assignment(assignment_id, student_id)
    return jsonify(submission or {}), 200


@lms_bp.route("/my-submissions", methods=["GET"])
@jwt_required()
def my_submissions():
    student_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    result = submission_repo.find_by_student(student_id, page=page)
    for s in result.get("data", []):
        assignment = assignment_repo.find_by_id(s.get("assignment_id", ""))
        if not assignment:
            continue
        s["assignment_title"] = assignment.get("title", "")
        s["class_id"] = assignment.get("class_id", "")
        s["max_score"] = assignment.get("max_score", 10)
        cls = class_repo.find_by_id(assignment.get("class_id", ""))
        if cls:
            s["class_name"] = cls.get("name", "")
    return jsonify(result), 200


@lms_bp.route("/submissions/<submission_id>/grade", methods=["PUT"])
@teacher_required
def grade_submission(submission_id, current_user):
    submission = submission_repo.find_by_id(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    _, err = _teacher_owns_assignment(submission["assignment_id"], current_user["id"], current_user.get("role", "teacher"))
    if err:
        return jsonify(err[0]), err[1]

    data = request.get_json(silent=True) or {}
    score = data.get("score")
    if score is None:
        return jsonify({"error": "score is required"}), 400

    updated = submission_repo.update(submission_id, {
        "score": float(score),
        "feedback": data.get("feedback", ""),
        "status": "graded",
        "graded_at": datetime.utcnow(),
    })
    assignment = assignment_repo.find_by_id(submission["assignment_id"])
    class_id = assignment.get("class_id", "") if assignment else ""
    notification_repo.create({
        "user_id": submission["student_id"],
        "title": "Bài tập đã được chấm điểm",
        "message": f"Điểm: {score}",
        "type": "assignment",
        "read": False,
        "link": f"/classes/{class_id}" if class_id else "",
    })
    return jsonify(updated), 200


@lms_bp.route("/attendance", methods=["GET"])
@jwt_required()
def list_attendance():
    class_id = request.args.get("class_id")
    if not class_id:
        return jsonify({"error": "class_id is required"}), 400
    page = request.args.get("page", 1, type=int)
    return jsonify(attendance_repo.find_by_class(class_id, page=page)), 200


@lms_bp.route("/attendance", methods=["POST"])
@teacher_required
def create_attendance(current_user):
    data = request.get_json(silent=True) or {}
    if not data.get("class_id"):
        return jsonify({"error": "class_id is required"}), 400
    record = attendance_repo.create({
        "class_id": data["class_id"],
        "date": data.get("date", datetime.utcnow().isoformat()),
        "records": data.get("records", []),
        "created_by": current_user["id"],
    })
    return jsonify(record), 201


@lms_bp.route("/announcements", methods=["GET"])
@jwt_required()
def list_announcements():
    class_id = request.args.get("class_id")
    if not class_id:
        return jsonify({"error": "class_id is required"}), 400
    page = request.args.get("page", 1, type=int)
    return jsonify(announcement_repo.find_by_class(class_id, page=page)), 200


@lms_bp.route("/announcements", methods=["POST"])
@teacher_required
def create_announcement(current_user):
    data = request.get_json(silent=True) or {}
    if not data.get("class_id") or not data.get("title"):
        return jsonify({"error": "class_id and title are required"}), 400
    announcement = announcement_repo.create({
        "class_id": data["class_id"],
        "title": data["title"],
        "content": data.get("content", ""),
        "created_by": current_user["id"],
    })
    from app.repositories.class_repo import ClassRepository
    cls = ClassRepository().find_by_id(data["class_id"])
    if cls:
        for sid in cls.get("student_ids", []):
            notification_repo.create({
                "user_id": sid,
                "title": data["title"],
                "message": data.get("content", "")[:100],
                "type": "announcement",
                "read": False,
                "link": f"/classes/{data['class_id']}",
            })
    return jsonify(announcement), 201
