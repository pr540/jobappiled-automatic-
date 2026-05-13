"""ATS scoring and resume keyword optimization via OpenAI."""
import re
from core.config import Config
from core.logger import get_logger
from ats.resume_parser import parse_resume

try:
    from openai import OpenAI
    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False

log = get_logger("ats_engine")
_client = None


def _get_client():
    global _client
    if not _OPENAI_OK:
        return None
    if _client is None:
        _client = OpenAI(api_key=Config.OPENAI_API_KEY)
    return _client


def calculate_ats_score(job_description: str, resume_text: str) -> float:
    result = calculate_ats_details(job_description, resume_text)
    return result["score"]


def calculate_ats_details(job_description: str, resume_text: str) -> dict:
    if not job_description or len(job_description.strip()) < 80:
        return {
            "score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "skills_in_jd": [],
            "jd_too_short": True,
            "resume_loaded": bool(resume_text and len(resume_text) > 50),
        }

    jd_lower = job_description.lower()
    resume_lower = resume_text.lower() if resume_text else ""

    skills_in_jd = [s for s in Config.SKILLS if s.lower() in jd_lower]
    matched = [s for s in skills_in_jd if s.lower() in resume_lower]
    missing = [s for s in skills_in_jd if s.lower() not in resume_lower]

    skill_total = max(1, len(skills_in_jd))
    skill_score = (len(matched) / skill_total) * 60

    jd_words = set(re.findall(r"\b[a-z][a-z0-9+#.-]{2,}\b", jd_lower))
    resume_words = set(re.findall(r"\b[a-z][a-z0-9+#.-]{2,}\b", resume_lower))
    common = jd_words & resume_words
    overlap_score = min(40, (len(common) / max(1, len(jd_words))) * 100)

    total = round(min(skill_score + overlap_score, 100.0), 1)
    log.info("ATS score", extra={"score": total, "matched": len(matched), "missing": len(missing)})

    return {
        "score": total,
        "matched_skills": matched,
        "missing_skills": missing,
        "skills_in_jd": skills_in_jd,
        "jd_too_short": False,
        "resume_loaded": bool(resume_lower and len(resume_lower) > 50),
    }


def optimize_resume(job_description: str, resume_text: str) -> dict:
    if not Config.OPENAI_API_KEY or not _OPENAI_OK:
        log.warning("No OpenAI key or openai not installed — returning original resume")
        return {"optimized_resume": resume_text, "keywords_added": [], "estimated_ats_score": 0}

    client = _get_client()
    if not client:
        return {"optimized_resume": resume_text, "keywords_added": [], "estimated_ats_score": 0}

    prompt = f"""You are an expert ATS resume optimizer.

JOB DESCRIPTION:
{job_description[:3000]}

CANDIDATE RESUME:
{resume_text[:3000]}

Task:
1. Identify missing keywords from the JD that should be in the resume.
2. Rewrite the resume summary and skills section to include those keywords naturally.
3. Keep all facts accurate — do NOT fabricate experience.
4. Return JSON with keys: optimized_resume (string), keywords_added (list), estimated_ats_score (float 0-100).
"""
    try:
        import json
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )
        result = json.loads(resp.choices[0].message.content)
        log.info("Resume optimized", extra={"score": result.get("estimated_ats_score")})
        return result
    except Exception as e:
        log.error("OpenAI optimization failed", extra={"error": str(e)})
        return {"optimized_resume": resume_text, "keywords_added": [], "estimated_ats_score": 0}


def should_apply(job_description: str, experience_str: str) -> tuple[bool, float]:
    parsed = parse_resume()
    score = calculate_ats_score(job_description, parsed["raw_text"])

    years = 0
    match = re.search(r"(\d+)", experience_str or "")
    if match:
        years = int(match.group(1))

    apply = score >= Config.ATS_MIN_SCORE and (years == 0 or years <= Config.MAX_EXPERIENCE_YEARS)
    return apply, score
