"""Job matching: rule-based skill extraction from a job description, compared to the
evidence-backed passport. Formula (see scoring_config):
    score = 100 * Σ(weight_i × credit_i) / Σ(weight_i)
    weight: required = 2, preferred = 1
    credit: evidence_supported 1.0, partially_supported / flagged_for_review 0.5,
            unverified (resume-only) 0, missing 0
Skills on the passport that the job does not ask for are listed but never add to the score.
The job description is untrusted text: it is only searched for skill names."""
from __future__ import annotations

import re

from app.services import scoring_config as cfg
from app.services.taxonomy import SKILLS_BY_ID, find_skill_mentions

PREFERRED_HEAD = re.compile(r"(?i)\b(nice[- ]to[- ]have|preferred|bonus|good to have|plus\b|desirable|optional|familiarity)")
REQUIRED_HEAD = re.compile(r"(?i)\b(requirements?|required|must[- ]have|qualifications|responsibilities|what you.?ll need|you have|skills)\b")

FORMULA = ("score = 100 × Σ(weight × credit) / Σ(weight); weight: required 2, preferred 1; "
           "credit: evidence-supported 1.0, partially supported or flagged 0.5, resume-only 0, missing 0")


class JobMatchError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def extract_job_skills(jd: str) -> dict[str, dict]:
    found: dict[str, dict] = {}
    mode = "required"
    for raw in jd.splitlines():
        line = raw.strip()
        if not line:
            continue
        mentions = find_skill_mentions(line)
        # heading lines switch the mode for following lines
        if len(line) < 60 and line.rstrip(":").strip() and (line.endswith(":") or not mentions):
            if PREFERRED_HEAD.search(line):
                mode = "preferred"
            elif REQUIRED_HEAD.search(line):
                mode = "required"
        line_mode = "preferred" if PREFERRED_HEAD.search(line) else mode
        for sid, *_rest in mentions:
            current = found.get(sid)
            if current is None or (current["requirement"] == "preferred" and line_mode == "required"):
                found[sid] = {"requirement": line_mode, "snippet": line[:160]}
    return found


def match(passport_skills: list[dict], job_title: str, jd: str) -> dict:
    if len(jd.strip()) < 30:
        raise JobMatchError("Job description is too short; paste the full description.")
    wanted = extract_job_skills(jd + "\n" + job_title)
    if not wanted:
        raise JobMatchError("No recognisable technical skills were found in the job description.")
    by_id = {s["skill_id"]: s for s in passport_skills}
    items = []
    num = den = 0.0
    for sid, info in wanted.items():
        rec = by_id.get(sid)
        status = rec["verification_status"] if rec else "missing"
        weight = cfg.REQUIRED_WEIGHT if info["requirement"] == "required" else cfg.PREFERRED_WEIGHT
        credit = cfg.MATCH_CREDIT[status]
        num += weight * credit
        den += weight
        items.append({
            "skill": SKILLS_BY_ID[sid].name, "skill_id": sid, "requirement": info["requirement"], "weight": weight,
            "status": status, "credit": credit, "points": round(weight * credit, 2),
            "estimated_level": rec["estimated_level"] if rec else None,
            "evidence_strength": rec["evidence_strength"] if rec else 0.0, "jd_snippet": info["snippet"],
        })
    score = round(100 * num / den, 1) if den else 0.0
    items.sort(key=lambda i: (i["requirement"] != "required", -i["credit"], i["skill"]))
    return {
        "score": score,
        "formula": FORMULA,
        "points_earned": round(num, 2), "points_possible": round(den, 2),
        "items": items,
        "supported": [i for i in items if i["status"] == "evidence_supported"],
        "partial": [i for i in items if i["status"] in ("partially_supported", "flagged_for_review")],
        "unverified_claims": [i for i in items if i["status"] == "unverified"],
        "missing": [i for i in items if i["status"] == "missing"],
        "important_gaps": [i for i in items if i["requirement"] == "required" and i["credit"] < 1],
        "not_requested": sorted(s["skill"] for s in passport_skills if s["skill_id"] not in wanted),
    }
