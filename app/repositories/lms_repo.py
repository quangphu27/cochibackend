"""LMS repositories - assignments, attendance, announcements."""
from app.models.collections import COLLECTIONS
from app.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository):
    collection_name = COLLECTIONS["assignments"]

    def find_by_class(self, class_id, page=1, limit=20):
        return self.find_all({"class_id": class_id}, page=page, limit=limit, sort=[("created_at", -1)])


class SubmissionRepository(BaseRepository):
    collection_name = COLLECTIONS["submissions"]

    def find_by_assignment(self, assignment_id):
        return self.find_all({"assignment_id": assignment_id}, limit=100)

    def find_by_student_assignment(self, assignment_id, student_id):
        return self.find_one({"assignment_id": assignment_id, "student_id": student_id})

    def find_by_student(self, student_id, page=1, limit=50):
        return self.find_all(
            {"student_id": student_id},
            page=page,
            limit=limit,
            sort=[("submitted_at", -1)],
        )

    def delete_by_assignment(self, assignment_id):
        result = self.collection.delete_many({"assignment_id": assignment_id})
        return result.deleted_count


class AttendanceRepository(BaseRepository):
    collection_name = COLLECTIONS["attendance"]

    def find_by_class(self, class_id, page=1):
        return self.find_all({"class_id": class_id}, page=page, sort=[("date", -1)])


class AnnouncementRepository(BaseRepository):
    collection_name = COLLECTIONS["announcements"]

    def find_by_class(self, class_id, page=1):
        return self.find_all({"class_id": class_id}, page=page, sort=[("created_at", -1)])


class CommentRepository(BaseRepository):
    collection_name = COLLECTIONS["comments"]

    def find_by_post(self, post_id, page=1):
        return self.find_all({"post_id": post_id}, page=page, sort=[("created_at", 1)])


class LikeRepository(BaseRepository):
    collection_name = COLLECTIONS["likes"]

    def toggle(self, post_id, user_id):
        existing = self.collection.find_one({"post_id": post_id, "user_id": user_id})
        if existing:
            self.collection.delete_one({"_id": existing["_id"]})
            return False
        from datetime import datetime
        self.collection.insert_one({
            "post_id": post_id, "user_id": user_id, "created_at": datetime.utcnow(),
        })
        return True


class SpeakingRepository(BaseRepository):
    collection_name = COLLECTIONS["speaking_records"]


class WritingRepository(BaseRepository):
    collection_name = COLLECTIONS["writing_evaluations"]
