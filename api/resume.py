"""Resume upload, parse, and ATS optimize endpoints."""
import os
from flask import Blueprint, jsonify, request, current_app
from core.config import Config
from core.database import db, ResumeVersion
from ats.resume_parser import parse_resume
from ats.ats_engine import calculate_ats_score, optimize_resume

resume_bp = Blueprint("resume", __name__)


@resume_bp.post("/upload")
def upload_resume():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "Only PDF supported"}), 400
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "resume.pdf")
    file.save(path)
    parsed = parse_resume(path)
    return jsonify({
        "message": "Resume uploaded and parsed",
        "skills_found": parsed["skills"],
        "email": parsed["email"],
    })


@resume_bp.get("/parse")
def get_parsed():
    parsed = parse_resume()
    return jsonify({
        "name": parsed["name"],
        "email": parsed["email"],
        "phone": parsed["phone"],
        "skills": parsed["skills"],
        "text_length": len(parsed["raw_text"]),
    })


@resume_bp.post("/optimize")
def optimize():
    data = request.get_json()
    jd = data.get("job_description", "")
    if not jd:
        return jsonify({"error": "job_description required"}), 400
    parsed = parse_resume()
    result = optimize_resume(jd, parsed["raw_text"])
    record = ResumeVersion(
        content=result.get("optimized_resume", ""),
        ats_score=result.get("estimated_ats_score", 0),
        keywords_added=",".join(result.get("keywords_added", [])),
    )
    db.session.add(record)
    db.session.commit()
    return jsonify(result)


@resume_bp.post("/ats-score")
def ats_score():
    data = request.get_json()
    jd = data.get("job_description", "")
    parsed = parse_resume()
    score = calculate_ats_score(jd, parsed["raw_text"])
    return jsonify({"ats_score": score, "threshold": Config.ATS_MIN_SCORE, "pass": score >= Config.ATS_MIN_SCORE})
