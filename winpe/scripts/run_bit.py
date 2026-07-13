import os
import subprocess
import time
from typing import Callable


def resolve_burnintest_paths(cfg_filename: str) -> tuple[str, str]:
    bit_exe = r"X:\burnintest\bit.exe"
    bit_cfg = os.path.join(r"X:\burnintest", cfg_filename)
    return bit_exe, bit_cfg


def launch_burnintest(cfg_filename: str, duration_minutes: int) -> tuple[bool, dict]:
    bit_exe, bit_cfg = resolve_burnintest_paths(cfg_filename)
    if not os.path.exists(bit_exe):
        return False, {"status": "SKIP", "detail": "BurnInTest not found"}
    if not os.path.exists(bit_cfg):
        return False, {"status": "SKIP", "detail": f"Config file not found: {cfg_filename}"}

    try:
        proc = subprocess.Popen(
            [bit_exe, "-R", "-C", bit_cfg, "-D", str(duration_minutes), "-P"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:
        return False, {"status": "FAIL", "detail": f"BurnInTest launch failed: {type(exc).__name__}: {exc}"}

    return True, {"process": proc, "cfg_file": cfg_filename, "duration_minutes": duration_minutes}


def wait_for_burnintest(
    process: subprocess.Popen,
    duration_minutes: int,
    poll_interval_seconds: int = 60,
    on_tick: Callable[[int], None] | None = None,
) -> dict:
    timeout_seconds = (duration_minutes * 60) + 300
    start = time.time()
    stdout_tail = ""
    stderr_tail = ""

    while True:
        rc = process.poll()
        elapsed = int(time.time() - start)
        if on_tick:
            on_tick(elapsed)
        if rc is not None:
            stdout, stderr = process.communicate()
            stdout_tail = (stdout or "")[-500:]
            stderr_tail = (stderr or "")[-500:]
            if rc == 0:
                return {"status": "PASS", "detail": f"BurnInTest passed ({duration_minutes} min)"}
            return {
                "status": "FAIL",
                "detail": f"BurnInTest failed (rc={rc})",
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
            }
        if elapsed > timeout_seconds:
            try:
                process.kill()
            except Exception:
                pass
            return {"status": "FAIL", "detail": "BurnInTest timed out"}
        time.sleep(max(1, poll_interval_seconds))


def run_burnintest(cfg_filename: str, duration_minutes: int) -> dict:
    ok, launch_result = launch_burnintest(cfg_filename, duration_minutes)
    if not ok:
        return launch_result
    return wait_for_burnintest(launch_result["process"], duration_minutes)
