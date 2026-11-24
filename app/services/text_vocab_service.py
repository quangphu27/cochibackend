"""Analyze reading texts: vocabulary gloss + student practice (JSON from AI)."""
import json
import re

from app.services.ai_service import AIService

CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
MAX_CHARS = 6000
PRACTICE_MODES = ("summary", "discussion", "fill_gaps", "vocab_quiz")

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


def _normalize_level(level: str) -> str:
    upper = (level or "B1").strip().upper()
    if upper in CEFR_LEVELS:
        return upper
    if "10" in upper:
        return "B1"
    if "11" in upper:
        return "B2"
    if "12" in upper or "THPT" in upper:
        return "C1"
    return "B1"


ANALYZE_PROMPT = """Bạn là giáo viên tiếng Anh cho học sinh Việt Nam.
Phân tích đoạn văn tiếng Anh dưới đây với trình độ CEFR {level}.

Trả về CHỈ một JSON hợp lệ (không markdown):
{{
  "word_count": <số từ>,
  "level_match_percent": <0-100, ước lượng % từ vựng phù hợp {level}>,
  "hard_word_count": <số từ khó>,
  "difficulty": "easy"|"moderate"|"hard",
  "difficulty_message_vi": "1-2 câu tiếng Việt: bài khó/dễ so với {level}",
  "summary_vi": "tóm tắt nội dung 2-3 câu tiếng Việt",
  "hard_words": [
    {{
      "word": "từ trong bài",
      "lemma": "dạng gốc",
      "part_of_speech": "noun/verb/...",
      "meaning_vi": "nghĩa tiếng Việt ngắn",
      "ipa": "/.../",
      "example_in_text": "câu ngắn trích từ bài hoặc dùng lại từ",
      "note_vi": "mẹo học hoặc collocation"
    }}
  ],
  "hard_word_forms": ["danh sách mọi biến thể cần gạch chân trong bài: word, words, Word..."]
}}

Chọn 8-25 từ/cụm KHÓ hoặc TRÊN trình {level}. hard_word_forms gồm đủ dạng xuất hiện trong văn bản.

VĂN BẢN ({char_count} ký tự):
\"\"\"{content}\"\"\"
"""


PRACTICE_PROMPTS = {
    "summary": """Tạo ôn tập "summary" từ bài đọc và từ khó: {words}
CEFR {level}. CHỈ JSON:
{{
  "mode": "summary",
  "summary_en": "5-7 câu tiếng Anh đơn giản",
  "key_points_vi": ["...", "..."],
  "vocab_review": [{{"word":"","meaning_vi":"","your_turn_vi":"bài tập mini cho HS viết 1 câu"}}]
}}

BÀI ĐỌC:
\"\"\"{content}\"\"\"
""",
    "discussion": """Tạo 4-5 câu hỏi mở thảo luận bằng tiếng Anh (kèm gợi ý tiếng Việt) về bài đọc.
Tập trung từ vựng: {words}
CEFR {level}. CHỈ JSON:
{{
  "mode": "discussion",
  "questions": [
    {{"question_en":"","question_vi":"","vocab_hint_vi":"","sample_answer_en":""}}
  ]
}}

BÀI ĐỌC:
\"\"\"{content}\"\"\"
""",
    "fill_gaps": """Tạo 8-10 câu điền từ (gap filling) luyện từ vựng trích từ ngữ cảnh bài đọc.
Đáp án thuộc danh sách: {words}
CEFR {level}. CHỈ JSON:
{{
  "mode": "fill_gaps",
  "items": [
    {{"sentence": "câu có ___","answer": "từ điền","hint_vi":""}}
  ]
}}

BÀI ĐỌC:
\"\"\"{content}\"\"\"
""",
    "vocab_quiz": """Tạo 8 câu trắc nghiệm từ vựng (nghĩa tiếng Việt) dựa từ: {words}
CHỈ JSON:
{{
  "mode": "vocab_quiz",
  "items": [
    {{"question_vi":"nghĩa của X?","options":["a","b","c","d"],"correct_index":0,"word":""}}
  ]
}}

BÀI ĐỌC:
\"\"\"{content}\"\"\"
""",
}


DISCUSS_FEEDBACK_PROMPT = """Học sinh Việt Nam (CEFR {level}) trả lời câu hỏi thảo luận.
Cho nhận xét ngắn, khích lệ, sửa lỗi ngữ pháp/từ vựng nếu có.

CHỈ JSON:
{{
  "feedback_vi": "2-4 câu tiếng Việt",
  "feedback_en": "1-2 câu tiếng Anh",
  "corrected_answer_en": "phiên bản chỉnh sửa nhẹ nếu cần",
  "score_hint": "tốt|ổn|cần_cải_thiện"
}}

Câu hỏi: {question}
Câu trả lời HS: {answer}

Ngữ cảnh bài đọc (rút gọn):
\"\"\"{content_slice}\"\"\"
"""


class TextVocabService:
    def analyze(self, content: str, level: str, provider: str = "gemini"):
        text = (content or "").strip()
        if len(text) < 40:
            return {"error": "Văn bản quá ngắn (tối thiểu ~40 ký tự)"}, 400
        if len(text) > MAX_CHARS:
            return {"error": f"Văn bản tối đa {MAX_CHARS} ký tự"}, 400
        cefr = _normalize_level(level)
        prompt = ANALYZE_PROMPT.format(level=cefr, content=text, char_count=len(text))
        ai_result = ai_service.generate(
            "reading_questions",
            {"prompt": prompt, "content": text, "json_mode": True},
            provider,
        )
        if ai_result.get("error") and not ai_result.get("response"):
            return {"error": ai_result["error"]}, 502
        try:
            data = _extract_json(ai_result.get("response") or "")
        except (json.JSONDecodeError, ValueError) as e:
            return {"error": str(e), "raw": ai_result.get("response")}, 502
        data["level"] = cefr
        data["provider"] = ai_result.get("provider", provider)
        return data, 200

    def practice(self, content: str, level: str, mode: str, words: list, provider: str = "gemini"):
        text = (content or "").strip()
        if len(text) < 40:
            return {"error": "Cần văn bản đã phân tích"}, 400
        mode = (mode or "fill_gaps").strip().lower()
        if mode not in PRACTICE_MODES:
            return {"error": f"mode phải là một trong: {', '.join(PRACTICE_MODES)}"}, 400
        cefr = _normalize_level(level)
        word_list = ", ".join(words[:30]) if words else "(từ khó trong bài)"
        tpl = PRACTICE_PROMPTS[mode]
        prompt = tpl.format(level=cefr, content=text[:MAX_CHARS], words=word_list)
        ai_result = ai_service.generate(
            "vocabulary_builder",
            {"prompt": prompt, "topic": word_list, "level": cefr, "json_mode": True},
            provider,
        )
        if ai_result.get("error") and not ai_result.get("response"):
            return {"error": ai_result["error"]}, 502
        try:
            data = _extract_json(ai_result.get("response") or "")
        except (json.JSONDecodeError, ValueError) as e:
            return {"error": str(e), "raw": ai_result.get("response")}, 502
        data["provider"] = ai_result.get("provider", provider)
        return data, 200

    def discussion_feedback(self, content: str, level: str, question: str, answer: str, provider: str = "gemini"):
        if not (question or "").strip() or not (answer or "").strip():
            return {"error": "Thiếu câu hỏi hoặc câu trả lời"}, 400
        cefr = _normalize_level(level)
        prompt = DISCUSS_FEEDBACK_PROMPT.format(
            level=cefr,
            question=question.strip(),
            answer=answer.strip(),
            content_slice=(content or "")[:2000],
        )
        ai_result = ai_service.generate(
            "writing_evaluation",
            {"prompt": prompt, "content": answer, "json_mode": True},
            provider,
        )
        if ai_result.get("error") and not ai_result.get("response"):
            return {"error": ai_result["error"]}, 502
        try:
            data = _extract_json(ai_result.get("response") or "")
        except (json.JSONDecodeError, ValueError) as e:
            return {"error": str(e), "raw": ai_result.get("response")}, 502
        return data, 200