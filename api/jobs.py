"""Jobs API — CRUD + trigger search/apply/full-cycle."""
import threading
from datetime import datetime
from flask import Blueprint, jsonify, request
from core.database import db, Job

jobs_bp = Blueprint("jobs", __name__)

# ── live task status (in-memory, single-server only) ──────────────────────────
_task_lock = threading.Lock()
_task_status: dict = {"running": False, "phase": "", "started": None,
                       "scanned": 0, "saved": 0, "applied": 0, "failed": 0,
                       "skipped_ats": 0, "skipped_dup": 0, "last_platform": ""}


def _reset_status(phase: str):
    with _task_lock:
        _task_status.update(running=True, phase=phase,
                             started=datetime.utcnow().isoformat(),
                             scanned=0, saved=0, applied=0, failed=0,
                             skipped_ats=0, skipped_dup=0, last_platform="")


def _update_status(**kwargs):
    with _task_lock:
        _task_status.update(**kwargs)


def _finish_status():
    with _task_lock:
        _task_status["running"] = False
        _task_status["phase"] = "done"


# ── helpers ────────────────────────────────────────────────────────────────────
def _kill_chrome():
    import subprocess
    for proc in ["chromedriver.exe", "chrome.exe"]:
        subprocess.run(["taskkill", "/F", "/IM", proc],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── routes ─────────────────────────────────────────────────────────────────────
@jobs_bp.get("/")
def list_jobs():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    status = request.args.get("status")
    platform = request.args.get("platform")

    try:
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
    except Exception as e:
        return jsonify({"total": 0, "page": page, "jobs": [], "error": str(e)}), 200


@jobs_bp.get("/status")
def task_status():
    with _task_lock:
        return jsonify(dict(_task_status))


@jobs_bp.post("/trigger-search")
def trigger_search():
    data = request.get_json(silent=True) or {}
    platforms = data.get("platforms") or ["linkedin", "naukri", "indeed"]
    app = _get_app()

    def _run():
        _reset_status("searching")
        try:
            with app.app_context():
                from agents.job_search_agent import run_job_search
                r = run_job_search(platforms=platforms)
                _update_status(scanned=r.get("scanned", 0), saved=r.get("saved", 0),
                                skipped_ats=r.get("skipped_ats", 0),
                                skipped_dup=r.get("skipped_dup", 0))
        except Exception as e:
            _update_status(phase=f"search error: {e}")
        finally:
            _finish_status()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"message": f"Job search started for {platforms}"})


@jobs_bp.post("/trigger-apply")
def trigger_apply():
    data = request.get_json(silent=True) or {}
    limit = int(data.get("limit", 150))
    app = _get_app()

    def _run():
        _reset_status("applying")
        try:
            with app.app_context():
                from agents.apply_agent import run_auto_apply
                r = run_auto_apply(daily_limit=limit)
                _update_status(applied=r.get("applied", 0), failed=r.get("failed", 0))
        except Exception as e:
            _update_status(phase=f"apply error: {e}")
        finally:
            _finish_status()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Auto-apply started in background"})


@jobs_bp.post("/trigger-full")
def trigger_full():
    """Search new jobs → apply to all pending.  One button, full cycle."""
    data = request.get_json(silent=True) or {}
    platforms = data.get("platforms") or ["linkedin", "naukri", "indeed"]
    limit = int(data.get("limit", 150))
    app = _get_app()

    def _run():
        _reset_status("searching")
        try:
            with app.app_context():
                # ── Phase 1: search ──────────────────────────────────
                from agents.job_search_agent import run_job_search
                sr = run_job_search(platforms=platforms)
                _update_status(phase="applying",
                                scanned=sr.get("scanned", 0),
                                saved=sr.get("saved", 0),
                                skipped_ats=sr.get("skipped_ats", 0),
                                skipped_dup=sr.get("skipped_dup", 0))
                _kill_chrome()

                # ── Phase 2: apply ───────────────────────────────────
                from agents.apply_agent import run_auto_apply
                ar = run_auto_apply(daily_limit=limit)
                _update_status(applied=ar.get("applied", 0),
                                failed=ar.get("failed", 0))
                _kill_chrome()

        except Exception as e:
            _update_status(phase=f"error: {str(e)[:120]}")
        finally:
            _finish_status()

    with _task_lock:
        if _task_status["running"]:
            return jsonify({"message": "A task is already running — please wait"}), 409

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"message": f"Full cycle started: search + apply on {platforms}",
                    "platforms": platforms})


@jobs_bp.patch("/<int:job_id>/status")
def update_status(job_id: int):
    try:
        job = db.session.get(Job, job_id)
        if not job:
            return jsonify({"error": "Not found"}), 404
        data = request.get_json() or {}
        job.status = data.get("status", job.status)
        db.session.commit()
        return jsonify({"id": job.id, "status": job.status})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@jobs_bp.delete("/<int:job_id>")
def delete_job(job_id: int):
    try:
        job = db.session.get(Job, job_id)
        if not job:
            return jsonify({"error": "Not found"}), 404
        db.session.delete(job)
        db.session.commit()
        return jsonify({"deleted": job_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def _get_app():
    from flask import current_app
    return current_app._get_current_object()
