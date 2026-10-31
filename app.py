
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import json
import os

DATA_FILE = Path(os.getenv(
    "DATA_FILE", "/var/lib/backend_data/messages.json"
))


def read_messages():
    if not DATA_FILE.exists():
        return []

    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def write_messages(messages):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(messages, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def save_message(message):
    messages = read_messages()
    item = {
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    messages.append(item)
    write_messages(messages)
    return item


class APIHandler(BaseHTTPRequestHandler):

    def send_json(self, status, payload):
        body = json.dumps(
            payload, ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, DELETE, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type"
        )
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(200, {"status": "ok"})

    def do_GET(self):
        if self.path in ("/", "/health"):
            return self.send_json(200, {
                "status": "active",
                "service": "Backend API",
                "version": "2.0"
            })

        if self.path == "/messages":
            messages = read_messages()
            return self.send_json(200, {
                "messages": messages,
                "total": len(messages)
            })

        return self.send_json(404, {
            "error": "Endpoint not found"
        })

    def do_POST(self):
        if self.path != "/messages":
            return self.send_json(404, {
                "error": "Endpoint not found"
            })

        try:
            length = int(
                self.headers.get("Content-Length", "0")
            )
            payload = json.loads(
                self.rfile.read(length).decode("utf-8")
            )
            message = str(
                payload.get("message", "")
            ).strip()

            if not message:
                return self.send_json(400, {
                    "error": "message must not be empty"
                })

            if len(message) > 500:
                return self.send_json(400, {
                    "error": "message must be 500 characters or fewer"
                })

            return self.send_json(201, {
                "status": "created",
                "message": save_message(message)
            })

        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {
                "error": "Invalid JSON request body"
            })

    def do_DELETE(self):
        parsed = urlparse(self.path)

        if parsed.path != "/messages":
            return self.send_json(404, {
                "error": "Endpoint not found"
            })

        query = parse_qs(parsed.query)

        if "index" not in query:
            return self.send_json(400, {
                "error": "Missing index parameter"
            })

        try:
            index = int(query["index"][0])
            messages = read_messages()

            if index < 0 or index >= len(messages):
                return self.send_json(404, {
                    "error": "Message not found"
                })

            removed = messages.pop(index)
            write_messages(messages)

            return self.send_json(200, {
                "status": "deleted",
                "removed": removed
            })

        except (ValueError, IndexError):
            return self.send_json(400, {
                "error": "Index must be an integer"
            })

    def log_message(self, fmt, *args):
        print(
            f"[{self.log_date_time_string()}] {fmt % args}",
            flush=True
        )


if __name__ == "__main__":
    print("Backend API listening on 0.0.0.0:5000", flush=True)
    ThreadingHTTPServer(
        ("0.0.0.0", 5000), APIHandler
    ).serve_forever()
