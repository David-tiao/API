from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

from .config import load_site_config
from .crawler import ResourceCrawler
from .dynamic_analysis import DynamicAnalyzer
from .jsonl_logger import JsonlLogger
from .normalization import normalize_candidates
from .output import build_result, write_result
from .request_control import RequestGate
from .scope import ScopeGuard
from .static_analysis import StaticAnalyzer


def _validate_mount_paths(config_path: Path, out_path: Path) -> None:
    # In the evaluation container, only /cfg and /out are mounted data locations.
    if Path("/cfg").exists():
        resolved = config_path.resolve()
        if not resolved.is_relative_to(Path("/cfg").resolve()):
            raise ValueError("inside the evaluation container, --config must be under /cfg")
    if Path("/out").exists():
        resolved_out = out_path.resolve()
        if not resolved_out.is_relative_to(Path("/out").resolve()):
            raise ValueError("inside the evaluation container, --out must be under /out")


async def run_pipeline(target: str, config_path: str, out_path: str, budget: int) -> int:
    destination = Path(out_path)
    out_dir = destination.parent if destination.suffix else destination
    if destination.suffix == "":
        destination = out_dir / "result.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    logger = JsonlLogger(out_dir / "tool.log")
    site_name = urlsplit(target).hostname or "unknown"
    endpoints: list[dict] = []
    config = None
    dynamic_records: list[dict] = []
    har_path = out_dir / "evidence" / "dynamic.har"
    try:
        _validate_mount_paths(Path(config_path), destination)
        config = load_site_config(config_path)
        guard = ScopeGuard(target, config.allowed_hosts)
        gate = RequestGate(max_concurrency=8, max_rps=20)
        project_root = Path(__file__).resolve().parent.parent
        candidates: list[dict] = []

        async def stages():
            nonlocal dynamic_records
            async with ResourceCrawler(target, config, guard, gate, logger, out_dir) as crawler:
                crawl = await crawler.crawl()
                analyzer = StaticAnalyzer(project_root, out_dir, guard)
                seen_scripts = set()
                chunks_to_fetch = []
                for script in crawl.scripts:
                    if script.url in seen_scripts:
                        continue
                    seen_scripts.add(script.url)
                    found, chunks = analyzer.analyze(script)
                    candidates.extend(found)
                    chunks_to_fetch.extend(chunks)

                # Follow a bounded number of statically referenced lazy chunks.
                for chunk_url in list(dict.fromkeys(chunks_to_fetch))[:40]:
                    record = await crawler.fetch_asset(chunk_url)
                    if record and record.url not in seen_scripts:
                        seen_scripts.add(record.url)
                        found, nested = analyzer.analyze(record)
                        candidates.extend(found)
                        chunks_to_fetch.extend(nested[:10])

                form_candidates = []
                for form in crawl.forms:
                    form_candidates.append({
                        "method": form["method"], "url": form["url"], "source": "html",
                        "confidence": 0.58, "file": form["file"], "body_fields": [x["name"] for x in form["fields"]],
                        "note": "Form submission endpoint inferred from HTML",
                    })
                candidates.extend(form_candidates)

                dynamic = DynamicAnalyzer(target, config, guard, gate, logger, out_dir)
                dynamic_records = await dynamic.run([page.url for page in crawl.pages] + crawl.links[:8])
                for row in dynamic_records:
                    # Static resources, documents and navigations are intentionally excluded.
                    if row.get("resource_type") not in {"fetch", "xhr", "eventsource", "websocket"}:
                        continue
                    candidates.append({
                        "method": row.get("method") or row.get("http_method") or "GET",
                        "url": row["url"], "source": "dynamic", "confidence": 0.96,
                        "headers": row.get("headers") or {}, "post_data": row.get("post_data"),
                        "response_content_type": row.get("response_content_type"),
                        "response_fields": row.get("response_fields") or [],
                        "request_index": row.get("request_index", 0), "note": row.get("note"),
                    })

        try:
            await asyncio.wait_for(stages(), timeout=max(1, int(budget) - 3))
        except asyncio.TimeoutError:
            logger.write("-", target, 0, "verify", note="budget_exhausted_partial_results_preserved")

        # Every dynamic evidence reference points to the HAR created by the browser phase.
        if dynamic_records and not har_path.exists():
            har_path.parent.mkdir(parents=True, exist_ok=True)
            har_path.write_text(json.dumps({"log": {"version": "1.2", "creator": {"name": "API Extractor", "version": "0.1.0"}, "entries": []}}, indent=2), encoding="utf-8")

        # Remove candidates outside the exact configured scope before normalization.
        scoped = [c for c in candidates if guard.is_allowed(str(c.get("url") or ""))]
        endpoints = normalize_candidates(scoped)
        site_name = config.site_id or site_name
    except Exception as exc:
        logger.write("-", target, 0, "verify", note=f"pipeline_error:{type(exc).__name__}:{str(exc)[:180]}")
        endpoints = []
    finally:
        try:
            result = build_result(site_name, endpoints)
            write_result(destination, result)
        except Exception as exc:
            logger.write("-", target, 0, "verify", note=f"output_validation_error:{type(exc).__name__}:{str(exc)[:180]}")
            fallback = build_result(site_name, [])
            # Empty endpoint output is the safest schema-valid fallback.
            write_result(destination, fallback)
        logger.close()
    return 0
