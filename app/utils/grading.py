"""Automatic grading engine for all question types."""
import json
import re


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def grade_mcq(student_answer, correct_answer):
    return 1.0 if _norm(student_answer) == _norm(correct_answer) else 0.0


def grade_true_false(student_answer, correct_answer):
    mapping = {"đúng": "true", "sai": "false", "dung": "true"}
    sa = mapping.get(_norm(student_answer), _norm(student_answer))
    ca = mapping.get(_norm(correct_answer), _norm(correct_answer))
    return 1.0 if sa == ca else 0.0


def _parse_json(val):
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def grade_multi_select(student_answer, correct_answer):
    correct = _parse_json(correct_answer)
    student = _parse_json(student_answer)
    if not isinstance(correct, list):
        correct = [x.strip() for x in str(correct).split(",") if x.strip()]
    if not isinstance(student, list):
        student = [x.strip() for x in str(student).split(",") if x.strip()]
    correct_set = {_norm(x) for x in correct}
    student_set = {_norm(x) for x in student}
    if not correct_set:
        return 0.0
    if correct_set == student_set:
        return 1.0
    # partial credit: intersection / union
    inter = len(correct_set & student_set)
    wrong = len(student_set - correct_set)
    if wrong > 0:
        return max(0.0, (inter - wrong) / len(correct_set))
    return inter / len(correct_set)


def grade_matching(student_answer, correct_answer):
    correct = _parse_json(correct_answer)
    student = _parse_json(student_answer)
    if not isinstance(correct, dict):
        if isinstance(correct, str) and "-" in correct:
            correct = dict(p.split("-", 1) for p in correct.split(",") if "-" in p)
        else:
            return 0.0
    if not isinstance(student, dict):
        return 0.0
    total = len(correct)
    if total == 0:
        return 0.0
    correct_count = sum(1 for k, v in correct.items() if _norm(student.get(k)) == _norm(v))
    return correct_count / total


def grade_gap_filling(student_answer, correct_answer, alternatives=None):
    if isinstance(correct_answer, list):
        student = _parse_json(student_answer)
        if not isinstance(student, list):
            student = [student]
        total = len(correct_answer)
        if total == 0:
            return 0.0
        correct = 0
        for i, ans in enumerate(correct_answer):
            s = student[i] if i < len(student) else ""
            alts = alternatives[i] if alternatives and i < len(alternatives) else []
            valid = {_norm(ans)}
            if isinstance(alts, list):
                valid.update(_norm(a) for a in alts)
            if _norm(s) in valid:
                correct += 1
        return correct / total
    return grade_mcq(student_answer, correct_answer)


def grade_cloze(student_answer, correct_answer):
    return grade_gap_filling(student_answer, correct_answer)


def grade_word_order(student_answer, correct_answer):
    return 1.0 if _norm(student_answer) == _norm(correct_answer) else 0.0


def grade_sentence_order(student_answer, correct_answer):
    student = _parse_json(student_answer)
    correct = _parse_json(correct_answer)
    if isinstance(student, str):
        student = [s.strip() for s in student.split("|||") if s.strip()]
    if isinstance(correct, str):
        correct = [s.strip() for s in correct.split("|||") if s.strip()]
    if not isinstance(student, list) or not isinstance(correct, list):
        return grade_word_order(student_answer, correct_answer)
    if len(student) != len(correct):
        return 0.0
    matches = sum(1 for s, c in zip(student, correct) if _norm(s) == _norm(c))
    return matches / len(correct) if correct else 0.0


def grade_short_answer(student_answer, correct_answer, alternatives=None):
    valid = {_norm(correct_answer)}
    if alternatives:
        valid.update(_norm(a) for a in alternatives)
    return 1.0 if _norm(student_answer) in valid else 0.0


MANUAL_TYPES = frozenset({
    "rewrite", "essay", "letter", "image_description", "open_ended",
    "read_aloud", "speaking_topic", "image_speaking",
})


def grade_question(question_type, student_answer, correct_answer, question=None):
    question = question or {}
    alternatives = question.get("alternative_answers") or []

    graders = {
        "mcq": lambda s, c: grade_mcq(s, c),
        "true_false": grade_true_false,
        "multi_select": grade_multi_select,
        "matching": grade_matching,
        "gap_filling": lambda s, c: grade_gap_filling(s, c, alternatives),
        "cloze": grade_cloze,
        "error_identification": grade_mcq,
        "phonetics": grade_mcq,
        "stress": grade_mcq,
        "word_order": grade_word_order,
        "sentence_order": grade_sentence_order,
        "short_answer": lambda s, c: grade_short_answer(s, c, alternatives),
        "listening_fill": lambda s, c: grade_gap_filling(s, c, alternatives),
        "listening_mcq": grade_mcq,
        "listening_true_false": grade_true_false,
        "sentence_transformation_mcq": grade_mcq,
        "sentence_combination": grade_mcq,
        "functional_speaking": grade_mcq,
        "dictation": lambda s, c: grade_gap_filling(s, c, alternatives),
    }
    if question_type in MANUAL_TYPES:
        return None
    grader = graders.get(question_type)
    if grader:
        return grader(student_answer, correct_answer)
    return None


def grade_exam(questions, answers):
    results = []
    total_score = 0
    max_score = 0
    skill_scores = {}

    for q in questions:
        q_id = q.get("id") or str(q.get("_id", ""))
        student_answer = next((a["answer"] for a in answers if a.get("question_id") == q_id), None)
        points = q.get("points", 1)
        max_score += points

        ratio = grade_question(q.get("type", "mcq"), student_answer, q.get("correct_answer"), q)
        if ratio is not None:
            earned = ratio * points
            total_score += earned
            skill = q.get("skill", "general")
            skill_scores.setdefault(skill, {"earned": 0, "max": 0})
            skill_scores[skill]["earned"] += earned
            skill_scores[skill]["max"] += points
            results.append({
                "question_id": q_id,
                "correct": ratio >= 1.0,
                "score": round(earned, 2),
                "max": points,
            })
        else:
            results.append({
                "question_id": q_id,
                "correct": None,
                "score": None,
                "max": points,
                "needs_manual": True,
            })

    return {
        "results": results,
        "auto_score": round(total_score, 2),
        "max_score": max_score,
        "skill_scores": skill_scores,
        "percentage": round(total_score / max_score * 100, 1) if max_score > 0 else 0,
    }
