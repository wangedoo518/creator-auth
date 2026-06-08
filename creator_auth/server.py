import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from .app import CreatorAuthApp, HttpError
from .config import load_settings
from .db import Database


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    app = None

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_PUT(self) -> None:
        self._handle()

    def do_DELETE(self) -> None:
        self._handle()

    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(length) if length > 0 else b""
        headers = {k.lower(): v for k, v in self.headers.items()}

        try:
            status, response_headers, payload = self.app.handle(self.command, self.path, headers, body)
        except HttpError as exc:
            status, response_headers, payload = (
                exc.status,
                {"Content-Type": "application/json; charset=utf-8"},
                {"error": exc.message},
            )
        except Exception as exc:  # pragma: no cover - last resort server boundary
            status, response_headers, payload = (
                500,
                {"Content-Type": "application/json; charset=utf-8"},
                {"error": "internal server error", "detail": str(exc)},
            )

        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "authorization,content-type,x-admin-token")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        for key, value in response_headers.items():
            self.send_header(key, value)
        self.end_headers()

        if isinstance(payload, (dict, list)):
            data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        elif isinstance(payload, str):
            data = payload.encode("utf-8")
        else:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "authorization,content-type,x-admin-token")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.end_headers()

    def log_message(self, fmt, *args):
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), fmt % args))


def main() -> None:
    settings = load_settings()
    if not settings.secret or settings.secret.startswith("change-me"):
        print("WARNING: CREATOR_AUTH_SECRET is not set to a production value.")
    db = Database(settings.db_path)
    Handler.app = CreatorAuthApp(settings, db)
    server = ThreadingHTTPServer((settings.host, settings.port), Handler)
    print(f"creator-auth listening on http://{settings.host}:{settings.port}")
    try:
        server.serve_forever()
    finally:
        db.close()


if __name__ == "__main__":
    main()
