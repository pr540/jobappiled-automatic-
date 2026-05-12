"""ATS scoring and resume keyword optimization via OpenAI."""
import re
import os
from openai import OpenAI
from core.config import Config
from core.logger import get_logger
from ats.resume_parser import parse_resume

log = get_logger("ats_engine")
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=Config.OPENAI_API_KEY)
    return _client


def calculate_ats_score(job_description: str, resume_text: str) -> float:
    """Keyword-based ATS score (0–100) with optional LLM boost."""
    jd_lower = job_description.lower()
    resume_lower = resume_text.lower()

    # Extract words from JD
    jd_words = set(re.findall(r"\b[a-z][a-z0-9+#.-]{2,}\b", jd_lower))
    resume_words = set(re.findall(r"\b[a-z][a-z0-9+#.-]{2,}\b", resume_lower))

    # Skill keyword matches
    skill_matches = sum(1 for s in Config.SKILLS if s.lower() in jd_lower and s.lower() in resume_lower)
    skill_total = max(1, sum(1 for s in Config.SKILLS if s.lower() in jd_lower))
    skill_score = (skill_matches / skill_total) * 60

    # General keyword overlap
    common = jd_words & resume_words
    overlap_score = min(40, (len(common) / max(1, len(jd_words))) * 100)

    total = round(skill_score + overlap_score, 1)
    log.info("ATS score calculated", extra={"score": total, "skill_matches": skill_matches})
    return min(total, 100.0)


def optimize_resume(job_description: str, resume_text: str) -> dict:
    """Use GPT to generate an ATS-optimised resume tailored to the JD."""
    if not Config.OPENAI_API_KEY:
        log.warning("No OpenAI key — returning original resume")
        return {"optimized_resume": resume_text, "keywords_added": [], "score": 0}

    client = _get_client()
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
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )
        import json
        result = json.loads(resp.choices[0].message.content)
        log.info("Resume optimized", extra={"score": result.get("estimated_ats_score")})
        return result
    except Exception as e:
        log.error("OpenAI optimization failed", extra={"error": str(e)})
        return {"optimized_resume": resume_text, "keywords_added": [], "score": 0}


def should_apply(job_description: str, experience_str: str) -> tuple[bool, float]:
    """Return (apply_decision, ats_score)."""
    parsed = parse_resume()
    score = calculate_ats_score(job_description, parsed["raw_text"])

    # Parse experience requirement
    years = 0
    match = re.search(r"(\d+)", experience_str or "")
    if match:
        years = int(match.group(1))

    apply = score >= Config.ATS_MIN_SCORE and (years == 0 or years <= Config.MAX_EXPERIENCE_YEARS)
    return apply, score
