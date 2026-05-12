"""Unit tests for ATS scoring engine."""
import pytest
from ats.ats_engine import calculate_ats_score, should_apply
from unittest.mock import patch


DEVOPS_JD = """
We are looking for a DevOps Engineer with experience in:
- AWS (EC2, S3, EKS, IAM, CloudWatch)
- Kubernetes and Docker container orchestration
- Terraform infrastructure as code
- CI/CD pipelines using Jenkins and GitHub Actions
- Linux and Bash scripting
- Prometheus and Grafana monitoring
Experience: 1-3 years
"""

RESUME_TEXT = """
Sanagapalli Sri Ram Praneeth
DevOps Engineer | 2+ Years Experience

Skills: AWS, EC2, S3, VPC, IAM, EKS, CloudWatch, Terraform, Docker,
Kubernetes, Jenkins, GitHub Actions, Linux, Bash, Python,
Prometheus, Grafana, CI/CD

Projects:
- Deployed microservices on EKS using Terraform and Helm
- Built CI/CD pipeline with Jenkins and GitHub Actions
- Monitored infrastructure with Prometheus and Grafana
"""


def test_ats_score_high_match():
    score = calculate_ats_score(DEVOPS_JD, RESUME_TEXT)
    assert score >= 70, f"Expected score >= 70, got {score}"


def test_ats_score_low_match():
    unrelated_jd = "Looking for a Java Spring Boot developer with Oracle DB experience"
    score = calculate_ats_score(unrelated_jd, RESUME_TEXT)
    assert score < 70, f"Expected score < 70 for unrelated JD, got {score}"


def test_should_apply_pass():
    with patch("ats.ats_engine.parse_resume") as mock_parse:
        mock_parse.return_value = {"raw_text": RESUME_TEXT}
        apply, score = should_apply(DEVOPS_JD, "2 years")
        assert apply is True
        assert score >= 75


def test_should_apply_fail_experience():
    with patch("ats.ats_engine.parse_resume") as mock_parse:
        mock_parse.return_value = {"raw_text": RESUME_TEXT}
        apply, score = should_apply(DEVOPS_JD, "5 years")
        assert apply is False


def test_score_in_range():
    score = calculate_ats_score(DEVOPS_JD, RESUME_TEXT)
    assert 0 <= score <= 100
