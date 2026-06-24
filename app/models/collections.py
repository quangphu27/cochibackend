"""MongoDB collection names and indexes."""
COLLECTIONS = {
    "users": "users",
    "roles": "roles",
    "classes": "classes",
    "courses": "courses",
    "lessons": "lessons",
    "assignments": "assignments",
    "submissions": "submissions",
    "questions": "questions",
    "question_sets": "question_sets",
    "exams": "exams",
    "results": "results",
    "resources": "resources",
    "documents": "documents",
    "posts": "posts",
    "comments": "comments",
    "notifications": "notifications",
    "media": "media",
    "albums": "albums",
    "ai_history": "ai_history",
    "teacher_feedback": "teacher_feedback",
    "speaking_records": "speaking_records",
    "writing_evaluations": "writing_evaluations",
    "attendance": "attendance",
    "announcements": "announcements",
    "bookmarks": "bookmarks",
    "likes": "likes",
    "events": "events",
    "entertainment": "entertainment",
    "learning_tools": "learning_tools",
    "lesson_progress": "lesson_progress",
}


def create_indexes(db):
    """Create database indexes for performance."""
    db[COLLECTIONS["users"]].create_index("email", unique=True)
    db[COLLECTIONS["users"]].create_index("role")
    db[COLLECTIONS["users"]].create_index("created_at")
    db[COLLECTIONS["classes"]].create_index("class_code", unique=True)
    db[COLLECTIONS["classes"]].create_index("teacher_id")
    db[COLLECTIONS["classes"]].create_index("created_at")
    db[COLLECTIONS["questions"]].create_index([("category", 1), ("difficulty", 1)])
    db[COLLECTIONS["questions"]].create_index("tags")
    db[COLLECTIONS["question_sets"]].create_index("created_by")
    db[COLLECTIONS["posts"]].create_index("created_at")
    db[COLLECTIONS["notifications"]].create_index([("user_id", 1), ("read", 1)])
    db[COLLECTIONS["resources"]].create_index([("grade", 1), ("skill", 1)])
    db[COLLECTIONS["exams"]].create_index("class_id")
    db[COLLECTIONS["exams"]].create_index("created_at")
    db[COLLECTIONS["assignments"]].create_index("class_id")
    db[COLLECTIONS["assignments"]].create_index("created_at")
    db[COLLECTIONS["results"]].create_index([("student_id", 1), ("exam_id", 1)])
    db[COLLECTIONS["results"]].create_index("submitted_at")
    db[COLLECTIONS["lessons"]].create_index("created_by")
    db[COLLECTIONS["lessons"]].create_index([("grade", 1), ("skill", 1)])
    db[COLLECTIONS["lessons"]].create_index("status")
    db[COLLECTIONS["lesson_progress"]].create_index([("lesson_id", 1), ("student_id", 1)], unique=True)
