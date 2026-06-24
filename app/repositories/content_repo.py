"""Content repositories."""
from app.models.collections import COLLECTIONS
from app.repositories.base import BaseRepository


class ResourceRepository(BaseRepository):
    collection_name = COLLECTIONS["resources"]

    def find_by_grade_skill(self, grade=None, skill=None, page=1, limit=20):
        query = {}
        if grade:
            query["grade"] = grade
        if skill:
            query["skill"] = skill
        return self.find_all(query, page=page, limit=limit)


class PostRepository(BaseRepository):
    collection_name = COLLECTIONS["posts"]

    def find_by_category(self, category, page=1, limit=20):
        return self.find_all({"category": category}, page=page, limit=limit, sort=[("created_at", -1)])


class DocumentRepository(BaseRepository):
    collection_name = COLLECTIONS["documents"]

    def find_by_category(self, category, page=1, limit=20):
        return self.find_all({"category": category}, page=page, limit=limit)


class NotificationRepository(BaseRepository):
    collection_name = COLLECTIONS["notifications"]

    def find_by_user(self, user_id, unread_only=False, page=1, limit=20):
        query = {"user_id": user_id}
        if unread_only:
            query["read"] = False
        return self.find_all(query, page=page, limit=limit, sort=[("created_at", -1)])

    def mark_read(self, notification_id):
        return self.update(notification_id, {"read": True})

    def mark_all_read(self, user_id):
        self.collection.update_many({"user_id": user_id, "read": False}, {"$set": {"read": True}})
