"""Skill verification engine: turns findings + commit history + resume claims into
skill records with a status, proficiency estimate, strength, evidence and explanation.
All thresholds come from scoring_config.py."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.services import scoring_config as cfg
from app.services.taxonomy import SKILLS, SKILLS_BY_ID

TYPE_LABEL = {
    "code_usage": "code usage", "source_file": "source file", "test": "test file", "config": "configuration",
    "commit_history": "commit", "code_import": "import-only reference", "dependency_manifest": "dependency declaration",
    "documentation": "README mention", "resume_claim": "resume claim",
}


def blob_url(repo_url: str, ref: str | None, path: str | None, start: int | None, end: int | None) -> str | None:
    if not (repo_url and ref and path):
        return None
    url = f"{repo_url}/blob/{ref}/{path}"
    if start:
        url += f"#L{start}" + (f"-L{end}" if end and end != start else "")
    return url


def _git_findings(commits: list[dict], owner: str) -> tuple[list[dict], set[str]]:
    own = [c for c in commits if (c.get("author_login") or "").lower() == owner.lower()]
    days = {c["date"][:10] for c in own if c.get("date")}
    feats: set[str] = set()
    if len(own) >= 10 and len(days) >= 3:
        feats.add("regular commit history")
    if len(own) >= 30 and len(days) >= 10:
        feats.add("sustained commit history")
    evidence = [{
        "skill": "git", "type": "commit_history", "file": None, "line_start": None, "line_end": None,
        "snippet": c.get("message"), "feature": None, "commit_sha": c["sha"], "url": c.get("url"),
        "detail": f"commit by {owner} on {(c.get('date') or '')[:10]}",
    } for c in own]
    return evidence, feats | ({f"{len(own)} owner commits over {len(days)} days"} if own else set())


def verify_skills(*, findings: list[dict], commits: list[dict], owner: str, repo_url: str, ref: str | None,
                  resume_claims: list[dict], high_trust_concern: bool, illustrative: bool = False) -> list[dict]:
    by_skill: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple] = set()
    for f in findings:
        if f["skill"] not in SKILLS_BY_ID:
            continue
        key = (f["skill"], f["type"], f.get("file"), f.get("feature"), f.get("line_start") if not f.get("feature") else None)
        if key in seen:
            continue
        seen.add(key)
        by_skill[f["skill"]].append(f)

    git_evidence, git_feats = _git_findings(commits, owner) if commits else ([], set())
    claims = {c["skill_id"]: c for c in resume_claims}
    records: list[dict] = []

    for skill in SKILLS:
        items = list(by_skill.get(skill.id, []))
        if skill.id == "git":
            items += git_evidence
        claim = claims.get(skill.id)
        if not items and not claim:
            continue

        # ---- weights
        per_file_strong: dict[str, float] = defaultdict(float)
        per_file_weak: dict[str, float] = defaultdict(float)
        commit_weight = 0.0
        for it in items:
            w = cfg.EVIDENCE_WEIGHTS.get(it["type"], 0.0)
            if it["type"] == "commit_history":
                commit_weight += w
            elif it["type"] in cfg.STRONG_TYPES:
                per_file_strong[it["file"]] += w
            else:
                per_file_weak[it["file"]] += w
        strong = sum(min(cfg.PER_FILE_WEIGHT_CAP, v) for v in per_file_strong.values()) + min(cfg.COMMIT_WEIGHT_CAP, commit_weight)
        weak = sum(min(cfg.PER_FILE_WEIGHT_CAP, v) for v in per_file_weak.values())
        total = strong + weak
        strong_files = len(per_file_strong) + (1 if commit_weight else 0)
        features = {it["feature"] for it in items if it.get("feature") and it["type"] in cfg.STRONG_TYPES}
        if skill.id == "git":
            features |= {f for f in git_feats if not f[0].isdigit()}
        strength = round(min(1.0, total / cfg.STRENGTH_FULL_WEIGHT), 2)

        # ---- status
        if not items:
            status = "unverified"
        elif strong >= cfg.SUPPORTED_MIN_STRONG_WEIGHT and strong_files >= skill.min_files:
            status = "flagged_for_review" if high_trust_concern else "evidence_supported"
        else:
            status = "partially_supported"

        # ---- level
        level = None
        if strong > 0:
            level = "Beginner"
            if (strong_files >= cfg.INTERMEDIATE_MIN_FILES or len(features) >= cfg.INTERMEDIATE_MIN_FEATURES
                    or features & skill.intermediate_features or features & skill.advanced_features):
                level = "Intermediate"
            if ((strong_files >= cfg.ADVANCED_MIN_FILES and len(features) >= cfg.ADVANCED_MIN_FEATURES)
                    or (features & skill.advanced_features and strong_files >= 3 and len(features) >= 5)):
                level = "Advanced"

        # ---- explanation
        type_counts: dict[str, int] = defaultdict(int)
        for it in items:
            type_counts[it["type"]] += 1
        parts = ", ".join(f"{n} {TYPE_LABEL.get(t, t)}{'s' if n > 1 else ''}" for t, n in sorted(type_counts.items(), key=lambda x: -x[1]))
        feat_txt = ", ".join(sorted(features)[:6])
        expl: list[str] = []
        if items:
            expl.append(f"Found {parts} in the repository.")
            expl.append(f"Strong-evidence weight {strong:.1f} across {strong_files} file(s) "
                        f"(needs ≥ {cfg.SUPPORTED_MIN_STRONG_WEIGHT:g} across ≥ {skill.min_files} file(s) to be evidence-supported).")
            if feat_txt:
                expl.append(f"Observed features: {feat_txt}.")
        if status == "evidence_supported":
            expl.append(f"Estimated {level} from {strong_files} file(s) and {len(features)} distinct feature(s).")
        elif status == "flagged_for_review":
            expl.append("Evidence meets the threshold, but a high-severity repository trust signal means a human should confirm authorship.")
        elif status == "partially_supported":
            if strong == 0:
                expl.append("Only imports, dependency declarations or documentation were found — actual usage was not observed.")
            else:
                expl.append("Real usage was found, but not yet enough independent evidence to be fully supported.")
        else:
            expl.append("This skill is claimed on the resume but no supporting evidence was found in the analysed repository.")
        if claim:
            expl.append(f"Also claimed on resume (page {claim.get('page')}); resume claims add no evidence weight.")

        limitations = ["Static analysis only — repository code was never executed."]
        if items:
            limitations.append("Evidence shows the skill is used in this repository, not who wrote each line.")
        if strong == 0 and items:
            limitations.append("An import or dependency entry does not prove the candidate used it.")
        if illustrative:
            limitations.insert(0, "DEMO DATA — illustrative evidence, not a live verification.")

        # ---- evidence list (strongest first, bounded)
        order = {t: i for i, t in enumerate(["code_usage", "test", "config", "source_file", "commit_history", "code_import", "dependency_manifest", "documentation"])}
        items.sort(key=lambda it: (order.get(it["type"], 9), it.get("file") or "", it.get("line_start") or 0))
        evidence: list[dict] = []
        for it in items[:14]:
            url = it.get("url")
            commit_sha = it.get("commit_sha")
            if it["type"] != "commit_history" and not illustrative:
                url = blob_url(repo_url, ref, it.get("file"), it.get("line_start"), it.get("line_end"))
                commit_sha = ref if ref and len(ref) == 40 else None
            evidence.append({
                "evidence_type": it["type"], "source": "repository", "repo_url": repo_url if not illustrative else None,
                "file_path": it.get("file"), "line_start": it.get("line_start"), "line_end": it.get("line_end"),
                "commit_sha": commit_sha, "url": url, "page": None, "snippet": it.get("snippet"),
                "detail": (it.get("feature") + ": " if it.get("feature") and it.get("feature") not in it.get("detail", "") else "") + it.get("detail", ""),
                "weight": cfg.EVIDENCE_WEIGHTS.get(it["type"], 0.0), "illustrative": illustrative,
            })
        if claim:
            evidence.append({
                "evidence_type": "resume_claim", "source": "resume", "repo_url": None, "file_path": None,
                "line_start": None, "line_end": None, "commit_sha": None, "url": None, "page": claim.get("page"),
                "snippet": claim.get("snippet"), "detail": f"claimed in resume section '{claim.get('section')}'",
                "weight": 0.0, "illustrative": illustrative,
            })

        records.append({
            "skill": skill.name, "skill_id": skill.id, "category": skill.category,
            "estimated_level": level, "verification_status": status, "evidence_strength": strength,
            "explanation": " ".join(expl), "limitations": limitations, "resume_claimed": bool(claim),
            "metrics": {"strong_weight": round(strong, 2), "weak_weight": round(weak, 2), "strong_files": strong_files,
                        "features": sorted(features), "evidence_count": len(items)},
            "evidence": evidence,
        })

    status_order = {"evidence_supported": 0, "flagged_for_review": 1, "partially_supported": 2, "unverified": 3}
    records.sort(key=lambda r: (status_order[r["verification_status"]], -r["evidence_strength"], r["skill"]))
    return records


def key_evidence_files(records: list[dict], limit: int) -> list[str]:
    """Files with the most strong evidence — used for file-level history lookups."""
    score: dict[str, float] = defaultdict(float)
    for r in records:
        for e in r["evidence"]:
            if e["file_path"] and e["evidence_type"] in ("code_usage", "test", "config"):
                score[e["file_path"]] += e["weight"]
    return [f for f, _ in sorted(score.items(), key=lambda x: -x[1])[:limit]]


def summarize(records: list[dict]) -> dict:
    counts = defaultdict(int)
    for r in records:
        counts[r["verification_status"]] += 1
    return {
        "total_skills": len(records),
        "evidence_supported": counts["evidence_supported"],
        "partially_supported": counts["partially_supported"],
        "unverified": counts["unverified"],
        "flagged_for_review": counts["flagged_for_review"],
        "needs_review": counts["flagged_for_review"] + counts["unverified"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
