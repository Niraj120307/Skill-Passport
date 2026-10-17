"""Unit tests for analysis engines (no network)."""
import pymupdf
import pytest

from app.services import authorship_guard
from app.services.github_client import GitHubError, parse_repo_url
from app.services.job_matcher import extract_job_skills, match
from app.services.repo_analyzer import scan_zip
from app.services.resume_parser import ResumeError, parse_resume
from app.services.skill_engine import verify_skills
from app.tests.conftest import REPO_FILES, RESUME_TEXT, make_commits, make_pdf, make_zip


def _norm(c):
    return authorship_guard.normalize_commits(c)


def test_parse_repo_url_valid_and_invalid():
    ref = parse_repo_url("https://github.com/octo/hello-world.git")
    assert (ref.owner, ref.repo) == ("octo", "hello-world")
    assert parse_repo_url("github.com/a/b/").repo == "b"
    for bad in ["https://gitlab.com/a/b", "not a url", "https://github.com/onlyowner"]:
        with pytest.raises(GitHubError):
            parse_repo_url(bad)


def test_scan_finds_ast_evidence_with_lines_and_redacts_secrets():
    scan = scan_zip(make_zip(REPO_FILES), 100, 300)
    by = {}
    for f in scan.findings:
        by.setdefault(f.skill, []).append(f)
    routes = [f for f in by["fastapi"] if f.feature == "route handlers"]
    assert routes and routes[0].file == "app/main.py" and routes[0].line_start == 8
    assert any(f.feature == "dependency injection" for f in by["fastapi"])
    assert any(f.feature == "multiple HTTP methods" for f in by["rest_api"])
    assert any(f.feature == "ORM models" for f in by["sql"])
    assert any(f.type == "test" for f in by["testing"])
    assert any(f.feature == "fixtures" for f in by["testing"])
    # pandas only imported -> import + manifest, no code usage
    assert {f.type for f in by["pandas"]} <= {"code_import", "dependency_manifest"}
    # no snippet anywhere contains the secret
    assert all("supersecretvalue" not in (f.snippet or "") for f in scan.findings)


def _records(findings, commits, claims=None, high=False):
    return {r["skill_id"]: r for r in verify_skills(findings=findings, commits=_norm(commits), owner="student",
                                                    repo_url="https://github.com/student/taskapi", ref="a" * 40,
                                                    resume_claims=claims or [], high_trust_concern=high)}


def test_statuses_follow_rules():
    scan = scan_zip(make_zip(REPO_FILES), 100, 300)
    claims = [{"skill_id": "machine_learning", "skill": "Machine Learning", "page": 1, "section": "skills", "snippet": "ML"}]
    recs = _records([f.to_dict() for f in scan.findings], make_commits("student", 14), claims)
    assert recs["fastapi"]["verification_status"] == "evidence_supported"
    assert recs["python"]["verification_status"] == "evidence_supported"
    assert recs["pandas"]["verification_status"] == "partially_supported"
    assert recs["pandas"]["estimated_level"] is None  # import-only never gets a level
    assert recs["machine_learning"]["verification_status"] == "unverified"
    assert recs["git"]["verification_status"] == "evidence_supported"
    # docker: README mention only
    assert recs["docker"]["verification_status"] == "partially_supported"
    # evidence links point at real file + line permalinks
    ev = [e for e in recs["fastapi"]["evidence"] if e["evidence_type"] == "code_usage"][0]
    assert ev["url"].startswith("https://github.com/student/taskapi/blob/" + "a" * 40 + "/")
    assert "#L" in ev["url"]


def test_resume_claim_alone_never_supported():
    claims = [{"skill_id": s, "skill": s, "page": 1, "section": "skills", "snippet": s} for s in ["python", "docker", "react"]]
    recs = _records([], [], claims)
    assert {r["verification_status"] for r in recs.values()} == {"unverified"}


def test_high_trust_concern_flags_supported_skills():
    scan = scan_zip(make_zip(REPO_FILES), 100, 300)
    recs = _records([f.to_dict() for f in scan.findings], [], high=True)
    assert recs["fastapi"]["verification_status"] == "flagged_for_review"


def test_authorship_guard_fork_and_burst_and_incomplete():
    repo = {"owner": "student", "url": "u", "is_fork": True, "parent_full_name": "up/x", "parent_url": "p",
            "commits": _norm(make_commits("someoneelse", 12, days=1)), "contributors": [], "file_histories": {},
            "source_file_count": 5, "readme_excerpt": ""}
    res = authorship_guard.evaluate(repo, 100)
    types = {s["signal_type"]: s for s in res["signals"]}
    assert res["trust_level"] == "high_concern"
    assert "fork_without_owner_commits" in types
    assert "commit_burst" not in types or types["commit_burst"]["severity"] == "low"
    res2 = authorship_guard.evaluate({**repo, "is_fork": False, "commits": []}, 100)
    assert res2["trust_level"] == "incomplete"
    assert res2["meta"]["assessment_complete"] is False


def test_burst_detected():
    commits = make_commits("student", 6, days=6) + [
        {**c, "commit": {**c["commit"], "author": {"name": "s", "date": "2026-09-20T10:00:00Z"}}} for c in make_commits("student", 12, days=1)
    ]
    for i, c in enumerate(commits):
        c["sha"] = f"{i:040x}"
    res = authorship_guard.evaluate({"owner": "student", "is_fork": False, "commits": _norm(commits)}, 100)
    assert any(s["signal_type"] == "commit_burst" for s in res["signals"])
    assert res["trust_level"] != "high_concern"  # a burst alone is never high severity


def test_job_match_formula_and_no_inflation():
    skills = [
        {"skill_id": "python", "verification_status": "evidence_supported", "estimated_level": "Intermediate", "evidence_strength": 1, "skill": "Python"},
        {"skill_id": "sql", "verification_status": "partially_supported", "estimated_level": None, "evidence_strength": .3, "skill": "SQL"},
        {"skill_id": "docker", "verification_status": "unverified", "estimated_level": None, "evidence_strength": 0, "skill": "Docker"},
        {"skill_id": "react", "verification_status": "evidence_supported", "estimated_level": "Advanced", "evidence_strength": 1, "skill": "React"},
    ]
    jd = "Requirements:\n- Python\n- SQL databases\n- Docker\n- Kubernetes knowledge\nNice to have:\n- CI/CD pipelines\n"
    res = match(skills, "Backend Developer", jd)
    # required: python(2*1) sql(2*.5) docker(2*0); preferred ci_cd(1*0) => 3/7
    assert res["score"] == pytest.approx(round(100 * 3 / 7, 1))
    assert "React" in res["not_requested"]  # unrelated skill does not inflate score
    assert [i["skill_id"] for i in res["unverified_claims"]] == ["docker"]
    assert any(i["skill_id"] == "ci_cd" and i["requirement"] == "preferred" for i in res["missing"])


def test_extract_job_skills_ignores_lowercase_ambiguous():
    found = extract_job_skills("We use node to rest and ts in the ml lab. Must know Node.js and REST APIs.")
    assert "nodejs" in found and "rest_api" in found
    assert "typescript" not in found and "machine_learning" not in found


def test_resume_parser_claims_and_errors():
    res = parse_resume(make_pdf(RESUME_TEXT), "cv.pdf", 5)
    names = {c["skill"] for c in res.claims}
    assert {"Python", "SQL", "Docker", "Machine Learning", "React", "FastAPI"} <= names
    assert all(c["page"] == 1 for c in res.claims)
    assert res.projects and res.projects[0]["title"] == "Task API"
    with pytest.raises(ResumeError):
        parse_resume(b"hello", "cv.txt", 5)
    with pytest.raises(ResumeError):
        parse_resume(b"%PDF-1.4 garbage", "cv.pdf", 5)
    # encrypted
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 72), RESUME_TEXT)
    enc = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="x", owner_pw="y")
    with pytest.raises(ResumeError, match="password"):
        parse_resume(enc, "cv.pdf", 5)
    # scanned (image only)
    doc2 = pymupdf.open()
    pg = doc2.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
    pg.insert_image(pg.rect, pixmap=pix)
    with pytest.raises(ResumeError, match="scanned"):
        parse_resume(doc2.tobytes(), "cv.pdf", 5)
