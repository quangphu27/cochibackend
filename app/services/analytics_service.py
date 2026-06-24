"""Dashboard analytics — optimized aggregations (few MongoDB round-trips)."""
from datetime import datetime, timedelta


PERIOD_MAP = {
    "today": "today",
    "week": "week",
    "month": "month",
    "year": "year",
    "hom_nay": "today",
    "tuan_nay": "week",
    "thang_nay": "month",
    "nam_nay": "year",
}


def normalize_period(raw: str | None) -> str:
    if not raw:
        return "month"
    key = raw.strip().lower().replace(" ", "_")
    return PERIOD_MAP.get(key, "month")


def period_range(period: str, now: datetime | None = None):
    now = now or datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now
    if period == "week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now
    if period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now
    start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def previous_period_range(period: str, now: datetime | None = None):
    now = now or datetime.utcnow()
    start, end = period_range(period, now)
    delta = end - start
    prev_end = start
    prev_start = prev_end - delta
    return prev_start, prev_end


def _count_created(db, collection: str, start: datetime, end: datetime, extra_match: dict | None = None) -> int:
    match = {"created_at": {"$gte": start, "$lte": end}}
    if extra_match:
        match.update(extra_match)
    return db[collection].count_documents(match)


def _series_calendar_months(db, collection: str, extra_match: dict | None = None, year: int | None = None):
    """One aggregation: counts per month in a calendar year."""
    year = year or datetime.utcnow().year
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31, 23, 59, 59)
    match: dict = {"created_at": {"$gte": start, "$lte": end}}
    if extra_match:
        match.update(extra_match)
    pipeline = [
        {"$match": match},
        {"$group": {"_id": {"$month": "$created_at"}, "count": {"$sum": 1}}},
    ]
    counts = {row["_id"]: row["count"] for row in db[collection].aggregate(pipeline)}
    now = datetime.utcnow()
    last_month = now.month if year == now.year else 12
    labels = [f"T{m}" for m in range(1, last_month + 1)]
    values = [counts.get(m, 0) for m in range(1, last_month + 1)]
    return labels, values


def _series_by_day(db, collection: str, start: datetime, end: datetime, extra_match: dict | None = None):
    """One aggregation: counts per day in range."""
    match: dict = {"created_at": {"$gte": start, "$lte": end}}
    if extra_match:
        match.update(extra_match)
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%d/%m", "date": "$created_at"},
                },
                "count": {"$sum": 1},
            },
        },
        {"$sort": {"_id": 1}},
    ]
    rows = list(db[collection].aggregate(pipeline))
    return [r["_id"] for r in rows], [r["count"] for r in rows]


def _pct_change(current: int, previous: int) -> tuple[float | None, bool | None]:
    if previous <= 0:
        if current > 0:
            return 100.0, True
        return None, None
    change = round((current - previous) / previous * 100, 1)
    return abs(change), change >= 0


def class_ranking(db, collections_module, teacher_id: str | None = None, limit: int = 7):
    col = collections_module["classes"]
    query = {"teacher_id": teacher_id} if teacher_id else {}
    classes = list(db[col].find(query, {"name": 1, "student_ids": 1}).limit(50))
    ranked = sorted(classes, key=lambda c: len(c.get("student_ids") or []), reverse=True)[:limit]
    return [
        {
            "id": str(c["_id"]),
            "name": c.get("name", "Lớp học"),
            "value": len(c.get("student_ids") or []),
        }
        for c in ranked
    ]


def teacher_activity_ranking(db, collections_module, class_ids: list[str], limit: int = 7):
    if not class_ids:
        return []
    exams = list(db[collections_module["exams"]].find(
        {"class_id": {"$in": class_ids}},
        {"title": 1},
    ))
    exam_ids = [str(e["_id"]) for e in exams]
    exam_titles = {str(e["_id"]): e.get("title", "Bài kiểm tra") for e in exams}

    result_counts: dict[str, int] = {}
    if exam_ids:
        pipeline = [
            {"$match": {"exam_id": {"$in": exam_ids}}},
            {"$group": {"_id": "$exam_id", "count": {"$sum": 1}}},
        ]
        for row in db[collections_module["results"]].aggregate(pipeline):
            result_counts[row["_id"]] = row["count"]

    assignments = list(db[collections_module["assignments"]].find(
        {"class_id": {"$in": class_ids}},
        {"title": 1},
    ))
    assignment_ids = [str(a["_id"]) for a in assignments]
    assign_titles = {str(a["_id"]): a.get("title", "Bài tập") for a in assignments}

    assignment_counts: dict[str, int] = {}
    if assignment_ids:
        pipeline = [
            {"$match": {"assignment_id": {"$in": assignment_ids}}},
            {"$group": {"_id": "$assignment_id", "count": {"$sum": 1}}},
        ]
        for row in db[collections_module["submissions"]].aggregate(pipeline):
            assignment_counts[row["_id"]] = row["count"]

    items = []
    for eid, count in result_counts.items():
        items.append({"name": exam_titles.get(eid, "Bài kiểm tra"), "value": count})
    for aid, count in assignment_counts.items():
        items.append({"name": assign_titles.get(aid, "Bài tập"), "value": count})

    items.sort(key=lambda x: x["value"], reverse=True)
    return items[:limit]


def efficiency_pct(db, collections_module, role: str, user_id: str, class_ids: list[str]) -> int:
    if role == "super_admin":
        total_exams = db[collections_module["exams"]].estimated_document_count()
        if total_exams == 0:
            return 0
        pipeline = [
            {"$group": {"_id": "$exam_id"}},
            {"$count": "n"},
        ]
        rows = list(db[collections_module["results"]].aggregate(pipeline))
        with_results = rows[0]["n"] if rows else 0
        return min(100, round(with_results / total_exams * 100))

    if not class_ids:
        return 0

    assignment_ids = [
        str(a["_id"]) for a in db[collections_module["assignments"]].find(
            {"class_id": {"$in": class_ids}}, {"_id": 1},
        )
    ]
    exam_ids = [
        str(e["_id"]) for e in db[collections_module["exams"]].find(
            {"class_id": {"$in": class_ids}}, {"_id": 1},
        )
    ]

    graded = 0
    total_submissions = 0
    if assignment_ids:
        pipeline = [
            {"$match": {"assignment_id": {"$in": assignment_ids}}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        for row in db[collections_module["submissions"]].aggregate(pipeline):
            total_submissions += row["count"]
            if row["_id"] == "graded":
                graded = row["count"]

    exam_done = 0
    if exam_ids:
        exam_done = db[collections_module["results"]].count_documents({"exam_id": {"$in": exam_ids}})

    denom = total_submissions + len(exam_ids)
    if denom == 0:
        return 0
    return min(100, round((graded + exam_done) / denom * 100))


def build_dashboard_charts(db, collections_module, role: str, user_id: str, period: str, class_ids: list[str]):
    start, end = period_range(period)
    is_admin = role == "super_admin"

    if is_admin:
        series_defs = [
            (collections_module["users"], None),
            (collections_module["classes"], None),
        ]
        series_labels = ["Người dùng", "Lớp học"]
    else:
        class_filter = {"class_id": {"$in": class_ids}} if class_ids else {"class_id": "__none__"}
        series_defs = [
            (collections_module["exams"], class_filter),
            (collections_module["assignments"], class_filter),
        ]
        series_labels = ["Bài kiểm tra", "Bài tập"]

    if period in ("month", "year"):
        labels = None
        all_series = []
        for col, extra in series_defs:
            month_labels, values = _series_calendar_months(db, col, extra)
            if labels is None:
                labels = month_labels
            all_series.append(values)
        growth = {"labels": labels or [], "series": all_series}
    else:
        labels = None
        all_series = []
        for col, extra in series_defs:
            day_labels, values = _series_by_day(db, col, start, end, extra)
            if labels is None:
                labels = day_labels
            all_series.append(values)
        growth = {"labels": labels or [], "series": all_series}

    return {
        "growth": {
            "labels": growth["labels"],
            "datasets": [
                {"label": series_labels[i], "data": growth["series"][i]}
                for i in range(len(series_labels))
            ],
        },
        "date_range": {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
        },
    }


def count_users_by_role(db, users_col: str) -> dict[str, int]:
    """Single aggregation for user role counts."""
    pipeline = [
        {"$group": {"_id": "$role", "count": {"$sum": 1}}},
    ]
    rows = {r["_id"]: r["count"] for r in db[users_col].aggregate(pipeline)}
    total = sum(rows.values())
    return {
        "users": total,
        "students": rows.get("student", 0),
        "teachers": rows.get("teacher", 0),
    }
