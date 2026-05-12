"""Dashboard API — summary stats."""
from flask import Blueprint, jsonify
from core.database import db, Job, RecruiterOutreach, DailyReport
from sqlalchemy import func

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/stats")
def get_stats():
    total = db.session.query(func.count(Job.id)).scalar()
    applied = db.session.query(func.count(Job.id)).filter_by(status="applied").scalar()
    interviews = db.session.query(func.count(Job.id)).filter_by(status="interview").scalar()
    rejected = db.session.query(func.count(Job.id)).filter_by(status="rejected").scalar()
    pending = db.session.query(func.count(Job.id)).filter_by(status="pending").scalar()
    avg_ats = db.session.query(func.avg(Job.ats_score)).scalar() or 0
    recruiters = db.session.query(func.count(RecruiterOutreach.id)).scalar()
    recruiter_replies = db.session.query(func.count(RecruiterOutreach.id)).filter_by(replied=True).scalar()

    return jsonify({
        "total_jobs_scanned": total,
        "jobs_applied": applied,
        "interview_calls": interviews,
        "rejected": rejected,
        "pending": pending,
        "avg_ats_score": round(float(avg_ats), 1),
        "recruiters_contacted": recruiters,
        "recruiter_replies": recruiter_replies,
    })


@dashboard_bp.get("/recent-jobs")
def recent_jobs():
    jobs = db.session.query(Job).order_by(Job.created_at.desc()).limit(20).all()
    return jsonify([{
        "id": j.id, "platform": j.platform, "title": j.title,
        "company": j.company, "location": j.location,
        "ats_score": j.ats_score, "status": j.status,
        "applied_at": j.applied_at.isoformat() if j.applied_at else None,
    } for j in jobs])
