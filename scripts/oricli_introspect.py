#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install -e .", file=sys.stderr)
    raise


def _headers() -> Dict[str, str]:
    key = os.getenv("MAVAIA_API_KEY")
    if not key:
        return {}
    return {"Authorization": f"Bearer {key}"}


def _pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Oricli-Alpha introspection CLI helper")
    ap.add_argument("--base", default=os.getenv("MAVAIA_API_BASE", "http://localhost:8000"))

    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("capabilities")

    p_recent = sub.add_parser("recent")
    p_recent.add_argument("--limit", type=int, default=20)

    p_get = sub.add_parser("get")
    p_get.add_argument("trace_id")

    sub.add_parser("router")

    p_diag = sub.add_parser("diagnostics")
    p_diag.add_argument("--max-modules", type=int, default=250)
    p_diag.add_argument("--import-timeout-s", type=float, default=8.0)

    args = ap.parse_args()

    base = str(args.base).rstrip("/")
    headers = _headers()

    with httpx.Client(timeout=30.0, headers=headers) as client:
        if args.cmd == "capabilities":
            r = client.get(f"{base}/v1/introspection")
            r.raise_for_status()
            print(_pretty(r.json()))
            return 0

        if args.cmd == "recent":
            r = client.get(f"{base}/v1/introspection/traces", params={"limit": args.limit})
            r.raise_for_status()
            print(_pretty(r.json()))
            return 0

        if args.cmd == "get":
            r = client.get(f"{base}/v1/introspection/traces/{args.trace_id}")
            r.raise_for_status()
            print(_pretty(r.json()))
            return 0

        if args.cmd == "router":
            r = client.get(f"{base}/v1/introspection/router")
            r.raise_for_status()
            print(_pretty(r.json()))
            return 0

        if args.cmd == "diagnostics":
            r = client.get(
                f"{base}/v1/introspection/diagnostics/modules",
                params={"max_modules": args.max_modules, "import_timeout_s": args.import_timeout_s},
            )
            r.raise_for_status()
            print(_pretty(r.json()))
            return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
