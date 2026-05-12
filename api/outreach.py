"""Recruiter outreach API."""
from flask import Blueprint, jsonify, request
from core.database import db, RecruiterOutreach
from core.logger import get_logger

outreach_bp = Blueprint("outreach", __name__)
log = get_logger("outreach_api")


@outreach_bp.get("/")
def list_outreach():
    records = db.session.query(RecruiterOutreach).order_by(RecruiterOutreach.created_at.desc()).limit(100).all()
    return jsonify([{
        "id": r.id, "name": r.name, "company": r.company,
        "linkedin_url": r.linkedin_url, "connection_sent": r.connection_sent,
        "message_sent": r.message_sent, "replied": r.replied,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in records])


@outreach_bp.post("/trigger")
def trigger_outreach():
    from threading import Thread
    from flask import current_app
    app = current_app._get_current_object()

    def _run():
        with app.app_context():
            from agents.recruiter_agent import run_recruiter_outreach
            run_recruiter_outreach(app=app)

    Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Recruiter outreach started"})


@outreach_bp.patch("/<int:rec_id>/replied")
def mark_replied(rec_id: int):
    rec = db.session.get(RecruiterOutreach, rec_id)
    if not rec:
        return jsonify({"error": "Not found"}), 404
    rec.replied = True
    db.session.commit()
    return jsonify({"id": rec.id, "replied": True})
