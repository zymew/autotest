import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4


TASK_STATUS_ACTIVE = {"queued", "booting", "running", "burnin_running"}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def append_jsonl(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class TaskStore:
    def __init__(self, results_dir: Path) -> None:
        self.results_dir = results_dir
        self.tasks_dir = results_dir / "tasks"
        self.archive_dir = results_dir / "archive"
        ensure_dir(self.tasks_dir)
        ensure_dir(self.archive_dir)

    def _task_file(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def _archive_task_dir(self, created_at: str, sn: str, task_id: str) -> Path:
        date_part = created_at.split("T", 1)[0]
        return self.archive_dir / date_part / sn / task_id

    def _persist_task(self, task: dict) -> dict:
        write_json(self._task_file(task["task_id"]), task)
        archive_dir = Path(task["archive_dir"])
        ensure_dir(archive_dir)
        write_json(archive_dir / "task.json", task)
        return task

    def create_task(
        self,
        sn: str,
        station_id: str,
        model_code: str,
        hardware_identity: dict,
        test_plan: dict,
        capabilities: dict,
    ) -> dict:
        created_at = now_iso()
        task_id = uuid4().hex[:12]
        archive_dir = self._archive_task_dir(created_at, sn, task_id)
        ensure_dir(archive_dir)
        task = {
            "task_id": task_id,
            "sn": sn,
            "station_id": station_id,
            "model_code": model_code,
            "status": "queued",
            "current_test_item": "",
            "created_at": created_at,
            "updated_at": created_at,
            "last_heartbeat_at": created_at,
            "ended_at": "",
            "failure_reason": "",
            "hardware_identity": hardware_identity,
            "capabilities": capabilities,
            "test_plan": test_plan,
            "results_by_item": {},
            "final_result": {},
            "archive_dir": str(archive_dir),
            "channels": {
                "lifecycle_count": 0,
                "telemetry_count": 0,
                "event_count": 0,
                "result_count": 0,
            },
        }
        self._persist_task(task)
        return task

    def load_task(self, task_id: str) -> Optional[dict]:
        path = self._task_file(task_id)
        if not path.exists():
            return None
        return load_json(path)

    def find_active_task(self, sn: str) -> Optional[dict]:
        for path in sorted(self.tasks_dir.glob("*.json"), reverse=True):
            task = load_json(path)
            if task.get("sn") == sn and task.get("status") in TASK_STATUS_ACTIVE:
                return task
        return None

    def save_task(self, task: dict) -> dict:
        task["updated_at"] = now_iso()
        return self._persist_task(task)

    def list_tasks(self, limit: int = 50, sn: str = "", status: str = "") -> list[dict]:
        items = []
        for path in sorted(self.tasks_dir.glob("*.json"), reverse=True):
            task = load_json(path)
            if sn and task.get("sn") != sn:
                continue
            if status and task.get("status") != status:
                continue
            items.append(task)
            if len(items) >= limit:
                break
        return items

    def _channel_file(self, task: dict, channel: str) -> Path:
        archive_dir = Path(task["archive_dir"])
        return archive_dir / f"{channel}.jsonl"

    def record_message(self, task_id: str, channel: str, payload: dict) -> dict:
        task = self.load_task(task_id)
        if not task:
            raise FileNotFoundError(f"Task not found: {task_id}")

        message = deepcopy(payload)
        message.setdefault("task_id", task_id)
        message.setdefault("sn", task["sn"])
        message.setdefault("station_id", task["station_id"])
        message.setdefault("model_code", task["model_code"])
        message.setdefault("timestamp", now_iso())
        append_jsonl(self._channel_file(task, channel), message)

        task["last_heartbeat_at"] = message["timestamp"]
        count_key = f"{channel}_count"
        if count_key in task["channels"]:
            task["channels"][count_key] += 1

        status = message.get("status", "")
        test_item = message.get("test_item", "")
        if test_item:
            task["current_test_item"] = test_item

        if channel == "lifecycle":
            if status:
                task["status"] = status
        elif channel == "telemetry":
            if task.get("status") in {"queued", "booting"}:
                task["status"] = "running"
        elif channel == "event":
            if test_item:
                task["results_by_item"][test_item] = {
                    "status": status or "UNKNOWN",
                    "timestamp": message["timestamp"],
                    "payload": message.get("payload", {}),
                    "event_type": message.get("event_type", ""),
                }
            if status == "RUNNING" and test_item == "burnin_check":
                task["status"] = "burnin_running"
            elif status == "FAIL":
                task["status"] = "failed"
                task["failure_reason"] = (
                    message.get("payload", {}).get("detail")
                    or message.get("payload", {}).get("failure_reason")
                    or task.get("failure_reason", "")
                )
            elif status == "PASS" and task.get("status") not in {"failed", "aborted", "timeout"}:
                task["status"] = "running"
        elif channel == "result":
            task["final_result"] = message
            overall_result = message.get("payload", {}).get("overall_result") or status
            normalized = str(overall_result).upper()
            if normalized == "PASS":
                task["status"] = "passed"
            elif normalized in {"FAIL", "ABORTED", "TIMEOUT"}:
                task["status"] = normalized.lower()
            task["failure_reason"] = message.get("payload", {}).get("failure_reason", task.get("failure_reason", ""))
            task["ended_at"] = message["timestamp"]

        self.save_task(task)
        return task

    def build_dashboard_summary(self) -> dict:
        tasks = self.list_tasks(limit=200)
        counts = {
            "queued": 0,
            "booting": 0,
            "running": 0,
            "burnin_running": 0,
            "passed": 0,
            "failed": 0,
            "aborted": 0,
            "timeout": 0,
        }
        for task in tasks:
            status = task.get("status", "")
            if status in counts:
                counts[status] += 1

        return {
            "generated_at": now_iso(),
            "counts": counts,
            "active_tasks": [task for task in tasks if task.get("status") in TASK_STATUS_ACTIVE][:20],
            "recent_tasks": tasks[:20],
        }

    def load_trace(self, task: dict) -> dict:
        archive_dir = Path(task["archive_dir"])

        def read_jsonl(name: str) -> list[dict]:
            path = archive_dir / f"{name}.jsonl"
            if not path.exists():
                return []
            items = []
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    items.append(json.loads(stripped))
            return items

        return {
            "task": task,
            "lifecycle": read_jsonl("lifecycle"),
            "telemetry": read_jsonl("telemetry"),
            "event": read_jsonl("event"),
            "result": read_jsonl("result"),
        }
