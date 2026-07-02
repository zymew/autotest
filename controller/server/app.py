import argparse
import json
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
SPECS_DIR = ROOT_DIR / "specs"
RESULTS_DIR = ROOT_DIR / "results"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_result(payload: dict) -> Path:
    timestamp = payload.get("end_time") or payload.get("start_time") or datetime.now().isoformat()
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        date_part = dt.date().isoformat()
    except ValueError:
        date_part = datetime.now().date().isoformat()

    model_code = payload.get("model_code") or "UNKNOWN_MODEL"
    sn = payload.get("sn") or "UNKNOWN_SN"

    target_dir = RESULTS_DIR / date_part / model_code / sn
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"final_result_{sn}.json"
    with target_file.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return target_file


class SandboxHandler(BaseHTTPRequestHandler):
    server_version = "FactorySandboxHTTP/1.0"

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return

        if parsed.path == "/api/specs/model_specs":
            path = SPECS_DIR / "model_specs.json"
            if not path.exists():
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "model_specs.json not found"})
                return
            self._send_json(HTTPStatus.OK, load_json(path))
            return

        if parsed.path == "/api/specs/model_identity_rules":
            path = SPECS_DIR / "model_identity_rules.json"
            if not path.exists():
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "model_identity_rules.json not found"})
                return
            self._send_json(HTTPStatus.OK, load_json(path))
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/results":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid json: {exc}"})
            return

        saved_path = write_result(payload)
        self._send_json(
            HTTPStatus.CREATED,
            {
                "status": "saved",
                "path": str(saved_path),
            },
        )

    def log_message(self, format: str, *args) -> None:
        timestamp = datetime.now().isoformat(timespec="seconds")
        print(f"[{timestamp}] {self.address_string()} {format % args}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Factory sandbox controller service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), SandboxHandler)
    print(f"Listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
