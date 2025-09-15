import asyncio
import os
import time
import uuid
from typing import Dict, Tuple, Optional

from aiohttp import web


class HtmlHost:
    """Lightweight temporary static host for generated HTML sites.

    - Start an aiohttp server on a configured host/port.
    - Register a directory with a TTL to get a tokenized URL.
    - Serves files under /site/{token}/... with index.html fallback.
    - Periodically cleans expired registrations and optionally deletes dirs.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, base_url: Optional[str] = None, delete_on_expire: bool = True):
        self._host = host
        self._port = port
        self._base_url = base_url or f"http://localhost:{port}"
        self._delete_on_expire = delete_on_expire
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._map: Dict[str, Tuple[str, float]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

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
        # Periodic cleanup every 5 minutes
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        if self._site:
            await self._site.stop()
            self._site = None
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None

    async def _periodic_cleanup(self):
        try:
            while True:
                await asyncio.sleep(300)
                self.cleanup_expired()
        except asyncio.CancelledError:
            return

    def cleanup_expired(self):
        now = time.time()
        to_delete = [t for t, (_, exp) in self._map.items() if exp <= now]
        for token in to_delete:
            path, _ = self._map.pop(token, (None, None))
            if self._delete_on_expire and path and os.path.isdir(path):
                try:
                    import shutil
                    shutil.rmtree(path, ignore_errors=True)
                except Exception:
                    pass

    def register_dir(self, dir_path: str, ttl_seconds: int = 3600) -> str:
        token = uuid.uuid4().hex
        expire_at = time.time() + max(60, ttl_seconds)
        self._map[token] = (os.path.abspath(dir_path), expire_at)
        return f"{self._base_url}/site/{token}/"

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
        item = self._map.get(token)
        if not item:
            return None
        path, exp = item
        if time.time() > exp:
            return None
        return path
