import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional


class GitHubDeployer:
    """Deploy a local directory to a GitHub repository branch path using the Contents API.

    This performs individual PUT requests per file. Suitable for small static sites (files <1 MB each).
    """

    def __init__(self, token: str, owner: str, repo: str, branch: str = "gh-pages", dir_prefix: str = ""):
        if not token:
            raise ValueError("Missing GitHub token")
        if not owner or not repo:
            raise ValueError("Missing GitHub owner or repo")
        self._token = token
        self._owner = owner
        self._repo = repo
        self._branch = branch or "gh-pages"
        self._dir_prefix = dir_prefix.strip("/")

    def _api(self, path: str) -> str:
        return f"https://api.github.com{path}"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "WatashinoLatexBot"
        }

    def _get_sha_if_exists(self, repo_path: str) -> Optional[str]:
        # Preserve path separators; GitHub expects slashes in the path portion
        url = self._api(f"/repos/{self._owner}/{self._repo}/contents/{urllib.parse.quote(repo_path, safe='/')}?ref={self._branch}")
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and data.get("sha"):
                    return data["sha"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            # Surface error body for easier debugging
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise urllib.error.HTTPError(e.url, e.code, f"{e.reason} — {body}", e.hdrs, None)
        return None

    def _put_file(self, repo_path: str, content_bytes: bytes, message: str):
        sha = self._get_sha_if_exists(repo_path)
        # Preserve path separators; GitHub expects slashes in the path portion
        url = self._api(f"/repos/{self._owner}/{self._repo}/contents/{urllib.parse.quote(repo_path, safe='/')}")
        payload = {
            "message": message,
            "content": base64.b64encode(content_bytes).decode("ascii"),
            "branch": self._branch,
        }
        if sha:
            payload["sha"] = sha
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={**self._headers(), "Content-Type": "application/json"}, method="PUT")
        try:
            with urllib.request.urlopen(req) as resp:
                # We ignore body except for errors
                resp.read()
        except urllib.error.HTTPError as e:
            # Include response body in error for diagnostics (e.g., missing branch, permissions)
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise urllib.error.HTTPError(e.url, e.code, f"{e.reason} — {body}", e.hdrs, None)

    def _branch_exists(self) -> bool:
        url = self._api(f"/repos/{self._owner}/{self._repo}/branches/{urllib.parse.quote(self._branch, safe='')}")
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req):
                return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            return False

    def deploy_dir(self, local_dir: str, dest_slug: Optional[str] = None) -> str:
        if not os.path.isdir(local_dir):
            raise ValueError(f"Local directory not found: {local_dir}")
        # Preflight branch check for clearer errors than a later 404
        if not self._branch_exists():
            raise RuntimeError(f"Branch '{self._branch}' not found in {self._owner}/{self._repo}. Create it or set GITHUB_BRANCH.")
        slug = dest_slug or time.strftime("site-%Y%m%d-%H%M%S")
        root_parts = [p for p in [self._dir_prefix, slug] if p]
        root_repo_path = "/".join(root_parts)
        # Upload files
        for root, _, files in os.walk(local_dir):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, local_dir).replace("\\", "/")
                repo_path = "/".join([p for p in [root_repo_path, rel] if p])
                with open(full, "rb") as f:
                    content = f.read()
                self._put_file(repo_path, content, message=f"deploy: {slug} -> {repo_path}")
        return slug

    @staticmethod
    def compute_pages_url(owner: str, repo: str, base_url: Optional[str], slug: str) -> str:
        if base_url:
            return base_url.rstrip("/") + "/" + slug + "/"
        # Default GitHub Pages project site URL
        return f"https://{owner}.github.io/{repo}/{slug}/"
