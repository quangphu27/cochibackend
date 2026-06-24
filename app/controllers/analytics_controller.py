"""Analytics and dashboard API controller."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import get_db
from app.models.collections import COLLECTIONS
from app.middleware.auth_middleware import teacher_required
from app.services.analytics_service import (
    build_dashboard_charts,
    class_ranking,
    teacher_activity_ranking,
    efficiency_pct,
    normalize_period,
    period_range,
    previous_period_range,
    _count_created,
    _pct_change,
)

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard_stats():
    db = get_db()
    user_id = get_jwt_identity()
    from app.repositories.user_repo import UserRepository
    from app.repositories.content_repo import NotificationRepository
    user = UserRepository().find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    period = normalize_period(request.args.get("period"))
    role = user.get("role")

    stats = {
        "users": db[COLLECTIONS["users"]].count_documents({}),
        "students": db[COLLECTIONS["users"]].count_documents({"role": "student"}),
        "teachers": db[COLLECTIONS["users"]].count_documents({"role": "teacher"}),
        "classes": db[COLLECTIONS["classes"]].count_documents({}),
        "resources": db[COLLECTIONS["resources"]].count_documents({}),
        "exams": db[COLLECTIONS["exams"]].count_documents({}),
        "posts": db[COLLECTIONS["posts"]].count_documents({}),
    }

    class_ids: list[str] = []

    if role in ("teacher", "super_admin"):
        teacher_filter = {} if role == "super_admin" else {"teacher_id": user_id}
        stats["my_classes"] = db[COLLECTIONS["classes"]].count_documents(teacher_filter)
        teacher_classes = list(db[COLLECTIONS["classes"]].find(teacher_filter, {"_id": 1}))
        class_ids = [str(c["_id"]) for c in teacher_classes]
        stats["assignments"] = db[COLLECTIONS["assignments"]].count_documents({"class_id": {"$in": class_ids}}) if class_ids else 0
        agg = list(db[COLLECTIONS["classes"]].aggregate([
            {"$match": teacher_filter},
            {"$project": {"count": {"$size": {"$ifNull": ["$student_ids", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$count"}}},
        ]))
        stats["my_students"] = agg[0]["total"] if agg else 0
        if role == "teacher":
            stats["exams"] = db[COLLECTIONS["exams"]].count_documents({"class_id": {"$in": class_ids}}) if class_ids else 0

    if role == "student":
        stats["my_classes"] = len(user.get("class_ids", []))
        stats["my_results"] = db[COLLECTIONS["results"]].count_documents({"student_id": user_id})

    if role == "parent":
        child_ids = user.get("student_ids", [])
        stats["my_children"] = len(child_ids)
        stats["my_results"] = db[COLLECTIONS["results"]].count_documents({"student_id": {"$in": child_ids}}) if child_ids else 0
        stats["my_classes"] = 0

    unread = NotificationRepository().find_by_user(user_id, unread_only=True, limit=1)
    stats["unread_notifications"] = unread.get("total", 0)

    results = list(db[COLLECTIONS["results"]].find(
        {"student_id": user_id} if role == "student" else {},
        {"skill_scores": 1},
    ).limit(20))

    skill_totals = {}
    for r in results:
        for skill, scores in (r.get("skill_scores") or {}).items():
            skill_totals.setdefault(skill, {"earned": 0, "max": 0})
            skill_totals[skill]["earned"] += scores.get("earned", 0)
            skill_totals[skill]["max"] += scores.get("max", 0)

    stats["skill_performance"] = {
        k: round(v["earned"] / v["max"] * 100, 1) if v["max"] > 0 else 0
        for k, v in skill_totals.items()
    }

    charts = None
    ranking = []
    trends = {}
    efficiency = 0

    if role in ("teacher", "super_admin"):
        charts = build_dashboard_charts(db, COLLECTIONS, role, user_id, period, class_ids)
        if role == "super_admin":
            ranking = class_ranking(db, COLLECTIONS, teacher_id=None)
        else:
            ranking = class_ranking(db, COLLECTIONS, teacher_id=user_id)
            activity = teacher_activity_ranking(db, COLLECTIONS, class_ids)
            if activity:
                ranking = activity

        start, end = period_range(period)
        prev_start, prev_end = previous_period_range(period)
        if role == "super_admin":
            cur_users = _count_created(db, COLLECTIONS["users"], start, end)
            prev_users = _count_created(db, COLLECTIONS["users"], prev_start, prev_end)
            pct, up = _pct_change(cur_users, prev_users)
            trends["primary"] = {"label": "Người dùng mới", "pct": pct, "up": up}
        else:
            cur_students = stats["my_students"]
            prev_students = cur_students  # snapshot; use new users in classes as proxy
            exam_cur = _count_created(
                db, COLLECTIONS["exams"],
                start, end,
                {"class_id": {"$in": class_ids}} if class_ids else {"class_id": "__none__"},
            )
            exam_prev = _count_created(
                db, COLLECTIONS["exams"],
                prev_start, prev_end,
                {"class_id": {"$in": class_ids}} if class_ids else {"class_id": "__none__"},
            )
            pct, up = _pct_change(exam_cur, exam_prev)
            trends["primary"] = {"label": "Bài kiểm tra mới", "pct": pct, "up": up}

        efficiency = efficiency_pct(db, COLLECTIONS, role, user_id, class_ids)

    return jsonify({
        "stats": stats,
        "role": role,
        "period": period,
        "charts": charts,
        "ranking": ranking,
        "trends": trends,
        "efficiency_pct": efficiency,
    }), 200


@analytics_bp.route("/class/<class_id>", methods=["GET"])
@teacher_required
def class_analytics(class_id, current_user):
    db = get_db()
    exam_ids = [str(e["_id"]) for e in db[COLLECTIONS["exams"]].find({"class_id": class_id})]
    pipeline = [
        {"$match": {"exam_id": {"$in": exam_ids}}},
        {"$group": {
            "_id": "$student_id",
            "avg_score": {"$avg": "$final_score"},
            "total_exams": {"$sum": 1},
        }},
    ]
    student_stats = list(db[COLLECTIONS["results"]].aggregate(pipeline))

    return jsonify({
        "student_stats": [
            {"student_id": s["_id"], "avg_score": round(s["avg_score"], 1), "total_exams": s["total_exams"]}
            for s in student_stats
        ],
        "total_exams": len(exam_ids),
    }), 200
