"""Examination and grading service."""
from datetime import datetime
from app.repositories.exam_repo import ExamRepository, QuestionRepository, ResultRepository
from app.repositories.question_set_repo import QuestionSetRepository
from app.repositories.user_repo import UserRepository
from app.utils.grading import grade_exam
from app.utils.question_resolver import resolve_question_refs, ensure_sub_question_ids, SET_PREFIX

exam_repo = ExamRepository()
question_repo = QuestionRepository()
set_repo = QuestionSetRepository()
result_repo = ResultRepository()
user_repo = UserRepository()


class ExamService:
    def _build_question_refs(self, data):
        refs = list(data.get("question_ids") or [])
        for sid in data.get("question_set_ids") or []:
            refs.append(f"{SET_PREFIX}{sid}")
        return refs

    def _calc_total_points(self, questions):
        if not questions:
            return 0
        return sum(q.get("points", 1) for q in questions)

    def create_exam(self, teacher_id, data):
        refs = self._build_question_refs(data)
        resolved = resolve_question_refs(refs)
        total_points = self._calc_total_points(resolved)

        exam = exam_repo.create({
            "title": data["title"],
            "description": data.get("description", ""),
            "class_id": data["class_id"],
            "type": data.get("type", "mixed"),
            "skills": data.get("skills", []),
            "questions": refs,
            "duration_minutes": data.get("duration_minutes", 45),
            "total_points": total_points,
            "shuffle_questions": data.get("shuffle_questions", True),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "created_by": teacher_id,
        })
        return exam, 201

    def get_exam(self, exam_id, include_answers=False):
        exam = exam_repo.find_by_id(exam_id)
        if not exam:
            return {"error": "Exam not found"}, 404
        questions = resolve_question_refs(exam.get("questions", []))
        if not include_answers:
            for q in questions:
                q.pop("correct_answer", None)
                q.pop("explanation", None)
                q.pop("alternative_answers", None)
        exam["question_details"] = questions
        return exam, 200

    def list_by_class(self, class_id, page=1):
        return exam_repo.find_by_class(class_id, page=page)

    def submit_exam(self, student_id, exam_id, answers):
        exam = exam_repo.find_by_id(exam_id)
        if not exam:
            return {"error": "Exam not found"}, 404

        existing = result_repo.find_one({"exam_id": exam_id, "student_id": student_id})
        if existing:
            return {"error": "Already submitted", "result": existing}, 409

        questions = resolve_question_refs(exam.get("questions", []))
        grading = grade_exam(questions, answers)

        result = result_repo.create({
            "exam_id": exam_id,
            "student_id": student_id,
            "answers": answers,
            "auto_score": grading["auto_score"],
            "teacher_score": None,
            "final_score": grading["auto_score"],
            "skill_scores": grading["skill_scores"],
            "grading": grading,
            "feedback": "",
            "status": "graded" if not any(r.get("needs_manual") for r in grading["results"]) else "partial",
            "submitted_at": datetime.utcnow(),
        })

        return {"result": result, "grading": grading}, 200

    def grade_result(self, result_id, data):
        result = result_repo.find_by_id(result_id)
        if not result:
            return {"error": "Result not found"}, 404

        teacher_score = data.get("teacher_score")
        feedback = data.get("feedback", "")
        final = teacher_score if teacher_score is not None else result.get("auto_score", 0)

        updated = result_repo.update(result_id, {
            "teacher_score": teacher_score,
            "final_score": final,
            "feedback": feedback,
            "status": "graded",
            "graded_at": datetime.utcnow(),
        })
        return updated, 200

    def get_class_results(self, exam_id):
        result = result_repo.find_by_exam(exam_id)
        exam = exam_repo.find_by_id(exam_id)
        questions = resolve_question_refs(exam.get("questions", [])) if exam else []
        for item in result.get("data", []):
            student = user_repo.find_by_id(item.get("student_id", ""))
            if student:
                item["student_name"] = student.get("full_name", "")
                item["student_email"] = student.get("email", "")
            if not item.get("grading") and questions:
                item["grading"] = grade_exam(questions, item.get("answers", []))
        return result

    def get_my_exam_result(self, student_id, exam_id):
        result = result_repo.find_one({"exam_id": exam_id, "student_id": student_id})
        if not result:
            return {}, 200
        exam = exam_repo.find_by_id(exam_id)
        if not exam:
            return {"error": "Exam not found"}, 404
        questions = resolve_question_refs(exam.get("questions", []))
        grading = result.get("grading") or grade_exam(questions, result.get("answers", []))
        safe_questions = []
        for q in questions:
            safe = {k: v for k, v in q.items() if k not in ("correct_answer", "alternative_answers", "explanation")}
            safe_questions.append(safe)
        return {
            "result": result,
            "grading": grading,
            "question_details": safe_questions,
        }, 200

    def get_student_results(self, student_id, page=1):
        result = result_repo.find_by_student(student_id, page=page)
        for item in result.get("data", []):
            exam = exam_repo.find_by_id(item.get("exam_id", ""))
            if exam:
                item["exam_title"] = exam.get("title", "")
                item["class_id"] = exam.get("class_id", "")
                item["max_score"] = exam.get("total_points", 10)
        return result


def create_question_set(teacher_id, data):
    questions = ensure_sub_question_ids(data.get("questions", []))
    payload = {
        "title": data["title"],
        "passage": data.get("passage", ""),
        "instructions": data.get("instructions", ""),
        "skill": data.get("skill", ""),
        "grade": data.get("grade", ""),
        "topic": data.get("topic", ""),
        "difficulty": data.get("difficulty", "medium"),
        "tags": data.get("tags", []),
        "image_url": data.get("image_url", ""),
        "audio_url": data.get("audio_url", ""),
        "video_url": data.get("video_url", ""),
        "time_limit": data.get("time_limit"),
        "subtitles": data.get("subtitles") or [],
        "content_type": data.get("content_type", ""),
        "questions": questions,
        "created_by": teacher_id,
    }
    return set_repo.create(payload)
