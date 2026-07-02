import os
import subprocess


def run_burnintest(cfg_filename: str, duration_minutes: int) -> dict:
    bit_exe = r"X:\burnintest\bit.exe"
    bit_cfg = os.path.join(r"X:\burnintest", cfg_filename)

    if not os.path.exists(bit_exe):
        return {"status": "SKIP", "detail": "BurnInTest not found"}
    if not os.path.exists(bit_cfg):
        return {"status": "SKIP", "detail": f"Config file not found: {cfg_filename}"}

    try:
        proc = subprocess.run(
            [bit_exe, "-R", "-C", bit_cfg, "-D", str(duration_minutes), "-P"],
            capture_output=True,
            text=True,
            timeout=(duration_minutes * 60) + 300,
        )
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "detail": "BurnInTest timed out"}
    except Exception as exc:
        return {"status": "FAIL", "detail": f"BurnInTest launch failed: {type(exc).__name__}: {exc}"}

    if proc.returncode == 0:
        return {"status": "PASS", "detail": f"BurnInTest passed ({duration_minutes} min)"}
    return {
        "status": "FAIL",
        "detail": f"BurnInTest failed (rc={proc.returncode})",
        "stdout_tail": proc.stdout[-500:],
        "stderr_tail": proc.stderr[-500:],
    }
