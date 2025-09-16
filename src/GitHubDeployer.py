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
        url = self._api(f"/repos/{self._owner}/{self._repo}/contents/{urllib.parse.quote(repo_path)}?ref={self._branch}")
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and data.get("sha"):
                    return data["sha"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        return None

    def _put_file(self, repo_path: str, content_bytes: bytes, message: str):
        sha = self._get_sha_if_exists(repo_path)
        url = self._api(f"/repos/{self._owner}/{self._repo}/contents/{urllib.parse.quote(repo_path)}")
        payload = {
            "message": message,
            "content": base64.b64encode(content_bytes).decode("ascii"),
            "branch": self._branch,
        }
        if sha:
            payload["sha"] = sha
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={**self._headers(), "Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(req) as resp:
            # We ignore body except for errors
            resp.read()

    def deploy_dir(self, local_dir: str, dest_slug: Optional[str] = None) -> str:
        if not os.path.isdir(local_dir):
            raise ValueError(f"Local directory not found: {local_dir}")
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
