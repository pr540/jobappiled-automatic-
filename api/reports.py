"""Daily report generation and retrieval."""
from datetime import date
from flask import Blueprint, jsonify
from sqlalchemy import func
from core.database import db, Job, RecruiterOutreach, DailyReport
from core.logger import get_logger

reports_bp = Blueprint("reports", __name__)
log = get_logger("reports")


def generate_daily_report():
    today = date.today()
    try:
        existing = db.session.query(DailyReport).filter_by(date=today).first()
        scanned = db.session.query(func.count(Job.id)).filter(
            func.date(Job.created_at) == today
        ).scalar() or 0
        applied = db.session.query(func.count(Job.id)).filter(
            Job.status == "applied",
            func.date(Job.applied_at) == today
        ).scalar() or 0
        avg_ats = db.session.query(func.avg(Job.ats_score)).filter(
            Job.status == "applied",
            func.date(Job.applied_at) == today
        ).scalar() or 0
        interviews = db.session.query(func.count(Job.id)).filter_by(status="interview").scalar() or 0
        contacted = db.session.query(func.count(RecruiterOutreach.id)).filter(
            func.date(RecruiterOutreach.created_at) == today
        ).scalar() or 0

        if existing:
            existing.jobs_scanned = scanned
            existing.jobs_applied = applied
            existing.ats_avg_score = round(float(avg_ats), 1)
            existing.interview_calls = interviews
            existing.recruiters_contacted = contacted
        else:
            db.session.add(DailyReport(
                date=today,
                jobs_scanned=scanned,
                jobs_applied=applied,
                ats_avg_score=round(float(avg_ats), 1),
                interview_calls=interviews,
                recruiters_contacted=contacted,
            ))
        db.session.commit()
        log.info("Daily report saved", extra={"date": str(today), "applied": applied})
    except Exception as e:
        db.session.rollback()
        log.error(f"Report generation failed: {e}")


@reports_bp.get("/daily")
def get_daily_reports():
    try:
        reports = db.session.query(DailyReport).order_by(DailyReport.date.desc()).limit(30).all()
        return jsonify([{
            "date": str(r.date),
            "jobs_scanned": r.jobs_scanned,
            "jobs_applied": r.jobs_applied,
            "ats_avg_score": r.ats_avg_score,
            "recruiters_contacted": r.recruiters_contacted,
            "interview_calls": r.interview_calls,
        } for r in reports])
    except Exception:
        return jsonify([])


@reports_bp.get("/platform-breakdown")
def platform_breakdown():
    try:
        rows = (
            db.session.query(Job.platform, Job.status, func.count(Job.id))
            .group_by(Job.platform, Job.status)
            .all()
        )
        result: dict = {}
        for platform, status, count in rows:
            if platform not in result:
                result[platform] = {}
            result[platform][status] = count
        return jsonify(result)
    except Exception:
        return jsonify({})


@reports_bp.post("/generate")
def trigger_report():
    try:
        generate_daily_report()
        return jsonify({"message": "Report generated", "date": str(date.today())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
