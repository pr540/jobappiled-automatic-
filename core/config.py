"""Central config sourced from environment."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Sanagapalli Sri Ram Praneeth")
    CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL", "praneethssr.2002@gmail.com")
    CANDIDATE_LINKEDIN = os.getenv("CANDIDATE_LINKEDIN", "https://www.linkedin.com/in/sriampraneeth143/")
    RESUME_PDF_PATH = os.getenv("RESUME_PDF_PATH", "./data/resume.pdf")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ATS_MIN_SCORE = float(os.getenv("ATS_MIN_SCORE", "75"))
    MAX_EXPERIENCE_YEARS = int(os.getenv("MAX_EXPERIENCE_YEARS", "3"))
    DAILY_APPLY_TARGET = int(os.getenv("DAILY_APPLY_TARGET", "100"))
    RECRUITER_OUTREACH_LIMIT = int(os.getenv("RECRUITER_OUTREACH_LIMIT", "30"))
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
    BROWSER_PROFILE_DIR = os.getenv("BROWSER_PROFILE_DIR", "./data/browser_profiles")
    MORNING_SCAN_TIME = os.getenv("MORNING_SCAN_TIME", "08:00")
    REPORT_TIME = os.getenv("REPORT_TIME", "20:00")

    TARGET_ROLES = [
        "DevOps Engineer",
        "AWS Cloud Engineer",
        "Kubernetes Engineer",
        "Site Reliability Engineer",
        "Infrastructure Engineer",
        "Platform Engineer",
    ]

    TARGET_LOCATIONS = ["Remote", "Hyderabad", "Bangalore", "Pune", "Chennai"]

    SKILLS = [
        "AWS", "Terraform", "Docker", "Kubernetes", "Jenkins",
        "GitHub Actions", "Linux", "Bash", "Python", "CI/CD",
        "CloudWatch", "Grafana", "Prometheus", "IAM", "EKS",
        "EC2", "S3", "VPC", "Route53", "ELB", "Auto Scaling", "WAF",
    ]

    RECRUITER_MESSAGE = (
        "Hi, I'm a DevOps Engineer with hands-on experience in AWS, Terraform, Kubernetes, "
        "Docker, Jenkins, GitHub Actions, and CI/CD automation. I came across your opening and "
        "would love to connect regarding the opportunity."
    )
