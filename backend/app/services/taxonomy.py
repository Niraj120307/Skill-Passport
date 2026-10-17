"""Configurable skill taxonomy.

Each skill describes *how* it can be evidenced in a repository:
  - aliases:        words used to detect claims in resumes / job descriptions
  - py_modules:     Python import roots (matched through the AST, never by executing code)
  - py_packages / npm_packages / jvm_artifacts: dependency-manifest names
  - extensions:     source files that are themselves evidence (language skills)
  - line_patterns:  regexes applied line-by-line to non-Python files
  - path_patterns:  regexes applied to file paths (Dockerfile, workflows ...)
  - intermediate_features / advanced_features: feature names that raise the
    proficiency estimate (see scoring_config.py for the thresholds)
  - min_files:      distinct files with strong evidence required for `evidence_supported`

Edit this file to extend the taxonomy; nothing else needs to change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LinePattern:
    regex: str
    feature: str
    exts: tuple[str, ...] = ()  # empty = any scanned text file
    kind: str = "code_usage"


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    category: str
    aliases: tuple[str, ...]
    py_modules: tuple[str, ...] = ()
    py_packages: tuple[str, ...] = ()
    npm_packages: tuple[str, ...] = ()
    jvm_artifacts: tuple[str, ...] = ()
    extensions: tuple[str, ...] = ()
    line_patterns: tuple[LinePattern, ...] = ()
    path_patterns: tuple[tuple[str, str], ...] = ()  # (regex, feature) -> config evidence
    intermediate_features: frozenset[str] = field(default_factory=frozenset)
    advanced_features: frozenset[str] = field(default_factory=frozenset)
    min_files: int = 2


JS_EXT = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
PY = (".py",)

SKILLS: tuple[Skill, ...] = (
    Skill(
        id="python", name="Python", category="Language",
        aliases=("python", "python3"),
        extensions=(".py",),
        intermediate_features=frozenset({"classes", "decorators used", "comprehensions", "type hints", "exception handling"}),
        advanced_features=frozenset({"async functions", "custom decorators", "dataclasses", "context managers", "generators"}),
    ),
    Skill(
        id="java", name="Java", category="Language", aliases=("java",),
        extensions=(".java",),
        line_patterns=(
            LinePattern(r"\binterface\s+\w+", "interfaces", (".java",)),
            LinePattern(r"\bextends\s+\w+|\bimplements\s+\w+", "inheritance", (".java",)),
            LinePattern(r"\.stream\(\)", "streams API", (".java",)),
            LinePattern(r"<\s*[A-Z]\w*\s*(extends\s+\w+)?\s*>", "generics", (".java",)),
            LinePattern(r"try\s*\{|catch\s*\(", "exception handling", (".java",)),
            LinePattern(r"\bsynchronized\b|ExecutorService|CompletableFuture", "concurrency", (".java",)),
        ),
        intermediate_features=frozenset({"interfaces", "inheritance", "generics", "exception handling"}),
        advanced_features=frozenset({"streams API", "concurrency"}),
    ),
    Skill(
        id="cpp", name="C++", category="Language", aliases=("c++", "cpp"),
        extensions=(".cpp", ".cc", ".cxx", ".hpp", ".hh"),
        line_patterns=(
            LinePattern(r"^\s*class\s+\w+", "classes", (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h")),
            LinePattern(r"\btemplate\s*<", "templates", (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h")),
            LinePattern(r"std::(vector|map|unordered_map|set|string|pair)", "STL containers", (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h")),
            LinePattern(r"std::(unique_ptr|shared_ptr|make_unique|make_shared)", "smart pointers", (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h")),
            LinePattern(r"\boperator\s*[^\w\s(]{1,3}\s*\(", "operator overloading", (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h")),
            LinePattern(r"\bvirtual\b", "polymorphism", (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h")),
        ),
        intermediate_features=frozenset({"classes", "STL containers", "polymorphism"}),
        advanced_features=frozenset({"templates", "smart pointers", "operator overloading"}),
    ),
    Skill(
        id="javascript", name="JavaScript", category="Language", aliases=("javascript", "js", "es6", "ecmascript"),
        extensions=(".js", ".jsx", ".mjs", ".cjs"),
        line_patterns=(
            LinePattern(r"\basync\s+(function|\()|\bawait\s", "async/await", (".js", ".jsx", ".mjs", ".cjs")),
            LinePattern(r"^\s*(export\s+)?class\s+\w+", "classes", (".js", ".jsx", ".mjs", ".cjs")),
            LinePattern(r"\.(map|filter|reduce)\(", "array methods", (".js", ".jsx", ".mjs", ".cjs")),
            LinePattern(r"^\s*(import|export)\s", "ES modules", (".js", ".jsx", ".mjs")),
            LinePattern(r"new\s+Promise\(|Promise\.all", "promises", (".js", ".jsx", ".mjs", ".cjs")),
        ),
        intermediate_features=frozenset({"async/await", "ES modules", "array methods", "classes"}),
        advanced_features=frozenset({"promises"}),
    ),
    Skill(
        id="typescript", name="TypeScript", category="Language", aliases=("typescript", "ts"),
        extensions=(".ts", ".tsx"),
        npm_packages=("typescript",),
        line_patterns=(
            LinePattern(r"^\s*(export\s+)?interface\s+\w+", "interfaces", (".ts", ".tsx")),
            LinePattern(r"^\s*(export\s+)?type\s+\w+\s*=", "type aliases", (".ts", ".tsx")),
            LinePattern(r"\w+<\s*[A-Z]\w*(\s*extends\s+[^>]+)?\s*>\s*\(", "generics", (".ts", ".tsx")),
            LinePattern(r"\b(Partial|Pick|Omit|Record|Readonly)<", "utility types", (".ts", ".tsx")),
        ),
        path_patterns=((r"(^|/)tsconfig(\.\w+)?\.json$", "tsconfig"),),
        intermediate_features=frozenset({"interfaces", "type aliases"}),
        advanced_features=frozenset({"generics", "utility types"}),
    ),
    Skill(
        id="react", name="React", category="Frontend",
        aliases=("react", "react.js", "reactjs"),
        npm_packages=("react", "react-dom", "next"),
        line_patterns=(
            LinePattern(r"from\s+['\"]react['\"]|require\(['\"]react['\"]\)", "react import", JS_EXT, "code_import"),
            LinePattern(r"\buse(State|Effect)\s*\(", "state/effect hooks", JS_EXT),
            LinePattern(r"\buse(Context|Reducer|Memo|Callback|Ref)\s*\(", "advanced hooks", JS_EXT),
            LinePattern(r"\bcreateContext\s*\(", "context API", JS_EXT),
            LinePattern(r"^\s*(export\s+)?(function|const)\s+use[A-Z]\w*", "custom hooks", JS_EXT),
            LinePattern(r"<(Routes|Route|BrowserRouter|Link)\b", "routing", (".jsx", ".tsx", ".js")),
            LinePattern(r"return\s*\(\s*$|<[A-Z]\w*[\s/>]", "JSX components", (".jsx", ".tsx")),
        ),
        intermediate_features=frozenset({"advanced hooks", "routing", "context API"}),
        advanced_features=frozenset({"custom hooks"}),
    ),
    Skill(
        id="html_css", name="HTML/CSS", category="Frontend",
        aliases=("html", "css", "html5", "css3", "html/css", "tailwind", "sass", "scss", "bootstrap"),
        extensions=(".html", ".css", ".scss"),
        npm_packages=("tailwindcss", "sass", "bootstrap"),
        line_patterns=(
            LinePattern(r"display\s*:\s*flex", "flexbox", (".css", ".scss")),
            LinePattern(r"display\s*:\s*grid", "css grid", (".css", ".scss")),
            LinePattern(r"@media\s", "responsive media queries", (".css", ".scss")),
            LinePattern(r"<(header|nav|main|section|article|footer)\b", "semantic HTML", (".html",)),
            LinePattern(r"--[\w-]+\s*:|var\(--", "CSS variables", (".css", ".scss")),
            LinePattern(r"@keyframes|transition\s*:", "animations", (".css", ".scss")),
        ),
        intermediate_features=frozenset({"flexbox", "css grid", "semantic HTML"}),
        advanced_features=frozenset({"responsive media queries", "CSS variables", "animations"}),
    ),
    Skill(
        id="fastapi", name="FastAPI", category="Backend", aliases=("fastapi",),
        py_modules=("fastapi",), py_packages=("fastapi",),
        intermediate_features=frozenset({"route handlers", "pydantic models", "APIRouter", "HTTPException"}),
        advanced_features=frozenset({"dependency injection", "background tasks", "websockets", "middleware"}),
    ),
    Skill(
        id="flask", name="Flask", category="Backend", aliases=("flask",),
        py_modules=("flask", "flask_sqlalchemy", "flask_restful", "flask_cors"), py_packages=("flask",),
        intermediate_features=frozenset({"route handlers", "blueprints", "templates rendering"}),
        advanced_features=frozenset({"app factory", "error handlers", "before_request hooks"}),
    ),
    Skill(
        id="nodejs", name="Node.js/Express", category="Backend",
        aliases=("node.js", "nodejs", "node", "express", "express.js", "expressjs"),
        npm_packages=("express", "fastify", "koa", "@nestjs/core"),
        line_patterns=(
            LinePattern(r"require\(['\"]express['\"]\)|from\s+['\"]express['\"]", "express import", JS_EXT, "code_import"),
            LinePattern(r"\b(app|router)\.(get|post|put|patch|delete)\s*\(\s*['\"`]/", "route handlers", JS_EXT),
            LinePattern(r"\bapp\.use\s*\(", "middleware", JS_EXT),
            LinePattern(r"\.listen\s*\(\s*\w*", "server bootstrap", JS_EXT),
            LinePattern(r"express\.Router\s*\(", "routers", JS_EXT),
        ),
        intermediate_features=frozenset({"route handlers", "routers"}),
        advanced_features=frozenset({"middleware"}),
    ),
    Skill(
        id="rest_api", name="REST APIs", category="Backend",
        aliases=("rest", "rest api", "rest apis", "restful", "api development", "http api", "web api", "web apis"),
        line_patterns=(
            LinePattern(r"\b(app|router)\.(get|post|put|patch|delete)\s*\(\s*['\"`]/", "HTTP route handlers", JS_EXT),
            LinePattern(r"@(Get|Post|Put|Delete|Patch|Request)Mapping|@RestController", "HTTP route handlers", (".java",)),
            LinePattern(r"\bfetch\s*\(|axios\.(get|post|put|delete|patch)\s*\(", "HTTP client calls", JS_EXT),
            LinePattern(r"status_code\s*=\s*\d{3}|res\.status\(\d{3}\)|HttpStatus\.", "explicit status codes", JS_EXT + PY + (".java",)),
        ),
        intermediate_features=frozenset({"multiple HTTP methods", "explicit status codes", "request validation"}),
        advanced_features=frozenset({"error handling", "API versioning"}),
    ),
    Skill(
        id="sql", name="SQL", category="Data",
        aliases=("sql", "mysql", "postgresql", "postgres", "sqlite", "sql server", "oracle sql", "pl/sql", "relational databases", "rdbms"),
        py_modules=("sqlite3", "sqlalchemy", "sqlmodel", "psycopg2", "psycopg", "pymysql", "mysql", "asyncpg", "alembic"),
        py_packages=("sqlalchemy", "sqlmodel", "alembic", "psycopg2", "psycopg2-binary", "psycopg", "pymysql", "mysql-connector-python", "asyncpg"),
        npm_packages=("pg", "mysql2", "mysql", "sqlite3", "better-sqlite3", "sequelize", "prisma", "@prisma/client", "knex", "typeorm"),
        jvm_artifacts=("mysql-connector", "postgresql", "spring-boot-starter-data-jpa", "h2"),
        extensions=(".sql",),
        line_patterns=(
            LinePattern(r"(?i)\bcreate\s+table\b", "schema definition"),
            LinePattern(r"(?i)\b(inner|left|right|full)?\s*join\s+\w+\s+(\w+\s+)?on\b", "joins"),
            LinePattern(r"(?i)\bgroup\s+by\b", "aggregation"),
            LinePattern(r"(?i)\bcreate\s+(unique\s+)?index\b", "indexes"),
            LinePattern(r"(?i)\bcreate\s+(trigger|procedure|function|view)\b", "views/procedures/triggers"),
            LinePattern(r"(?i)\bselect\s+.+\s+from\s+\w+", "queries"),
            LinePattern(r"java\.sql\.|PreparedStatement", "JDBC", (".java",)),
        ),
        intermediate_features=frozenset({"joins", "aggregation", "ORM models", "schema definition"}),
        advanced_features=frozenset({"indexes", "views/procedures/triggers", "transactions", "migrations"}),
    ),
    Skill(
        id="pandas", name="Pandas", category="Data", aliases=("pandas",),
        py_modules=("pandas",), py_packages=("pandas",),
        intermediate_features=frozenset({"pd.merge", "groupby", "pd.concat", "apply", "fillna", "dropna"}),
        advanced_features=frozenset({"pivot_table", "agg", "rolling", "resample", "melt"}),
    ),
    Skill(
        id="numpy", name="NumPy", category="Data", aliases=("numpy",),
        py_modules=("numpy",), py_packages=("numpy",),
        intermediate_features=frozenset({"np.reshape", "np.dot", "np.where", "np.concatenate", "np.mean"}),
        advanced_features=frozenset({"np.linalg", "np.einsum", "np.random", "np.vectorize", "np.fft"}),
    ),
    Skill(
        id="machine_learning", name="Machine Learning", category="AI/ML",
        aliases=("machine learning", "ml", "deep learning", "scikit-learn", "sklearn", "tensorflow", "pytorch", "keras", "xgboost", "neural networks"),
        py_modules=("sklearn", "torch", "tensorflow", "keras", "xgboost", "lightgbm", "transformers"),
        py_packages=("scikit-learn", "sklearn", "torch", "tensorflow", "keras", "xgboost", "lightgbm", "transformers"),
        intermediate_features=frozenset({"model training", "train/test split", "evaluation metrics", "predictions"}),
        advanced_features=frozenset({"pipelines", "hyperparameter search", "custom neural network", "cross-validation"}),
    ),
    Skill(
        id="git", name="Git", category="Tooling", aliases=("git", "github", "gitlab", "version control"),
        min_files=1,
        intermediate_features=frozenset({"regular commit history"}),
        advanced_features=frozenset({"sustained commit history"}),
    ),
    Skill(
        id="docker", name="Docker", category="DevOps", aliases=("docker", "containers", "containerization", "docker-compose", "docker compose"),
        path_patterns=((r"(^|/)Dockerfile(\.\w+)?$", "Dockerfile"), (r"(^|/)(docker-)?compose\.ya?ml$|(^|/)docker-compose[\w.-]*\.ya?ml$", "docker compose")),
        line_patterns=(
            LinePattern(r"^\s*FROM\s+\S+\s+(AS|as)\s+\w+", "multi-stage build", ("Dockerfile",)),
            LinePattern(r"^\s*(HEALTHCHECK|USER)\s", "production hardening", ("Dockerfile",)),
        ),
        min_files=1,
        intermediate_features=frozenset({"docker compose"}),
        advanced_features=frozenset({"multi-stage build", "production hardening"}),
    ),
    Skill(
        id="ci_cd", name="CI/CD", category="DevOps",
        aliases=("ci/cd", "ci cd", "continuous integration", "continuous deployment", "github actions", "jenkins", "gitlab ci", "circleci"),
        path_patterns=(
            (r"^\.github/workflows/[^/]+\.ya?ml$", "GitHub Actions workflow"),
            (r"(^|/)\.gitlab-ci\.ya?ml$", "GitLab CI pipeline"),
            (r"(^|/)Jenkinsfile$", "Jenkins pipeline"),
            (r"^\.circleci/config\.ya?ml$", "CircleCI pipeline"),
        ),
        line_patterns=(
            LinePattern(r"^\s*strategy:\s*$|^\s*matrix:\s*$", "build matrix", (".yml", ".yaml")),
            LinePattern(r"(?i)deploy|docker/build-push-action|aws-actions|azure/", "deployment step", (".yml", ".yaml")),
        ),
        min_files=1,
        intermediate_features=frozenset({"multiple jobs"}),
        advanced_features=frozenset({"build matrix", "deployment step"}),
    ),
    Skill(
        id="testing", name="Automated Testing", category="Quality",
        aliases=("testing", "unit testing", "pytest", "jest", "junit", "unittest", "test automation", "tdd", "vitest"),
        py_modules=("pytest", "unittest"), py_packages=("pytest",),
        npm_packages=("jest", "vitest", "mocha", "@testing-library/react", "cypress", "playwright"),
        jvm_artifacts=("junit",),
        line_patterns=(
            LinePattern(r"\b(describe|it|test)\s*\(\s*['\"`]", "test cases", JS_EXT),
            LinePattern(r"\bexpect\s*\(", "assertions", JS_EXT),
            LinePattern(r"@Test\b", "test cases", (".java",)),
            LinePattern(r"jest\.mock|vi\.mock", "mocking", JS_EXT),
        ),
        intermediate_features=frozenset({"assertions", "fixtures"}),
        advanced_features=frozenset({"mocking", "parametrized tests"}),
    ),
)

SKILLS_BY_ID: dict[str, Skill] = {s.id: s for s in SKILLS}
SKILLS_BY_NAME: dict[str, Skill] = {s.name: s for s in SKILLS}

# Pre-compiled alias matchers for resumes / job descriptions.
_ALIAS_PATTERNS: list[tuple[re.Pattern, str]] = []
for _s in SKILLS:
    for _a in sorted(_s.aliases, key=len, reverse=True):
        # Word-ish boundaries that also work for "c++", "ci/cd", "node.js"
        _ALIAS_PATTERNS.append((re.compile(rf"(?<![\w+#.]){re.escape(_a)}(?![\w+#])", re.IGNORECASE), _s.id))

# Aliases that are too ambiguous on their own ("ml", "ts", "js", "node", "rest", "git" inside "github" is fine)
AMBIGUOUS_ALIASES = {"ml", "ts", "js", "node", "rest"}


def find_skill_mentions(text: str) -> list[tuple[str, int, int, str]]:
    """Return (skill_id, start, end, matched_text) for every alias found in text."""
    hits: list[tuple[str, int, int, str]] = []
    taken: list[tuple[int, int]] = []
    for pattern, skill_id in _ALIAS_PATTERNS:
        for m in pattern.finditer(text):
            alias = m.group(0)
            if alias.lower() in AMBIGUOUS_ALIASES and not alias.isupper() and alias.lower() != "node":
                # require exact upper-case form for ambiguous short aliases (e.g. "ML", "JS")
                continue
            if alias.lower() == "node" and not re.match(r"(?i)node\b(?!\s*\()", text[m.start():m.end() + 2]):
                continue
            if any(s <= m.start() < e or s < m.end() <= e for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            hits.append((skill_id, m.start(), m.end(), alias))
    return hits
