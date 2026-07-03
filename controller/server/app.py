import argparse
import json
from copy import deepcopy
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from task_store import TaskStore


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
SPECS_DIR = ROOT_DIR / "specs"
RESULTS_DIR = ROOT_DIR / "results"
TASK_STORE = TaskStore(RESULTS_DIR)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def identify_model(identity: dict, rules: dict) -> str:
    product_name = (identity.get("product_name") or "").upper()
    baseboard = (identity.get("baseboard_product") or "").upper()
    serial_number = (identity.get("bios_serial_number") or "").upper()

    for rule in rules.get("rules", []):
        match = rule.get("match", {})
        product_terms = [item.upper() for item in match.get("product_name_contains", [])]
        baseboard_terms = [item.upper() for item in match.get("baseboard_contains", [])]
        serial_terms = [item.upper() for item in match.get("serial_contains", [])]

        product_ok = True if not product_terms else any(term in product_name for term in product_terms)
        baseboard_ok = True if not baseboard_terms else any(term in baseboard for term in baseboard_terms)
        serial_ok = True if not serial_terms else any(term in serial_number for term in serial_terms)

        if product_ok and baseboard_ok and serial_ok:
            return rule.get("model_code", "UNKNOWN_MODEL")
    return "UNKNOWN_MODEL"


def deep_merge(base: dict, override: dict) -> dict:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def load_model_specs() -> dict:
    path = SPECS_DIR / "model_specs.json"
    return load_json(path) if path.exists() else {}


def load_identity_rules() -> dict:
    path = SPECS_DIR / "model_identity_rules.json"
    return load_json(path) if path.exists() else {}


def build_test_plan(model_code: str, specs: dict) -> dict:
    defaults = specs.get("defaults", {})
    model_spec = specs.get("models", {}).get(model_code, {})
    merged = deep_merge(defaults, model_spec)
    tests = merged.setdefault("test_items", {})

    tests.setdefault("inventory_check", {"enabled": True, "blocking": True})
    tests.setdefault("lan_check", {"enabled": True, "blocking": True})
    tests.setdefault("serial_loopback_check", {"enabled": True, "blocking": True})
    tests.setdefault("usb_check", {"enabled": False, "blocking": False, "placeholder_only": True})
    tests.setdefault("display_check", {"enabled": False, "blocking": False, "placeholder_only": True})
    tests.setdefault("io_check", {"enabled": False, "blocking": False, "placeholder_only": True})
    tests.setdefault("burnin_check", {"enabled": True, "blocking": True})

    merged["model_code"] = model_code
    merged["config_status"] = "configured" if model_spec else "pending"
    merged.setdefault("description", "未配置机型，使用默认测试策略")
    return merged


def render_dashboard_html(summary: dict) -> str:
    rows = []
    for task in summary.get("recent_tasks", []):
        rows.append(
            "<tr>"
            f"<td><a href=\"/trace/{task['sn']}\">{task['sn']}</a></td>"
            f"<td>{task['task_id']}</td>"
            f"<td>{task.get('station_id', '')}</td>"
            f"<td>{task.get('status', '')}</td>"
            f"<td>{task.get('current_test_item', '')}</td>"
            f"<td>{task.get('updated_at', '')}</td>"
            "</tr>"
        )
    counts = summary.get("counts", {})
    count_html = "".join(f"<li>{name}: {value}</li>" for name, value in counts.items())
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Factory Dashboard</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 24px; background: #f6f7fb; color: #111827; }}
    h1 {{ margin-bottom: 8px; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; margin: 16px 0 24px; }}
    .card {{ background: white; border-radius: 12px; padding: 12px 16px; box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06); }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }}
    th {{ background: #111827; color: white; }}
    a {{ color: #0f766e; text-decoration: none; }}
  </style>
</head>
<body>
  <h1>产线工位看板</h1>
  <p>生成时间：{summary.get('generated_at', '')}</p>
  <div class="cards">{''.join(f'<div class="card"><strong>{k}</strong><div>{v}</div></div>' for k, v in counts.items())}</div>
  <ul>{count_html}</ul>
  <table>
    <thead>
      <tr><th>SN</th><th>Task</th><th>工位</th><th>状态</th><th>当前步骤</th><th>更新时间</th></tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>"""


def render_trace_html(trace: dict) -> str:
    task = trace["task"]
    lines = []
    for channel in ("lifecycle", "event", "telemetry", "result"):
        for item in trace.get(channel, []):
            lines.append(
                "<tr>"
                f"<td>{item.get('timestamp', '')}</td>"
                f"<td>{channel}</td>"
                f"<td>{item.get('test_item', '')}</td>"
                f"<td>{item.get('status', '')}</td>"
                f"<td><pre>{json.dumps(item.get('payload', {}), ensure_ascii=False, indent=2)}</pre></td>"
                "</tr>"
            )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>SN Trace</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 24px; background: #f6f7fb; color: #111827; }}
    .panel {{ background: white; border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06); margin-bottom: 16px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; }}
    th {{ background: #111827; color: white; }}
    pre {{ margin: 0; white-space: pre-wrap; }}
    a {{ color: #0f766e; }}
  </style>
</head>
<body>
  <div class="panel">
    <h1>SN 追溯：{task.get('sn', '')}</h1>
    <p><a href="/dashboard">返回看板</a></p>
    <p>Task: {task.get('task_id', '')} | 状态: {task.get('status', '')} | 机型: {task.get('model_code', '')}</p>
    <p>开始: {task.get('created_at', '')} | 结束: {task.get('ended_at', '')} | 失败原因: {task.get('failure_reason', '')}</p>
  </div>
  <table>
    <thead>
      <tr><th>时间</th><th>通道</th><th>测试项</th><th>状态</th><th>详情</th></tr>
    </thead>
    <tbody>{''.join(lines)}</tbody>
  </table>
</body>
</html>"""


class SandboxHandler(BaseHTTPRequestHandler):
    server_version = "FactorySandboxHTTP/2.0"

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        return json.loads(raw_body.decode("utf-8")) if raw_body else {}

    def _handle_register(self, payload: dict) -> None:
        sn = payload.get("sn") or payload.get("hardware_identity", {}).get("bios_serial_number") or "UNKNOWN_SN"
        station_id = payload.get("station_id", "UNKNOWN_STATION")
        hardware_identity = payload.get("hardware_identity", {})
        capabilities = payload.get("capabilities", {})

        active = TASK_STORE.find_active_task(sn)
        if active:
            self._send_json(HTTPStatus.OK, active)
            return

        model_code = payload.get("model_code", "")
        if not model_code:
            model_code = identify_model(hardware_identity, load_identity_rules())

        test_plan = build_test_plan(model_code, load_model_specs())
        task = TASK_STORE.create_task(
            sn=sn,
            station_id=station_id,
            model_code=model_code,
            hardware_identity=hardware_identity,
            test_plan=test_plan,
            capabilities=capabilities,
        )
        TASK_STORE.record_message(
            task["task_id"],
            "lifecycle",
            {
                "event_type": "registered",
                "status": "booting",
                "test_item": "bootstrap",
                "payload": {"hardware_identity": hardware_identity, "capabilities": capabilities},
            },
        )
        task = TASK_STORE.load_task(task["task_id"]) or task
        self._send_json(HTTPStatus.CREATED, task)

    def _handle_event(self, payload: dict) -> None:
        task_id = payload.get("task_id", "")
        channel = payload.get("channel", "event")
        if channel not in {"lifecycle", "telemetry", "event", "result"}:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid channel: {channel}"})
            return
        try:
            task = TASK_STORE.record_message(task_id, channel, payload)
        except FileNotFoundError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            return
        self._send_json(HTTPStatus.ACCEPTED, {"status": "accepted", "task_id": task_id, "task_status": task["status"]})

    def _handle_legacy_result(self, payload: dict) -> None:
        sn = payload.get("sn", "UNKNOWN_SN")
        active = TASK_STORE.find_active_task(sn)
        if active:
            task = active
        else:
            model_code = payload.get("model_code", "UNKNOWN_MODEL")
            task = TASK_STORE.create_task(
                sn=sn,
                station_id=payload.get("station_id", "LEGACY"),
                model_code=model_code,
                hardware_identity=payload.get("hardware_identity", {}),
                test_plan=build_test_plan(model_code, load_model_specs()),
                capabilities={},
            )
        result_status = payload.get("overall_result", "FAIL")
        TASK_STORE.record_message(
            task["task_id"],
            "result",
            {
                "channel": "result",
                "event_type": "legacy_final_result",
                "status": str(result_status).upper(),
                "test_item": "final_result",
                "payload": payload,
                "timestamp": payload.get("end_time", now_iso()),
            },
        )
        archive_dir = Path(task["archive_dir"])
        with (archive_dir / f"final_result_{sn}.json").open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        self._send_json(HTTPStatus.CREATED, {"status": "saved", "task_id": task["task_id"], "path": str(archive_dir)})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send_json(HTTPStatus.OK, {"status": "ok", "time": now_iso()})
            return

        if parsed.path == "/dashboard":
            self._send_html(HTTPStatus.OK, render_dashboard_html(TASK_STORE.build_dashboard_summary()))
            return

        if parsed.path.startswith("/trace/"):
            sn = parsed.path.split("/", 2)[-1]
            tasks = TASK_STORE.list_tasks(limit=1, sn=sn)
            if not tasks:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": f"sn not found: {sn}"})
                return
            task = tasks[0]
            self._send_html(HTTPStatus.OK, render_trace_html(TASK_STORE.load_trace(task)))
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

        if parsed.path == "/api/dashboard/summary":
            self._send_json(HTTPStatus.OK, TASK_STORE.build_dashboard_summary())
            return

        if parsed.path == "/api/tasks":
            query = parse_qs(parsed.query)
            tasks = TASK_STORE.list_tasks(
                limit=int(query.get("limit", ["50"])[0]),
                sn=query.get("sn", [""])[0],
                status=query.get("status", [""])[0],
            )
            self._send_json(HTTPStatus.OK, {"tasks": tasks})
            return

        if parsed.path.startswith("/api/tasks/"):
            task_id = parsed.path.rsplit("/", 1)[-1]
            task = TASK_STORE.load_task(task_id)
            if not task:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": f"task not found: {task_id}"})
                return
            self._send_json(HTTPStatus.OK, TASK_STORE.load_trace(task))
            return

        if parsed.path.startswith("/api/duts/"):
            sn = parsed.path.rsplit("/", 1)[-1]
            tasks = TASK_STORE.list_tasks(limit=20, sn=sn)
            if not tasks:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": f"sn not found: {sn}"})
                return
            self._send_json(HTTPStatus.OK, {"sn": sn, "tasks": tasks})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json_body()
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid json: {exc}"})
            return

        if parsed.path == "/api/tasks/register":
            self._handle_register(payload)
            return

        if parsed.path == "/api/events":
            self._handle_event(payload)
            return

        if parsed.path == "/api/results":
            self._handle_legacy_result(payload)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def log_message(self, format: str, *args) -> None:
        print(f"[{now_iso()}] {self.address_string()} {format % args}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Factory sandbox controller service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), SandboxHandler)
    print(f"Listening on http://{server.server_address[0]}:{server.server_address[1]}")
    server.serve_forever()


if __name__ == "__main__":
    main()
