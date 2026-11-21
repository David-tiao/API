from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

from .config import SiteConfig
from .jsonl_logger import JsonlLogger, redact_url
from .request_control import RequestGate
from .scope import ScopeGuard


def _proxy_config() -> dict | None:
    raw = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    if not raw:
        return None
    from urllib.parse import urlsplit
    parsed = urlsplit(raw)
    if not parsed.scheme or not parsed.hostname:
        return {"server": raw}
    config = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}"}
    if parsed.username:
        config["username"] = parsed.username
    if parsed.password:
        config["password"] = parsed.password
    return config


class BrowserRequestLimiter:
    def __init__(self, gate: RequestGate):
        self.gate = gate
        self.active: set[int] = set()

    async def before(self, request_id: int) -> None:
        await self.gate.acquire()
        self.active.add(request_id)

    def after(self, request_id: int) -> None:
        if request_id in self.active:
            self.active.remove(request_id)
            self.gate.release()

    def close(self) -> None:
        for request_id in list(self.active):
            self.after(request_id)


class DynamicAnalyzer:
    def __init__(self, target: str, config: SiteConfig, guard: ScopeGuard, gate: RequestGate, logger: JsonlLogger, out_dir: Path):
        self.target = target
        self.config = config
        self.guard = guard
        self.gate = gate
        self.logger = logger
        self.out_dir = out_dir
        self.records: list[dict] = []
        self._request_map: dict[int, dict] = {}
        self._tasks: set[asyncio.Task] = set()
        self._limiter = BrowserRequestLimiter(gate)

    async def _login(self, page, context) -> None:
        if not self.config.credentials:
            return
        credential = self.config.credentials[0]
        username = credential.get("username")
        password = credential.get("password")
        login_url = credential.get("login_hint") or self.target
        if not username or not password or not self.guard.is_allowed(str(login_url)):
            return
        try:
            await page.goto(str(login_url), wait_until="domcontentloaded", timeout=12000)
            password_input = page.locator('input[type="password"]').first
            if await password_input.count() == 0:
                return
            user_selectors = [
                'input[type="email"]', 'input[name*="user" i]', 'input[name*="email" i]',
                'input[autocomplete="username"]', 'input[type="text"]',
            ]
            for selector in user_selectors:
                locator = page.locator(selector).first
                if await locator.count() and await locator.is_visible():
                    await locator.fill(str(username))
                    break
            await password_input.fill(str(password))
            submit = page.locator('button[type="submit"], input[type="submit"]').first
            if await submit.count() and await submit.is_visible():
                await submit.click(timeout=5000)
            else:
                await password_input.press("Enter")
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            # Login is best-effort; no credential value is written to logs or evidence.
            return

    async def run(self, pages: list[str]) -> list[dict]:
        browser = None
        try:
            async with async_playwright() as playwright:
                launch_args = {"headless": True}
                proxy = _proxy_config()
                if proxy:
                    launch_args["proxy"] = proxy
                browser = await playwright.chromium.launch(**launch_args)
                context = await browser.new_context(ignore_https_errors=False, service_workers="block")

                async def route_handler(route):
                    request = route.request
                    if not self.guard.is_allowed(request.url):
                        await route.abort()
                        return
                    request_id = id(request)
                    try:
                        await self._limiter.before(request_id)
                        await route.continue_()
                    except Exception:
                        self._limiter.after(request_id)
                        try:
                            await route.abort()
                        except Exception:
                            pass

                await context.route("**/*", route_handler)

                async def websocket_route_handler(websocket_route):
                    if not self.guard.is_allowed(websocket_route.url):
                        await websocket_route.close()
                        return
                    # A WebSocket handshake is a single connection; do not let it
                    # starve behind the shared HTTP concurrency gate.
                    websocket_route.connect_to_server()

                # Playwright 1.55 supports explicit WebSocket routing; fail closed if unavailable.
                if not hasattr(context, "route_web_socket"):
                    raise RuntimeError("Playwright WebSocket routing is unavailable")
                await context.route_web_socket("**/*", websocket_route_handler)
                page = await context.new_page()

                def on_request(request):
                    if not self.guard.is_allowed(request.url):
                        return
                    resource_type = request.resource_type
                    if resource_type not in {"fetch", "xhr", "eventsource"}:
                        return
                    row = {
                        "url": request.url,
                        "http_method": request.method.upper(),
                        "method": request.method.upper(),
                        "headers": {},
                        "post_data": request.post_data,
                        "resource_type": resource_type,
                        "status": 0,
                        "response_content_type": "",
                        "response_fields": [],
                        "request_index": len(self.records),
                    }
                    self._request_map[id(request)] = row
                    self.records.append(row)
                    self.logger.write(row["http_method"], row["url"], 0, "dynamic", request_index=row["request_index"], resource_type=row["resource_type"], note="request_observed")

                async def on_response(response):
                    request = response.request
                    # Release the in-flight slot at response headers; SSE streams may stay open.
                    self._limiter.after(id(request))
                    row = self._request_map.get(id(request))
                    if not row:
                        return
                    row["status"] = response.status
                    try:
                        request_headers = await request.all_headers()
                        safe_request_headers = {}
                        for key, value in request_headers.items():
                            lower_key = key.lower()
                            if lower_key in {"authorization", "cookie", "x-api-key", "api-key"} or any(term in lower_key for term in ("token", "secret", "signature", "sign")):
                                if lower_key == "authorization" and value.lower().startswith("bearer "):
                                    safe_request_headers[lower_key] = "Bearer [REDACTED]"
                                else:
                                    safe_request_headers[lower_key] = "[REDACTED]"
                            else:
                                safe_request_headers[lower_key] = value
                        row["headers"] = safe_request_headers
                        headers = await response.all_headers()
                        row["response_content_type"] = headers.get("content-type", "")
                        if "json" in row["response_content_type"].lower():
                            body = await response.body()
                            if len(body) <= 1024 * 1024:
                                payload = json.loads(body.decode("utf-8", errors="replace"))
                                row["response_fields"] = self._flatten_fields(payload)[:80]
                    except Exception:
                        pass
                    api_method = self._api_method(row)
                    self.logger.write(row["http_method"], row["url"], response.status, "dynamic", request_index=row["request_index"], resource_type=row["resource_type"])
                    row["method"] = api_method
                    if api_method == "GQL":
                        operation = self._graphql_operation(row.get("post_data"))
                        if operation:
                            row["note"] = operation
                    if "text/event-stream" in row.get("response_content_type", "").lower():
                        row["note"] = "Server-Sent Events stream observed"

                def on_finished(request):
                    self._limiter.after(id(request))

                def on_failed(request):
                    self._limiter.after(id(request))
                    row = self._request_map.get(id(request))
                    if row and row.get("status") == 0:
                        row["status"] = -1

                def on_websocket(websocket):
                    if not self.guard.is_allowed(websocket.url):
                        return
                    index = len(self.records)
                    row = {
                        "url": websocket.url,
                        "http_method": "GET",
                        "method": "WS",
                        "headers": {},
                        "post_data": None,
                        "resource_type": "websocket",
                        "status": 101,
                        "response_content_type": "",
                        "response_fields": [],
                        "request_index": index,
                        "note": "WebSocket connection observed",
                    }
                    self.records.append(row)
                    self.logger.write("GET", websocket.url, 101, "dynamic", request_index=index, resource_type="websocket", protocol="WS")

                page.on("request", on_request)
                page.on("response", lambda response: self._schedule(on_response(response)))
                page.on("requestfinished", on_finished)
                page.on("requestfailed", on_failed)
                page.on("websocket", on_websocket)

                await self._login(page, context)
                visit_list = []
                for url in [self.target, *pages]:
                    if url not in visit_list and self.guard.is_allowed(url):
                        visit_list.append(url)
                for url in visit_list[:12]:
                    try:
                        start_index = len(self.records)
                        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        try:
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        except Exception:
                            pass
                        await self._settle_page(start_index)
                    except Exception:
                        continue
                if self._tasks:
                    await asyncio.gather(*list(self._tasks), return_exceptions=True)
                await context.close()
                await browser.close()
                browser = None
        except Exception as exc:
            self.logger.write("-", self.target, 0, "dynamic", note=f"browser_phase_error:{type(exc).__name__}")
        finally:
            self._limiter.close()
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            self._write_har()
        return self.records

    async def _settle_page(self, start_index: int, timeout_seconds: float = 5.0) -> None:
        """Wait until the requests fired by the current page settle.

        A fixed short wait loses response bodies on API-heavy pages. Wait for
        in-flight fetch/XHR/SSE requests to finish, with a bounded timeout so a
        long-lived stream cannot stall the whole run.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        last_count = len(self.records)
        stable_since = None
        while loop.time() < deadline:
            await asyncio.sleep(0.1)
            current_count = len(self.records)
            pending = any(
                row.get("status") == 0
                for row in self.records[start_index:]
                if row.get("resource_type") in {"fetch", "xhr", "eventsource"}
            )
            if current_count == last_count and not pending:
                if stable_since is None:
                    stable_since = loop.time()
                elif loop.time() - stable_since >= 0.3:
                    return
            else:
                stable_since = None
                last_count = current_count

    def _schedule(self, coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @staticmethod
    def _flatten_fields(value, prefix="") -> list[str]:
        fields = []
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                fields.append(path)
                fields.extend(DynamicAnalyzer._flatten_fields(child, path))
        elif isinstance(value, list) and value:
            fields.extend(DynamicAnalyzer._flatten_fields(value[0], prefix + "[]"))
        return fields

    @staticmethod
    def _api_method(row: dict) -> str:
        url = row["url"].lower()
        body = str(row.get("post_data") or "").lower()
        if "graphql" in url or '"query"' in body or "mutation " in body or "query " in body:
            return "GQL"
        return row["http_method"]

    @staticmethod
    def _graphql_operation(raw_body: str | None) -> str | None:
        if not raw_body:
            return None
        try:
            payload = json.loads(raw_body)
            query = str(payload.get("query") or "") if isinstance(payload, dict) else ""
            operation_name = payload.get("operationName") if isinstance(payload, dict) else None
        except Exception:
            query, operation_name = raw_body, None
        import re
        match = re.search(r"\b(query|mutation|subscription)\s+([_A-Za-z][_0-9A-Za-z]*)", query)
        operation_type = match.group(1) if match else "operation"
        name = operation_name or (match.group(2) if match else None)
        return f"GraphQL {operation_type} {name} observed" if name else "GraphQL request observed"

    def _write_har(self) -> None:
        entries = []
        for row in self.records:
            entries.append({
                "startedDateTime": None,
                "request": {
                    "method": row.get("http_method", "GET"),
                    "url": redact_url(row.get("url", "")),
                    "headers": [],
                    "queryString": [],
                    "postData": {"mimeType": "application/json", "text": "[REDACTED]"} if row.get("post_data") else None,
                },
                "response": {
                    "status": row.get("status", 0),
                    "headers": [],
                    "content": {"size": -1, "mimeType": row.get("response_content_type", "")},
                },
                "_requestIndex": row.get("request_index"),
                "_resourceType": row.get("resource_type"),
            })
        destination = self.out_dir / "evidence" / "dynamic.har"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps({"log": {"version": "1.2", "creator": {"name": "API Extractor", "version": "0.1.0"}, "entries": entries}}, ensure_ascii=False, indent=2), encoding="utf-8")
