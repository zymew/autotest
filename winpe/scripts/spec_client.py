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


def safe_post_json(url: str, payload: dict, timeout: int = 15) -> tuple[bool, str]:
    try:
        response = post_json(url, payload, timeout=timeout)
        return True, response.get("status", "ok")
    except error.URLError as exc:
        return False, f"upload failed: {exc}"
    except Exception as exc:
        return False, f"upload failed: {type(exc).__name__}: {exc}"
