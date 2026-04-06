#!/usr/bin/env python3
"""Serve a built SPA directory with index.html fallback."""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
from pathlib import Path


class SPARequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serve static assets directly and fall back to index.html for routes."""

    def __init__(self, *args, directory: str, **kwargs):
        self._spa_directory = Path(directory).resolve()
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        target = self.path.split("?", 1)[0].split("#", 1)[0]
        candidate = (self._spa_directory / target.lstrip("/")).resolve()

        if target in ("", "/"):
            self.path = "/index.html"
        elif not str(candidate).startswith(str(self._spa_directory)):
            self.send_error(403, "Forbidden")
            return
        elif not candidate.exists() or candidate.is_dir():
            self.path = "/index.html"

        super().do_GET()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a single-page app build directory.")
    parser.add_argument("root", help="Directory containing the built SPA assets.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=4173, help="Bind port (default: 4173).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    index_file = root / "index.html"
    if not index_file.exists():
        raise SystemExit(f"Missing SPA entrypoint: {index_file}")

    handler = functools.partial(SPARequestHandler, directory=str(root))

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer((args.host, args.port), handler) as httpd:
        print(f"Serving {root} on http://{args.host}:{args.port}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
