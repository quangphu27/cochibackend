"""Content and community schemas."""
from datetime import datetime

RESOURCE_SCHEMA = {
    "title": str,
    "description": str,
    "grade": str,
    "skill": str,
    "category": str,
    "file_type": str,
    "file_url": str,
    "cloudinary_id": str,
    "thumbnail_url": str,
    "uploaded_by": str,
    "downloads": int,
    "created_at": datetime,
}

DOCUMENT_SCHEMA = {
    "title": str,
    "description": str,
    "category": str,
    "file_url": str,
    "file_type": str,
    "uploaded_by": str,
    "created_at": datetime,
}

POST_SCHEMA = {
    "author_id": str,
    "title": str,
    "content": str,
    "category": str,
    "tags": list,
    "attachments": list,
    "likes_count": int,
    "comments_count": int,
    "created_at": datetime,
    "updated_at": datetime,
}

COMMENT_SCHEMA = {
    "post_id": str,
    "author_id": str,
    "content": str,
    "parent_id": str,
    "created_at": datetime,
}

MEDIA_SCHEMA = {
    "title": str,
    "type": str,
    "url": str,
    "cloudinary_id": str,
    "album_id": str,
    "category": str,
    "uploaded_by": str,
    "created_at": datetime,
}

ALBUM_SCHEMA = {
    "title": str,
    "description": str,
    "category": str,
    "cover_url": str,
    "media_ids": list,
    "created_by": str,
    "created_at": datetime,
}

ENTERTAINMENT_SCHEMA = {
    "title": str,
    "category": str,
    "description": str,
    "media_url": str,
    "thumbnail_url": str,
    "duration": int,
    "uploaded_by": str,
    "created_at": datetime,
}

NOTIFICATION_SCHEMA = {
    "user_id": str,
    "title": str,
    "message": str,
    "type": str,
    "read": bool,
    "link": str,
    "created_at": datetime,
}

AI_HISTORY_SCHEMA = {
    "user_id": str,
    "tool_type": str,
    "prompt": str,
    "response": str,
    "provider": str,
    "tokens_used": int,
    "created_at": datetime,
}
