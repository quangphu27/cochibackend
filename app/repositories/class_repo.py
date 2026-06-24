"""Class repository."""
from app.models.collections import COLLECTIONS
from app.repositories.base import BaseRepository


class ClassRepository(BaseRepository):
    collection_name = COLLECTIONS["classes"]

    def find_by_code(self, code):
        return self.find_one({"class_code": code.upper()})

    def find_by_teacher(self, teacher_id, page=1, limit=20):
        return self.find_all({"teacher_id": teacher_id}, page=page, limit=limit)

    def find_by_student(self, student_id, page=1, limit=20):
        return self.find_all({"student_ids": student_id}, page=page, limit=limit)

    def add_student(self, class_id, student_id):
        from bson import ObjectId
        self.collection.update_one(
            {"_id": ObjectId(class_id)},
            {"$addToSet": {"student_ids": student_id}},
        )

    def remove_student(self, class_id, student_id):
        from bson import ObjectId
        self.collection.update_one(
            {"_id": ObjectId(class_id)},
            {"$pull": {"student_ids": student_id}},
        )
