"""Integration tests for Flask API endpoints."""
import pytest
import os
os.environ["DATABASE_URL"] = "sqlite:///test_api.db"
os.environ["OPENAI_API_KEY"] = "test"
os.environ["FLASK_SECRET_KEY"] = "test-secret"

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_dashboard_stats(client):
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert "jobs_applied" in data
    assert "avg_ats_score" in data


def test_jobs_list(client):
    res = client.get("/api/jobs/")
    assert res.status_code == 200
    data = res.get_json()
    assert "jobs" in data
    assert "total" in data


def test_ats_score_endpoint(client):
    res = client.post("/api/resume/ats-score", json={
        "job_description": "Looking for DevOps Engineer with AWS Kubernetes Docker experience"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "ats_score" in data


def test_reports_list(client):
    res = client.get("/api/reports/daily")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_platform_breakdown(client):
    res = client.get("/api/reports/platform-breakdown")
    assert res.status_code == 200


def test_outreach_list(client):
    res = client.get("/api/outreach/")
    assert res.status_code == 200
