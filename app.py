"""Flask entry point — mounts all blueprints and starts the scheduler."""
import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template
from flask_cors import CORS
from core.database import db, init_db
from core.logger import get_logger

log = get_logger("app")


def create_app() -> Flask:
    app = Flask(__name__, static_folder="frontend/static", template_folder="frontend/templates")
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

    # Database — Vercel writes only to /tmp; local uses sqlite in project dir
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        if os.getenv("VERCEL"):
            db_url = "sqlite:////tmp/jobbot.db"
        else:
            db_url = "sqlite:///jobbot.db"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # SQLite needs check_same_thread=False for Flask threading; Postgres uses pool settings
    if db_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False},
        }
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }

    CORS(app)
    db.init_app(app)

    with app.app_context():
        try:
            init_db()
        except Exception as e:
            log.warning(f"DB init skipped: {e}")

    # Register blueprints — each wrapped so one bad import won't kill the app
    _register_blueprints(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/health")
    def health():
        return {"status": "ok", "db": db_url.split("://")[0]}

    return app


def _register_blueprints(app: Flask):
    try:
        from api.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    except Exception as e:
        log.error(f"dashboard blueprint failed: {e}")

    try:
        from api.jobs import jobs_bp
        app.register_blueprint(jobs_bp, url_prefix="/api/jobs")
    except Exception as e:
        log.error(f"jobs blueprint failed: {e}")

    try:
        from api.resume import resume_bp
        app.register_blueprint(resume_bp, url_prefix="/api/resume")
    except Exception as e:
        log.error(f"resume blueprint failed: {e}")

    try:
        from api.outreach import outreach_bp
        app.register_blueprint(outreach_bp, url_prefix="/api/outreach")
    except Exception as e:
        log.error(f"outreach blueprint failed: {e}")

    try:
        from api.reports import reports_bp
        app.register_blueprint(reports_bp, url_prefix="/api/reports")
    except Exception as e:
        log.error(f"reports blueprint failed: {e}")


# Module-level app instance — required by Vercel and gunicorn WSGI
app = create_app()

if __name__ == "__main__":
    # Start scheduler only when running locally (not on Vercel/gunicorn)
    try:
        from scheduler.task_runner import start_scheduler
        start_scheduler(app)
        log.info("Scheduler started")
    except Exception as e:
        log.warning(f"Scheduler could not start: {e} — continuing without it")

    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
