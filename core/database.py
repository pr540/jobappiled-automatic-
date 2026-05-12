"""SQLAlchemy models and DB helpers."""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200))
    location = db.Column(db.String(200))
    experience_required = db.Column(db.String(100))
    job_url = db.Column(db.String(500), unique=True, nullable=False)
    job_description = db.Column(db.Text)
    ats_score = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="pending")  # pending|applied|rejected|interview
    applied_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    error_message = db.Column(db.Text)


class RecruiterOutreach(db.Model):
    __tablename__ = "recruiter_outreach"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    title = db.Column(db.String(200))
    company = db.Column(db.String(200))
    linkedin_url = db.Column(db.String(500))
    connection_sent = db.Column(db.Boolean, default=False)
    message_sent = db.Column(db.Boolean, default=False)
    replied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=True)


class DailyReport(db.Model):
    __tablename__ = "daily_reports"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, default=datetime.utcnow)
    jobs_scanned = db.Column(db.Integer, default=0)
    jobs_applied = db.Column(db.Integer, default=0)
    ats_avg_score = db.Column(db.Float, default=0.0)
    recruiters_contacted = db.Column(db.Integer, default=0)
    interview_calls = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ResumeVersion(db.Model):
    __tablename__ = "resume_versions"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=True)
    content = db.Column(db.Text)
    ats_score = db.Column(db.Float, default=0.0)
    keywords_added = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def init_db():
    db.create_all()
