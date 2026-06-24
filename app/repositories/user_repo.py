"""User repository."""
from app.models.collections import COLLECTIONS
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    collection_name = COLLECTIONS["users"]

    def find_by_email(self, email):
        return self.find_one({"email": email.lower()})

    def find_by_role(self, role, page=1, limit=20):
        return self.find_all({"role": role}, page=page, limit=limit)

    def find_by_class(self, class_id):
        return self.find_all({"class_ids": class_id}, limit=100)
