import json
import os
import socket
from datetime import datetime
from pathlib import Path

from hardware_probe import (
    attempt_serial_loopback,
    compare_against_spec,
    evaluate_lan_check,
    get_cpu_info,
    get_disk_info,
    get_identity,
    get_memory_info,
    get_network_info,
    get_runtime_telemetry,
    get_serial_port_info,
    summarize_failure,
)
from run_bit import launch_burnintest, wait_for_burnintest
from spec_client import publish_event, register_task


CONTROLLER_BASE_URL = "http://192.168.10.1:8080"
LOCAL_OUTPUT_DIR = Path(r"X:\\")
STATION_ID = os.environ.get("FACTORY_STATION_ID") or socket.gethostname().upper()
TELEMETRY_INTERVAL_SECONDS = 60


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def build_capabilities() -> dict:
    try:
        import serial  # type: ignore

        serial_available = True
    except Exception:
        serial_available = False

    return {
        "inventory_check": True,
        "lan_check": True,
        "serial_loopback_check": serial_available,
        "burnin_check": True,
        "usb_check": False,
        "display_check": False,
        "io_check": False,
    }


def publish_task_message(task: dict, channel: str, event_type: str, test_item: str, status: str, payload: dict) -> tuple[bool, str]:
    message = {
        "channel": channel,
        "task_id": task["task_id"],
        "sn": task["sn"],
        "station_id": task["station_id"],
        "model_code": task["model_code"],
        "event_type": event_type,
        "test_item": test_item,
        "status": status,
        "timestamp": now_iso(),
        "payload": payload,
    }
    ok, response = publish_event(CONTROLLER_BASE_URL, message)
    return ok, response if isinstance(response, str) else response.get("status", "ok")


def build_final_result(task: dict, hardware_identity: dict, test_results: dict, failure_reason: str) -> dict:
    overall_result = "PASS"
    for item_result in test_results.values():
        if item_result.get("status") == "FAIL":
            overall_result = "FAIL"
            break

    return {
        "task_id": task["task_id"],
        "station_id": task["station_id"],
        "sn": task["sn"],
        "model_code": task["model_code"],
        "hardware_identity": hardware_identity,
        "test_results": test_results,
        "overall_result": overall_result,
        "failure_reason": failure_reason,
        "started_at": task.get("created_at", now_iso()),
        "ended_at": now_iso(),
    }


def run_inventory_check(task: dict, plan: dict) -> tuple[dict, bool]:
    cpu_info = get_cpu_info()
    memory_info = get_memory_info()
    disk_info = get_disk_info()
    hardware_check = compare_against_spec(cpu_info, memory_info, disk_info, plan)
    if plan.get("config_status") != "configured":
        detail = "model configuration pending"
        status = "FAIL"
        matches = False
    else:
        detail = summarize_failure(hardware_check)
        status = "PASS" if hardware_check.get("overall_match", False) else "FAIL"
        matches = hardware_check.get("overall_match", False)
    result = {
        "status": status,
        "payload": {
            "hardware_check_result": hardware_check,
            "detail": detail,
            "config_status": plan.get("config_status", "pending"),
        },
    }
    write_json(LOCAL_OUTPUT_DIR / f"inventory_check_{task['sn']}.json", result["payload"])
    return result, matches


def run_lan_check(plan: dict) -> tuple[dict, bool]:
    network_info = get_network_info()
    result_payload = evaluate_lan_check(network_info, plan.get("lan_check", {}))
    return {"status": result_payload["status"], "payload": result_payload}, result_payload.get("matches_spec", False)


def run_serial_check(plan: dict) -> tuple[dict, bool]:
    serial_info = get_serial_port_info()
    result_payload = attempt_serial_loopback(serial_info, plan.get("serial_loopback_check", {}))
    status = result_payload.get("status", "FAIL")
    matches = result_payload.get("matches_spec", False)
    if status == "SKIP":
        matches = True
    return {"status": status, "payload": result_payload}, matches


def run_placeholder_check(name: str) -> dict:
    return {
        "status": "SKIP",
        "payload": {
            "detail": f"{name} is reserved for a future fixture-based implementation",
            "placeholder_only": True,
        },
    }


def run_burnin_check(task: dict, plan: dict) -> tuple[dict, bool]:
    burnin_profile = plan.get("burnin_profile", {})
    cfg_file = burnin_profile.get("cfg_file", "")
    duration_minutes = int(burnin_profile.get("duration_minutes", 0))

    ok, launch_result = launch_burnintest(cfg_file, duration_minutes)
    if not ok:
        return {"status": launch_result["status"], "payload": launch_result}, launch_result["status"] == "PASS"

    def on_tick(elapsed_seconds: int) -> None:
        publish_task_message(
            task,
            channel="telemetry",
            event_type="burnin_heartbeat",
            test_item="burnin_check",
            status="RUNNING",
            payload={
                "elapsed_seconds": elapsed_seconds,
                "duration_minutes": duration_minutes,
                "runtime_telemetry": get_runtime_telemetry(),
            },
        )

    publish_task_message(
        task,
        channel="event",
        event_type="burnin_started",
        test_item="burnin_check",
        status="RUNNING",
        payload={"cfg_file": cfg_file, "duration_minutes": duration_minutes},
    )
    final = wait_for_burnintest(
        launch_result["process"],
        duration_minutes,
        poll_interval_seconds=TELEMETRY_INTERVAL_SECONDS,
        on_tick=on_tick,
    )
    return {"status": final["status"], "payload": final}, final["status"] == "PASS"


def main() -> None:
    start_time = now_iso()
    print("=" * 60)
    print("Phase 1 production-test agent starting...")
    print("=" * 60)

    identity = get_identity()
    sn = identity.get("bios_serial_number", "UNKNOWN_SN")
    registration_payload = {
        "sn": sn,
        "station_id": STATION_ID,
        "hardware_identity": identity,
        "capabilities": build_capabilities(),
    }
    ok, task_response = register_task(CONTROLLER_BASE_URL, registration_payload)
    if not ok or not isinstance(task_response, dict):
        raise RuntimeError(f"Task registration failed: {task_response}")

    task = task_response
    plan = task.get("test_plan", {})
    task["sn"] = sn
    print(f"[TASK] task_id={task['task_id']} sn={sn} model_code={task.get('model_code', '')}")

    publish_task_message(
        task,
        channel="lifecycle",
        event_type="agent_started",
        test_item="bootstrap",
        status="running",
        payload={"started_at": start_time},
    )

    test_results = {}
    failure_reason = ""
    mandatory_ok = True

    checks = [
        ("inventory_check", lambda: run_inventory_check(task, plan), True),
        ("lan_check", lambda: run_lan_check(plan), True),
        ("serial_loopback_check", lambda: run_serial_check(plan), True),
        ("usb_check", lambda: (run_placeholder_check("usb_check"), True), False),
        ("display_check", lambda: (run_placeholder_check("display_check"), True), False),
        ("io_check", lambda: (run_placeholder_check("io_check"), True), False),
    ]

    for name, runner, blocking in checks:
        test_item_cfg = plan.get("test_items", {}).get(name, {})
        if not test_item_cfg.get("enabled", False):
            skipped = run_placeholder_check(name)
            test_results[name] = skipped
            publish_task_message(task, "event", "test_skipped", name, skipped["status"], skipped["payload"])
            continue

        publish_task_message(task, "event", "test_started", name, "RUNNING", {"blocking": blocking})
        result, passed = runner()
        test_results[name] = result
        publish_task_message(task, "event", "test_finished", name, result["status"], result["payload"])
        if blocking and not passed:
            mandatory_ok = False
            failure_reason = result["payload"].get("detail", "") or failure_reason or name
            break

    burnin_cfg = plan.get("test_items", {}).get("burnin_check", {"enabled": True})
    if mandatory_ok and burnin_cfg.get("enabled", True):
        result, passed = run_burnin_check(task, plan)
        test_results["burnin_check"] = result
        publish_task_message(task, "event", "test_finished", "burnin_check", result["status"], result["payload"])
        if not passed:
            failure_reason = result["payload"].get("detail", "") or "burnin_check failed"
    else:
        test_results["burnin_check"] = {
            "status": "SKIP",
            "payload": {"detail": "Skipped because a blocking test failed earlier"},
        }
        publish_task_message(task, "event", "test_skipped", "burnin_check", "SKIP", test_results["burnin_check"]["payload"])

    if not failure_reason:
        for name, result in test_results.items():
            if result.get("status") == "FAIL":
                failure_reason = result.get("payload", {}).get("detail", name)
                break

    final_result = build_final_result(task, identity, test_results, failure_reason)
    write_json(LOCAL_OUTPUT_DIR / f"final_result_{sn}.json", final_result)
    publish_task_message(
        task,
        channel="result",
        event_type="task_finished",
        test_item="final_result",
        status=final_result["overall_result"],
        payload=final_result,
    )
    print(f"[RESULT] overall={final_result['overall_result']}")


if __name__ == "__main__":
    main()
