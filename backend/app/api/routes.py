from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database.db import get_db
from app.models.models import Passport, Repository, Resume
from app.schemas.schemas import AnalyzeRequest, GitHubAnalyzeRequest, JobMatchRequest, ShareRequest
from app.services import demo, pipeline
from app.services.github_client import GitHubClient, GitHubError
from app.services.job_matcher import JobMatchError
from app.services.resume_parser import ResumeError, parse_resume

router = APIRouter(prefix="/api")


def get_github_client():
    client = GitHubClient()
    try:
        yield client
    finally:
        client.close()


def _passport_or_404(db: Session, passport_id: str) -> Passport:
    p = db.get(Passport, passport_id)
    if not p:
        raise HTTPException(404, "Passport not found.")
    return p


def _repo_summary(repo: Repository) -> dict:
    skills = sorted({f["skill"] for f in repo.findings or []})
    return {
        "repository_id": repo.id, "url": repo.url, "owner": repo.owner, "name": repo.name, "description": repo.description,
        "is_fork": repo.is_fork, "parent_full_name": repo.parent_full_name, "languages": repo.languages,
        "file_count": repo.file_count, "files_scanned": repo.files_scanned, "findings_count": len(repo.findings or []),
        "commits_fetched": len(repo.commits or []), "skills_detected": skills,
        "notes": [n for n in (repo.scan_notes or []) if not n.startswith("source_file_count=")],
    }


@router.get("/health")
def health():
    return {"status": "ok", "github_token_configured": bool(settings.github_token)}


@router.post("/resume/upload", status_code=201)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read(settings.max_resume_mb * 1024 * 1024 + 1)
    try:
        parsed = parse_resume(data, file.filename or "resume.pdf", settings.max_resume_mb)
    except ResumeError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    resume = Resume(filename=(file.filename or "resume.pdf")[:255], page_count=parsed.page_count, text_chars=parsed.text_chars,
                    claims=parsed.claims, projects=parsed.projects, experience=parsed.experience, notes=parsed.notes)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return {"resume_id": resume.id, "filename": resume.filename, "page_count": resume.page_count, "claims": resume.claims,
            "projects": resume.projects, "experience": resume.experience, "notes": resume.notes}


@router.post("/github/analyze", status_code=201)
def analyze_github(body: GitHubAnalyzeRequest, db: Session = Depends(get_db), client: GitHubClient = Depends(get_github_client)):
    try:
        repo = pipeline.ingest_repository(db, client, body.repo_url)
    except GitHubError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return _repo_summary(repo)


@router.post("/analyze", status_code=201)
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db), client: GitHubClient = Depends(get_github_client)):
    if body.repository_id:
        repo = db.get(Repository, body.repository_id)
        if not repo or repo.is_demo:
            raise HTTPException(404, "Repository analysis not found.")
    elif body.repo_url:
        try:
            repo = pipeline.ingest_repository(db, client, body.repo_url)
        except GitHubError as exc:
            raise HTTPException(exc.status_code, exc.message) from exc
    else:
        raise HTTPException(422, "Provide repo_url or repository_id.")
    resume = None
    if body.resume_id:
        resume = db.get(Resume, body.resume_id)
        if not resume or resume.is_demo:
            raise HTTPException(404, "Resume not found.")
    passport = pipeline.build_passport(db, client, body.name, repo, resume)
    return pipeline.passport_dict(passport)


@router.get("/passports")
def list_passports(limit: int = 10, db: Session = Depends(get_db)):
    rows = db.query(Passport).order_by(Passport.created_at.desc()).limit(min(max(limit, 1), 50)).all()
    return [{"id": p.id, "student_name": p.student.name, "repository": p.repository.url, "is_demo": p.is_demo,
             "created_at": pipeline.iso(p.created_at), "summary": p.summary, "trust_level": p.trust_level} for p in rows]


@router.get("/passports/{passport_id}")
def get_passport(passport_id: str, db: Session = Depends(get_db)):
    return pipeline.passport_dict(_passport_or_404(db, passport_id))


@router.get("/passports/{passport_id}/evidence")
def get_evidence(passport_id: str, db: Session = Depends(get_db)):
    p = _passport_or_404(db, passport_id)
    out = []
    for s in p.skills:
        for e in pipeline.skill_dict(s)["evidence"]:
            out.append({"skill": s.skill, "verification_status": s.verification_status, **e})
    return {"passport_id": p.id, "count": len(out), "evidence": out}


@router.post("/match-job", status_code=201)
def match_job(body: JobMatchRequest, db: Session = Depends(get_db)):
    p = _passport_or_404(db, body.passport_id)
    try:
        m = pipeline.run_job_match(db, p, body.job_title, body.job_description)
    except JobMatchError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return pipeline.job_match_dict(m)


@router.get("/roadmap/{passport_id}")
def get_roadmap(passport_id: str, db: Session = Depends(get_db)):
    return pipeline.roadmap_for(_passport_or_404(db, passport_id))


@router.post("/passports/{passport_id}/share")
def share_passport(passport_id: str, body: ShareRequest, db: Session = Depends(get_db)):
    p = pipeline.set_sharing(db, _passport_or_404(db, passport_id), body.enabled)
    return pipeline.passport_dict(p)["sharing"]


@router.get("/public/passports/{public_id}")
def public_passport(public_id: str, db: Session = Depends(get_db)):
    p = db.query(Passport).filter(Passport.public_id == public_id, Passport.is_public.is_(True)).first()
    if not p:
        raise HTTPException(404, "This passport is not shared or does not exist.")
    return pipeline.public_passport_dict(p)


@router.post("/demo/load", status_code=201)
def load_demo(db: Session = Depends(get_db)):
    return pipeline.passport_dict(demo.load_demo(db))


@router.get("/demo/job")
def demo_job():
    return {"job_title": demo.DEMO_JOB_TITLE, "job_description": demo.DEMO_JOB_DESCRIPTION}
