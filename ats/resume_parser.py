"""Extract text, skills, and sections from a PDF resume."""
import re
import pdfplumber
from core.config import Config
from core.logger import get_logger

log = get_logger("resume_parser")


def extract_text(pdf_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        log.error("PDF extraction failed", extra={"error": str(e), "path": pdf_path})
    return text


def extract_skills(resume_text: str) -> list[str]:
    found = []
    text_lower = resume_text.lower()
    for skill in Config.SKILLS:
        if skill.lower() in text_lower:
            found.append(skill)
    return found


def parse_resume(pdf_path: str | None = None) -> dict:
    path = pdf_path or Config.RESUME_PDF_PATH
    text = extract_text(path)
    skills = extract_skills(text)
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", text)
    phone_match = re.search(r"(\+91[\s-]?)?[6-9]\d{9}", text)
    return {
        "raw_text": text,
        "skills": skills,
        "email": email_match.group() if email_match else Config.CANDIDATE_EMAIL,
        "phone": phone_match.group() if phone_match else "",
        "name": Config.CANDIDATE_NAME,
    }
