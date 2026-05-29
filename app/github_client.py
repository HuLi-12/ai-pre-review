import re
import base64
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

import httpx
from config import settings


class PRInfo:
    def __init__(self, owner: str, repo: str, number: int, title: str = "",
                 description: str = "", author: str = "", source_branch: str = "",
                 target_branch: str = "", commit_sha: str = "",
                 created_at: str = "", updated_at: str = ""):
        self.owner = owner
        self.repo = repo
        self.number = number
        self.title = title
        self.description = description
        self.author = author
        self.source_branch = source_branch
        self.target_branch = target_branch
        self.commit_sha = commit_sha
        self.created_at = created_at
        self.updated_at = updated_at


class ChangedFile:
    def __init__(self, file_path: str, change_type: str, additions: int = 0,
                 deletions: int = 0, patch: str = "", raw_content: str = ""):
        self.file_path = file_path
        self.change_type = change_type  # added / modified / removed / renamed
        self.additions = additions
        self.deletions = deletions
        self.patch = patch
        self.raw_content = raw_content


class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        self.base_url = settings.github_api_base
        self.headers = {
            "Accept": "application/vnd.github.v3.diff",
            "User-Agent": "AI-Code-Review-Tool/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _get_headers(self, accept: str = "application/vnd.github.v3+json") -> Dict[str, str]:
        h = {**self.headers, "Accept": accept}
        return h

    @staticmethod
    def parse_pr_url(url: str) -> tuple:
        """Parse GitHub PR URL into (owner, repo, number)"""
        pattern = r"(?:https?://)?github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, url.strip())
        if not match:
            raise ValueError(f"Invalid GitHub PR URL: {url}")
        return match.group(1), match.group(2), int(match.group(3))

    def get_pr_info(self, owner: str, repo: str, number: int) -> PRInfo:
        """Fetch PR basic information"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{number}"
        resp = httpx.get(url, headers=self._get_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        commit_sha = ""
        if data.get("head") and data["head"].get("sha"):
            commit_sha = data["head"]["sha"]

        return PRInfo(
            owner=owner,
            repo=repo,
            number=number,
            title=data.get("title", ""),
            description=data.get("body", ""),
            author=data.get("user", {}).get("login", "") if data.get("user") else "",
            source_branch=data.get("head", {}).get("ref", "") if data.get("head") else "",
            target_branch=data.get("base", {}).get("ref", "") if data.get("base") else "",
            commit_sha=commit_sha,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def get_changed_files(self, owner: str, repo: str, number: int) -> List[ChangedFile]:
        """Fetch changed files with patch diff"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{number}/files"
        resp = httpx.get(url, headers=self._get_headers(accept="application/vnd.github.v3+json"), timeout=60)
        resp.raise_for_status()
        files_data = resp.json()

        changed_files = []
        for f in files_data:
            change_type = "modified"
            if f.get("status") == "added":
                change_type = "added"
            elif f.get("status") == "removed":
                change_type = "removed"
            elif f.get("status") == "renamed":
                change_type = "renamed"

            raw_content = ""
            if f.get("raw_url"):
                try:
                    raw_resp = httpx.get(f["raw_url"], timeout=30)
                    if raw_resp.status_code == 200:
                        raw_content = raw_resp.text
                except Exception:
                    pass

            changed_files.append(ChangedFile(
                file_path=f.get("filename", ""),
                change_type=change_type,
                additions=f.get("additions", 0),
                deletions=f.get("deletions", 0),
                patch=f.get("patch", ""),
                raw_content=raw_content,
            ))

        return changed_files

    def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[str]:
        """Get file content from repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={ref}"
        try:
            resp = httpx.get(url, headers=self._get_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get("content"):
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        except Exception:
            return None
        return None

    def get_repo_file_list(self, owner: str, repo: str, path: str = "", ref: str = "main") -> List[Dict[str, Any]]:
        """List files in a repository directory"""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={ref}"
        try:
            resp = httpx.get(url, headers=self._get_headers(), timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    def create_pr_comment(self, owner: str, repo: str, number: int, body: str) -> bool:
        """Create a PR comment"""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{number}/comments"
        try:
            resp = httpx.post(url, headers=self._get_headers(), json={"body": body}, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to create PR comment: {e}")
            return False

    def create_review_comment(self, owner: str, repo: str, number: int,
                               body: str, commit_sha: str, file_path: str, line: int) -> bool:
        """Create a line-level review comment"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{number}/comments"
        payload = {
            "body": body,
            "commit_id": commit_sha,
            "path": file_path,
            "line": line,
        }
        try:
            resp = httpx.post(url, headers=self._get_headers(), json=payload, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to create review comment: {e}")
            return False
