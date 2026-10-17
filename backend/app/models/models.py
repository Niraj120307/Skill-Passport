"""SQLAlchemy models. JSON columns hold structured, already-sanitised analysis data."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Repository(Base):
    """A snapshot of one analysed GitHub repository (raw findings, never source code)."""

    __tablename__ = "repositories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(300))
    owner: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(120), default="main")
    head_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_full_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    parent_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    languages: Mapped[dict] = mapped_column(JSON, default=dict)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    files_scanned: Mapped[int] = mapped_column(Integer, default=0)
    findings: Mapped[list] = mapped_column(JSON, default=list)
    commits: Mapped[list] = mapped_column(JSON, default=list)
    contributors: Mapped[list] = mapped_column(JSON, default=list)
    file_histories: Mapped[dict] = mapped_column(JSON, default=dict)
    readme_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    scan_notes: Mapped[list] = mapped_column(JSON, default=list)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Resume(Base):
    """Extracted resume data. The original PDF is NOT stored."""

    __tablename__ = "resumes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    text_chars: Mapped[int] = mapped_column(Integer, default=0)
    claims: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    experience: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[list] = mapped_column(JSON, default=list)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Passport(Base):
    __tablename__ = "passports"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"))
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    trust_level: Mapped[str] = mapped_column(String(20), default="unknown")
    trust_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    public_id: Mapped[str | None] = mapped_column(String(40), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    student: Mapped[Student] = relationship()
    repository: Mapped[Repository] = relationship()
    resume: Mapped[Resume | None] = relationship()
    skills: Mapped[list["SkillRecord"]] = relationship(back_populates="passport", cascade="all, delete-orphan")
    trust_signals: Mapped[list["TrustSignal"]] = relationship(back_populates="passport", cascade="all, delete-orphan")
    job_matches: Mapped[list["JobMatch"]] = relationship(
        back_populates="passport", cascade="all, delete-orphan", order_by="JobMatch.created_at"
    )


class SkillRecord(Base):
    __tablename__ = "skill_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    passport_id: Mapped[str] = mapped_column(ForeignKey("passports.id"), index=True)
    skill: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(40), default="")
    estimated_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30))
    evidence_strength: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[str] = mapped_column(Text, default="")
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    resume_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)

    passport: Mapped[Passport] = relationship(back_populates="skills")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="skill_record", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_record_id: Mapped[int] = mapped_column(ForeignKey("skill_records.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(20), default="repository")  # repository | resume
    repo_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    illustrative: Mapped[bool] = mapped_column(Boolean, default=False)

    skill_record: Mapped[SkillRecord] = relationship(back_populates="evidence")


class TrustSignal(Base):
    __tablename__ = "trust_signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    passport_id: Mapped[str] = mapped_column(ForeignKey("passports.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(10))  # info | low | medium | high
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")

    passport: Mapped[Passport] = relationship(back_populates="trust_signals")


class JobMatch(Base):
    __tablename__ = "job_matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    passport_id: Mapped[str] = mapped_column(ForeignKey("passports.id"), index=True)
    job_title: Mapped[str] = mapped_column(String(200))
    job_description: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    roadmap: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    passport: Mapped[Passport] = relationship(back_populates="job_matches")
