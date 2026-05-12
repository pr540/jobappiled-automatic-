"""Jobs API — CRUD + trigger search/apply."""
from flask import Blueprint, jsonify, request
from core.database import db, Job

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.get("/")
def list_jobs():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    status = request.args.get("status")
    platform = request.args.get("platform")

    q = db.session.query(Job)
    if status:
        q = q.filter_by(status=status)
    if platform:
        q = q.filter_by(platform=platform)

    total = q.count()
    jobs = q.order_by(Job.ats_score.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "total": total,
        "page": page,
        "jobs": [{
            "id": j.id, "platform": j.platform, "title": j.title,
            "company": j.company, "location": j.location,
            "ats_score": j.ats_score, "status": j.status,
            "job_url": j.job_url, "experience_required": j.experience_required,
            "applied_at": j.applied_at.isoformat() if j.applied_at else None,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        } for j in jobs],
    })


@jobs_bp.post("/trigger-search")
def trigger_search():
    from threading import Thread
    from flask import current_app
    app = current_app._get_current_object()

    def _run():
        with app.app_context():
            from agents.job_search_agent import run_job_search
            run_job_search(app=app)

    Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Job search started in background"})


@jobs_bp.post("/trigger-apply")
def trigger_apply():
    from threading import Thread
    from flask import current_app
    app = current_app._get_current_object()

    def _run():
        with app.app_context():
            from agents.apply_agent import run_auto_apply
            run_auto_apply(app=app)

    Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Auto-apply started in background"})


@jobs_bp.patch("/<int:job_id>/status")
def update_status(job_id: int):
    job = db.session.get(Job, job_id)
    if not job:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json()
    job.status = data.get("status", job.status)
    db.session.commit()
    return jsonify({"id": job.id, "status": job.status})


@jobs_bp.delete("/<int:job_id>")
def delete_job(job_id: int):
    job = db.session.get(Job, job_id)
    if not job:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(job)
    db.session.commit()
    return jsonify({"deleted": job_id})
