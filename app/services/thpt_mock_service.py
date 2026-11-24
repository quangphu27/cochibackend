"""THPT National Exam mock paper generation and attempts."""
import copy
import json
import re
import secrets
import uuid
from datetime import datetime

from app.repositories.base import BaseRepository
from app.models.collections import COLLECTIONS
from app.services.ai_service import AIService
from app.utils.grading import grade_exam

LEVELS = {
    "A12": {"label": "A12", "question_count": 10, "hint": "cơ bản, từ vựng và ngữ pháp THCS nâng cao"},
    "B12": {"label": "B12", "question_count": 12, "hint": "trung bình, bám sát đề minh họa THPT Quốc gia"},
    "C12": {"label": "C12", "question_count": 15, "hint": "nâng cao, suy luận và đọc hiểu phức tạp"},
}

THPT_PROMPT = """Bạn là chuyên gia soạn đề tiếng Anh THPT Quốc gia Việt Nam (Bộ GD&ĐT).
Từ văn bản nguồn bên dưới, soạn đề minh họa mức {level} ({level_hint}).

YÊU CẦU:
- Có đoạn đọc (passage) bám nội dung văn bản nguồn (có thể chỉnh sửa nhẹ cho phù hợp đề thi).
- Tạo đúng {question_count} câu hỏi, chủ yếu type "mcq", có thể thêm "gap_filling" hoặc "true_false".
- Mỗi câu MCQ có options đủ A, B, C, D (chuỗi bắt đầu bằng "A. ", "B. ", ...).
- correct_answer chỉ là chữ cái A/B/C/D hoặc "true"/"false" hoặc chuỗi điền cho gap_filling.
- points mỗi câu: 0.25
- skill: reading, grammar, hoặc vocabulary

CHỈ TRẢ VỀ JSON hợp lệ (không markdown), dạng:
{{
  "title": "Đề minh họa tiếng Anh THPT - {level}",
  "passage": "...",
  "questions": [
    {{
      "id": "q1",
      "type": "mcq",
      "content": "Câu hỏi...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "A",
      "points": 0.25,
      "skill": "reading",
      "explanation": "..."
    }}
  ]
}}

VĂN BẢN NGUỒN ({char_count} ký tự):
{source_text}
"""


class ThptPaperRepo(BaseRepository):
    collection_name = COLLECTIONS["thpt_mock_papers"]


class ThptAttemptRepo(BaseRepository):
    collection_name = COLLECTIONS["thpt_mock_attempts"]


paper_repo = ThptPaperRepo()
attempt_repo = ThptAttemptRepo()
ai_service = AIService()


def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("AI không trả về nội dung")
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Không parse được JSON từ AI")
    return json.loads(text[start : end + 1])


def _normalize_questions(questions: list) -> list:
    out = []
    for i, q in enumerate(questions or []):
        q = dict(q)
        q.setdefault("id", f"q{i + 1}")
        q["id"] = str(q["id"])
        q.setdefault("type", "mcq")
        q.setdefault("points", 0.25)
        q.setdefault("skill", "reading")
        q.setdefault("options", [])
        out.append(q)
    return out


def _unique_share_code() -> str:
    for _ in range(8):
        code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:10]
        if not paper_repo.find_one({"share_code": code}):
            return code
    return uuid.uuid4().hex[:10]


class ThptMockService:
    def generate_paper(self, creator_id: str, source_text: str, level: str, provider: str = "gemini"):
        level = (level or "B12").upper()
        if level not in LEVELS:
            return {"error": "Trình độ phải là A12, B12 hoặc C12"}, 400

        source_text = (source_text or "").strip()
        if len(source_text) < 50:
            return {"error": "Văn bản nguồn cần tối thiểu 50 ký tự"}, 400
        if len(source_text) > 20000:
            return {"error": "Văn bản nguồn tối đa 20.000 ký tự"}, 400

        meta = LEVELS[level]
        prompt = THPT_PROMPT.format(
            level=level,
            level_hint=meta["hint"],
            question_count=meta["question_count"],
            char_count=len(source_text),
            source_text=source_text[:18000],
        )

        ai_result = ai_service.generate(
            "thpt_mock_exam",
            {"prompt": prompt, "content": source_text, "json_mode": True},
            provider,
        )
        if ai_result.get("error") and not ai_result.get("response"):
            return {"error": ai_result.get("error", "AI lỗi")}, 502

        try:
            payload = _extract_json(ai_result.get("response", ""))
        except (json.JSONDecodeError, ValueError) as exc:
            return {"error": f"AI trả về định dạng không hợp lệ: {exc}"}, 422

        questions = _normalize_questions(payload.get("questions"))
        if not questions:
            return {"error": "AI không tạo được câu hỏi"}, 422

        total_points = sum(float(q.get("points", 0.25)) for q in questions)
        share_code = _unique_share_code()
        paper = paper_repo.create({
            "title": payload.get("title") or f"Đề minh họa THPT - {level}",
            "level": level,
            "source_text": source_text,
            "passage": payload.get("passage") or source_text[:3000],
            "questions": questions,
            "share_code": share_code,
            "duration_minutes": 50,
            "total_points": total_points,
            "provider": ai_result.get("provider", provider),
            "created_by": creator_id,
            "status": "published",
        })
        return {"paper": paper, "ai": {"provider": ai_result.get("provider"), "tokens_used": ai_result.get("tokens_used", 0)}}, 201

    def get_by_share_code(self, share_code: str, include_answers: bool = False):
        paper = paper_repo.find_one({"share_code": share_code, "status": "published"})
        if not paper:
            return {"error": "Không tìm thấy đề thi"}, 404
        questions = copy.deepcopy(paper.get("questions") or [])
        if not include_answers:
            for q in questions:
                q.pop("correct_answer", None)
                q.pop("explanation", None)
        safe_paper = dict(paper)
        safe_paper["questions"] = questions
        return safe_paper, 200

    def submit_attempt(self, share_code: str, student_id: str, student_name: str, answers: list):
        paper = paper_repo.find_one({"share_code": share_code})
        if not paper:
            return {"error": "Không tìm thấy đề thi"}, 404

        existing = attempt_repo.find_one({"paper_id": paper["id"], "student_id": student_id})
        if existing:
            return {"error": "Bạn đã làm bài này rồi", "attempt": existing}, 409

        questions = paper.get("questions") or []
        grading = grade_exam(questions, answers)

        attempt = attempt_repo.create({
            "paper_id": paper["id"],
            "share_code": share_code,
            "student_id": student_id,
            "student_name": student_name or "",
            "answers": answers,
            "auto_score": grading["auto_score"],
            "max_score": grading["max_score"],
            "grading": grading,
            "level": paper.get("level"),
            "submitted_at": datetime.utcnow(),
        })
        return {"attempt": attempt, "grading": grading}, 201

    def list_my_papers(self, creator_id: str, page: int = 1):
        return paper_repo.find_all({"created_by": creator_id}, page=page, sort=[("created_at", -1)])

    def list_attempts(self, paper_id: str, creator_id: str):
        paper = paper_repo.find_by_id(paper_id)
        if not paper:
            return {"error": "Không tìm thấy đề"}, 404
        if paper.get("created_by") != creator_id:
            return {"error": "Không có quyền"}, 403
        result = attempt_repo.find_all({"paper_id": paper_id}, page=1, limit=200, sort=[("submitted_at", -1)])
        return result, 200