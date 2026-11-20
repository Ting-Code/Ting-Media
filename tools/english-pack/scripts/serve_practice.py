#!/usr/bin/env python3
"""Serve a generated english-pack practice page over HTTP."""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORT = 8781


def main() -> None:
    parser = argparse.ArgumentParser(description="用 http 预览英语跟读练习页")
    parser.add_argument(
        "dir",
        nargs="?",
        type=Path,
        default=ROOT / "practice" / "frontend-workplace",
        help="含 index.html 的练习页目录",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--open", action="store_true", help="启动后打开浏览器")
    args = parser.parse_args()

    folder = args.dir.expanduser().resolve()
    if folder.is_file():
        folder = folder.parent
    index = folder / "index.html"
    if not index.is_file():
        raise SystemExit(f"这里没有 index.html：{folder}")

    os.chdir(folder)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *rest):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % rest))

    try:
        httpd = socketserver.TCPServer(("127.0.0.1", args.port), Handler)
    except OSError as err:
        raise SystemExit(f"端口 {args.port} 不可用：{err}") from err

    url = f"http://127.0.0.1:{args.port}/index.html"
    print(url, flush=True)
    if args.open:
        import webbrowser

        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
