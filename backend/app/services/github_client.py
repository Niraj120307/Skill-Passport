"""Minimal GitHub REST client. ~5-10 requests per analysis:
repo metadata, languages, commits, contributors, one zipball download, plus a few
per-file history lookups. Works unauthenticated (60 req/hour) or with GITHUB_TOKEN.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.config import settings

REPO_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/(?P<repo>[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?(?:[?#].*)?$"
)


class GitHubError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class RepoRef:
    owner: str
    repo: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def html_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"


def parse_repo_url(url: str) -> RepoRef:
    url = (url or "").strip()
    m = REPO_URL_RE.match(url)
    if not m:
        raise GitHubError(
            "Invalid GitHub repository URL. Use the form https://github.com/<owner>/<repo>.", 422
        )
    return RepoRef(m.group("owner"), m.group("repo"))


class GitHubClient:
    def __init__(self, token: str | None = None, base_url: str | None = None, timeout: int | None = None):
        self.token = token if token is not None else settings.github_token
        self.base = (base_url or settings.github_api_base).rstrip("/")
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "skill-passport-prototype"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self._client = httpx.Client(
            headers=headers, timeout=timeout or settings.github_timeout_seconds, follow_redirects=True
        )

    def close(self) -> None:
        self._client.close()

    # ---- low level -------------------------------------------------------
    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        try:
            resp = self._client.get(f"{self.base}{path}", params=params)
        except httpx.TimeoutException as exc:
            raise GitHubError("GitHub did not respond in time. Try again in a moment.", 504) from exc
        except httpx.HTTPError as exc:
            raise GitHubError(f"Network error while contacting GitHub: {exc.__class__.__name__}.", 502) from exc
        if resp.status_code == 404:
            raise GitHubError("Repository not found or not public.", 404)
        if resp.status_code in (403, 429):
            remaining = resp.headers.get("x-ratelimit-remaining")
            if remaining == "0" or resp.status_code == 429:
                raise GitHubError(
                    "GitHub API rate limit reached. Wait an hour or add a free GITHUB_TOKEN to backend/.env.", 429
                )
            raise GitHubError("GitHub refused the request (403). The repository may be private or blocked.", 403)
        if resp.status_code == 409:  # empty repository
            raise GitHubError("Repository is empty.", 422)
        if resp.status_code >= 400:
            raise GitHubError(f"GitHub returned HTTP {resp.status_code}.", 502)
        return resp

    # ---- API calls ---------------------------------------------------------
    def get_repo(self, ref: RepoRef) -> dict:
        data = self._get(f"/repos/{ref.full_name}").json()
        if data.get("private"):
            raise GitHubError("Only public repositories can be analysed.", 422)
        return data

    def get_languages(self, ref: RepoRef) -> dict:
        try:
            return self._get(f"/repos/{ref.full_name}/languages").json()
        except GitHubError:
            return {}

    def get_commits(self, ref: RepoRef, limit: int, path: str | None = None) -> list[dict]:
        params = {"per_page": min(limit, 100)}
        if path:
            params["path"] = path
        try:
            data = self._get(f"/repos/{ref.full_name}/commits", params=params).json()
        except GitHubError as exc:
            if exc.status_code == 422:  # empty repo
                return []
            raise
        return data if isinstance(data, list) else []

    def get_contributors(self, ref: RepoRef) -> list[dict]:
        try:
            data = self._get(f"/repos/{ref.full_name}/contributors", params={"per_page": 30}).json()
            return data if isinstance(data, list) else []
        except GitHubError:
            return []

    def download_zipball(self, ref: RepoRef, branch: str, max_mb: int) -> bytes:
        """Stream the repository archive with a hard size cap. The archive is only read, never executed."""
        url = f"{self.base}/repos/{ref.full_name}/zipball/{branch}"
        limit = max_mb * 1024 * 1024
        chunks: list[bytes] = []
        size = 0
        try:
            with self._client.stream("GET", url) as resp:
                if resp.status_code >= 400:
                    raise GitHubError(f"Could not download repository archive (HTTP {resp.status_code}).", 502)
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > limit:
                        raise GitHubError(
                            f"Repository archive is larger than {max_mb} MB; analyse a smaller repository or raise MAX_REPO_ZIP_MB.",
                            413,
                        )
                    chunks.append(chunk)
        except httpx.TimeoutException as exc:
            raise GitHubError("Timed out downloading the repository archive.", 504) from exc
        except httpx.HTTPError as exc:
            raise GitHubError(f"Network error downloading repository: {exc.__class__.__name__}.", 502) from exc
        return b"".join(chunks)
