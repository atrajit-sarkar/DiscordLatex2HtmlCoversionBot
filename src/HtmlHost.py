import asyncio
import os
import time
import uuid
import socket
from typing import Dict, Tuple, Optional

from aiohttp import web


class HtmlHost:
    """Lightweight temporary static host for generated HTML sites.

    - Start an aiohttp server on a configured host/port.
    - Register a directory to get a tokenized URL.
    - Serves files under /site/{token}/... with index.html fallback.
    - No automatic expiration; manual management via list/unregister/unregister_all.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, base_url: Optional[str] = None):
        self._host = host
        self._port = port
        # Determine a sensible public-facing base URL for links
        if base_url:
            self._base_url = base_url.rstrip("/")
        else:
            # Prefer environment override if present
            env_base = os.environ.get("HTML_BASE_URL")
            if env_base:
                self._base_url = env_base.rstrip("/")
            else:
                host_for_link = host
                # Avoid 0.0.0.0/:: in links; try to pick a concrete IP
                if host in ("0.0.0.0", "::"):
                    # Allow explicit public host via env
                    public_host = os.environ.get("HTML_PUBLIC_HOST") or os.environ.get("PUBLIC_HOST")
                    if public_host:
                        host_for_link = public_host
                    else:
                        # Best-effort: detect outbound interface IP (may be private on cloud VMs)
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            s.connect(("8.8.8.8", 80))
                            host_for_link = s.getsockname()[0]
                            s.close()
                        except Exception:
                            host_for_link = "localhost"
                if not host_for_link:
                    host_for_link = "localhost"
                self._base_url = f"http://{host_for_link}:{port}"
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        # token -> directory path
        self._map: Dict[str, str] = {}

    @property
    def base_url(self) -> str:
        return self._base_url

    def is_running(self) -> bool:
        return self._app is not None

    async def start(self):
        if self._app is not None:
            return
        self._app = web.Application()
        self._app.add_routes([
            web.get("/site/{token}", self._handle_root),
            web.get("/site/{token}/", self._handle_root),
            web.get("/site/{token}/{tail:.*}", self._handle_file),
        ])
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

    async def stop(self):
        if self._site:
            await self._site.stop()
            self._site = None
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None
    def register_dir(self, dir_path: str) -> str:
        token = uuid.uuid4().hex
        self._map[token] = os.path.abspath(dir_path)
        return f"{self._base_url}/site/{token}/"

    def list_previews(self) -> Dict[str, str]:
        """Return a mapping of token -> directory path for all registered sites."""
        return dict(self._map)

    def unregister(self, token: str, delete_dir: bool = False) -> bool:
        """Unregister a single token, optionally deleting the directory."""
        path = self._map.pop(token, None)
        if not path:
            return False
        if delete_dir and os.path.isdir(path):
            try:
                import shutil
                shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass
        return True

    def unregister_all(self, delete_dirs: bool = False) -> int:
        """Unregister all tokens; optionally delete their directories. Returns count removed."""
        items = list(self._map.items())
        self._map.clear()
        if delete_dirs:
            for _, path in items:
                if os.path.isdir(path):
                    try:
                        import shutil
                        shutil.rmtree(path, ignore_errors=True)
                    except Exception:
                        pass
        return len(items)

    async def _handle_root(self, request: web.Request):
        token = request.match_info.get("token")
        base = self._get_valid_dir(token)
        if not base:
            raise web.HTTPNotFound()
        return web.FileResponse(os.path.join(base, "index.html"))

    async def _handle_file(self, request: web.Request):
        token = request.match_info.get("token")
        tail = request.match_info.get("tail") or "index.html"
        base = self._get_valid_dir(token)
        if not base:
            raise web.HTTPNotFound()
        # Prevent path traversal
        full = os.path.abspath(os.path.join(base, tail))
        if not full.startswith(os.path.abspath(base)):
            raise web.HTTPForbidden()
        if not os.path.exists(full) or not os.path.isfile(full):
            raise web.HTTPNotFound()
        return web.FileResponse(full)

    def _get_valid_dir(self, token: str) -> Optional[str]:
        path = self._map.get(token)
        if not path:
            return None
        return path
