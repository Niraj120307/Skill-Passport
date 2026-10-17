"""Deterministic learning-roadmap catalog (no LLM). One entry per taxonomy skill."""
from __future__ import annotations

CATALOG: dict[str, dict] = {
    "python": {
        "why": "Python is the base language for most backend, data and automation roles.",
        "steps": ["Write modules with functions, classes and type hints", "Handle errors with try/except and custom exceptions", "Use comprehensions, generators and context managers", "Package code with a requirements file and a README"],
        "project": "CLI expense tracker: reads a CSV, categorises expenses with classes, writes a monthly summary report.",
        "acceptance": ["At least 3 modules with type hints", "Custom exception class used", "Runs with `python -m tracker report data.csv`", "README explains usage"],
        "evidence": "Public repo with ≥ 3 Python source files and commits spread over several days.",
    },
    "java": {
        "why": "Java is widely used for enterprise backends and Android.",
        "steps": ["Model a domain with classes, interfaces and inheritance", "Use collections and the Streams API", "Handle exceptions properly", "Build with Maven or Gradle"],
        "project": "Library management console app with Book/Member classes, a Loan interface and stream-based reports.",
        "acceptance": ["Interface + 2 implementations", "Streams used for at least 2 reports", "Builds with `mvn package`"],
        "evidence": "Repository with pom.xml/build.gradle and ≥ 3 Java files using interfaces and streams.",
    },
    "cpp": {
        "why": "C++ matters for systems, performance-critical and embedded work.",
        "steps": ["Classes with constructors/destructors and RAII", "STL containers and algorithms", "Smart pointers instead of raw new/delete", "Templates for reusable code"],
        "project": "Bank account simulator using classes, std::vector, unique_ptr and a templated transaction log.",
        "acceptance": ["No raw new/delete", "At least one template", "Builds with CMake or a documented g++ command"],
        "evidence": "Repository with ≥ 3 .cpp/.hpp files showing classes, STL and smart pointers.",
    },
    "javascript": {
        "why": "JavaScript powers the web front end and Node.js back ends.",
        "steps": ["ES modules, arrow functions and destructuring", "Array methods map/filter/reduce", "Promises and async/await with fetch", "DOM manipulation or a small Node script"],
        "project": "Weather dashboard that fetches a public API with async/await and renders results with array methods.",
        "acceptance": ["Uses async/await with error handling", "At least 3 ES modules", "Works by opening index.html or `npm start`"],
        "evidence": "Repository with ≥ 3 .js files using modules and async code.",
    },
    "typescript": {
        "why": "TypeScript is now the default for professional JavaScript codebases.",
        "steps": ["Add tsconfig with strict mode", "Model data with interfaces and type aliases", "Write generic helper functions", "Type API responses end-to-end"],
        "project": "Convert a small JS app to TypeScript with strict mode and typed API client.",
        "acceptance": ["`strict: true` in tsconfig", "No `any` in the API layer", "`tsc --noEmit` passes"],
        "evidence": "tsconfig.json plus ≥ 3 .ts/.tsx files with interfaces and generics.",
    },
    "react": {
        "why": "React is the most requested front-end library in job listings.",
        "steps": ["Build components with props and useState/useEffect", "Lift state up and use context for shared state", "Add routing with React Router", "Extract a custom hook"],
        "project": "Task board app with routing, a context-backed store and a custom useTasks hook.",
        "acceptance": ["≥ 5 components", "One custom hook", "Two routes", "Builds with `npm run build`"],
        "evidence": "Repository with ≥ 3 React component files, a custom hook and routing.",
    },
    "html_css": {
        "why": "Every web role expects solid, responsive layout skills.",
        "steps": ["Semantic HTML structure", "Flexbox and CSS Grid layouts", "Responsive design with media queries", "CSS variables for theming"],
        "project": "Responsive portfolio page with grid layout, dark-mode variables and semantic sections.",
        "acceptance": ["Works at 375px and 1280px widths", "Uses grid + flexbox", "Uses CSS variables"],
        "evidence": "HTML and CSS files showing grid, media queries and semantic tags.",
    },
    "fastapi": {
        "why": "FastAPI is a fast-growing choice for Python APIs with automatic validation and docs.",
        "steps": ["Create routes with path/query parameters", "Validate bodies with Pydantic models", "Use Depends for a database session", "Raise HTTPException for errors and test with TestClient"],
        "project": "Notes API with CRUD endpoints, Pydantic schemas, SQLite via SQLAlchemy and pytest tests.",
        "acceptance": ["4 CRUD endpoints", "Pydantic request/response models", "Dependency-injected DB session", "≥ 5 passing tests"],
        "evidence": "Repository with FastAPI routes in ≥ 2 files plus a tests/ folder.",
    },
    "flask": {
        "why": "Flask is a common lightweight Python web framework.",
        "steps": ["App factory pattern", "Blueprints for route groups", "Templates or JSON responses", "Error handlers"],
        "project": "Flask URL shortener with blueprints, SQLite storage and a custom 404 handler.",
        "acceptance": ["App factory + 2 blueprints", "Error handler registered", "Tests for 3 routes"],
        "evidence": "Repository with Flask routes across ≥ 2 files.",
    },
    "nodejs": {
        "why": "Node.js/Express backends are common in full-stack JavaScript roles.",
        "steps": ["Express routes and routers", "Middleware for logging and validation", "Connect a database", "Environment-based configuration"],
        "project": "Express REST API for a bookstore with routers, validation middleware and PostgreSQL/SQLite.",
        "acceptance": ["Routers in separate files", "Custom middleware", "Proper status codes"],
        "evidence": "Repository with Express routes in ≥ 2 files and package.json.",
    },
    "rest_api": {
        "why": "Designing clean HTTP APIs is a core backend skill.",
        "steps": ["Resource-oriented URLs and HTTP methods", "Correct status codes and error bodies", "Input validation", "Versioning and documentation (OpenAPI)"],
        "project": "Versioned /api/v1 inventory API with validation, consistent error responses and OpenAPI docs.",
        "acceptance": ["GET/POST/PUT/DELETE implemented", "4xx errors return JSON bodies", "Documented endpoints"],
        "evidence": "Route handlers using ≥ 2 HTTP methods across ≥ 2 files, with error handling.",
    },
    "sql": {
        "why": "Almost every application stores data in a relational database.",
        "steps": ["Design normalised tables with keys", "Write JOIN and GROUP BY queries", "Add indexes and explain why", "Use an ORM or parameterised queries from code"],
        "project": "College event registration DB: schema.sql, seed data, 5 reporting queries and an ORM-backed API.",
        "acceptance": ["≥ 3 related tables with foreign keys", "JOIN + GROUP BY queries", "At least one index", "No string-concatenated SQL"],
        "evidence": ".sql files or ORM models plus queries in ≥ 2 files.",
    },
    "pandas": {
        "why": "Pandas is the standard tool for data cleaning and analysis in Python.",
        "steps": ["Load and inspect data", "Clean missing values and types", "groupby/merge/pivot_table analyses", "Export results and charts"],
        "project": "Analyse a public dataset (e.g. India trade data): clean it, merge two tables, produce monthly pivot summaries.",
        "acceptance": ["Uses merge + groupby + pivot_table", "Handles missing values explicitly", "Script reproduces outputs end-to-end"],
        "evidence": "Python files using Pandas transformations (not just an import).",
    },
    "numpy": {
        "why": "NumPy underpins numerical computing and ML in Python.",
        "steps": ["Array creation and vectorised operations", "Broadcasting and reshaping", "Linear algebra with np.linalg", "Random sampling"],
        "project": "Implement linear regression from scratch with NumPy (normal equation + gradient descent).",
        "acceptance": ["No Python loops over samples", "Uses np.linalg", "Matches sklearn result within 1e-3"],
        "evidence": "Python files with vectorised NumPy operations.",
    },
    "machine_learning": {
        "why": "ML roles expect end-to-end model building and honest evaluation.",
        "steps": ["Train/test split and baselines", "Feature preprocessing pipelines", "Cross-validation and hyperparameter search", "Report metrics and limitations"],
        "project": "Student performance predictor with a scikit-learn Pipeline, GridSearchCV and a metrics report.",
        "acceptance": ["Pipeline with preprocessing", "Cross-validated metrics", "Baseline comparison documented"],
        "evidence": "Code that trains and evaluates models (fit/predict + metrics), ideally with pipelines.",
    },
    "git": {
        "why": "Teams expect clean, incremental version control history.",
        "steps": ["Commit small logical changes with clear messages", "Use branches and pull requests", "Resolve a merge conflict", "Tag a release"],
        "project": "Develop your next project over ≥ 1 week with feature branches and PRs merged into main.",
        "acceptance": ["≥ 15 commits over ≥ 5 days", "≥ 2 merged pull requests", "Meaningful commit messages"],
        "evidence": "Commit history authored by your GitHub account across multiple days.",
    },
    "docker": {
        "why": "Containers are the standard way to ship and run backend services.",
        "steps": ["Write a Dockerfile for a FastAPI app", "Use .dockerignore and a slim base image", "Run with docker compose alongside a database", "Add a multi-stage build"],
        "project": "Containerise a FastAPI app: Dockerfile + docker-compose.yml with a database; the container runs successfully.",
        "acceptance": ["`docker compose up` starts the app", "Image uses a slim base", "Health endpoint reachable from host"],
        "evidence": "Repository containing the Dockerfile, docker-compose.yml and README run instructions.",
    },
    "ci_cd": {
        "why": "Automated testing and deployment pipelines are expected in modern teams.",
        "steps": ["Add a GitHub Actions workflow that runs tests", "Cache dependencies", "Add lint + test jobs", "Build a Docker image on main"],
        "project": "GitHub Actions pipeline for your API: lint, test (matrix of 2 Python versions) and Docker build.",
        "acceptance": ["Workflow passes on main", "Matrix build", "Badge in README"],
        "evidence": ".github/workflows/*.yml with real jobs and passing runs.",
    },
    "testing": {
        "why": "Tested code is a strong signal of professional engineering habits.",
        "steps": ["Unit tests with pytest/Jest", "Fixtures and parametrised tests", "Mock external services", "Measure coverage"],
        "project": "Add a test suite to an existing project reaching ≥ 70% coverage with mocked network calls.",
        "acceptance": ["≥ 10 tests", "At least one mock", "Coverage report in README"],
        "evidence": "tests/ folder with test files that exercise real code.",
    },
}


def build_roadmap(gaps: list[dict]) -> list[dict]:
    """gaps: items with skill_id, skill, status, requirement (job-match items or passport records)."""
    plan = []
    for g in gaps:
        entry = CATALOG.get(g["skill_id"])
        if not entry:
            continue
        status = g.get("status") or g.get("verification_status")
        reason = {
            "missing": "No evidence and no claim — this is a new skill to build.",
            "unverified": "Claimed on your resume but not demonstrated in your repository.",
            "partially_supported": "Some evidence exists but not enough to be fully supported.",
            "flagged_for_review": "Evidence exists but repository authorship needs review — build fresh evidence in your own repo.",
        }.get(status, "")
        plan.append({
            "skill": g["skill"], "skill_id": g["skill_id"], "current_status": status,
            "priority": "high" if g.get("requirement", "required") == "required" else "medium",
            "why_it_matters": entry["why"], "gap_reason": reason,
            "steps": entry["steps"], "mini_project": entry["project"],
            "acceptance_criteria": entry["acceptance"], "evidence_needed": entry["evidence"],
        })
    plan.sort(key=lambda p: (p["priority"] != "high", p["skill"]))
    return plan
