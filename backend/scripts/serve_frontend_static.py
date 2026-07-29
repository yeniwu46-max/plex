"""Serve prebuilt frontend dist and proxy /api to Flask backend."""
from __future__ import annotations

import argparse
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


def _direct_urlopen(request: Request, timeout: float = 30):
    """Open upstream without system HTTP(S)_PROXY (localhost API must not go via Clash/VPN)."""
    opener = build_opener(ProxyHandler({}))
    return opener.open(request, timeout=timeout)


class PlexFrontendHandler(SimpleHTTPRequestHandler):
    dist_dir: Path
    api_target: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.dist_dir), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        if args and str(args[0]).startswith("GET /api/"):
            return
        super().log_message(format, *args)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy()
            return
        if self.path in ("", "/"):
            self.path = "/index.html"
        elif "." not in Path(self.path).name:
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy()
            return
        self.send_error(405, "Method Not Allowed")

    def do_PUT(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy()
            return
        self.send_error(405, "Method Not Allowed")

    def do_PATCH(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy()
            return
        self.send_error(405, "Method Not Allowed")

    def do_DELETE(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy()
            return
        self.send_error(405, "Method Not Allowed")

    def _proxy(self) -> None:
        target = f"{self.api_target.rstrip('/')}{self.path}"
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "content-length", "connection"}
        }
        request = Request(target, data=body, headers=headers, method=self.command)
        try:
            with _direct_urlopen(request, timeout=30) as upstream:
                payload = upstream.read()
                self.send_response(upstream.status)
                for key, value in upstream.headers.items():
                    if key.lower() in {"transfer-encoding", "connection"}:
                        continue
                    self.send_header(key, value)
                self.end_headers()
                if payload:
                    self.wfile.write(payload)
        except HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            for key, value in exc.headers.items():
                if key.lower() in {"transfer-encoding", "connection"}:
                    continue
                self.send_header(key, value)
            self.end_headers()
            if payload:
                self.wfile.write(payload)
        except URLError as exc:
            message = f"API proxy error: {exc}".encode("utf-8", errors="replace")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5180)
    parser.add_argument("--api-target", default="http://127.0.0.1:5100")
    args = parser.parse_args()

    dist = args.dist.resolve()
    if not (dist / "index.html").exists():
        print(f"[ERROR] dist index.html not found: {dist}", file=sys.stderr)
        return 1

    PlexFrontendHandler.dist_dir = dist
    PlexFrontendHandler.api_target = args.api_target
    server = ThreadingHTTPServer((args.host, args.port), PlexFrontendHandler)

    def _serve() -> None:
        server.serve_forever(poll_interval=0.5)

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    print(f"PLEX static frontend at http://{args.host}:{args.port} (dist={dist})")
    print(f"Proxy /api -> {args.api_target}")
    try:
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
