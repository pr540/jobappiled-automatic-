"""Flask entry point — mounts all blueprints and starts the scheduler."""
import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_cors import CORS
from core.database import db, init_db
from api.dashboard import dashboard_bp
from api.jobs import jobs_bp
from api.resume import resume_bp
from api.outreach import outreach_bp
from api.reports import reports_bp
from scheduler.task_runner import start_scheduler


def create_app() -> Flask:
    app = Flask(__name__, static_folder="frontend/static", template_folder="frontend/templates")
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///data/jobbot.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    CORS(app)
    db.init_app(app)
    with app.app_context():
        init_db()
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(jobs_bp, url_prefix="/api/jobs")
    app.register_blueprint(resume_bp, url_prefix="/api/resume")
    app.register_blueprint(outreach_bp, url_prefix="/api/outreach")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    from flask import render_template
    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    start_scheduler(app)
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
