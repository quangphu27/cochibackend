"""Persist interactive game / studio tool sets per user."""
from app.models.collections import COLLECTIONS
from app.repositories.base import BaseRepository

EDITOR_TYPES = ("wheel", "flashcards", "crossword")
TOOL_TYPES = (
    "name-picker",
    "match-pairs",
    "word-search",
    "paced-quiz",
    "tug-of-war",
    "html-game",
    "countdown",
    "sleeping-dragon",
    "text-profiler",
)
VALID_TYPES = EDITOR_TYPES + TOOL_TYPES
MAX_TITLE = 120
MAX_WHEEL = 80
MAX_FLASHCARDS = 200
MAX_CROSSWORD_ROWS = 20
MAX_CONTENT = 100_000


class GameSetRepo(BaseRepository):
    collection_name = COLLECTIONS["game_sets"]


repo = GameSetRepo()


def _clean_wheel(items):
    out = []
    for it in items or []:
        label = (it.get("label") if isinstance(it, dict) else str(it or "")).strip()
        if label:
            out.append({"label": label[:80]})
        if len(out) >= MAX_WHEEL:
            break
    return out


def _clean_flashcards(items):
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        front = (it.get("front") or "").strip()
        back = (it.get("back") or "").strip()
        if front and back:
            out.append({"front": front[:200], "back": back[:400]})
        if len(out) >= MAX_FLASHCARDS:
            break
    return out


def _clean_crossword(data):
    if not isinstance(data, dict):
        return None
    rows_in = data.get("rows") or []
    rows = []
    for r in rows_in[:MAX_CROSSWORD_ROWS]:
        if not isinstance(r, dict):
            continue
        word = (r.get("word") or "").strip().upper()
        clue = (r.get("clue") or "").strip()
        try:
            pivot = int(r.get("pivot", 0))
        except (TypeError, ValueError):
            pivot = 0
        if word and clue:
            rows.append({"word": word[:40], "clue": clue[:300], "pivot": max(0, pivot)})
    if not rows:
        return None
    return {
        "acrossCount": len(rows),
        "rows": rows,
        "verticalClue": (data.get("verticalClue") or "").strip()[:300],
    }


def _nonempty_lines(text: str):
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def _validate_tool_content(game_type: str, content_text: str):
    text = (content_text or "").strip()
    if not text:
        return "Nội dung trống — nhập rồi mới lưu"

    if game_type == "name-picker":
        if len(_nonempty_lines(text)) < 1:
            return "Cần ít nhất 1 tên trong danh sách"
        return None

    if game_type == "match-pairs":
        pairs = 0
        for ln in _nonempty_lines(text):
            if "|" in ln or "\t" in ln:
                pairs += 1
        if pairs < 2:
            return "Cần ít nhất 2 cặp (trái | phải)"
        return None

    if game_type == "word-search":
        if len(_nonempty_lines(text)) < 2:
            return "Cần ít nhất 2 từ để tạo bảng"
        return None

    if game_type in ("paced-quiz", "tug-of-war"):
        raw = text
        if game_type == "tug-of-war" and text.startswith("{"):
            try:
                import json

                data = json.loads(text)
                raw = (data.get("raw") or "") if isinstance(data, dict) else text
            except Exception:
                raw = text
        qs = 0
        for ln in _nonempty_lines(raw):
            if "|" in ln:
                qs += 1
        if qs < 1:
            return "Cần ít nhất 1 câu hỏi (Câu | Đúng | Sai…)"
        return None

    if game_type == "html-game":
        if len(text) < 3:
            return "Dán mã HTML trước khi lưu"
        return None

    if game_type in ("countdown", "sleeping-dragon"):
        return None

    if game_type == "text-profiler":
        if len(text.split()) < 5:
            return "Cần đoạn văn dài hơn để lưu (ít nhất ~5 từ)"
        return None

    return None


def _payload_from_body(body: dict):
    game_type = (body.get("type") or "").strip()
    if game_type not in VALID_TYPES:
        return None, "Loại trò chơi không hợp lệ"
    title = (body.get("title") or "").strip() or "Bộ trò chơi mới"
    title = title[:MAX_TITLE]
    content_text = (body.get("content_text") or body.get("contentText") or "")[:MAX_CONTENT]

    doc = {
        "type": game_type,
        "title": title,
        "content_text": content_text,
        "wheel_items": [],
        "flashcards": [],
        "crossword_data": None,
    }

    if game_type == "wheel":
        items = _clean_wheel(body.get("wheel_items") or body.get("wheelItems"))
        if len(items) < 2:
            return None, "Vòng quay cần ít nhất 2 mục"
        doc["wheel_items"] = items
    elif game_type == "flashcards":
        cards = _clean_flashcards(body.get("flashcards"))
        if len(cards) < 1:
            return None, "Cần ít nhất 1 thẻ flashcard"
        doc["flashcards"] = cards
    elif game_type == "crossword":
        cw = _clean_crossword(body.get("crossword_data") or body.get("crosswordData"))
        if not cw:
            return None, "Ô chữ chưa đủ từ / gợi ý"
        doc["crossword_data"] = cw
    else:
        err = _validate_tool_content(game_type, content_text)
        if err:
            return None, err

    return doc, None


class GameSetService:
    def list(self, user_id: str, game_type: str | None = None, page: int = 1, limit: int = 50):
        query = {"user_id": user_id}
        if game_type in VALID_TYPES:
            query["type"] = game_type
        return repo.find_all(query, page=page, limit=min(limit, 100), sort=[("updated_at", -1)]), 200

    def get(self, user_id: str, item_id: str):
        item = repo.find_by_id(item_id)
        if not item or item.get("user_id") != user_id:
            return {"error": "Không tìm thấy bộ trò chơi"}, 404
        return {"item": item}, 200

    def create(self, user_id: str, body: dict):
        doc, err = _payload_from_body(body)
        if err:
            return {"error": err}, 400
        doc["user_id"] = user_id
        created = repo.create(doc)
        return {"item": created}, 201

    def update(self, user_id: str, item_id: str, body: dict):
        existing = repo.find_by_id(item_id)
        if not existing or existing.get("user_id") != user_id:
            return {"error": "Không tìm thấy bộ trò chơi"}, 404
        merged = {
            "type": body.get("type") or existing.get("type"),
            "title": body.get("title", existing.get("title")),
            "content_text": body.get("content_text", body.get("contentText", existing.get("content_text"))),
            "wheel_items": body.get("wheel_items", body.get("wheelItems", existing.get("wheel_items"))),
            "flashcards": body.get("flashcards", existing.get("flashcards")),
            "crossword_data": body.get("crossword_data", body.get("crosswordData", existing.get("crossword_data"))),
        }
        doc, err = _payload_from_body(merged)
        if err:
            return {"error": err}, 400
        updated = repo.update(item_id, doc)
        return {"item": updated}, 200

    def delete(self, user_id: str, item_id: str):
        item = repo.find_by_id(item_id)
        if not item or item.get("user_id") != user_id:
            return {"error": "Không tìm thấy bộ trò chơi"}, 404
        repo.delete(item_id)
        return {"ok": True}, 200
