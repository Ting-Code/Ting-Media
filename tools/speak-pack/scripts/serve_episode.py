#!/usr/bin/env python3
"""Serve an episode folder over http for local preview."""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import sys
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="用 http 预览口播录屏页")
    parser.add_argument("dir", nargs="?", type=Path, help="含 index.html 的期次目录")
    parser.add_argument("--port", type=int, default=8777)
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    folder = (args.dir or Path.cwd()).expanduser().resolve()
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
    print(url)
    if not args.no_open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
