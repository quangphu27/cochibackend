"""Question and exam repositories."""
from app.models.collections import COLLECTIONS
from app.repositories.base import BaseRepository


class QuestionRepository(BaseRepository):
    collection_name = COLLECTIONS["questions"]

    def find_by_filters(self, filters, page=1, limit=20):
        query = {}
        for key in ("category", "skill", "grade", "difficulty", "type"):
            if filters.get(key):
                query[key] = filters[key]
        if filters.get("tags"):
            query["tags"] = {"$in": filters["tags"]}
        if filters.get("search"):
            query["$or"] = [
                {"content": {"$regex": filters["search"], "$options": "i"}},
                {"tags": {"$regex": filters["search"], "$options": "i"}},
            ]
        return self.find_all(query, page=page, limit=limit)


class ExamRepository(BaseRepository):
    collection_name = COLLECTIONS["exams"]

    def find_by_class(self, class_id, page=1, limit=20):
        return self.find_all({"class_id": class_id}, page=page, limit=limit)


class ResultRepository(BaseRepository):
    collection_name = COLLECTIONS["results"]

    def find_by_student(self, student_id, page=1, limit=20):
        return self.find_all({"student_id": student_id}, page=page, limit=limit)

    def find_by_exam(self, exam_id):
        return self.find_all({"exam_id": exam_id}, limit=100)
