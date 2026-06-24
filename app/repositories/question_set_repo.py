"""Question set (passage / group with multiple sub-questions) repository."""
from app.models.collections import COLLECTIONS
from app.repositories.base import BaseRepository


class QuestionSetRepository(BaseRepository):
    collection_name = COLLECTIONS["question_sets"]

    def find_by_teacher(self, teacher_id, page=1, limit=20):
        return self.find_all({"created_by": teacher_id}, page=page, limit=limit)

    def find_by_filters(self, filters, page=1, limit=20):
        query = {}
        for key in ("skill", "grade", "difficulty", "topic"):
            if filters.get(key):
                query[key] = filters[key]
        if filters.get("search"):
            query["$or"] = [
                {"title": {"$regex": filters["search"], "$options": "i"}},
                {"passage": {"$regex": filters["search"], "$options": "i"}},
            ]
        return self.find_all(query, page=page, limit=limit)
