"""Examination and question schemas."""
from datetime import datetime

QUESTION_TYPES = [
    "mcq", "true_false", "matching", "gap_filling", "cloze",
    "error_identification", "short_answer", "open_ended",
    "sentence_ordering", "sentence_transformation", "dictation",
    "reading_comprehension", "phonetics", "stress",
]

QUESTION_SCHEMA = {
    "type": str,
    "content": str,
    "options": list,
    "correct_answer": object,
    "explanation": str,
    "category": str,
    "skill": str,
    "grade": str,
    "difficulty": str,
    "tags": list,
    "media_url": str,
    "points": float,
    "created_by": str,
    "created_at": datetime,
}

EXAM_SCHEMA = {
    "title": str,
    "description": str,
    "class_id": str,
    "type": str,
    "skills": list,
    "questions": list,
    "duration_minutes": int,
    "total_points": float,
    "shuffle_questions": bool,
    "start_time": datetime,
    "end_time": datetime,
    "created_by": str,
    "created_at": datetime,
}

RESULT_SCHEMA = {
    "exam_id": str,
    "student_id": str,
    "answers": list,
    "auto_score": float,
    "teacher_score": float,
    "final_score": float,
    "skill_scores": dict,
    "feedback": str,
    "status": str,
    "submitted_at": datetime,
    "graded_at": datetime,
}

SPEAKING_RECORD_SCHEMA = {
    "student_id": str,
    "exam_id": str,
    "assignment_id": str,
    "audio_url": str,
    "transcript": str,
    "ai_evaluation": dict,
    "teacher_feedback": str,
    "pronunciation_score": float,
    "fluency_score": float,
    "vocabulary_score": float,
    "created_at": datetime,
}

WRITING_EVALUATION_SCHEMA = {
    "student_id": str,
    "exam_id": str,
    "assignment_id": str,
    "content": str,
    "ai_evaluation": dict,
    "teacher_feedback": str,
    "rubric_scores": dict,
    "final_score": float,
    "created_at": datetime,
}
