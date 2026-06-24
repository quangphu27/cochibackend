"""LMS-related schemas."""
from datetime import datetime

CLASS_SCHEMA = {
    "name": str,
    "description": str,
    "class_code": str,
    "teacher_id": str,
    "student_ids": list,
    "parent_ids": list,
    "grade": str,
    "subject": str,
    "schedule": list,
    "is_active": bool,
    "created_at": datetime,
}

COURSE_SCHEMA = {
    "title": str,
    "description": str,
    "grade": str,
    "skill": str,
    "teacher_id": str,
    "lessons": list,
    "thumbnail_url": str,
    "is_published": bool,
    "created_at": datetime,
}

LESSON_SCHEMA = {
    "course_id": str,
    "title": str,
    "content": str,
    "order": int,
    "media_urls": list,
    "duration_minutes": int,
    "created_at": datetime,
}

ASSIGNMENT_SCHEMA = {
    "class_id": str,
    "title": str,
    "description": str,
    "type": str,
    "due_date": datetime,
    "max_score": float,
    "attachments": list,
    "rubric": dict,
    "created_by": str,
    "created_at": datetime,
}

SUBMISSION_SCHEMA = {
    "assignment_id": str,
    "student_id": str,
    "content": str,
    "attachments": list,
    "score": float,
    "feedback": str,
    "status": str,
    "submitted_at": datetime,
    "graded_at": datetime,
}

ATTENDANCE_SCHEMA = {
    "class_id": str,
    "date": datetime,
    "records": list,
    "created_by": str,
}

ANNOUNCEMENT_SCHEMA = {
    "class_id": str,
    "title": str,
    "content": str,
    "created_by": str,
    "created_at": datetime,
}
