"""Resume (PDF) parsing with PyMuPDF. The PDF is processed in memory and never stored;
only the extracted, structured claims are persisted. Resume text is untrusted data."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pymupdf

from app.services.repo_analyzer import safe_snippet
from app.services.taxonomy import SKILLS_BY_ID, find_skill_mentions


class ResumeError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class ResumeData:
    page_count: int = 0
    text_chars: int = 0
    claims: list[dict] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


SECTION_RE = re.compile(
    r"^\s*(projects?|academic projects|personal projects|experience|work experience|internships?|professional experience|"
    r"skills|technical skills|education|certifications?|achievements|awards|publications|summary|objective|languages|interests|"
    r"extra[- ]curricular.*|positions? of responsibility|activities)\s*:?\s*$",
    re.IGNORECASE,
)


def _sections(pages: list[str]) -> list[tuple[str, int, str]]:
    """Split text into (section_name, page, line) items, preserving page numbers."""
    current = "header"
    out: list[tuple[str, int, str]] = []
    for pno, text in enumerate(pages, start=1):
        for line in text.splitlines():
            if not line.strip():
                continue
            m = SECTION_RE.match(line)
            if m and len(line.strip()) < 45:
                current = m.group(1).lower()
                continue
            out.append((current, pno, line.strip()))
    return out


def _group_entries(items: list[tuple[str, int, str]], keys: tuple[str, ...]) -> list[dict]:
    entries: list[dict] = []
    for section, page, line in items:
        if not any(k in section for k in keys):
            continue
        is_bullet = bool(re.match(r"^[•\-•●*▪◦]\s*", line))
        clean = re.sub(r"^[•\-•●*▪◦]\s*", "", line)
        if not entries or (not is_bullet and len(clean) < 90 and not clean.endswith(".")):
            entries.append({"title": clean[:120], "page": page, "details": [], "technologies": []})
        else:
            entries[-1]["details"].append(clean[:200])
    for e in entries:
        blob = e["title"] + " " + " ".join(e["details"])
        e["technologies"] = sorted({SKILLS_BY_ID[sid].name for sid, *_ in find_skill_mentions(blob)})
        e["details"] = e["details"][:6]
    return entries[:12]


def parse_resume(data: bytes, filename: str, max_mb: int) -> ResumeData:
    if not filename.lower().endswith(".pdf"):
        raise ResumeError("Only PDF resumes are accepted.", 415)
    if len(data) == 0:
        raise ResumeError("The uploaded file is empty.")
    if len(data) > max_mb * 1024 * 1024:
        raise ResumeError(f"Resume is larger than {max_mb} MB.", 413)
    if not data.lstrip()[:5].startswith(b"%PDF"):
        raise ResumeError("File does not look like a valid PDF.", 415)
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # malformed
        raise ResumeError("The PDF could not be opened; it may be corrupted.") from exc
    try:
        if doc.needs_pass or doc.is_encrypted:
            raise ResumeError("The PDF is password-protected. Upload an unlocked copy.")
        result = ResumeData(page_count=doc.page_count)
        pages: list[str] = []
        image_pages = 0
        for page in doc:
            txt = page.get_text("text") or ""
            pages.append(txt)
            if not txt.strip() and page.get_images():
                image_pages += 1
    finally:
        doc.close()

    full = "\n".join(pages)
    result.text_chars = len(full.strip())
    if result.text_chars < 40:
        if image_pages:
            raise ResumeError("This looks like a scanned PDF (images only, no text layer). Export your resume as a text-based PDF; OCR is not supported.")
        raise ResumeError("No readable text was found in the PDF.")

    items = _sections(pages)
    claims: dict[str, dict] = {}
    for section, page, line in items:
        for sid, _s, _e, alias in find_skill_mentions(line):
            if sid not in claims:
                claims[sid] = {
                    "skill_id": sid, "skill": SKILLS_BY_ID[sid].name, "page": page, "section": section,
                    "snippet": safe_snippet(line), "matched": alias, "mentions": 0,
                }
            claims[sid]["mentions"] += 1
    result.claims = sorted(claims.values(), key=lambda c: c["skill"])
    result.projects = _group_entries(items, ("project",))
    result.experience = _group_entries(items, ("experience", "internship"))
    if not result.claims:
        result.notes.append("No skills from the taxonomy were found in the resume text.")
    result.notes.append("Resume claims are recorded as claims only; they never count as verified evidence.")
    return result
