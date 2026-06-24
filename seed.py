"""Database seed script - run: python seed.py"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import get_db
from app.models.collections import COLLECTIONS
from app.utils.auth_utils import hash_password

CORE_USERS = [
    {
        "email": "admin@gmail.com",
        "password": "matkhau123",
        "full_name": "Quản trị viên",
        "role": "super_admin",
        "phone": "0901000000",
    },
    {
        "email": "giaovien@gmail.com",
        "password": "matkhau123",
        "full_name": "Nguyễn Thị Kim Chi",
        "role": "teacher",
        "phone": "0901549899",
        "profile": {
            "biography": "Giáo viên tiếng Anh giàu kinh nghiệm với hơn 15 năm tâm huyết giảng dạy tiếng Anh THPT tại Việt Nam.",
            "philosophy": "Học tiếng Anh phải thú vị, thiết thực và giúp học sinh tự tin giao tiếp.",
            "certifications": ["CELTA", "TEFL", "Chứng chỉ sư phạm"],
            "experience_years": 15,
            "specializations": ["Tiếng Anh cho thanh thiếu niên", "Kỹ năng nói", "Kỹ năng viết"],
            "achievements": ["Giáo viên xuất sắc 2023", "Huấn luyện viên Olympic tiếng Anh"],
            "subjects": ["Tiếng Anh THPT"],
        },
    },
    {
        "email": "hocsinh@gmail.com",
        "password": "matkhau123",
        "full_name": "Lê Minh Học",
        "role": "student",
        "phone": "0901000002",
    },
]

LEGACY_EMAILS = [
    "kimchiltv3@gmail.com",
    "teacher.demo@brightfuture.vn",
    "student.demo@brightfuture.vn",
    "parent.demo@brightfuture.vn",
]


def upsert_user(db, u):
    email = u["email"].lower()
    doc = {
        "email": email,
        "password_hash": hash_password(u["password"]),
        "full_name": u["full_name"],
        "role": u["role"],
        "phone": u.get("phone", ""),
        "avatar_url": u.get("avatar_url", ""),
        "is_verified": True,
        "is_active": True,
        "class_ids": u.get("class_ids", []),
        "student_ids": u.get("student_ids", []),
        "preferences": {"theme": "light", "language": "vi"},
        "updated_at": datetime.utcnow(),
    }
    if u.get("profile"):
        doc["profile"] = u["profile"]

    existing = db[COLLECTIONS["users"]].find_one({"email": email})
    if existing:
        db[COLLECTIONS["users"]].update_one({"email": email}, {"$set": doc})
        print(f"Updated {u['role']}: {email} / {u['password']}")
    else:
        doc["created_at"] = datetime.utcnow()
        db[COLLECTIONS["users"]].insert_one(doc)
        print(f"Created {u['role']}: {email} / {u['password']}")


def seed():
    app = create_app()
    with app.app_context():
        db = get_db()

        removed = db[COLLECTIONS["users"]].delete_many({"email": {"$in": LEGACY_EMAILS}})
        if removed.deleted_count:
            print(f"Removed {removed.deleted_count} legacy demo account(s)")

        for u in CORE_USERS:
            upsert_user(db, u)

        if db[COLLECTIONS["resources"]].count_documents({}) == 0:
            resources = [
                {"title": "Past Simple Tense", "description": "Grammar guide for Grade 10", "grade": "Grade 10", "skill": "Grammar", "category": "worksheet", "file_type": "pdf", "file_url": "", "cloudinary_id": "", "thumbnail_url": "", "uploaded_by": "", "downloads": 0},
                {"title": "Reading Comprehension Unit 1", "description": "Practice reading for Grade 11", "grade": "Grade 11", "skill": "Reading", "category": "worksheet", "file_type": "pdf", "file_url": "", "cloudinary_id": "", "thumbnail_url": "", "uploaded_by": "", "downloads": 0},
                {"title": "THPT Vocabulary List", "description": "Essential vocabulary for graduation exam", "grade": "THPT Graduation Exam", "skill": "Vocabulary", "category": "list", "file_type": "pdf", "file_url": "", "cloudinary_id": "", "thumbnail_url": "", "uploaded_by": "", "downloads": 0},
                {"title": "Listening Practice Audio", "description": "Grade 12 listening exercises", "grade": "Grade 12", "skill": "Listening", "category": "audio", "file_type": "audio", "file_url": "", "cloudinary_id": "", "thumbnail_url": "", "uploaded_by": "", "downloads": 0},
                {"title": "Speaking Topics Grade 10", "description": "Common speaking topics and sample answers", "grade": "Grade 10", "skill": "Speaking", "category": "guide", "file_type": "pdf", "file_url": "", "cloudinary_id": "", "thumbnail_url": "", "uploaded_by": "", "downloads": 0},
            ]
            for r in resources:
                r["created_at"] = datetime.utcnow()
                r["updated_at"] = datetime.utcnow()
            db[COLLECTIONS["resources"]].insert_many(resources)
            print(f"Seeded {len(resources)} resources")

        if db[COLLECTIONS["questions"]].count_documents({}) == 0:
            questions = [
                {"type": "mcq", "content": "She ___ to school every day.", "options": ["go", "goes", "going", "gone"], "correct_answer": "goes", "explanation": "Third person singular", "category": "Grammar", "skill": "Grammar", "grade": "Grade 10", "difficulty": "easy", "tags": ["present-simple"], "points": 1, "created_by": "", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
                {"type": "true_false", "content": "The past participle of 'write' is 'written'.", "options": ["True", "False"], "correct_answer": "True", "explanation": "write-wrote-written", "category": "Grammar", "skill": "Grammar", "grade": "Grade 10", "difficulty": "easy", "tags": ["irregular-verbs"], "points": 1, "created_by": "", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
                {"type": "gap_filling", "content": "I have ___ (live) here for 5 years.", "options": [], "correct_answer": "lived", "explanation": "Present perfect uses past participle", "category": "Grammar", "skill": "Grammar", "grade": "Grade 11", "difficulty": "medium", "tags": ["present-perfect"], "points": 2, "created_by": "", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
            ]
            db[COLLECTIONS["questions"]].insert_many(questions)
            print(f"Seeded {len(questions)} questions")

        if db[COLLECTIONS["documents"]].count_documents({}) == 0:
            docs = [
                {"title": "English Curriculum Grade 10", "description": "Official curriculum guidelines", "category": "Ministry Documents", "file_url": "", "file_type": "pdf", "uploaded_by": "", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
                {"title": "Teaching Guidelines 2026", "description": "Department teaching standards", "category": "Department Documents", "file_url": "", "file_type": "pdf", "uploaded_by": "", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
            ]
            db[COLLECTIONS["documents"]].insert_many(docs)
            print(f"Seeded {len(docs)} documents")

        if db[COLLECTIONS["posts"]].count_documents({}) == 0:
            teacher = db[COLLECTIONS["users"]].find_one({"email": "giaovien@gmail.com"})
            author_id = str(teacher["_id"]) if teacher else ""
            posts = [
                {"author_id": author_id, "title": "Welcome to Teacher Community!", "content": "Share your teaching experiences and resources here.", "category": "general", "tags": ["welcome"], "attachments": [], "likes_count": 5, "comments_count": 2, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
                {"author_id": author_id, "title": "Tips for THPT Exam Preparation", "content": "Focus on reading comprehension and gap-filling exercises.", "category": "experience", "tags": ["thpt", "exam"], "attachments": [], "likes_count": 12, "comments_count": 4, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
            ]
            db[COLLECTIONS["posts"]].insert_many(posts)
            print(f"Seeded {len(posts)} posts")

        if db[COLLECTIONS["entertainment"]].count_documents({}) == 0:
            items = [
                {"title": "Shape of You - Ed Sheeran", "category": "English Songs", "description": "Popular English song for listening practice", "media_url": "", "thumbnail_url": "", "duration": 240, "uploaded_by": "", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
                {"title": "The Little Prince", "category": "Short Stories", "description": "Classic short story in English", "media_url": "", "thumbnail_url": "", "duration": 0, "uploaded_by": "", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
            ]
            db[COLLECTIONS["entertainment"]].insert_many(items)
            print(f"Seeded {len(items)} entertainment items")

        if db[COLLECTIONS["albums"]].count_documents({}) == 0:
            albums = [
                {"title": "School English Festival 2025", "description": "Photos from the annual festival", "category": "School Activities", "cover_url": "", "media_ids": [], "created_by": "", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
                {"title": "English Speaking Competition", "description": "Student speaking competition photos", "category": "Competitions", "cover_url": "", "media_ids": [], "created_by": "", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
            ]
            db[COLLECTIONS["albums"]].insert_many(albums)
            print(f"Seeded {len(albums)} albums")

        print("Seed completed successfully!")


if __name__ == "__main__":
    seed()
