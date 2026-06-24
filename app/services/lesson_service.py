"""Lesson builder service — CRUD, grading, progress, AI."""
import uuid
from datetime import datetime
from app.repositories.lesson_repo import LessonRepository, LessonProgressRepository
from app.repositories.class_repo import ClassRepository
from app.repositories.user_repo import UserRepository
from app.repositories.content_repo import NotificationRepository
from app.utils.grading import grade_question
from app.services.ai_service import AIService

lesson_repo = LessonRepository()
progress_repo = LessonProgressRepository()
class_repo = ClassRepository()
user_repo = UserRepository()
notification_repo = NotificationRepository()
ai_service = AIService()

BLOCK_TYPES = {
    "text", "image", "video", "audio", "pdf", "vocabulary", "grammar",
    "exercise", "quiz", "writing", "speaking", "assignment",
}

LESSON_AI_PROMPTS = {
    "text": "Write an English lesson introduction for {grade} on topic '{topic}' skill {skill}. Include headings and clear explanations.",
    "vocabulary": "Generate 5 English vocabulary items for {grade} topic '{topic}'. Format each: Word, IPA, Vietnamese meaning, example sentence.",
    "grammar": "Explain grammar rule for {grade} topic '{topic}'. Include rule, structure, 3 examples, and notes.",
    "exercise": "Create 3 multiple choice English questions for {grade} {skill} on '{topic}'. Include options A-D, correct answer, explanation.",
    "quiz": "Create 5 quiz questions (mix mcq and true/false) for {grade} {skill} on '{topic}'.",
    "writing": "Create a writing prompt for {grade} on '{topic}' with instructions and 120-150 word limit.",
    "speaking": "Create speaking lesson for {grade} on '{topic}' with 3 discussion questions.",
}


def _new_block_id():
    return str(uuid.uuid4())


def _normalize_blocks(blocks):
    if not blocks:
        return []
    normalized = []
    for i, b in enumerate(blocks):
        normalized.append({
            "id": b.get("id") or _new_block_id(),
            "type": b.get("type", "text"),
            "order": b.get("order", i),
            "title": b.get("title", ""),
            "content": b.get("content") or {},
        })
    normalized.sort(key=lambda x: x["order"])
    return normalized


class LessonService:
    def create_lesson(self, teacher_id, data):
        lesson = lesson_repo.create({
            "title": data["title"],
            "description": data.get("description", ""),
            "grade": data.get("grade", "Grade 10"),
            "skill": data.get("skill", "Grammar"),
            "blocks": _normalize_blocks(data.get("blocks", [])),
            "status": "draft",
            "class_ids": data.get("class_ids", []),
            "created_by": teacher_id,
        })
        return lesson, 201

    def update_lesson(self, lesson_id, teacher_id, role, data):
        lesson, err = self._assert_can_edit(lesson_id, teacher_id, role)
        if err:
            return err

        updates = {"updated_at": datetime.utcnow()}
        for field in ("title", "description", "grade", "skill", "status", "class_ids"):
            if field in data:
                updates[field] = data[field]
        if "blocks" in data:
            updates["blocks"] = _normalize_blocks(data["blocks"])

        updated = lesson_repo.update(lesson_id, updates)
        return updated, 200

    def delete_lesson(self, lesson_id, teacher_id, role):
        lesson, err = self._assert_can_edit(lesson_id, teacher_id, role)
        if err:
            return err
        lesson_repo.delete(lesson_id)
        return {"message": "Đã xóa bài học"}, 200

    def get_lesson(self, lesson_id, user_id, role):
        lesson = lesson_repo.find_by_id(lesson_id)
        if not lesson:
            return {"error": "Không tìm thấy bài học"}, 404

        if role in ("teacher", "super_admin"):
            if role != "super_admin" and lesson.get("created_by") != user_id:
                return {"error": "Không có quyền truy cập"}, 403
        else:
            if lesson.get("status") != "published":
                return {"error": "Bài học chưa được xuất bản"}, 403
            user = user_repo.find_by_id(user_id)
            class_ids = user.get("class_ids", []) if user else []
            lesson_classes = lesson.get("class_ids", [])
            if lesson_classes and not set(lesson_classes) & set(class_ids):
                return {"error": "Bạn không có quyền xem bài học này"}, 403

        return lesson, 200

    def list_lessons(self, user_id, role, page=1, grade=None, skill=None, status=None, class_id=None):
        filters = {}
        if grade:
            filters["grade"] = grade
        if skill:
            filters["skill"] = skill
        if status:
            filters["status"] = status
        if class_id:
            filters["class_ids"] = class_id

        if role in ("teacher", "super_admin"):
            if role == "super_admin" and not status:
                result = lesson_repo.find_all(filters, page=page, sort=[("updated_at", -1)])
            else:
                result = lesson_repo.find_by_teacher(user_id, page=page, **filters)
        else:
            user = user_repo.find_by_id(user_id)
            class_ids = user.get("class_ids", []) if user else []
            filters["status"] = "published"
            result = lesson_repo.find_published_for_classes(class_ids, page=page, **{k: v for k, v in filters.items() if k != "status"})

        return result, 200

    def publish_lesson(self, lesson_id, teacher_id, role, class_ids):
        lesson, err = self._assert_can_edit(lesson_id, teacher_id, role)
        if err:
            return err

        updated = lesson_repo.update(lesson_id, {
            "status": "published",
            "class_ids": class_ids or lesson.get("class_ids", []),
            "published_at": datetime.utcnow(),
        })

        for cid in updated.get("class_ids", []):
            cls = class_repo.find_by_id(cid)
            if not cls:
                continue
            for sid in cls.get("student_ids", []):
                notification_repo.create({
                    "user_id": sid,
                    "title": "Bài học mới",
                    "message": lesson.get("title", ""),
                    "type": "lesson",
                    "read": False,
                    "link": f"/lessons/{lesson_id}/study",
                })

        return updated, 200

    def grade_block(self, lesson_id, user_id, block_id, answers):
        lesson = lesson_repo.find_by_id(lesson_id)
        if not lesson:
            return {"error": "Không tìm thấy bài học"}, 404

        block = next((b for b in lesson.get("blocks", []) if b["id"] == block_id), None)
        if not block:
            return {"error": "Không tìm thấy block"}, 404

        btype = block["type"]
        content = block.get("content", {})
        results = []
        total = 0.0
        max_score = 0.0

        if btype in ("exercise", "quiz"):
            questions = content.get("questions", [])
            for q in questions:
                qid = q.get("id", q.get("question", ""))
                student_ans = answers.get(qid) or answers.get(str(qid))
                points = q.get("points", 1)
                max_score += points
                ratio = grade_question(q.get("type", "mcq"), student_ans, q.get("correct_answer"))
                earned = (ratio or 0) * points
                total += earned
                results.append({
                    "question_id": qid,
                    "correct": ratio == 1.0 if ratio is not None else None,
                    "score": earned,
                    "max": points,
                    "explanation": q.get("explanation", ""),
                })

        elif btype == "writing":
            return {
                "needs_manual": True,
                "message": "Bài viết cần giáo viên hoặc AI chấm",
                "submitted": answers.get("content", ""),
            }, 200

        elif btype == "speaking":
            return {
                "needs_manual": True,
                "message": "Bài nói cần giáo viên chấm",
                "audio_url": answers.get("audio_url", ""),
            }, 200

        else:
            return {"error": "Block không hỗ trợ chấm tự động"}, 400

        percentage = (total / max_score * 100) if max_score > 0 else 0
        passing = content.get("passing_score", 50)
        passed = percentage >= passing if btype == "quiz" else None

        progress = progress_repo.find_by_student_lesson(lesson_id, user_id) or {}
        block_scores = progress.get("block_scores", {})
        block_scores[block_id] = {
            "score": total,
            "max_score": max_score,
            "percentage": round(percentage, 1),
            "passed": passed,
            "graded_at": datetime.utcnow().isoformat(),
        }
        self._save_progress(lesson_id, user_id, lesson, block_scores=block_scores)

        return {
            "results": results,
            "score": total,
            "max_score": max_score,
            "percentage": round(percentage, 1),
            "passed": passed,
        }, 200

    def save_progress(self, lesson_id, user_id, data):
        lesson = lesson_repo.find_by_id(lesson_id)
        if not lesson:
            return {"error": "Không tìm thấy bài học"}, 404

        block_scores = data.get("block_scores")
        progress = self._save_progress(
            lesson_id, user_id, lesson,
            completion_percent=data.get("completion_percent"),
            block_scores=block_scores,
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
        )
        return progress, 200

    def get_progress(self, lesson_id, user_id, role):
        if role in ("teacher", "super_admin"):
            all_progress = progress_repo.find_by_lesson(lesson_id)
            for p in all_progress.get("data", []):
                student = user_repo.find_by_id(p.get("student_id", ""))
                if student:
                    p["student_name"] = student.get("full_name", "")
            return all_progress, 200

        progress = progress_repo.find_by_student_lesson(lesson_id, user_id)
        return progress or {}, 200

    def lesson_analytics(self, teacher_id, role):
        if role not in ("teacher", "super_admin"):
            return {"error": "Không có quyền"}, 403

        query = {} if role == "super_admin" else {"created_by": teacher_id}
        lessons = lesson_repo.find_all(query, limit=500)
        lesson_ids = [l["id"] for l in lessons.get("data", [])]

        all_progress = []
        weak_skills = {}
        for lid in lesson_ids:
            lp = progress_repo.find_by_lesson(lid)
            lesson = next((l for l in lessons["data"] if l["id"] == lid), {})
            for p in lp.get("data", []):
                all_progress.append({**p, "lesson_title": lesson.get("title", ""), "skill": lesson.get("skill", "")})
                skill = lesson.get("skill", "General")
                scores = p.get("block_scores", {})
                if scores:
                    avg = sum(s.get("percentage", 0) for s in scores.values()) / len(scores)
                    weak_skills.setdefault(skill, []).append(avg)

        avg_completion = 0
        avg_score = 0
        if all_progress:
            avg_completion = sum(p.get("completion_percent", 0) for p in all_progress) / len(all_progress)
            score_vals = []
            for p in all_progress:
                for s in p.get("block_scores", {}).values():
                    if s.get("percentage") is not None:
                        score_vals.append(s["percentage"])
            avg_score = sum(score_vals) / len(score_vals) if score_vals else 0

        skill_summary = {
            k: round(sum(v) / len(v), 1) for k, v in weak_skills.items() if v
        }
        weak = sorted(skill_summary.items(), key=lambda x: x[1])[:3]
        strong = sorted(skill_summary.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "total_lessons": len(lesson_ids),
            "total_students_tracked": len(all_progress),
            "avg_completion": round(avg_completion, 1),
            "avg_score": round(avg_score, 1),
            "weak_skills": [{"skill": s, "avg": v} for s, v in weak],
            "strong_skills": [{"skill": s, "avg": v} for s, v in strong],
        }, 200

    def generate_block_ai(self, lesson_id, teacher_id, role, block_type, topic, grade, skill):
        lesson, err = self._assert_can_edit(lesson_id, teacher_id, role)
        if err:
            return err

        prompt_tpl = LESSON_AI_PROMPTS.get(block_type, LESSON_AI_PROMPTS["text"])
        params = {"topic": topic or lesson.get("title", ""), "grade": grade or lesson.get("grade"), "skill": skill or lesson.get("skill")}
        result = ai_service.generate("lesson_generator", params)

        return {
            "block_type": block_type,
            "suggested_content": result.get("response", ""),
            "provider": result.get("provider", ""),
        }, 200

    def _assert_can_edit(self, lesson_id, teacher_id, role):
        lesson = lesson_repo.find_by_id(lesson_id)
        if not lesson:
            return None, ({"error": "Không tìm thấy bài học"}, 404)
        if role != "super_admin" and lesson.get("created_by") != teacher_id:
            return None, ({"error": "Không có quyền chỉnh sửa"}, 403)
        return lesson, None

    def _save_progress(self, lesson_id, user_id, lesson, completion_percent=None,
                       block_scores=None, started_at=None, ended_at=None):
        existing = progress_repo.find_by_student_lesson(lesson_id, user_id)
        payload = {
            "lesson_id": lesson_id,
            "student_id": user_id,
            "updated_at": datetime.utcnow(),
        }
        if completion_percent is not None:
            payload["completion_percent"] = completion_percent
        if block_scores is not None:
            payload["block_scores"] = block_scores
        if started_at:
            payload["started_at"] = started_at
        if ended_at:
            payload["ended_at"] = ended_at

        total_blocks = len(lesson.get("blocks", []))
        gradable = [b for b in lesson.get("blocks", []) if b["type"] in ("exercise", "quiz", "writing", "speaking")]
        if block_scores and gradable:
            quiz_scores = [block_scores[b["id"]]["percentage"] for b in gradable if b["id"] in block_scores and "percentage" in block_scores[b["id"]]]
            if quiz_scores:
                payload["quiz_score"] = round(sum(quiz_scores) / len(quiz_scores), 1)
            payload["total_score"] = payload.get("quiz_score", 0)

        if completion_percent is None and total_blocks > 0 and block_scores:
            viewed = len(block_scores)
            payload["completion_percent"] = min(100, round(viewed / total_blocks * 100, 1))

        if existing:
            merged = {**existing, **payload}
            if block_scores:
                merged["block_scores"] = {**existing.get("block_scores", {}), **block_scores}
            return progress_repo.update(existing["id"], merged)

        payload["started_at"] = payload.get("started_at") or datetime.utcnow()
        payload["completion_percent"] = payload.get("completion_percent", 0)
        payload["block_scores"] = payload.get("block_scores", {})
        return progress_repo.create(payload)
