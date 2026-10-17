"""Static repository analysis. Reads a repository archive in memory and produces
evidence *findings*. Nothing from the repository is ever executed or imported:
Python files are parsed with `ast.parse` only, everything else is scanned as text.
Repository content is treated as untrusted data (instructions inside it are ignored).
"""
from __future__ import annotations

import ast
import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from app.services.taxonomy import SKILLS, SKILLS_BY_ID, find_skill_mentions

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "venv", ".venv", "env", "__pycache__", "vendor", "target",
    ".next", "coverage", "site-packages", ".idea", ".vscode", "out", "bin", "obj", ".mypy_cache", ".pytest_cache",
    "bower_components", ".gradle", "migrations_backup",
}
TEXT_EXTS = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h", ".c",
    ".html", ".css", ".scss", ".sql", ".yml", ".yaml", ".json", ".toml", ".txt", ".md", ".rst", ".gradle", ".xml",
    ".cfg", ".ini",
}
SPECIAL_NAMES = {"Dockerfile", "Jenkinsfile", "Pipfile", "Makefile"}
MANIFEST_NAMES = {"requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile", "package.json", "pom.xml", "build.gradle", "build.gradle.kts", "setup.py"}
SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token|private[_-]?key|aws_access)\s*[:=]|-----BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}")
TEST_PATH_RE = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]+\.py$|_test\.py$|\.(test|spec)\.[jt]sx?$|(^|/)src/test/java/")
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


@dataclass
class Finding:
    skill: str
    type: str
    file: str | None
    line_start: int | None = None
    line_end: int | None = None
    snippet: str | None = None
    feature: str | None = None
    detail: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class RepoScan:
    file_count: int = 0
    files_scanned: int = 0
    findings: list[Finding] = field(default_factory=list)
    readme_excerpt: str | None = None
    notes: list[str] = field(default_factory=list)
    source_file_count: int = 0


def safe_snippet(line: str) -> str:
    line = line.strip()
    if SECRET_RE.search(line):
        return "[redacted: line may contain a secret]"
    return line[:160]


# ------------------------------------------------------------------ Python AST
PY_MODULE_TO_SKILL: dict[str, str] = {}
for _s in SKILLS:
    for _m in _s.py_modules:
        PY_MODULE_TO_SKILL[_m] = _s.id


# method name -> (skill, feature) applied when the skill's module is imported in the same file
METHOD_FEATURES: dict[str, list[tuple[str, str]]] = {
    "groupby": [("pandas", "groupby")], "merge": [("pandas", "pd.merge")], "pivot_table": [("pandas", "pivot_table")],
    "agg": [("pandas", "agg")], "apply": [("pandas", "apply")], "fillna": [("pandas", "fillna")],
    "dropna": [("pandas", "dropna")], "rolling": [("pandas", "rolling")], "resample": [("pandas", "resample")],
    "melt": [("pandas", "melt")], "to_csv": [("pandas", "data export")], "value_counts": [("pandas", "value_counts")],
    "fit": [("machine_learning", "model training")], "fit_transform": [("machine_learning", "feature transformation")],
    "predict": [("machine_learning", "predictions")], "predict_proba": [("machine_learning", "predictions")],
    "backward": [("machine_learning", "model training")], "execute": [("sql", "queries")],
    "commit": [("sql", "transactions")], "rollback": [("sql", "transactions")],
}
MODULE_CALL_FEATURES: dict[str, dict[str, str]] = {
    "pandas": {"read_csv": "data loading", "read_excel": "data loading", "read_sql": "data loading", "read_json": "data loading",
               "merge": "pd.merge", "concat": "pd.concat", "DataFrame": "DataFrame construction", "to_datetime": "datetime handling",
               "pivot_table": "pivot_table", "get_dummies": "encoding"},
    "numpy": {"dot": "np.dot", "matmul": "np.dot", "reshape": "np.reshape", "where": "np.where", "concatenate": "np.concatenate",
              "mean": "np.mean", "std": "np.mean", "einsum": "np.einsum", "vectorize": "np.vectorize",
              "array": "array creation", "zeros": "array creation", "ones": "array creation", "arange": "array creation", "linspace": "array creation"},
}
NAME_FEATURES: dict[str, tuple[str, str]] = {
    "train_test_split": ("machine_learning", "train/test split"),
    "accuracy_score": ("machine_learning", "evaluation metrics"), "f1_score": ("machine_learning", "evaluation metrics"),
    "precision_score": ("machine_learning", "evaluation metrics"), "recall_score": ("machine_learning", "evaluation metrics"),
    "mean_squared_error": ("machine_learning", "evaluation metrics"), "classification_report": ("machine_learning", "evaluation metrics"),
    "confusion_matrix": ("machine_learning", "evaluation metrics"), "r2_score": ("machine_learning", "evaluation metrics"),
    "Pipeline": ("machine_learning", "pipelines"), "make_pipeline": ("machine_learning", "pipelines"),
    "GridSearchCV": ("machine_learning", "hyperparameter search"), "RandomizedSearchCV": ("machine_learning", "hyperparameter search"),
    "cross_val_score": ("machine_learning", "cross-validation"), "KFold": ("machine_learning", "cross-validation"),
    "StratifiedKFold": ("machine_learning", "cross-validation"),
    "FastAPI": ("fastapi", "app instance"), "APIRouter": ("fastapi", "APIRouter"), "Depends": ("fastapi", "dependency injection"),
    "BackgroundTasks": ("fastapi", "background tasks"), "HTTPException": ("fastapi", "HTTPException"),
    "Flask": ("flask", "app instance"), "Blueprint": ("flask", "blueprints"), "render_template": ("flask", "templates rendering"),
    "jsonify": ("flask", "JSON responses"),
    "create_engine": ("sql", "database connection"), "connect": ("sql", "database connection"),
    "Column": ("sql", "ORM models"), "relationship": ("sql", "ORM models"), "mapped_column": ("sql", "ORM models"),
    "declarative_base": ("sql", "ORM models"), "sessionmaker": ("sql", "database sessions"),
    "select": ("sql", "queries"), "Field": ("sql", "ORM models"),
}


def _dotted(node: ast.AST) -> list[str]:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return list(reversed(parts))
    return []


def analyze_python(path: str, source: str, lines: list[str], is_test: bool) -> tuple[list[Finding], str | None]:
    findings: list[Finding] = []
    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, ValueError) as exc:
        return findings, f"{path}: could not be parsed as Python ({exc.__class__.__name__}); only text evidence used."

    def add(skill: str, ftype: str, node_or_line, feature: str | None, detail: str, end: int | None = None):
        line = node_or_line if isinstance(node_or_line, int) else getattr(node_or_line, "lineno", None)
        end_line = end or (getattr(node_or_line, "end_lineno", None) if not isinstance(node_or_line, int) else None) or line
        if end_line and line and end_line - line > 40:
            end_line = line + 40
        snippet = safe_snippet(lines[line - 1]) if line and 0 < line <= len(lines) else None
        findings.append(Finding(skill, ftype, path, line, end_line, snippet, feature, detail))

    alias_to_module: dict[str, str] = {}  # local name -> top-level module
    imported_skills: dict[str, ast.AST] = {}
    seen_features: set[tuple[str, str]] = set()

    def feature_once(skill: str, feature: str, node, detail: str, ftype: str = "code_usage", end: int | None = None):
        key = (skill, feature)
        if key in seen_features:
            return
        seen_features.add(key)
        add(skill, ftype, node, feature, detail, end)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                alias_to_module[(a.asname or a.name).split(".")[0]] = root
                if root in PY_MODULE_TO_SKILL and PY_MODULE_TO_SKILL[root] in SKILLS_BY_ID and root not in imported_skills:
                    imported_skills[root] = node
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            root = node.module.split(".")[0]
            for a in node.names:
                alias_to_module[a.asname or a.name] = root
            if root in PY_MODULE_TO_SKILL and PY_MODULE_TO_SKILL[root] in SKILLS_BY_ID and root not in imported_skills:
                imported_skills[root] = node

    skills_in_file = {PY_MODULE_TO_SKILL[m] for m in imported_skills}
    for mod, node in imported_skills.items():
        add(PY_MODULE_TO_SKILL[mod], "code_import", node, None, f"imports `{mod}`")

    route_methods: set[str] = set()
    app_names: dict[str, str] = {}  # variable -> fastapi|flask

    for node in ast.walk(tree):
        # app / router instances
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            callee = _dotted(node.value.func)
            if callee:
                base = callee[-1]
                fw = {"FastAPI": "fastapi", "APIRouter": "fastapi", "Flask": "flask", "Blueprint": "flask"}.get(base)
                if fw and fw in skills_in_file:
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            app_names[t.id] = fw

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            parts = _dotted(node.func)
            if not parts:
                continue
            base, last = parts[0], parts[-1]
            mod = alias_to_module.get(base)
            if mod in MODULE_CALL_FEATURES and len(parts) >= 2:
                feat = MODULE_CALL_FEATURES[mod].get(parts[1])
                if mod == "numpy" and parts[1] in ("linalg", "random", "fft"):
                    feat = f"np.{parts[1]}"
                if feat:
                    feature_once(PY_MODULE_TO_SKILL[mod], feat, node, f"calls `{'.'.join(parts)}`")
            elif mod in PY_MODULE_TO_SKILL and len(parts) == 1 and last in NAME_FEATURES:
                sk, feat = NAME_FEATURES[last]
                if sk in skills_in_file:
                    feature_once(sk, feat, node, f"calls `{last}`")
            elif mod in PY_MODULE_TO_SKILL and PY_MODULE_TO_SKILL[mod] in SKILLS_BY_ID and len(parts) >= 2:
                sk = PY_MODULE_TO_SKILL[mod]
                if sk == "sql" and parts[-1] in ("connect", "create_engine"):
                    feature_once("sql", "database connection", node, f"calls `{'.'.join(parts)}`")
                elif sk == "machine_learning" and parts[-1] in NAME_FEATURES:
                    feature_once(sk, NAME_FEATURES[parts[-1]][1], node, f"calls `{'.'.join(parts)}`")
                elif sk == "machine_learning" and "optim" in parts:
                    feature_once(sk, "model training", node, f"uses `{'.'.join(parts)}`")
            if len(parts) >= 2 and last in METHOD_FEATURES:
                for sk, feat in METHOD_FEATURES[last]:
                    if sk in skills_in_file:
                        feature_once(sk, feat, node, f"calls `.{last}()`")
            if last in ("add_middleware",) and "fastapi" in skills_in_file:
                feature_once("fastapi", "middleware", node, "registers middleware")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                parts = _dotted(target)
                if len(parts) >= 2 and parts[0] in app_names:
                    fw, meth = app_names[parts[0]], parts[-1]
                    if meth in HTTP_METHODS or meth == "route":
                        feature_once(fw, "route handlers", dec.lineno, f"HTTP route `{node.name}`", end=node.end_lineno)
                        add("rest_api", "code_usage", dec.lineno, "HTTP route handlers", f"{fw} route handler `{node.name}`", node.end_lineno)
                        if meth in HTTP_METHODS:
                            route_methods.add(meth)
                        elif isinstance(dec, ast.Call):
                            for kw in dec.keywords:
                                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                                    route_methods.update(
                                        e.value.lower() for e in kw.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)
                                    )
                        if isinstance(dec, ast.Call) and dec.args and isinstance(dec.args[0], ast.Constant):
                            if re.search(r"/v\d+/", str(dec.args[0].value) + "/"):
                                feature_once("rest_api", "API versioning", node, "versioned API path")
                    elif meth == "websocket":
                        feature_once("fastapi", "websockets", node, "websocket endpoint")
                    elif meth == "middleware":
                        feature_once(fw, "middleware", node, "middleware function")
                    elif meth == "errorhandler" or meth == "exception_handler":
                        feature_once(fw, "error handlers", node, "custom error handler")
                        feature_once("rest_api", "error handling", node, "custom API error handler")
                    elif meth == "before_request":
                        feature_once("flask", "before_request hooks", node, "before_request hook")
                if parts and alias_to_module.get(parts[0]) == "pytest" and parts[-1] == "fixture":
                    feature_once("testing", "fixtures", node, "pytest fixture")
                if parts and alias_to_module.get(parts[0]) == "pytest" and "parametrize" in parts:
                    feature_once("testing", "parametrized tests", node, "parametrized test")
            if node.name == "create_app" and "flask" in skills_in_file:
                feature_once("flask", "app factory", node, "Flask application factory")
            if is_test and node.name.startswith("test"):
                feature_once("testing", "test cases", node, f"test function `{node.name}`")

        elif isinstance(node, ast.ClassDef):
            bases = [".".join(_dotted(b)) for b in node.bases]
            if any(b.endswith("BaseModel") for b in bases) and "fastapi" in skills_in_file:
                feature_once("fastapi", "pydantic models", node, f"request/response model `{node.name}`")
                feature_once("rest_api", "request validation", node, f"validated schema `{node.name}`")
            if any(b in ("nn.Module", "torch.nn.Module", "Module") for b in bases) and "machine_learning" in skills_in_file:
                feature_once("machine_learning", "custom neural network", node, f"custom model class `{node.name}`")
            if any(b.endswith("TestCase") for b in bases):
                feature_once("testing", "test cases", node, f"unittest class `{node.name}`")
            if (any(b in ("Base", "DeclarativeBase", "db.Model", "Model") for b in bases) or any(b == "SQLModel" for b in bases) and any(k.arg == "table" for k in node.keywords)) and "sql" in skills_in_file:
                feature_once("sql", "ORM models", node, f"ORM model `{node.name}`")
        elif isinstance(node, ast.Assert) and is_test:
            feature_once("testing", "assertions", node, "assert statement")
        elif isinstance(node, ast.Raise) and node.exc is not None and "HTTPException" in ast.unparse(node.exc)[:40]:
            feature_once("rest_api", "error handling", node, "raises HTTP errors")

    if len(route_methods) >= 2:
        first = next((f for f in findings if f.skill == "rest_api"), None)
        if first:
            findings.append(Finding("rest_api", "code_usage", path, first.line_start, first.line_end, first.snippet,
                                    "multiple HTTP methods", f"methods used: {', '.join(sorted(route_methods)).upper()}"))
    if "unittest" in alias_to_module.values() and "mock" in source:
        feature_once("testing", "mocking", 1, "uses unittest.mock")
    if "monkeypatch" in source and is_test:
        feature_once("testing", "mocking", 1, "uses pytest monkeypatch")

    # Python language features (one finding per feature per file)
    py_feats: list[tuple[str, ast.AST]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            py_feats.append(("classes", node))
            if any("dataclass" in ".".join(_dotted(d.func if isinstance(d, ast.Call) else d)) for d in node.decorator_list):
                py_feats.append(("dataclasses", node))
        elif isinstance(node, ast.AsyncFunctionDef):
            py_feats.append(("async functions", node))
        elif isinstance(node, ast.FunctionDef):
            if node.decorator_list:
                py_feats.append(("decorators used", node))
            if node.returns is not None or any(a.annotation is not None for a in node.args.args):
                py_feats.append(("type hints", node))
            inner = [n for n in node.body if isinstance(n, ast.FunctionDef)]
            if inner and any(isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id == inner[0].name for n in node.body):
                py_feats.append(("custom decorators", node))
            if node.name == "__enter__":
                py_feats.append(("context managers", node))
        elif isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            py_feats.append(("comprehensions", node))
        elif isinstance(node, (ast.Yield, ast.YieldFrom)):
            py_feats.append(("generators", node))
        elif isinstance(node, ast.Try):
            py_feats.append(("exception handling", node))
        elif isinstance(node, ast.With):
            py_feats.append(("context managers", node))
    for feat, node in py_feats:
        feature_once("python", feat, node, f"Python {feat}")
    return findings, None


# ------------------------------------------------------------------ manifests
def analyze_manifest(path: str, text: str, lines: list[str]) -> list[Finding]:
    name = PurePosixPath(path).name
    out: list[Finding] = []
    deps: list[tuple[str, int]] = []  # (dependency name, line)
    if name == "package.json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return out
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for dep in (data.get(section) or {}):
                line = next((i + 1 for i, l in enumerate(lines) if f'"{dep}"' in l), None)
                deps.append((dep.lower(), line or 1))
        lookup = {d: s.id for s in SKILLS for d in s.npm_packages}
    elif name in ("pom.xml",) or name.startswith("build.gradle"):
        for i, l in enumerate(lines):
            m = re.search(r"<artifactId>([^<]+)</artifactId>|['\"]([\w.-]+):([\w.-]+)(:[\w.-]+)?['\"]", l)
            if m:
                deps.append(((m.group(1) or m.group(3) or "").lower(), i + 1))
        lookup = {a: s.id for s in SKILLS for a in s.jvm_artifacts}
        out.append(Finding("java", "dependency_manifest", path, 1, 1, None, None, f"Java build file `{name}`"))
    else:  # python manifests
        for i, l in enumerate(lines):
            raw = l.strip().strip('",\'')
            if not raw or raw.startswith("#") or raw.startswith("["):
                continue
            m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(\[.*\])?\s*([<>=!~].*)?$", raw)
            if m:
                deps.append((m.group(1).lower(), i + 1))
            else:
                m2 = re.match(r'^([A-Za-z0-9_.\-]+)\s*=', raw)  # Pipfile / poetry: name = "version"
                if m2:
                    deps.append((m2.group(1).lower(), i + 1))
        lookup = {p: s.id for s in SKILLS for p in s.py_packages}
    seen: set[str] = set()
    for dep, line in deps:
        sid = lookup.get(dep)
        if not sid and dep.startswith("@types/"):
            sid = "typescript"
        if sid and (sid, dep) not in seen:
            seen.add((sid, dep))
            out.append(Finding(sid, "dependency_manifest", path, line, line,
                               safe_snippet(lines[line - 1]) if 0 < line <= len(lines) else None, None, f"declares dependency `{dep}`"))
    return out


# ------------------------------------------------------------------ line patterns
def _ext_matches(path: str, exts: tuple[str, ...]) -> bool:
    if not exts:
        return True
    name = PurePosixPath(path).name
    for e in exts:
        if e == "Dockerfile":
            if name.startswith("Dockerfile"):
                return True
        elif name.endswith(e):
            return True
    return False


_COMPILED = [(s.id, re.compile(p.regex), p) for s in SKILLS for p in s.line_patterns]


def analyze_lines(path: str, lines: list[str], is_test: bool) -> list[Finding]:
    out: list[Finding] = []
    counts: dict[tuple[str, str], int] = {}
    is_doc = path.lower().endswith((".md", ".rst", ".txt", ".json", ".toml", ".xml", ".cfg", ".ini"))
    if is_doc:
        return out
    for sid, rx, pat in _COMPILED:
        if not _ext_matches(path, pat.exts):
            continue
        if sid == "testing" and not is_test:
            continue
        for i, line in enumerate(lines):
            if len(line) > 400:
                continue
            if rx.search(line):
                key = (sid, pat.feature)
                if counts.get(key, 0) >= 2:
                    break
                counts[key] = counts.get(key, 0) + 1
                out.append(Finding(sid, pat.kind, path, i + 1, i + 1, safe_snippet(line), pat.feature, f"{pat.feature}"))
    return out


def analyze_config(path: str, lines: list[str]) -> list[Finding]:
    out: list[Finding] = []
    meaningful = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    for s in SKILLS:
        for rx, feature in s.path_patterns:
            if re.search(rx, path):
                if len(meaningful) < 3:
                    out.append(Finding(s.id, "documentation", path, 1, len(lines), None, None, f"{feature} present but nearly empty"))
                    continue
                out.append(Finding(s.id, "config", path, 1, min(len(lines), 60), safe_snippet(meaningful[0]), feature,
                                   f"{feature} with {len(meaningful)} meaningful lines"))
                if s.id == "ci_cd":
                    jobs = sum(1 for l in lines if re.match(r"^  [\w-]+:\s*$", l))
                    if jobs >= 2:
                        out.append(Finding("ci_cd", "code_usage", path, 1, 1, None, "multiple jobs", f"{jobs} jobs defined"))
    return out


# ------------------------------------------------------------------ main entry
def _priority(path: str) -> tuple[int, int, str]:
    name = PurePosixPath(path).name
    depth = path.count("/")
    if name in MANIFEST_NAMES or name.lower().startswith("readme"):
        return (0, depth, path)
    if any(re.search(rx, path) for s in SKILLS for rx, _ in s.path_patterns):
        return (0, depth, path)
    if re.search(r"(^|/)(src|app|lib|backend|frontend|server|api)/", path):
        return (1, depth, path)
    return (2, depth, path)


def scan_zip(zip_bytes: bytes, max_files: int, max_file_kb: int) -> RepoScan:
    scan = RepoScan()
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        scan.notes.append("Repository archive could not be opened.")
        return scan

    candidates: list[tuple[str, zipfile.ZipInfo]] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        parts = info.filename.split("/", 1)
        if len(parts) < 2:
            continue
        rel = parts[1]
        if ".." in rel.split("/") or rel.startswith("/"):
            continue  # path traversal guard (we never write to disk anyway)
        segs = rel.split("/")
        if any(seg in SKIP_DIRS for seg in segs[:-1]):
            continue
        scan.file_count += 1
        name = segs[-1]
        ext = PurePosixPath(name).suffix.lower()
        if name.endswith(".min.js") or name.endswith(".map") or name in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml"):
            continue
        if ext in TEXT_EXTS or name in SPECIAL_NAMES or name.startswith("Dockerfile"):
            candidates.append((rel, info))

    candidates.sort(key=lambda c: _priority(c[0]))
    skipped_large = 0
    lang_exts = {e: s.id for s in SKILLS for e in s.extensions}
    readme_done = False

    for rel, info in candidates:
        if scan.files_scanned >= max_files:
            scan.notes.append(f"File limit reached: scanned {max_files} of {len(candidates)} candidate files (highest priority first).")
            break
        if info.file_size > max_file_kb * 1024:
            skipped_large += 1
            continue
        raw = zf.read(info)
        if b"\x00" in raw[:4096]:
            continue
        text = raw.decode("utf-8", errors="ignore")
        lines = text.splitlines()
        scan.files_scanned += 1
        name = PurePosixPath(rel).name
        ext = PurePosixPath(rel).suffix.lower()
        is_test = bool(TEST_PATH_RE.search(rel))

        if name.lower().startswith("readme") and "/" not in rel and not readme_done:
            readme_done = True
            scan.readme_excerpt = re.sub(r"<[^>]+>", "", text)[:700]
            first_line: dict[str, int] = {}
            for sid, start, _end, alias in find_skill_mentions(text):
                if sid not in first_line:
                    ln = text.count("\n", 0, start) + 1
                    first_line[sid] = ln
                    scan.findings.append(Finding(sid, "documentation", rel, ln, ln, safe_snippet(lines[ln - 1]), None, f"README mentions `{alias}`"))
            continue
        if name in MANIFEST_NAMES:
            scan.findings.extend(analyze_manifest(rel, text, lines))
            if name != "setup.py":
                continue
        scan.findings.extend(analyze_config(rel, lines))

        sid = lang_exts.get(ext)
        nonblank = sum(1 for l in lines if l.strip())
        if sid and nonblank >= 5:
            scan.source_file_count += 1
            scan.findings.append(Finding(sid, "source_file", rel, 1, len(lines), None, None, f"{nonblank} non-blank lines of {SKILLS_BY_ID[sid].name}"))
        if is_test and ext in (".py", ".js", ".jsx", ".ts", ".tsx", ".java") and nonblank >= 3:
            scan.findings.append(Finding("testing", "test", rel, 1, len(lines), None, None, "test file"))
        if ext == ".py":
            f, note = analyze_python(rel, text, lines, is_test)
            scan.findings.extend(f)
            if note:
                scan.notes.append(note)
        scan.findings.extend(analyze_lines(rel, lines, is_test))

    if skipped_large:
        scan.notes.append(f"{skipped_large} file(s) larger than {max_file_kb} KB were skipped.")
    return scan
