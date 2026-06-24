"""Class management service."""
from bson import ObjectId
from app.repositories.class_repo import ClassRepository
from app.repositories.user_repo import UserRepository
from app.utils.auth_utils import generate_class_code
from app.repositories.content_repo import NotificationRepository

class_repo = ClassRepository()
user_repo = UserRepository()
notification_repo = NotificationRepository()


def _strip_user(user):
    if user:
        user.pop("password_hash", None)
    return user


class ClassService:
    def create_class(self, teacher_id, data):
        class_code = generate_class_code()
        while class_repo.find_by_code(class_code):
            class_code = generate_class_code()

        class_data = class_repo.create({
            "name": data["name"],
            "description": data.get("description", ""),
            "class_code": class_code,
            "teacher_id": teacher_id,
            "student_ids": [],
            "parent_ids": [],
            "grade": data.get("grade", ""),
            "subject": data.get("subject", "English"),
            "schedule": data.get("schedule", []),
            "is_active": True,
        })
        return class_data, 201

    def join_class(self, student_id, class_code):
        cls = class_repo.find_by_code(class_code)
        if not cls:
            return {"error": "Invalid class code"}, 404

        if student_id in cls.get("student_ids", []):
            return {"message": "Already in class", "class": cls}, 200

        class_repo.add_student(cls["id"], student_id)
        oid = user_repo._to_object_id(student_id)
        if oid:
            user_repo.collection.update_one(
                {"_id": oid},
                {"$addToSet": {"class_ids": cls["id"]}},
            )

        notification_repo.create({
            "user_id": cls["teacher_id"],
            "title": "New Student Joined",
            "message": f"A student joined class {cls['name']}",
            "type": "class",
            "read": False,
            "link": f"/classes/{cls['id']}",
        })

        return {"message": "Joined class successfully", "class": cls}, 200

    def get_user_classes(self, user_id, role, page=1):
        if role in ("teacher", "super_admin"):
            return class_repo.find_by_teacher(user_id, page=page)
        return class_repo.find_by_student(user_id, page=page)

    def get_class_details(self, class_id):
        cls = class_repo.find_by_id(class_id)
        if not cls:
            return {"error": "Class not found"}, 404
        students = [_strip_user(user_repo.find_by_id(sid)) for sid in cls.get("student_ids", [])]
        cls["students"] = [s for s in students if s]
        teacher = _strip_user(user_repo.find_by_id(cls.get("teacher_id", "")))
        cls["teacher"] = teacher
        return cls, 200

    def _assert_teacher_of_class(self, class_id, user_id, role):
        cls = class_repo.find_by_id(class_id)
        if not cls:
            return None, ({"error": "Class not found"}, 404)
        if role != "super_admin" and cls.get("teacher_id") != user_id:
            return None, ({"error": "Insufficient permissions"}, 403)
        return cls, None

    def add_student_by_email(self, class_id, email, teacher_id, role):
        cls, err = self._assert_teacher_of_class(class_id, teacher_id, role)
        if err:
            return err[0], err[1]

        student = user_repo.find_by_email(email.strip())
        if not student or student.get("role") != "student":
            return {"error": "Không tìm thấy học sinh với email này"}, 404

        student_id = student["id"]
        if student_id in cls.get("student_ids", []):
            return {"message": "Học sinh đã có trong lớp", "student": _strip_user(student)}, 200

        class_repo.add_student(class_id, student_id)
        oid = user_repo._to_object_id(student_id)
        if oid:
            user_repo.collection.update_one(
                {"_id": oid},
                {"$addToSet": {"class_ids": class_id}},
            )

        notification_repo.create({
            "user_id": student_id,
            "title": "Bạn được thêm vào lớp học",
            "message": f"Bạn đã được thêm vào lớp {cls['name']}",
            "type": "class",
            "read": False,
            "link": f"/classes/{class_id}",
        })

        return {"message": "Đã thêm học sinh vào lớp", "student": _strip_user(student)}, 200

    def remove_student(self, class_id, student_id, teacher_id, role):
        cls, err = self._assert_teacher_of_class(class_id, teacher_id, role)
        if err:
            return err[0], err[1]

        if student_id not in cls.get("student_ids", []):
            return {"error": "Học sinh không có trong lớp"}, 404

        class_repo.remove_student(class_id, student_id)
        oid = user_repo._to_object_id(student_id)
        if oid:
            user_repo.collection.update_one(
                {"_id": oid},
                {"$pull": {"class_ids": class_id}},
            )

        return {"message": "Đã xóa học sinh khỏi lớp"}, 200
