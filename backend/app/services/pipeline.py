"""Orchestration: GitHub ingestion -> skill verification -> authorship guard -> persistence."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.models import Evidence, JobMatch, Passport, Repository, Resume, SkillRecord, Student, TrustSignal
from app.services import authorship_guard, job_matcher, roadmap, skill_engine
from app.services.github_client import GitHubClient, parse_repo_url
from app.services.repo_analyzer import scan_zip


def iso(dt: datetime) -> str:
    """SQLite drops tzinfo; all stored times are UTC."""
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


def ingest_repository(db: Session, client: GitHubClient, repo_url: str) -> Repository:
    ref = parse_repo_url(repo_url)
    meta = client.get_repo(ref)
    owner = (meta.get("owner") or {}).get("login") or ref.owner
    name = meta.get("name") or ref.repo
    branch = meta.get("default_branch") or "main"
    languages = client.get_languages(ref)
    raw_commits = client.get_commits(ref, settings.max_commits)
    commits = authorship_guard.normalize_commits(raw_commits)
    contributors = [{"login": c.get("login"), "contributions": c.get("contributions")} for c in client.get_contributors(ref)]
    zip_bytes = client.download_zipball(ref, branch, settings.max_repo_zip_mb)
    scan = scan_zip(zip_bytes, settings.max_files_scanned, settings.max_file_kb)
    del zip_bytes
    parent = meta.get("parent") or meta.get("source") or {}
    repo = Repository(
        url=f"https://github.com/{owner}/{name}", owner=owner, name=name, description=(meta.get("description") or "")[:500],
        default_branch=branch, head_sha=commits[0]["sha"] if commits else None, is_fork=bool(meta.get("fork")),
        parent_full_name=parent.get("full_name"), parent_url=parent.get("html_url"), stars=meta.get("stargazers_count") or 0,
        languages=languages, file_count=scan.file_count, files_scanned=scan.files_scanned,
        findings=[f.to_dict() for f in scan.findings], commits=commits, contributors=contributors,
        readme_excerpt=scan.readme_excerpt, scan_notes=scan.notes + [f"source_file_count={scan.source_file_count}"],
    )
    if not scan.findings:
        repo.scan_notes.append("No skill evidence could be extracted from the scanned files.")
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def _source_count(repo: Repository) -> int:
    for n in repo.scan_notes or []:
        if n.startswith("source_file_count="):
            return int(n.split("=", 1)[1])
    return 0


def _repo_dict(repo: Repository) -> dict:
    return {
        "owner": repo.owner, "url": repo.url, "is_fork": repo.is_fork, "parent_full_name": repo.parent_full_name,
        "parent_url": repo.parent_url, "commits": repo.commits or [], "contributors": repo.contributors or [],
        "file_histories": repo.file_histories or {}, "source_file_count": _source_count(repo),
        "readme_excerpt": repo.readme_excerpt,
    }


def build_passport(db: Session, client: GitHubClient | None, student_name: str, repo: Repository,
                   resume: Resume | None, is_demo: bool = False) -> Passport:
    student = Student(name=student_name.strip()[:120])
    db.add(student)
    db.flush()

    trust = authorship_guard.evaluate(_repo_dict(repo), settings.max_commits)
    high = trust["trust_level"] == "high_concern"
    ref = repo.head_sha or repo.default_branch
    records = skill_engine.verify_skills(
        findings=repo.findings or [], commits=repo.commits or [], owner=repo.owner, repo_url=repo.url, ref=ref,
        resume_claims=(resume.claims if resume else []), high_trust_concern=high, illustrative=is_demo,
    )
    # File-level history for key evidence files (bounded number of API requests)
    if client is not None and not is_demo and repo.commits:
        histories = {}
        gh_ref = parse_repo_url(repo.url)
        for path in skill_engine.key_evidence_files(records, settings.max_file_history_lookups):
            try:
                histories[path] = authorship_guard.normalize_commits(client.get_commits(gh_ref, 10, path=path))
            except Exception:  # noqa: BLE001 - history is optional; record as unavailable
                histories[path] = []
        repo.file_histories = histories
        trust = authorship_guard.evaluate(_repo_dict(repo), settings.max_commits)

    passport = Passport(
        student_id=student.id, repository_id=repo.id, resume_id=resume.id if resume else None, is_demo=is_demo,
        trust_level=trust["trust_level"], trust_meta=trust["meta"], summary=skill_engine.summarize(records),
    )
    db.add(passport)
    db.flush()
    for r in records:
        rec = SkillRecord(
            passport_id=passport.id, skill=r["skill"], category=r["category"], estimated_level=r["estimated_level"],
            verification_status=r["verification_status"], evidence_strength=r["evidence_strength"],
            explanation=r["explanation"], limitations=r["limitations"], resume_claimed=r["resume_claimed"],
            metrics={**r["metrics"], "skill_id": r["skill_id"]},
        )
        rec.evidence = [Evidence(**e) for e in r["evidence"]]
        db.add(rec)
    for s in trust["signals"]:
        db.add(TrustSignal(passport_id=passport.id, **s))
    db.commit()
    db.refresh(passport)
    return passport


# ------------------------------------------------------------------ serialisation
def skill_dict(r: SkillRecord, public: bool = False) -> dict:
    ev = []
    for e in r.evidence:
        if public and e.source == "resume":
            continue  # never expose resume content publicly
        ev.append({
            "id": e.id, "evidence_type": e.evidence_type, "source": e.source, "repo_url": e.repo_url,
            "file_path": e.file_path, "line_start": e.line_start, "line_end": e.line_end, "commit_sha": e.commit_sha,
            "url": e.url, "page": None if public else e.page, "snippet": e.snippet, "detail": e.detail,
            "weight": e.weight, "illustrative": e.illustrative,
        })
    return {
        "id": r.id, "skill": r.skill, "skill_id": (r.metrics or {}).get("skill_id"), "category": r.category,
        "estimated_level": r.estimated_level, "verification_status": r.verification_status,
        "evidence_strength": r.evidence_strength, "explanation": r.explanation, "limitations": r.limitations,
        "resume_claimed": False if public else r.resume_claimed, "metrics": r.metrics, "evidence": ev,
    }


def passport_dict(p: Passport) -> dict:
    repo, resume = p.repository, p.resume
    latest = p.job_matches[-1] if p.job_matches else None
    return {
        "id": p.id, "is_demo": p.is_demo, "created_at": iso(p.created_at),
        "student": {"id": p.student.id, "name": p.student.name},
        "repository": {
            "url": repo.url, "owner": repo.owner, "name": repo.name, "description": repo.description,
            "default_branch": repo.default_branch, "head_sha": repo.head_sha, "is_fork": repo.is_fork,
            "parent_full_name": repo.parent_full_name, "parent_url": repo.parent_url, "stars": repo.stars,
            "languages": repo.languages, "file_count": repo.file_count, "files_scanned": repo.files_scanned,
            "scan_notes": [n for n in (repo.scan_notes or []) if not n.startswith("source_file_count=")],
            "fetched_at": iso(repo.fetched_at), "is_demo": repo.is_demo,
        },
        "resume": None if not resume else {
            "id": resume.id, "filename": resume.filename, "page_count": resume.page_count,
            "claims": resume.claims, "projects": resume.projects, "experience": resume.experience, "notes": resume.notes,
        },
        "summary": p.summary,
        "skills": [skill_dict(s) for s in p.skills],
        "trust": {
            "level": p.trust_level, "meta": p.trust_meta,
            "signals": [{"id": t.id, "signal_type": t.signal_type, "severity": t.severity, "title": t.title,
                         "description": t.description, "evidence": t.evidence, "limitations": t.limitations,
                         "recommendation": t.recommendation} for t in p.trust_signals],
        },
        "sharing": {"is_public": p.is_public, "public_id": p.public_id if p.is_public else None,
                    "public_url": f"{settings.public_base_url}/p/{p.public_id}" if p.is_public and p.public_id else None},
        "latest_job_match": job_match_dict(latest) if latest else None,
    }


def job_match_dict(m: JobMatch) -> dict:
    return {"id": m.id, "passport_id": m.passport_id, "job_title": m.job_title, "job_description": m.job_description,
            "score": m.score, "created_at": iso(m.created_at), **m.breakdown, "roadmap": m.roadmap}


def public_passport_dict(p: Passport) -> dict:
    """Sanitised view: no resume data, no job descriptions, no internal ids."""
    sev = {}
    for t in p.trust_signals:
        sev[t.severity] = sev.get(t.severity, 0) + 1
    return {
        "public_id": p.public_id, "is_demo": p.is_demo, "student_name": p.student.name,
        "repository": {"url": p.repository.url if not p.is_demo else None, "name": p.repository.name,
                       "languages": p.repository.languages, "is_fork": p.repository.is_fork},
        "generated_at": iso(p.created_at), "summary": {k: v for k, v in p.summary.items() if k != "unverified"},
        "trust": {"level": p.trust_level, "severity_counts": sev,
                  "signals": [{"severity": t.severity, "title": t.title} for t in p.trust_signals if t.severity != "info"]},
        # unverified (resume-only) skills are private
        "skills": [skill_dict(s, public=True) for s in p.skills if s.verification_status != "unverified"],
    }


# ------------------------------------------------------------------ job match / roadmap / share
def run_job_match(db: Session, p: Passport, title: str, jd: str) -> JobMatch:
    skills = [skill_dict(s) for s in p.skills]
    result = job_matcher.match(skills, title, jd)
    gaps = [i for i in result["items"] if i["credit"] < 1]
    plan = roadmap.build_roadmap(gaps)
    m = JobMatch(passport_id=p.id, job_title=title.strip()[:200], job_description=jd[:20000], score=result["score"],
                 breakdown={k: v for k, v in result.items() if k != "score"}, roadmap=plan)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def roadmap_for(p: Passport) -> dict:
    if p.job_matches:
        m = p.job_matches[-1]
        return {"passport_id": p.id, "based_on": "job_match", "job_title": m.job_title, "job_match_id": m.id, "items": m.roadmap}
    gaps = [{"skill_id": (s.metrics or {}).get("skill_id"), "skill": s.skill, "status": s.verification_status, "requirement": "required"}
            for s in p.skills if s.verification_status != "evidence_supported"]
    return {"passport_id": p.id, "based_on": "passport_gaps", "job_title": None, "job_match_id": None, "items": roadmap.build_roadmap(gaps)}


def set_sharing(db: Session, p: Passport, enabled: bool) -> Passport:
    if enabled and not p.public_id:
        p.public_id = secrets.token_urlsafe(9)
    p.is_public = enabled
    db.commit()
    db.refresh(p)
    return p
