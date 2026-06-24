"""Resolve question refs (single IDs or question sets) into flat question list."""
import uuid
from app.repositories.exam_repo import QuestionRepository
from app.repositories.question_set_repo import QuestionSetRepository

question_repo = QuestionRepository()
set_repo = QuestionSetRepository()

SET_PREFIX = "set:"


def _assign_sub_ids(questions, set_id, passage_meta):
    """Flatten sub-questions from a set with stable composite IDs."""
    flat = []
    for i, sq in enumerate(questions or []):
        q = dict(sq)
        sub_id = q.get("id") or f"{set_id}_q{i}"
        q["id"] = f"{set_id}::{sub_id}"
        q["set_id"] = set_id
        q["set_title"] = passage_meta.get("title", "")
        if passage_meta.get("passage") and not q.get("passage"):
            q["passage"] = passage_meta["passage"]
        if passage_meta.get("image_url") and not q.get("image_url"):
            q["image_url"] = passage_meta["image_url"]
        if passage_meta.get("audio_url") and not q.get("audio_url"):
            q["audio_url"] = passage_meta["audio_url"]
        if passage_meta.get("video_url") and not q.get("video_url"):
            q["video_url"] = passage_meta["video_url"]
        if passage_meta.get("instructions") and not q.get("instructions"):
            q["instructions"] = passage_meta["instructions"]
        q["set_subtitles"] = passage_meta.get("subtitles") or []
        q["set_content_type"] = passage_meta.get("content_type") or ""
        flat.append(q)
    return flat


def resolve_question_refs(refs):
    """Expand question IDs and set:ID refs into a flat list of question dicts."""
    if not refs:
        return []
    flat = []
    seen_sets = set()

    for ref in refs:
        if isinstance(ref, dict):
            flat.append(ref)
            continue
        ref_str = str(ref)
        if ref_str.startswith(SET_PREFIX):
            set_id = ref_str[len(SET_PREFIX):]
            if set_id in seen_sets:
                continue
            seen_sets.add(set_id)
            qset = set_repo.find_by_id(set_id)
            if not qset:
                continue
            meta = {
                "title": qset.get("title", ""),
                "passage": qset.get("passage", ""),
                "image_url": qset.get("image_url", ""),
                "audio_url": qset.get("audio_url", ""),
                "video_url": qset.get("video_url", ""),
                "instructions": qset.get("instructions", ""),
                "subtitles": qset.get("subtitles") or [],
                "content_type": qset.get("content_type", ""),
            }
            flat.extend(_assign_sub_ids(qset.get("questions", []), set_id, meta))
        else:
            q_doc = question_repo.find_by_id(ref_str)
            if q_doc:
                flat.append(q_doc)
    return flat


def ensure_sub_question_ids(questions):
    """Assign IDs to embedded sub-questions in a set payload."""
    result = []
    for i, q in enumerate(questions or []):
        item = dict(q)
        if not item.get("id"):
            item["id"] = f"sq_{uuid.uuid4().hex[:8]}"
        result.append(item)
    return result
