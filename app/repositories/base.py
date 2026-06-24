"""Base repository with common CRUD operations."""
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from app.extensions import get_db


class BaseRepository:
    collection_name = None

    @property
    def collection(self):
        return get_db()[self.collection_name]

    def _to_object_id(self, doc_id):
        try:
            return ObjectId(doc_id)
        except (InvalidId, TypeError):
            return None

    def _serialize(self, doc):
        if doc is None:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    def find_by_id(self, doc_id):
        oid = self._to_object_id(doc_id)
        if not oid:
            return None
        doc = self.collection.find_one({"_id": oid})
        return self._serialize(doc)

    def find_all(self, query=None, page=1, limit=20, sort=None):
        query = query or {}
        skip = (page - 1) * limit
        cursor = self.collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        total = self.collection.count_documents(query)
        docs = [self._serialize(d) for d in cursor.skip(skip).limit(limit)]
        return {"data": docs, "total": total, "page": page, "limit": limit}

    def create(self, data):
        data = dict(data)
        now = datetime.utcnow()
        data.setdefault("created_at", now)
        data["updated_at"] = now
        result = self.collection.insert_one(data)
        return self.find_by_id(result.inserted_id)

    def update(self, doc_id, data):
        oid = self._to_object_id(doc_id)
        if not oid:
            return None
        data = dict(data)
        data["updated_at"] = datetime.utcnow()
        self.collection.update_one({"_id": oid}, {"$set": data})
        return self.find_by_id(doc_id)

    def delete(self, doc_id):
        oid = self._to_object_id(doc_id)
        if not oid:
            return False
        result = self.collection.delete_one({"_id": oid})
        return result.deleted_count > 0

    def find_one(self, query):
        doc = self.collection.find_one(query)
        return self._serialize(doc)
