"""
analytics.py — Analytics Module
==================================
Calculates and returns analytics data for owner spaces.

Routes:
  GET /api/spaces/<space_id>/analytics  — Summary stats + rating distribution + trends

All calculations use real MongoDB data — no hardcoded values.
"""

from collections import defaultdict
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from flask import Blueprint, request, jsonify, g

from auth import login_required
from database import get_db
from utils import success_response, error_response, is_valid_object_id, utcnow

analytics_bp = Blueprint("analytics", __name__)


def calculate_average_rating(db, space_id):
    """
    Calculate the average star rating for approved testimonials in a space.

    Uses MongoDB aggregation:
    1. Match approved testimonials with a non-null rating.
    2. Group them and compute the average.

    Returns a float rounded to 1 decimal place, or None if no ratings exist.
    """
    pipeline = [
        {"$match": {
            "space_id": ObjectId(space_id),
            "status": "approved",
            "rating": {"$ne": None, "$exists": True}
        }},
        {"$group": {
            "_id": None,
            "average": {"$avg": "$rating"},
            "count": {"$sum": 1}
        }}
    ]
    result = list(db.testimonials.aggregate(pipeline))
    if not result:
        return None, 0
    return round(result[0]["average"], 1), result[0]["count"]


def calculate_rating_distribution(db, space_id):
    """
    Count how many approved testimonials have each star rating (1–5).

    Returns a dict like: { "1": 2, "2": 0, "3": 5, "4": 12, "5": 30 }
    """
    pipeline = [
        {"$match": {
            "space_id": ObjectId(space_id),
            "status": "approved",
            "rating": {"$ne": None, "$exists": True}
        }},
        {"$group": {
            "_id": "$rating",
            "count": {"$sum": 1}
        }}
    ]
    result = list(db.testimonials.aggregate(pipeline))

    # Build a complete dict for ratings 1-5 (filling 0 for missing)
    distribution = {str(i): 0 for i in range(1, 6)}
    for item in result:
        if item["_id"] is not None:
            distribution[str(item["_id"])] = item["count"]

    return distribution


def calculate_submission_trend(db, space_id, days=30):
    """
    Count testimonial submissions per day for the last N days.

    Returns a list of { date: "YYYY-MM-DD", count: N } dicts,
    one entry per day, starting from (today - days) up to today.

    This is used by the Chart.js line chart on the analytics page.
    """
    start_date = utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {
            "space_id": ObjectId(space_id),
            "submitted_at": {"$gte": start_date}
        }},
        {"$group": {
            "_id": {
                "year": {"$year": "$submitted_at"},
                "month": {"$month": "$submitted_at"},
                "day": {"$dayOfMonth": "$submitted_at"},
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}}
    ]

    result = list(db.testimonials.aggregate(pipeline))

    # Build a complete day-by-day list (with 0 for days with no submissions)
    day_map = {}
    for item in result:
        d = item["_id"]
        date_str = f"{d['year']:04d}-{d['month']:02d}-{d['day']:02d}"
        day_map[date_str] = item["count"]

    trend = []
    for i in range(days + 1):
        date = start_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        trend.append({"date": date_str, "count": day_map.get(date_str, 0)})

    return trend


@analytics_bp.route("/api/spaces/<space_id>/analytics", methods=["GET"])
@login_required
def get_space_analytics(space_id):
    """
    GET /api/spaces/<space_id>/analytics
    Return comprehensive analytics data for a single space.

    Includes:
    - Summary counts (total, approved, pending, rejected, archived, featured)
    - Average star rating
    - Rating distribution (1–5 star counts)
    - Submission trend (daily counts for the last 30 days)
    - Recent testimonials (last 5)
    """
    if not is_valid_object_id(space_id):
        return jsonify(error_response("Invalid space ID.", 400)[0]), 400

    owner_id = g.current_owner["_id"]
    db = get_db()

    # Verify ownership
    space = db.spaces.find_one({"_id": ObjectId(space_id), "owner_id": owner_id})
    if not space:
        return jsonify(error_response("Space not found.", 404)[0]), 404

    space_oid = space["_id"]

    # --- Summary counts ---
    total = db.testimonials.count_documents({"space_id": space_oid})
    approved = db.testimonials.count_documents({"space_id": space_oid, "status": "approved"})
    pending = db.testimonials.count_documents({"space_id": space_oid, "status": "pending"})
    rejected = db.testimonials.count_documents({"space_id": space_oid, "status": "rejected"})
    archived = db.testimonials.count_documents({"space_id": space_oid, "status": "archived"})
    featured = db.testimonials.count_documents({"space_id": space_oid, "is_featured": True})

    # --- Average rating (approved only) ---
    avg_rating, rated_count = calculate_average_rating(db, space_oid)

    # --- Rating distribution ---
    distribution = calculate_rating_distribution(db, space_oid)

    # --- Submission trend ---
    trend_days = int(request.args.get("trend_days", 30))
    trend_days = max(7, min(90, trend_days))  # clamp between 7 and 90
    trend = calculate_submission_trend(db, space_oid, trend_days)

    return jsonify(success_response({
        "space_name": space["name"],
        "space_slug": space["slug"],
        "enable_star_rating": space.get("enable_star_rating", True),
        "summary": {
            "total": total,
            "approved": approved,
            "pending": pending,
            "rejected": rejected,
            "archived": archived,
            "featured": featured,
        },
        "average_rating": avg_rating,
        "rated_count": rated_count,
        "rating_distribution": distribution,
        "submission_trend": trend,
        "trend_days": trend_days,
    })[0]), 200


@analytics_bp.route("/api/dashboard/overview", methods=["GET"])
@login_required
def get_dashboard_overview():
    """
    GET /api/dashboard/overview
    Return aggregated metrics across ALL spaces for the dashboard home page.
    """
    owner_id = g.current_owner["_id"]
    db = get_db()

    # Get all space IDs for this owner
    space_ids = [s["_id"] for s in db.spaces.find({"owner_id": owner_id}, {"_id": 1})]
    total_spaces = len(space_ids)

    if not space_ids:
        return jsonify(success_response({
            "total_spaces": 0,
            "total_testimonials": 0,
            "pending": 0,
            "approved": 0,
            "average_rating": None,
            "featured": 0,
            "recent_testimonials": [],
            "rating_distribution": {str(i): 0 for i in range(1, 6)},
        })[0]), 200

    query_base = {"space_id": {"$in": space_ids}}

    total = db.testimonials.count_documents(query_base)
    pending = db.testimonials.count_documents({**query_base, "status": "pending"})
    approved = db.testimonials.count_documents({**query_base, "status": "approved"})
    featured = db.testimonials.count_documents({**query_base, "is_featured": True})

    # Average rating across all spaces (approved with rating)
    pipeline = [
        {"$match": {**query_base, "status": "approved", "rating": {"$ne": None, "$exists": True}}},
        {"$group": {"_id": None, "average": {"$avg": "$rating"}}}
    ]
    avg_result = list(db.testimonials.aggregate(pipeline))
    avg_rating = round(avg_result[0]["average"], 1) if avg_result else None

    # Rating distribution across all spaces
    dist_pipeline = [
        {"$match": {**query_base, "status": "approved", "rating": {"$ne": None, "$exists": True}}},
        {"$group": {"_id": "$rating", "count": {"$sum": 1}}}
    ]
    dist_result = list(db.testimonials.aggregate(dist_pipeline))
    distribution = {str(i): 0 for i in range(1, 6)}
    for item in dist_result:
        if item["_id"] is not None:
            distribution[str(item["_id"])] = item["count"]

    # Recent testimonials (last 5)
    recent = list(
        db.testimonials.find(query_base)
        .sort("submitted_at", -1)
        .limit(5)
    )

    # Enrich with space name
    space_name_map = {
        s["_id"]: s["name"]
        for s in db.spaces.find({"owner_id": owner_id}, {"name": 1})
    }

    recent_serialized = []
    for t in recent:
        doc = {
            "id": str(t["_id"]),
            "customer_name": t["customer_name"],
            "company_name": t.get("company_name", ""),
            "rating": t.get("rating"),
            "status": t["status"],
            "submitted_at": t["submitted_at"].isoformat(),
            "space_name": space_name_map.get(t["space_id"], "Unknown"),
            "space_id": str(t["space_id"]),
            "review_text": t["review_text"][:100] + ("..." if len(t["review_text"]) > 100 else ""),
        }
        recent_serialized.append(doc)

    # Recent moderation activity
    recent_activity = list(
        db.moderation_logs.find({"owner_id": owner_id})
        .sort("created_at", -1)
        .limit(10)
    )
    activity_serialized = []
    for a in recent_activity:
        activity_serialized.append({
            "id": str(a["_id"]),
            "action": a["action"],
            "prev_status": a.get("prev_status"),
            "new_status": a.get("new_status"),
            "created_at": a["created_at"].isoformat(),
        })

    return jsonify(success_response({
        "total_spaces": total_spaces,
        "total_testimonials": total,
        "pending": pending,
        "approved": approved,
        "featured": featured,
        "average_rating": avg_rating,
        "rating_distribution": distribution,
        "recent_testimonials": recent_serialized,
        "recent_activity": activity_serialized,
    })[0]), 200


@analytics_bp.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    """
    GET /api/notifications
    Return the current owner's notifications (most recent first).
    """
    owner_id = g.current_owner["_id"]
    db = get_db()

    unread_count = db.notifications.count_documents({"owner_id": owner_id, "is_read": False})
    notifications = list(
        db.notifications.find({"owner_id": owner_id})
        .sort("created_at", -1)
        .limit(20)
    )

    result = []
    for n in notifications:
        result.append({
            "id": str(n["_id"]),
            "title": n["title"],
            "message": n["message"],
            "type": n.get("type", "info"),
            "is_read": n.get("is_read", False),
            "created_at": n["created_at"].isoformat(),
        })

    return jsonify(success_response({"notifications": result, "unread_count": unread_count})[0]), 200


@analytics_bp.route("/api/notifications/mark-read", methods=["POST"])
@login_required
def mark_notifications_read():
    """POST /api/notifications/mark-read — Mark all notifications as read."""
    owner_id = g.current_owner["_id"]
    db = get_db()
    db.notifications.update_many({"owner_id": owner_id}, {"$set": {"is_read": True}})
    return jsonify(success_response(message="All notifications marked as read.")[0]), 200
