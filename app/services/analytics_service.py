"""Dashboard analytics aggregations from real database data."""
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
        return "year"
    key = raw.strip().lower().replace(" ", "_")
    return PERIOD_MAP.get(key, "year")


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
    # year
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


def _count_submitted(db, collection: str, start: datetime, end: datetime, extra_match: dict | None = None) -> int:
    match = {"submitted_at": {"$gte": start, "$lte": end}}
    if extra_match:
        match.update(extra_match)
    return db[collection].count_documents(match)


def _growth_by_year(db, collections: list[tuple[str, dict | None]], years: int = 6):
    now = datetime.utcnow()
    labels = []
    series = [[] for _ in collections]
    for i in range(years - 1, -1, -1):
        year = now.year - i
        labels.append(str(year))
        y_start = datetime(year, 1, 1)
        y_end = datetime(year, 12, 31, 23, 59, 59)
        for idx, (col, extra) in enumerate(collections):
            series[idx].append(_count_created(db, col, y_start, y_end, extra))
    return {"labels": labels, "series": series}


def _growth_by_month(db, collections: list[tuple[str, dict | None]], year: int | None = None):
    year = year or datetime.utcnow().year
    labels = [f"T{m}" for m in range(1, 13)]
    series = [[] for _ in collections]
    for month in range(1, 13):
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year, 12, 31, 23, 59, 59)
        else:
            end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        for idx, (col, extra) in enumerate(collections):
            series[idx].append(_count_created(db, col, start, end, extra))
    return {"labels": labels, "series": series}


def _growth_by_day(db, collections: list[tuple[str, dict | None]], start: datetime, end: datetime):
    labels = []
    series = [[] for _ in collections]
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= end:
        labels.append(day.strftime("%d/%m"))
        day_end = day + timedelta(days=1) - timedelta(seconds=1)
        for idx, (col, extra) in enumerate(collections):
            series[idx].append(_count_created(db, col, day, min(day_end, end), extra))
        day += timedelta(days=1)
    return {"labels": labels, "series": series}


def _weekly_activity(db, collection: str, date_field: str, match: dict | None, start: datetime, end: datetime):
    weekday_labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    values = [0] * 7
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= end:
        day_end = day + timedelta(days=1) - timedelta(seconds=1)
        q = {date_field: {"$gte": day, "$lte": min(day_end, end)}}
        if match:
            q.update(match)
        idx = day.weekday()
        values[idx] += db[collection].count_documents(q)
        day += timedelta(days=1)
    return {"labels": weekday_labels, "values": values}


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
    classes = list(db[col].find(query, {"name": 1, "student_ids": 1, "grade": 1}))
    ranked = sorted(
        classes,
        key=lambda c: len(c.get("student_ids") or []),
        reverse=True,
    )[:limit]
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
        {"title": 1, "class_id": 1},
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

    assignment_counts: dict[str, int] = {}
    assignments = list(db[collections_module["assignments"]].find(
        {"class_id": {"$in": class_ids}},
        {"title": 1},
    ))
    assignment_ids = [str(a["_id"]) for a in assignments]
    assign_titles = {str(a["_id"]): a.get("title", "Bài tập") for a in assignments}
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
        total_exams = db[collections_module["exams"]].count_documents({})
        if total_exams == 0:
            return 0
        with_results = len(db[collections_module["results"]].distinct("exam_id"))
        return min(100, round(with_results / total_exams * 100))

    # teacher
    if not class_ids:
        return 0
    total_assignments = db[collections_module["assignments"]].count_documents({"class_id": {"$in": class_ids}})
    total_submissions = db[collections_module["submissions"]].count_documents({
        "assignment_id": {"$in": [
            str(a["_id"]) for a in db[collections_module["assignments"]].find(
                {"class_id": {"$in": class_ids}}, {"_id": 1},
            )
        ]},
    }) if total_assignments else 0
    graded = db[collections_module["submissions"]].count_documents({
        "status": "graded",
        "assignment_id": {"$in": [
            str(a["_id"]) for a in db[collections_module["assignments"]].find(
                {"class_id": {"$in": class_ids}}, {"_id": 1},
            )
        ]},
    }) if total_assignments else 0

    exam_ids = [str(e["_id"]) for e in db[collections_module["exams"]].find({"class_id": {"$in": class_ids}}, {"_id": 1})]
    exam_done = db[collections_module["results"]].count_documents({"exam_id": {"$in": exam_ids}}) if exam_ids else 0

    denom = total_submissions + len(exam_ids)
    if denom == 0:
        return 0
    numer = graded + exam_done
    return min(100, round(numer / denom * 100))


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
        series_defs = [
            (collections_module["exams"], {"class_id": {"$in": class_ids}} if class_ids else {"class_id": "__none__"}),
            (collections_module["assignments"], {"class_id": {"$in": class_ids}} if class_ids else {"class_id": "__none__"}),
        ]
        series_labels = ["Bài kiểm tra", "Bài tập"]

    if period == "year":
        growth = _growth_by_year(db, series_defs)
    elif period == "month":
        growth = _growth_by_month(db, series_defs)
    else:
        growth = _growth_by_day(db, series_defs, start, end)

    activity_col = collections_module["results"]
    activity_field = "submitted_at"
    activity_match = None
    if role == "teacher" and class_ids:
        exam_ids = [str(e["_id"]) for e in db[collections_module["exams"]].find({"class_id": {"$in": class_ids}}, {"_id": 1})]
        activity_match = {"exam_id": {"$in": exam_ids}} if exam_ids else {"exam_id": "__none__"}
    elif role == "super_admin":
        activity_col = collections_module["users"]
        activity_field = "created_at"

    weekly = _weekly_activity(db, activity_col, activity_field, activity_match, start, end)

    # Monthly line for metric card — current year months up to now
    monthly = _growth_by_month(db, series_defs[:1])

    return {
        "growth": {
            "labels": growth["labels"],
            "datasets": [
                {"label": series_labels[i], "data": growth["series"][i]}
                for i in range(len(series_labels))
            ],
        },
        "weekly_activity": weekly,
        "monthly_trend": {
            "labels": monthly["labels"][: datetime.utcnow().month],
            "values": monthly["series"][0][: datetime.utcnow().month],
        },
        "date_range": {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
        },
    }
