"""Lesson and progress repositories."""
from app.models.collections import COLLECTIONS
from app.repositories.base import BaseRepository


class LessonRepository(BaseRepository):
    collection_name = COLLECTIONS["lessons"]

    def find_by_teacher(self, teacher_id, page=1, limit=20, **filters):
        query = {"created_by": teacher_id, **filters}
        return self.find_all(query, page=page, limit=limit, sort=[("updated_at", -1)])

    def find_published_for_classes(self, class_ids, page=1, limit=50, **filters):
        query = {
            "status": "published",
            "$or": [
                {"class_ids": {"$in": class_ids}},
                {"class_ids": {"$size": 0}},
            ],
            **filters,
        }
        return self.find_all(query, page=page, limit=limit, sort=[("updated_at", -1)])


class LessonProgressRepository(BaseRepository):
    collection_name = COLLECTIONS["lesson_progress"]

    def find_by_student_lesson(self, lesson_id, student_id):
        return self.find_one({"lesson_id": lesson_id, "student_id": student_id})

    def find_by_lesson(self, lesson_id):
        return self.find_all({"lesson_id": lesson_id}, limit=200)
