from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="api-extractor", description="Discover frontend API endpoints on an authorized target")
    parser.add_argument("--target", required=True, help="Entry URL of the authorized target")
    parser.add_argument("--config", required=True, help="Read-only site.json configuration")
    parser.add_argument("--out", required=True, help="Absolute result.json path")
    parser.add_argument("--budget", type=int, default=1200, help="Execution budget in seconds (default: 1200)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.budget < 1:
        print("--budget must be >= 1", file=sys.stderr)
        return 2
    try:
        return asyncio.run(run_pipeline(args.target, args.config, args.out, args.budget))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
