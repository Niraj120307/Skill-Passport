"""Authorship Guard: explainable trust signals from repository metadata and git history.

What it does NOT do: detect AI-generated code, or prove who wrote a line. Git author
names/emails can be set by anyone; forks, templates, AI assistance and large commits
are normal and are never treated as fraud. Signals only say *what to review*.
"""
from __future__ import annotations

import re
import statistics
from collections import Counter
from datetime import datetime

from app.services import scoring_config as cfg

GENERAL_LIMITATIONS = [
    "Git author identity is self-reported and can be configured by anyone.",
    "Only public metadata and a bounded slice of recent history are analysed.",
    "No AI-generated-code detection is performed; using AI tools or templates is not misconduct.",
    "Signals indicate where human review is useful; they are not a judgement of honesty.",
]


def normalize_commits(raw: list[dict]) -> list[dict]:
    out = []
    for c in raw:
        commit = c.get("commit") or {}
        author = commit.get("author") or {}
        out.append({
            "sha": c.get("sha"),
            "url": c.get("html_url"),
            "date": author.get("date"),
            "author_login": (c.get("author") or {}).get("login"),
            "author_name": author.get("name"),
            "message": (commit.get("message") or "").splitlines()[0][:140] if commit.get("message") else "",
        })
    return [c for c in out if c["sha"]]


def _day(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _is_owner(c: dict, owner: str) -> bool:
    return (c.get("author_login") or "").lower() == owner.lower()


def evaluate(repo: dict, max_commits: int) -> dict:
    """repo: dict with owner, is_fork, parent_full_name, parent_url, commits, contributors,
    file_histories, source_file_count, readme_excerpt, url."""
    signals: list[dict] = []
    owner = repo["owner"]
    commits: list[dict] = repo.get("commits") or []
    contributors: list[dict] = repo.get("contributors") or []

    # ---- timeline
    per_day = Counter(d for d in (_day(c.get("date")) for c in commits) if d)
    timeline = [{"date": d, "commits": n, "owner_commits": sum(1 for c in commits if _day(c.get("date")) == d and _is_owner(c, owner))}
                for d, n in sorted(per_day.items())]
    owner_commits = [c for c in commits if _is_owner(c, owner)]
    owner_share = (len(owner_commits) / len(commits)) if commits else None
    history_truncated = len(commits) >= max_commits

    # ---- fork
    if repo.get("is_fork"):
        parent = repo.get("parent_full_name") or "an upstream repository"
        if commits and not owner_commits:
            signals.append(_sig("fork_without_owner_commits", "high", "Fork with no commits by the repository owner",
                f"This repository is a fork of {parent} and none of the {len(commits)} analysed commits are attributed to `{owner}`.",
                [{"label": "Upstream", "url": repo.get("parent_url")}],
                "Commits may be attributed to unlinked email addresses, so this is not proof the owner did no work.",
                "Ask the candidate to point to their own commits or a diff against the upstream repository."))
        else:
            signals.append(_sig("fork", "medium", "Repository is a fork",
                f"This repository is a fork of {parent}. Some code was likely written upstream by other people.",
                [{"label": "Upstream", "url": repo.get("parent_url")}],
                "Upstream code and the owner's changes are not separated by this prototype.",
                "Review the owner's commits (listed in the timeline) rather than the whole codebase."))

    # ---- history availability
    if not commits:
        signals.append(_sig("history_unavailable", "medium", "Commit history unavailable",
            "No commit history could be retrieved, so the authorship assessment is incomplete.", [],
            "Without history no contribution pattern can be evaluated.", "Treat all skill evidence as needing manual review."))
    else:
        if history_truncated:
            signals.append(_sig("history_truncated", "info", f"Only the latest {len(commits)} commits analysed",
                "Older history exists but was not fetched to stay within API limits.", [],
                "Patterns in older history are not reflected.", "Increase MAX_COMMITS or provide a GitHub token for deeper analysis."))
        # ---- owner share
        if owner_share is not None and owner_share < cfg.LOW_OWNER_SHARE and not (repo.get("is_fork") and not owner_commits):
            others = Counter((c.get("author_login") or c.get("author_name") or "unknown") for c in commits if not _is_owner(c, owner))
            top = ", ".join(f"{a} ({n})" for a, n in others.most_common(3))
            signals.append(_sig("low_owner_share", "medium", "Most commits are by other contributors",
                f"`{owner}` authored {len(owner_commits)} of {len(commits)} analysed commits ({owner_share:.0%}). Other authors: {top}.",
                [], "Team projects legitimately have many authors; commits may also be linked to other emails.",
                "Confirm which parts of the project the candidate built."))
        elif owner_share is not None:
            signals.append(_sig("owner_share", "info", "Owner commit share",
                f"`{owner}` authored {len(owner_commits)} of {len(commits)} analysed commits ({owner_share:.0%}).", [],
                "Commit counts say little about the size or quality of each contribution.", ""))
        # ---- bursts
        if per_day:
            counts = list(per_day.values())
            med = statistics.median(counts)
            for d, n in sorted(per_day.items()):
                if n >= cfg.BURST_MIN_COMMITS_PER_DAY and n >= cfg.BURST_MEDIAN_MULTIPLIER * med:
                    sample = [c for c in commits if _day(c.get("date")) == d][:3]
                    signals.append(_sig("commit_burst", "low", f"Commit burst on {d}",
                        f"{n} commits on a single day (median active day: {med:g}).",
                        [{"label": c["sha"][:7] + " " + c["message"][:50], "url": c["url"]} for c in sample],
                        "Bursts are common before deadlines or when importing history.", "Check whether the burst reflects real iterative work."))
        # ---- bulk import
        src = repo.get("source_file_count") or 0
        if len(commits) <= cfg.BULK_IMPORT_MAX_COMMITS and src >= cfg.BULK_IMPORT_MIN_FILES:
            signals.append(_sig("bulk_import", "medium", "Code arrived in very few commits",
                f"{src} source files but only {len(commits)} commit(s) in history.",
                [{"label": c["sha"][:7] + " " + c["message"][:50], "url": c["url"]} for c in commits[:3]],
                "Moving an existing project into a new repository also looks like this; it is not evidence of copying.",
                "Ask for the original working history or a walkthrough of the code."))

    # ---- file-level history for key evidence files
    fh: dict = repo.get("file_histories") or {}
    for path, hist in list(fh.items())[:5]:
        if not hist:
            continue
        own = sum(1 for c in hist if _is_owner(c, owner))
        sev = "info" if own else "low"
        signals.append(_sig("file_history", sev, f"History of `{path}`",
            f"{own} of {len(hist)} recent commits touching this key evidence file are by `{owner}`.",
            [{"label": c["sha"][:7] + " by " + (c.get("author_login") or c.get("author_name") or "unknown"), "url": c["url"]} for c in hist[:3]],
            "File history shows who committed changes, not who wrote the content.", "" if own else "Ask who implemented this file."))

    # ---- contributors
    if contributors:
        names = ", ".join(f"{c.get('login')} ({c.get('contributions')})" for c in contributors[:5])
        signals.append(_sig("contributors", "info", f"{len(contributors)} contributor(s) listed by GitHub", names, [],
                            "GitHub's contributor list only counts commits linked to accounts.", ""))

    # ---- template indicators
    readme = (repo.get("readme_excerpt") or "").lower()
    if re.search(r"create-react-app|bootstrapped with|this template|boilerplate|starter kit|vite \+ react|cookiecutter", readme):
        signals.append(_sig("template_indicators", "info", "Template or boilerplate indicators",
            "The README mentions a template or starter project. This prototype does not separate template scaffolding from original code.",
            [], "Using templates is standard practice.", "Focus review on code beyond the template defaults."))

    severities = {s["severity"] for s in signals}
    if not commits:
        level = "incomplete"
    elif "high" in severities:
        level = "high_concern"
    elif "medium" in severities:
        level = "review_recommended"
    elif "low" in severities:
        level = "minor_signals"
    else:
        level = "no_major_concerns"

    meta = {
        "is_fork": bool(repo.get("is_fork")),
        "parent_full_name": repo.get("parent_full_name"),
        "parent_url": repo.get("parent_url"),
        "commits_analyzed": len(commits),
        "owner_commits": len(owner_commits),
        "owner_share": round(owner_share, 3) if owner_share is not None else None,
        "history_complete": bool(commits) and not history_truncated,
        "assessment_complete": bool(commits),
        "timeline": timeline,
        "recent_commits": commits[:15],
        "contributors": [{"login": c.get("login"), "contributions": c.get("contributions")} for c in contributors[:10]],
        "limitations": GENERAL_LIMITATIONS,
    }
    return {"trust_level": level, "signals": signals, "meta": meta}


def _sig(signal_type, severity, title, description, evidence, limitations, recommendation) -> dict:
    return {
        "signal_type": signal_type, "severity": severity, "title": title, "description": description,
        "evidence": [e for e in evidence if e.get("url") or e.get("label")], "limitations": limitations,
        "recommendation": recommendation,
    }
