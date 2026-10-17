from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class GitHubAnalyzeRequest(BaseModel):
    repo_url: str = Field(..., min_length=10, max_length=300)


class AnalyzeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    repo_url: str | None = Field(None, max_length=300)
    repository_id: int | None = None
    resume_id: int | None = None

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class JobMatchRequest(BaseModel):
    passport_id: str = Field(..., min_length=8, max_length=40)
    job_title: str = Field(..., min_length=2, max_length=200)
    job_description: str = Field(..., min_length=30, max_length=20000)


class ShareRequest(BaseModel):
    enabled: bool
