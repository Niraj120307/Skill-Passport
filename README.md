# Skill Passport — Verified Skills from Real Work

**Team Beetles · Code Apex hackathon prototype**

Skill Passport reads a student's public GitHub repository and resume, and produces a passport of technical skills. Each skill is linked to the file, line range and commit that supports it, along with a status, a proficiency estimate and a plain-language explanation. An **Authorship Guard** surfaces repository trust signals. The passport can be matched against a real job description to get a transparent match score and a learning roadmap of practical mini-projects.

The core runs locally with no paid API, no LLM and no cloud services.

---

## Quick start (Windows PowerShell, VS Code)

Prerequisites: **Python 3.10–3.13** and **Node.js 18+** (`python --version`, `node --version`).

```powershell
# from the skill-passport folder
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # allow the scripts in this terminal
.\setup.ps1              # creates backend\.venv, installs Python + npm packages, creates backend\.env
```

Then open **two terminals**:

```powershell
.\start-backend.ps1      # http://127.0.0.1:8000   (API docs: http://127.0.0.1:8000/docs)
```
```powershell
.\start-frontend.ps1     # http://localhost:5173   ← open this in the browser
```

Manual equivalent:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000

# second terminal
cd frontend
npm install
npm run dev
```

**Recommended:** put a free GitHub token in `backend\.env` (`GITHUB_TOKEN=...`; GitHub → Settings → Developer settings → Fine-grained token, public-repo read only). Without a token GitHub allows about 60 requests per hour, and each analysis uses roughly 6–10.

Run the tests: `.\run-tests.ps1`, or `cd backend; .\.venv\Scripts\python -m pytest -q`.

---

## Live demo sequence (≈ 3 minutes)

1. **Dashboard → "Load demo (sample data)".** The violet banner marks it as illustrative.
2. **Skill Passport.** FastAPI and Python are *Evidence-supported* with file:line evidence. Docker is *Partially supported* because only the README mentions it. Machine Learning is an *Unverified claim* because it appears on the resume only. Expand **Show evidence** and open **All evidence**.
3. **Trust Analysis.** Shows the commit timeline with a burst and the burst signal, with its limitation and a recommended review step.
4. **Job Match.** The sample Backend Developer JD is preloaded at 81%. Docker is the important gap, and the weighted formula is displayed.
5. **Learning Roadmap.** Gives a Docker mini-project ("containerise a FastAPI app…") with acceptance criteria and the evidence needed.
6. **Share Passport.** Toggle sharing on to get a QR code and public link. Open the link: no resume data and no unverified claims are shown. Toggle it off and the link returns 404.
7. **Real run.** Go to Analyze Work, enter a public repo URL (e.g. `https://github.com/fastapi/full-stack-fastapi-template`) and a PDF resume, then click Analyze. Evidence links open the exact lines on GitHub. Refresh the page and the results are still there.

---

## How it works

```
Resume PDF ──PyMuPDF──▶ claims (skill, page, snippet)          ─┐
GitHub repo ─REST API─▶ metadata, languages, commits,           │
            ─zipball──▶ in-memory archive ─▶ Python AST +       ├─▶ Skill engine ─▶ Passport (SQLite)
                         text patterns + manifests + configs    │        ▲              │
                         = findings with file/line provenance  ─┘        │              ├─▶ Job matcher ─▶ score + gaps
                                                     Authorship Guard ───┘              └─▶ Roadmap catalog
```

* **GitHub ingestion** (`services/github_client.py`, `pipeline.py`) makes about 5 requests per repository: repo, languages, commits (≤100), contributors, and one **zipball** download capped at 40 MB. It then makes up to 5 per-file history lookups for the key evidence files. The archive is read in memory and is **never extracted to disk or executed**.
* **Static analysis** (`services/repo_analyzer.py`):
  * Python files are parsed with `ast.parse` to get imports, calls on imported modules, route decorators, `Depends`, Pydantic/ORM classes, pytest fixtures and parametrize, and language features (async, dataclasses, generators, …).
  * Other languages are scanned with line patterns from the taxonomy. Dependency manifests (`requirements.txt`, `pyproject.toml`, `package.json`, `pom.xml`, `build.gradle`) and configs (Dockerfile, compose, GitHub Actions, GitLab CI, Jenkinsfile, tsconfig) are also read.
  * Vendored folders are skipped (`node_modules`, `dist`, `venv`, …), and files over 300 KB, binaries, lock files and minified files are ignored.
  * Snippets that look like secrets are redacted.
* **Taxonomy** (`services/taxonomy.py`) covers 19 skills: Python, Java, C++, JavaScript, TypeScript, React, HTML/CSS, FastAPI, Flask, Node.js/Express, REST APIs, SQL, Pandas, NumPy, Machine Learning, Git, Docker, CI/CD and Automated Testing. Add a skill by adding one entry.
* **Evidence provenance.** Every evidence record stores the repo URL, file path, line range, snapshot commit SHA, a permalink (`/blob/<sha>/<path>#Lx-Ly`) and the evidence type. Git evidence links to real commits. Nothing is invented: if a value is unknown, it is left empty.

### Scoring rules (`backend/app/services/scoring_config.py`)

**Evidence weights**

| Evidence type | Weight |
|---|---|
| Code usage | 3 |
| Test file | 3 |
| Config | 3 |
| Source file | 2 |
| Import never used | 1.5 |
| Dependency declaration | 1 |
| README mention | 0.5 |
| Owner commit (Git only) | 0.5 |
| **Resume claim** | **0** |

A single file contributes at most 6 points to a skill.

**Verification status**

| Status | Rule |
|---|---|
| `evidence_supported` | Strong weight (code, tests, config, source files, commits) ≥ **6** across ≥ **2** files (1 for Docker, CI/CD, Git), and no high-severity trust signal. |
| `flagged_for_review` | Would be supported, but the repository has a **high**-severity trust signal (e.g. a fork with no commits by the owner). |
| `partially_supported` | Some repository evidence, but below the bar (e.g. import, manifest or README only, or a single file). |
| `unverified` | Claimed on the resume, with no repository evidence. |

**Proficiency** is only assessed when strong evidence exists, so an import alone never earns a level.

* **Beginner** is the starting level once strong evidence exists.
* **Intermediate** requires ≥ 3 files, or ≥ 4 distinct features, or one of the skill's intermediate or advanced features.
* **Advanced** requires (≥ 6 files and ≥ 8 features), or (an advanced feature and ≥ 3 files and ≥ 5 features).

Stars and commit counts are never used.

**Evidence strength** = `min(1, total weight / 15)`.

**Job match** = `100 × Σ(weight × credit) / Σ(weight)`.

* Weight is 2 for required skills and 1 for preferred skills (lines under "Nice to have", "Preferred", …).
* Credit is 1.0 for supported, 0.5 for partial or flagged, and 0 for resume-only or missing.
* Skills the job doesn't ask for are listed but never add points.

### Authorship Guard (`services/authorship_guard.py`)

| Signal | Severity |
|---|---|
| Fork, owner has commits | medium |
| Fork with **no** owner commits | high |
| Owner authored < 30% of commits | medium |
| Commit burst (≥ 10 commits on a day and ≥ 5× the median day) | low |
| ≤ 3 commits for ≥ 30 source files | medium |
| Per-file history of key evidence files | info / low |
| Contributors, history truncated, template indicators | info |
| No history | assessment marked **incomplete** |

Every signal carries supporting evidence links, a limitation and a recommended human-review step.

It **never** claims fraud or AI-generated-code detection. Forks, templates, AI assistance and large commits are treated as normal practice.

### Security & privacy

* Repository files, READMEs, resumes and job descriptions are treated as untrusted data. They are only parsed or searched for skill names, so instructions inside them have no effect. The test repo contains such an instruction.
* Code from analyzed repositories is never executed or imported.
* The **resume PDF is never stored**; only extracted claims (skill, page, short snippet) are saved.
* Public passports exist only after an explicit share toggle, using a random unguessable id. They exclude resume data, resume-only skills, job descriptions, scores and internal ids. Disabling sharing makes the link return 404.
* Configuration comes from `backend/.env`, and secrets are never logged or returned.
* There is no LLM provider: the roadmap and matching are deterministic. An optional LLM interface was **not** implemented.

---

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health + whether a GitHub token is configured |
| POST | `/api/resume/upload` | multipart `file` (PDF) → `resume_id`, claims |
| POST | `/api/github/analyze` | `{repo_url}` → `repository_id`, scan summary |
| POST | `/api/analyze` | `{name, repository_id \| repo_url, resume_id?}` → full passport |
| GET | `/api/passports` | Recent passports |
| GET | `/api/passports/{id}` | Passport with skills, evidence, trust, sharing, latest match |
| GET | `/api/passports/{id}/evidence` | Flat evidence list |
| POST | `/api/match-job` | `{passport_id, job_title, job_description}` → score, breakdown, roadmap |
| GET | `/api/roadmap/{id}` | Roadmap from latest job match (or passport gaps) |
| POST | `/api/passports/{id}/share` | `{enabled}` → sharing state |
| GET | `/api/public/passports/{public_id}` | Sanitized public passport |
| POST | `/api/demo/load` · GET `/api/demo/job` | Demo passport · sample JD |

Interactive docs are at `http://127.0.0.1:8000/docs`.

## Project structure

```
skill-passport/
├─ backend/
│  ├─ app/
│  │  ├─ main.py                 FastAPI app, CORS, error handling
│  │  ├─ config.py               env-based settings
│  │  ├─ api/routes.py           all endpoints
│  │  ├─ database/db.py          SQLite engine/session
│  │  ├─ models/models.py        Student, Repository, Resume, Passport, SkillRecord, Evidence, TrustSignal, JobMatch
│  │  ├─ schemas/schemas.py      Pydantic request models
│  │  ├─ services/               github_client, repo_analyzer, resume_parser, taxonomy, scoring_config,
│  │  │                          skill_engine, authorship_guard, job_matcher, roadmap, pipeline, demo
│  │  └─ tests/                  pytest suite (fake GitHub client, generated PDFs)
│  ├─ requirements.txt  .env.example  data/
├─ frontend/  (React + Vite + TS + Tailwind + Recharts + qrcode.react)
│  └─ src/pages/  Dashboard, Analyze, PassportPage, Trust, JobMatchPage, RoadmapPage, SharePage, PublicPassportPage
├─ setup.ps1  start-backend.ps1  start-frontend.ps1  run-tests.ps1
```

## Tested

* **Backend:** 16 pytest tests pass.
  * Repo URL validation; AST evidence with exact line numbers; secret redaction.
  * Every status rule, and resume-only claims never supported.
  * Fork, burst and incomplete-history signals, and high-severity flagging.
  * The job-match formula and no score inflation.
  * Resume parsing, including wrong type, malformed, password-protected and scanned PDFs.
  * The full API workflow and persistence; sharing sanitization and revocation; API error codes; demo mode.
* **Frontend:** `tsc` + `vite build` succeed.
* **End to end:** driven in headless Chromium (analyze → passport → evidence → trust → job match → roadmap → share → public page → reload), including a 390 px mobile viewport.
  * GitHub's API was not reachable from the build environment, so the E2E run used a real cloned repository (`fastapi/full-stack-fastapi-template`) served through a stand-in client.
  * The live GitHub calls themselves are covered by error-handling code but were not exercised against api.github.com. Please run one real analysis on your machine before the demo.

## Known limitations

* Only **one repository** per passport; private repositories are not supported.
* Analysis is synchronous, so a large repo can take 10–30 s and the progress steps are per API stage, not streaming.
* Non-Python languages use line patterns rather than full parsers, so their detection is shallower.
* Python files using syntax newer than the server's Python version are skipped with a scan note.
* Evidence shows a skill is **used in the repository**, not who wrote each line. Git blame is not available through the REST API, so file history uses per-file commit lists only.
* Commit-author matching uses the repository owner's login. Commits made with unlinked emails are counted as "others".
* Resume section detection is heuristic. Scanned PDFs are rejected (no OCR).
* Job-description skill extraction is limited to the taxonomy's aliases. Skills outside the taxonomy (e.g. Kubernetes) are not recognized.
* No user accounts: this is a single local user, and passports are selected in the browser via localStorage.
* For QR codes on a phone, the frontend must be reachable over the network (`npm run dev -- --host` and use your PC's IP).
