from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from .config import SiteConfig
from .jsonl_logger import JsonlLogger
from .request_control import RequestGate
from .scope import ScopeGuard


@dataclass(slots=True)
class PageRecord:
    url: str
    html: str
    local_file: str = ""


@dataclass(slots=True)
class ScriptRecord:
    url: str
    content: str
    local_file: str = ""


@dataclass(slots=True)
class CrawlResult:
    pages: list[PageRecord] = field(default_factory=list)
    scripts: list[ScriptRecord] = field(default_factory=list)
    stylesheets: list[tuple[str, str]] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    forms: list[dict] = field(default_factory=list)


class ResourceCrawler:
    def __init__(
        self,
        target: str,
        config: SiteConfig,
        guard: ScopeGuard,
        gate: RequestGate,
        logger: JsonlLogger,
        out_dir: Path,
        max_pages: int = 12,
        max_scripts: int = 80,
    ):
        self.target = target
        self.config = config
        self.guard = guard
        self.gate = gate
        self.logger = logger
        self.out_dir = out_dir
        self.max_pages = max_pages
        self.max_scripts = max_scripts
        self._client: httpx.AsyncClient | None = None
        self._seen_pages: set[str] = set()
        self._seen_assets: set[str] = set()
        self._result = CrawlResult()

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=False,
            headers={"User-Agent": "API-Extractor/0.1.0 (+authorized security assessment)"},
            trust_env=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._client:
            await self._client.aclose()

    async def _get(self, url: str, phase: str = "static") -> tuple[str, bytes, int, str] | None:
        if not self.guard.is_allowed(url):
            self.logger.write("GET", url, 0, phase, note="blocked_by_scope")
            return None
        if not self._client:
            raise RuntimeError("crawler client is not initialized")

        current = url
        for _ in range(6):
            if not self.guard.is_allowed(current):
                self.logger.write("GET", current, 0, phase, note="redirect_blocked_by_scope")
                return None
            try:
                async with self.gate.slot():
                    response = await self._client.get(current, headers=self.config.headers)
                self.logger.write("GET", current, response.status_code, phase)
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        return current, b"", response.status_code, response.headers.get("content-type", "")
                    current = urljoin(current, location)
                    continue
                return current, response.content[:8 * 1024 * 1024], response.status_code, response.headers.get("content-type", "")
            except (httpx.HTTPError, asyncio.TimeoutError) as exc:
                self.logger.write("GET", current, 0, phase, note=f"request_error:{type(exc).__name__}")
                return None
        self.logger.write("GET", current, 0, phase, note="redirect_limit")
        return None

    def _save_text(self, folder: str, url: str, content: bytes, suffix: str) -> str:
        digest = hashlib.sha256(url.encode("utf-8") + content).hexdigest()[:20]
        relative = f"evidence/{folder}/{digest}{suffix}"
        destination = self.out_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return relative

    async def fetch_asset(self, url: str) -> ScriptRecord | None:
        url = urljoin(self.target, url)
        if url in self._seen_assets or len(self._result.scripts) >= self.max_scripts:
            return None
        self._seen_assets.add(url)
        fetched = await self._get(url, "static")
        if not fetched:
            return None
        final_url, body, status, content_type = fetched
        if status >= 400 or not body:
            return None
        path = urlsplit(final_url).path.lower()
        is_js = "javascript" in content_type.lower() or path.endswith((".js", ".mjs", ".cjs"))
        if not is_js:
            return None
        content = body.decode("utf-8", errors="replace")
        record = ScriptRecord(final_url, content)
        record.local_file = self._save_text("js", final_url, body, ".js")
        self._result.scripts.append(record)
        return record

    async def crawl(self) -> CrawlResult:
        queue = [self.target]
        while queue and len(self._result.pages) < self.max_pages:
            url = queue.pop(0)
            if url in self._seen_pages or not self.guard.is_allowed(url):
                continue
            self._seen_pages.add(url)
            fetched = await self._get(url, "static")
            if not fetched:
                continue
            final_url, body, status, content_type = fetched
            if status >= 400 or not body:
                continue
            if "html" not in content_type.lower() and not body.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                continue
            html = body.decode("utf-8", errors="replace")
            page = PageRecord(final_url, html)
            page.local_file = self._save_text("pages", final_url, body, ".html")
            self._result.pages.append(page)
            soup = BeautifulSoup(html, "html.parser")

            for script in soup.find_all("script"):
                src = script.get("src")
                if src:
                    asset_url = urljoin(final_url, str(src))
                    if self.guard.is_allowed(asset_url):
                        await self.fetch_asset(asset_url)
                elif script.string or script.get_text(strip=False):
                    inline = script.string or script.get_text()
                    if inline.strip() and len(self._result.scripts) < self.max_scripts:
                        digest = hashlib.sha256((final_url + inline).encode()).hexdigest()[:20]
                        rel = f"evidence/js/inline-{digest}.js"
                        dest = self.out_dir / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_text(inline, encoding="utf-8")
                        self._result.scripts.append(ScriptRecord(final_url + f"#inline-{digest}", inline, rel))

            for link in soup.find_all("a", href=True):
                href = urljoin(final_url, str(link.get("href")))
                if self.guard.is_allowed(href):
                    clean = urlsplit(href)
                    href = clean._replace(fragment="").geturl()
                    if href not in self._seen_pages and href not in self._result.links:
                        self._result.links.append(href)
                        if len(queue) + len(self._result.pages) < self.max_pages * 2:
                            queue.append(href)

            for form in soup.find_all("form"):
                action = urljoin(final_url, str(form.get("action") or final_url))
                method = str(form.get("method") or "GET").upper()
                if not self.guard.is_allowed(action):
                    continue
                fields = []
                for element in form.find_all(["input", "select", "textarea"]):
                    name = element.get("name")
                    if name:
                        fields.append({"name": str(name), "type": "string", "required": bool(element.has_attr("required"))})
                if method != "GET" or "/api" in urlsplit(action).path.lower():
                    self._result.forms.append({"method": method, "url": action, "fields": fields, "file": page.local_file})

            for tag in soup.find_all("link", href=True):
                rel = " ".join(tag.get("rel") or []).lower()
                asset_url = urljoin(final_url, str(tag.get("href")))
                if "stylesheet" in rel and self.guard.is_allowed(asset_url):
                    css = await self._get(asset_url, "static")
                    if css and css[2] < 400:
                        css_url, css_body, _, _ = css
                        css_text = css_body.decode("utf-8", errors="replace")
                        self._result.stylesheets.append((css_url, css_text))
                        for ref in re.findall(r"@import\s+(?:url\()?['\"]?([^'\")\s;]+)", css_text, re.I):
                            nested = urljoin(css_url, ref)
                            if self.guard.is_allowed(nested):
                                await self._get(nested, "static")

        self._result.links = self._result.links[:200]
        return self._result
