"""Demo mode: a clearly labelled sample passport for judging without network access.
All evidence is ILLUSTRATIVE (flagged `illustrative=True`, no links), stored with
is_demo=True and kept separate from real analyses."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.models import Passport, Repository, Resume
from app.services import pipeline

DEMO_JOB_TITLE = "Backend Developer (Python)"
DEMO_JOB_DESCRIPTION = """We are hiring a Backend Developer to build and maintain our REST APIs.

Requirements:
- Strong Python skills
- Experience building REST APIs with FastAPI
- SQL and relational database design (PostgreSQL)
- Docker for containerised deployments
- Git and code review workflows
- Writing automated tests with pytest

Nice to have:
- CI/CD with GitHub Actions
- Basic React for internal dashboards
"""

OWNER = "demo-student"


def _f(skill, ftype, file, line=None, feature=None, detail="", snippet=None, end=None):
    return {"skill": skill, "type": ftype, "file": file, "line_start": line, "line_end": end or line,
            "snippet": snippet, "feature": feature, "detail": detail}


def _findings() -> list[dict]:
    F = []
    for path, n in [("app/main.py", 64), ("app/routers/tasks.py", 118), ("app/models.py", 52), ("app/schemas.py", 41), ("app/db.py", 23), ("tests/test_tasks.py", 88)]:
        F.append(_f("python", "source_file", path, 1, None, f"{n} non-blank lines of Python", end=n))
    F += [
        _f("python", "code_usage", "app/routers/tasks.py", 12, "type hints", "Python type hints", "def list_tasks(db: Session = Depends(get_db)) -> list[TaskOut]:"),
        _f("python", "code_usage", "app/schemas.py", 6, "classes", "Python classes", "class TaskCreate(BaseModel):"),
        _f("python", "code_usage", "app/db.py", 15, "generators", "Python generators", "yield db"),
        _f("python", "code_usage", "app/routers/tasks.py", 40, "exception handling", "Python exception handling", "try:"),
        _f("python", "code_usage", "app/main.py", 30, "decorators used", "Python decorators used", "@app.get(\"/health\")"),
        _f("fastapi", "code_import", "app/main.py", 1, None, "imports `fastapi`", "from fastapi import FastAPI"),
        _f("fastapi", "code_usage", "app/main.py", 30, "route handlers", "HTTP route `health`", "@app.get(\"/health\")"),
        _f("fastapi", "code_usage", "app/routers/tasks.py", 12, "dependency injection", "calls `Depends`", "db: Session = Depends(get_db)"),
        _f("fastapi", "code_usage", "app/routers/tasks.py", 5, "APIRouter", "calls `APIRouter`", "router = APIRouter(prefix=\"/api/v1/tasks\")"),
        _f("fastapi", "code_usage", "app/schemas.py", 6, "pydantic models", "request/response model `TaskCreate`", "class TaskCreate(BaseModel):"),
        _f("fastapi", "code_usage", "app/routers/tasks.py", 41, "HTTPException", "calls `HTTPException`", "raise HTTPException(status_code=404, detail=\"Task not found\")"),
        _f("fastapi", "dependency_manifest", "requirements.txt", 1, None, "declares dependency `fastapi`", "fastapi==0.115.0"),
        _f("rest_api", "code_usage", "app/routers/tasks.py", 11, "HTTP route handlers", "fastapi route handler `list_tasks`", "@router.get(\"/\")"),
        _f("rest_api", "code_usage", "app/routers/tasks.py", 22, "HTTP route handlers", "fastapi route handler `create_task`", "@router.post(\"/\", status_code=201)"),
        _f("rest_api", "code_usage", "app/routers/tasks.py", 11, "multiple HTTP methods", "methods used: DELETE, GET, POST, PUT", "@router.get(\"/\")"),
        _f("rest_api", "code_usage", "app/main.py", 30, "HTTP route handlers", "fastapi route handler `health`", "@app.get(\"/health\")"),
        _f("rest_api", "code_usage", "app/routers/tasks.py", 41, "error handling", "raises HTTP errors", "raise HTTPException(status_code=404, detail=\"Task not found\")"),
        _f("sql", "code_import", "app/db.py", 1, None, "imports `sqlalchemy`", "from sqlalchemy import create_engine"),
        _f("sql", "code_usage", "app/db.py", 6, "database connection", "calls `create_engine`", "engine = create_engine(DATABASE_URL)"),
        _f("sql", "code_usage", "app/models.py", 8, "ORM models", "ORM model `Task`", "class Task(Base):"),
        _f("sql", "code_usage", "app/routers/tasks.py", 28, "transactions", "calls `.commit()`", "db.commit()"),
        _f("sql", "dependency_manifest", "requirements.txt", 3, None, "declares dependency `sqlalchemy`", "sqlalchemy==2.0.35"),
        _f("testing", "test", "tests/test_tasks.py", 1, None, "test file", end=88),
        _f("testing", "test", "tests/conftest.py", 1, None, "test file", end=31),
        _f("testing", "code_usage", "tests/conftest.py", 9, "fixtures", "pytest fixture", "@pytest.fixture"),
        _f("testing", "code_usage", "tests/test_tasks.py", 20, "test cases", "test function `test_create_task`", "def test_create_task(client):"),
        _f("testing", "code_usage", "tests/test_tasks.py", 26, "assertions", "assert statement", "assert resp.status_code == 201"),
        _f("testing", "code_usage", "tests/test_tasks.py", 44, "parametrized tests", "parametrized test", "@pytest.mark.parametrize(\"title\", [\"\", \"x\" * 300])"),
        _f("testing", "dependency_manifest", "requirements.txt", 5, None, "declares dependency `pytest`", "pytest==8.3.3"),
        _f("docker", "documentation", "README.md", 34, None, "README mentions `Docker`", "Deployment with Docker is planned."),
    ]
    return F


def _commits() -> list[dict]:
    """Illustrative history: steady work by the owner plus a burst before the deadline."""
    base = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)
    commits = []
    i = 0
    for day in range(0, 20, 2):  # 10 active days, 2 commits each
        for k in range(2):
            commits.append({"sha": f"demo{i:036d}", "url": None, "date": (base + timedelta(days=day, hours=k)).isoformat(),
                            "author_login": OWNER, "author_name": "Demo Student", "message": f"Illustrative commit {i}"})
            i += 1
    burst_day = base + timedelta(days=21)
    for k in range(14):
        commits.append({"sha": f"demo{i:036d}", "url": None, "date": (burst_day + timedelta(minutes=10 * k)).isoformat(),
                        "author_login": OWNER if k % 2 else "teammate-x", "author_name": "Demo", "message": f"Illustrative burst commit {k}"})
        i += 1
    commits.sort(key=lambda c: c["date"], reverse=True)
    return commits


def load_demo(db: Session) -> Passport:
    existing = db.query(Passport).filter(Passport.is_demo.is_(True)).order_by(Passport.created_at.desc()).first()
    if existing:
        return existing
    repo = Repository(
        url="demo://sample-task-api", owner=OWNER, name="sample-task-api (DEMO)",
        description="Illustrative sample repository for demo mode — not a real GitHub repository.",
        default_branch="main", head_sha=None, is_fork=False, stars=0,
        languages={"Python": 18342},
        file_count=24, files_scanned=24, findings=_findings(), commits=_commits(),
        contributors=[{"login": OWNER, "contributions": 27}, {"login": "teammate-x", "contributions": 7}],
        readme_excerpt="Sample Task API (demo data).", scan_notes=["DEMO MODE: all evidence below is illustrative.", "source_file_count=6"],
        is_demo=True,
    )
    resume = Resume(
        filename="demo_resume.pdf (illustrative)", page_count=1, text_chars=1800, is_demo=True,
        claims=[
            {"skill_id": "python", "skill": "Python", "page": 1, "section": "technical skills", "snippet": "Languages: Python, SQL", "matched": "Python", "mentions": 3},
            {"skill_id": "fastapi", "skill": "FastAPI", "page": 1, "section": "projects", "snippet": "Task API built with FastAPI and SQLAlchemy", "matched": "FastAPI", "mentions": 1},
            {"skill_id": "sql", "skill": "SQL", "page": 1, "section": "technical skills", "snippet": "Languages: Python, SQL", "matched": "SQL", "mentions": 2},
            {"skill_id": "docker", "skill": "Docker", "page": 1, "section": "technical skills", "snippet": "Tools: Git, Docker", "matched": "Docker", "mentions": 1},
            {"skill_id": "machine_learning", "skill": "Machine Learning", "page": 1, "section": "technical skills", "snippet": "Interests: Machine Learning", "matched": "Machine Learning", "mentions": 1},
        ],
        projects=[{"title": "Sample Task API", "page": 1, "details": ["REST API with FastAPI, SQLAlchemy and pytest"], "technologies": ["FastAPI", "Python", "SQL"]}],
        experience=[], notes=["DEMO MODE: illustrative resume data.", "Resume claims are recorded as claims only; they never count as verified evidence."],
    )
    db.add_all([repo, resume])
    db.flush()
    passport = pipeline.build_passport(db, None, "Demo Student (sample)", repo, resume, is_demo=True)
    pipeline.run_job_match(db, passport, DEMO_JOB_TITLE, DEMO_JOB_DESCRIPTION)
    db.refresh(passport)
    return passport
