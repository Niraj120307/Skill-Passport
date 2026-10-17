"""End-to-end API tests with a fake GitHub client (no network)."""
from app.tests.conftest import RESUME_TEXT, make_pdf


def _full_flow(client):
    up = client.post("/api/resume/upload", files={"file": ("cv.pdf", make_pdf(RESUME_TEXT), "application/pdf")})
    assert up.status_code == 201, up.text
    gh = client.post("/api/github/analyze", json={"repo_url": "https://github.com/student/taskapi"})
    assert gh.status_code == 201, gh.text
    assert "fastapi" in gh.json()["skills_detected"]
    an = client.post("/api/analyze", json={"name": "Kedar", "repository_id": gh.json()["repository_id"], "resume_id": up.json()["resume_id"]})
    assert an.status_code == 201, an.text
    return an.json()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_full_workflow_and_persistence(client, fake_github):
    p = _full_flow(client)
    statuses = {s["skill"]: s["verification_status"] for s in p["skills"]}
    assert statuses["FastAPI"] == "evidence_supported"
    assert statuses["Machine Learning"] == "unverified"
    assert statuses["Docker"] == "partially_supported"
    assert p["trust"]["meta"]["commits_analyzed"] == 14
    assert any(s["signal_type"] == "file_history" for s in p["trust"]["signals"])  # per-file lookups happened
    # persistence: fetch again by id
    again = client.get(f"/api/passports/{p['id']}")
    assert again.status_code == 200 and again.json()["summary"] == p["summary"]
    ev = client.get(f"/api/passports/{p['id']}/evidence").json()
    assert ev["count"] > 5 and all(e["illustrative"] is False for e in ev["evidence"])

    jd = "Requirements:\n- Python\n- FastAPI\n- Docker\n- PostgreSQL\nNice to have:\n- GitHub Actions"
    m = client.post("/api/match-job", json={"passport_id": p["id"], "job_title": "Backend Dev", "job_description": jd})
    assert m.status_code == 201, m.text
    body = m.json()
    assert 0 < body["score"] < 100
    assert any(i["skill"] == "Docker" for i in body["important_gaps"])
    rm = client.get(f"/api/roadmap/{p['id']}").json()
    assert rm["based_on"] == "job_match"
    docker = next(i for i in rm["items"] if i["skill"] == "Docker")
    assert "Dockerfile" in docker["evidence_needed"]


def test_sharing_is_explicit_and_sanitized(client, fake_github):
    p = _full_flow(client)
    assert client.get("/api/public/passports/nonexistent").status_code == 404
    s = client.post(f"/api/passports/{p['id']}/share", json={"enabled": True}).json()
    assert s["is_public"] and s["public_id"]
    pub = client.get(f"/api/public/passports/{s['public_id']}").json()
    text = str(pub)
    assert "resume" not in pub and "Example Corp" not in text and "cv.pdf" not in text
    assert all(e["source"] != "resume" for sk in pub["skills"] for e in sk["evidence"])
    assert all(sk["verification_status"] != "unverified" for sk in pub["skills"])
    client.post(f"/api/passports/{p['id']}/share", json={"enabled": False})
    assert client.get(f"/api/public/passports/{s['public_id']}").status_code == 404


def test_errors(client, fake_github):
    assert client.post("/api/github/analyze", json={"repo_url": "https://example.com/x"}).status_code == 422
    fake_github.missing = True
    r = client.post("/api/github/analyze", json={"repo_url": "https://github.com/a/b"})
    assert r.status_code == 404 and "not found" in r.json()["detail"]
    assert client.post("/api/resume/upload", files={"file": ("cv.txt", b"hi", "text/plain")}).status_code == 415
    assert client.get("/api/passports/doesnotexist").status_code == 404
    assert client.post("/api/analyze", json={"name": "x"}).status_code == 422


def test_fork_without_owner_commits_flags(client, fake_github):
    from app.tests.conftest import make_commits
    fake_github.fork = True
    fake_github.commits = make_commits("upstreamdev", 10)
    r = client.post("/api/analyze", json={"name": "K", "repo_url": "https://github.com/student/taskapi"})
    assert r.status_code == 201
    p = r.json()
    assert p["trust"]["level"] == "high_concern"
    assert any(s["verification_status"] == "flagged_for_review" for s in p["skills"])
    assert not any(s["verification_status"] == "evidence_supported" for s in p["skills"])


def test_demo_mode(client):
    d = client.post("/api/demo/load")
    assert d.status_code == 201
    p = d.json()
    assert p["is_demo"] is True
    st = {s["skill"]: s["verification_status"] for s in p["skills"]}
    assert st["Machine Learning"] == "unverified"
    assert st["FastAPI"] == "evidence_supported"
    assert all(e["illustrative"] and e["url"] is None for s in p["skills"] for e in s["evidence"])
    assert any(sig["severity"] in ("low", "medium") for sig in p["trust"]["signals"])
    assert p["latest_job_match"] and p["latest_job_match"]["roadmap"]
    # idempotent
    assert client.post("/api/demo/load").json()["id"] == p["id"]
