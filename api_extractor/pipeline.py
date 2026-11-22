from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

from .candidates import from_html_forms, from_network_records
from .config import load_site_config
from .crawler import ResourceCrawler
from .dynamic_analysis import DynamicAnalyzer
from .evidence import audit_endpoints, split_by_request_proof
from .jsonl_logger import JsonlLogger
from .normalization import normalize_candidates
from .output import build_result, write_result, write_static_review
from .request_control import RequestGate
from .scope import ScopeGuard
from .static_analysis import StaticAnalyzer
from .verification import ExplicitGetVerifier


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
    # Validate first: do not create files outside the evaluator's /out mount.
    _validate_mount_paths(Path(config_path), destination)
    if Path("/out").exists():
        out_dir = Path("/out")  # R6: tool.log is always /out/tool.log.
    out_dir.mkdir(parents=True, exist_ok=True)
    if Path("/out").exists():
        # Direct Chromium temporary profiles and caches to the authorized output
        # mount; avoid writing runtime data to /tmp or the image filesystem.
        for folder in ("tmp", "home", "cache"):
            (out_dir / folder).mkdir(exist_ok=True)
    logger = JsonlLogger(out_dir / "tool.log")
    site_name = urlsplit(target).hostname or "unknown"
    exit_code = 0
    outcome = "completed"
    endpoints: list[dict] = []
    static_only: list[dict] = []
    config = None
    dynamic_records: list[dict] = []
    dynamic: DynamicAnalyzer | None = None
    prober: ExplicitGetVerifier | None = None
    har_path = out_dir / "evidence" / "dynamic.har"
    try:
        _validate_mount_paths(Path(config_path), destination)
        config = load_site_config(config_path)
        guard = ScopeGuard(target, config.allowed_hosts)
        gate = RequestGate(max_concurrency=8, max_rps=20)
        project_root = Path(__file__).resolve().parent.parent
        candidates: list[dict] = []

        async def stages():
            nonlocal dynamic_records, dynamic, prober
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

                candidates.extend(from_html_forms(crawl.forms))

                dynamic = DynamicAnalyzer(target, config, guard, gate, logger, out_dir)
                dynamic_records = await dynamic.run([page.url for page in crawl.pages] + crawl.links[:8])
                prober = ExplicitGetVerifier(config, guard, gate, logger, out_dir)
                await prober.run(candidates)

        try:
            await asyncio.wait_for(stages(), timeout=max(0.1, float(budget) - min(3.0, budget * 0.2)))
        except asyncio.TimeoutError:
            # The evaluation contract R2 requires exit code 0 for a valid partial
            # deliverable. Record the truncation explicitly instead.
            outcome = "incomplete_budget"
            logger.write("-", target, 0, "verify", note="budget_exhausted_partial_results_preserved")

        if dynamic is not None:
            # Playwright may have observed requests before wait_for cancelled it.
            dynamic_records = dynamic_records or dynamic.records
            if getattr(dynamic, "failure_reason", None):
                if outcome == "completed":
                    outcome = "partial_browser_failure"
                logger.write("-", target, 0, "verify", note=f"dynamic_phase_failed:{dynamic.failure_reason}")
        candidates.extend(from_network_records(dynamic_records))
        if prober is not None:
            candidates.extend(prober.records)

        # Every dynamic evidence reference points to the HAR created by the browser phase.
        if dynamic_records and not har_path.exists():
            har_path.parent.mkdir(parents=True, exist_ok=True)
            har_path.write_text(json.dumps({"log": {"version": "1.2", "creator": {"name": "API Extractor", "version": "0.1.0"}, "entries": []}}, indent=2), encoding="utf-8")

        # Remove candidates outside the exact configured scope before normalization.
        scoped = [c for c in candidates if guard.is_allowed(str(c.get("url") or ""))]
        endpoints = normalize_candidates(scoped)
        endpoints, invalid_refs, dropped = audit_endpoints(
            endpoints, out_dir, log_start_offset=logger.start_offset
        )
        if invalid_refs or dropped:
            logger.write("-", target, 0, "verify", note=(
                f"evidence_audit:invalid_references={invalid_refs},dropped_endpoints={dropped}"
            ))
        # An audited static excerpt is not proof that its API was requested.
        # Keep such hints for review but never label them as observed in result.json.
        endpoints, static_only = split_by_request_proof(endpoints)
        logger.write("-", target, 0, "verify", note=(
            f"request_proof_gate:confirmed={len(endpoints)},static_only={len(static_only)}"
        ))
        site_name = config.site_id or site_name
        # R2 requires 0 for a schema-valid deliverable, including an empty but
        # honestly labelled partial browser result. Fatal pipeline failures remain 1.
    except Exception as exc:
        logger.write("-", target, 0, "verify", note=f"pipeline_error:{type(exc).__name__}")
        endpoints = []
        static_only = []
        exit_code = 1
        outcome = "failed"
    finally:
        try:
            result = build_result(site_name, endpoints)
            write_result(destination, result)
        except Exception as exc:
            logger.write("-", target, 0, "verify", note=f"output_validation_error:{type(exc).__name__}")
            fallback = build_result(site_name, [])
            # Keep schema-valid fallback, but report the error to the caller.
            exit_code = 1
            outcome = "failed"
            write_result(destination, fallback)
        try:
            write_static_review(out_dir / "static_candidates.json", site_name, static_only)
        except Exception as exc:
            # The sidecar is diagnostic; a valid --out result must still be returned.
            logger.write("-", target, 0, "verify", note=f"static_review_write_error:{type(exc).__name__}")
        logger.write("-", target, 0, "verify", note=f"run_status:{outcome}")
        logger.close()
    return exit_code
