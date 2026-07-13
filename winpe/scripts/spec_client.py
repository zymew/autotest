import json
from pathlib import Path
from urllib import error, request


def fetch_json(url: str, timeout: int = 15) -> dict:
    with request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict, timeout: int = 15) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_local_json(path: str | Path) -> dict:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def safe_fetch_json(url: str, timeout: int = 15) -> tuple[bool, dict | str]:
    try:
        return True, fetch_json(url, timeout=timeout)
    except error.URLError as exc:
        return False, f"fetch failed: {exc}"
    except Exception as exc:
        return False, f"fetch failed: {type(exc).__name__}: {exc}"


def safe_post_json(url: str, payload: dict, timeout: int = 15) -> tuple[bool, str, dict]:
    try:
        response = post_json(url, payload, timeout=timeout)
        return True, response.get("status", "ok"), response
    except error.URLError as exc:
        return False, f"upload failed: {exc}", {}
    except Exception as exc:
        return False, f"upload failed: {type(exc).__name__}: {exc}", {}


def register_task(base_url: str, payload: dict, timeout: int = 15) -> tuple[bool, dict | str]:
    return safe_fetch_or_post("POST", f"{base_url}/api/tasks/register", payload, timeout)


def publish_event(base_url: str, payload: dict, timeout: int = 15) -> tuple[bool, dict | str]:
    return safe_fetch_or_post("POST", f"{base_url}/api/events", payload, timeout)


def safe_fetch_or_post(method: str, url: str, payload: dict | None = None, timeout: int = 15) -> tuple[bool, dict | str]:
    try:
        if method.upper() == "POST":
            return True, post_json(url, payload or {}, timeout=timeout)
        return True, fetch_json(url, timeout=timeout)
    except error.URLError as exc:
        return False, f"request failed: {exc}"
    except Exception as exc:
        return False, f"request failed: {type(exc).__name__}: {exc}"
