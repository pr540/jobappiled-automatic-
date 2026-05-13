"""Dashboard API — summary stats."""
from flask import Blueprint, jsonify
from core.database import db, Job, RecruiterOutreach
from core.logger import get_logger
from sqlalchemy import func

dashboard_bp = Blueprint("dashboard", __name__)
log = get_logger("dashboard")

_ZERO_STATS = {
    "total_jobs_scanned": 0,
    "jobs_applied": 0,
    "interview_calls": 0,
    "rejected": 0,
    "pending": 0,
    "avg_ats_score": 0.0,
    "recruiters_contacted": 0,
    "recruiter_replies": 0,
}


@dashboard_bp.get("/stats")
def get_stats():
    try:
        total    = db.session.query(func.count(Job.id)).scalar() or 0
        applied  = db.session.query(func.count(Job.id)).filter(Job.status == "applied").scalar() or 0
        interv   = db.session.query(func.count(Job.id)).filter(Job.status == "interview").scalar() or 0
        rejected = db.session.query(func.count(Job.id)).filter(Job.status == "rejected").scalar() or 0
        pending  = db.session.query(func.count(Job.id)).filter(Job.status == "pending").scalar() or 0
        avg_ats  = db.session.query(func.avg(Job.ats_score)).scalar() or 0.0
        recruiters      = db.session.query(func.count(RecruiterOutreach.id)).scalar() or 0
        recruiter_replies = db.session.query(func.count(RecruiterOutreach.id)).filter(
            RecruiterOutreach.replied == True  # noqa: E712
        ).scalar() or 0
        return jsonify({
            "total_jobs_scanned": total,
            "jobs_applied": applied,
            "interview_calls": interv,
            "rejected": rejected,
            "pending": pending,
            "avg_ats_score": round(float(avg_ats), 1),
            "recruiters_contacted": recruiters,
            "recruiter_replies": recruiter_replies,
        })
    except Exception as e:
        db.session.rollback()
        log.error(f"dashboard/stats failed: {e}")
        return jsonify(_ZERO_STATS)


@dashboard_bp.get("/recent-jobs")
def recent_jobs():
    try:
        jobs = (
            db.session.query(Job)
            .order_by(Job.created_at.desc())
            .limit(20)
            .all()
        )
        return jsonify([{
            "id": j.id,
            "platform": j.platform,
            "title": j.title,
            "company": j.company or "",
            "location": j.location or "",
            "ats_score": j.ats_score or 0,
            "status": j.status,
            "job_url": j.job_url or "",
            "applied_at": j.applied_at.isoformat() if j.applied_at else None,
        } for j in jobs])
    except Exception as e:
        db.session.rollback()
        log.error(f"dashboard/recent-jobs failed: {e}")
        return jsonify([])
