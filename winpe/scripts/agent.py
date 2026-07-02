import json
from datetime import datetime
from pathlib import Path

from hardware_probe import (
    compare_against_spec,
    get_cpu_info,
    get_disk_info,
    get_identity,
    get_memory_info,
    identify_model,
    summarize_failure,
)
from run_bit import run_burnintest
from spec_client import fetch_json, load_local_json, safe_post_json


CONTROLLER_BASE_URL = "http://192.168.10.1:8080"
MODEL_SPECS_URL = f"{CONTROLLER_BASE_URL}/api/specs/model_specs"
RESULTS_POST_URL = f"{CONTROLLER_BASE_URL}/api/results"
LOCAL_IDENTITY_RULES = Path(r"X:\scripts\model_identity_rules.json")
LOCAL_OUTPUT_DIR = Path(r"X:\\")


def write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def build_final_result(
    sn: str,
    model_code: str,
    hardware_identity: dict,
    hardware_check_result: dict,
    burnin_started: bool,
    burnin_profile: dict,
    burnin_result: dict,
    overall_result: str,
    failure_reason: str,
    start_time: str,
    end_time: str,
) -> dict:
    return {
        "sn": sn,
        "model_code": model_code,
        "hardware_identity": hardware_identity,
        "hardware_check_result": hardware_check_result,
        "burnin_started": burnin_started,
        "burnin_profile": burnin_profile,
        "burnin_result": burnin_result,
        "overall_result": overall_result,
        "failure_reason": failure_reason,
        "result_upload": {"status": "PENDING", "detail": ""},
        "start_time": start_time,
        "end_time": end_time,
    }


def main() -> None:
    start_time = datetime.now().isoformat()
    print("=" * 60)
    print("Phase 1 hardware validation agent starting...")
    print("=" * 60)

    identity = get_identity()
    sn = identity.get("bios_serial_number", "UNKNOWN_SN")
    print(f"[IDENT] SN: {sn}")

    if not LOCAL_IDENTITY_RULES.exists():
        raise FileNotFoundError(f"Local identity rules not found: {LOCAL_IDENTITY_RULES}")

    identity_rules = load_local_json(LOCAL_IDENTITY_RULES)
    model_code = identify_model(identity, identity_rules)
    print(f"[IDENT] model_code: {model_code}")

    specs = fetch_json(MODEL_SPECS_URL)
    model_spec = specs.get("models", {}).get(model_code)
    if not model_spec:
        hardware_check = {
            "cpu": {"status": "SKIP", "matches_spec": False},
            "memory": {"status": "SKIP", "matches_spec": False},
            "disk": {"status": "SKIP", "matches_spec": False},
            "overall_match": False,
        }
        final_result = build_final_result(
            sn=sn,
            model_code=model_code,
            hardware_identity=identity,
            hardware_check_result=hardware_check,
            burnin_started=False,
            burnin_profile={},
            burnin_result={"status": "SKIP", "detail": "Model spec not found"},
            overall_result="FAIL",
            failure_reason="model spec not found",
            start_time=start_time,
            end_time=datetime.now().isoformat(),
        )
        ok, detail = safe_post_json(RESULTS_POST_URL, final_result)
        final_result["result_upload"] = {"status": "SUCCESS" if ok else "FAIL", "detail": detail}
        write_json(LOCAL_OUTPUT_DIR / f"final_result_{sn}.json", final_result)
        return

    cpu_info = get_cpu_info()
    memory_info = get_memory_info()
    disk_info = get_disk_info()
    hardware_check = compare_against_spec(cpu_info, memory_info, disk_info, model_spec)

    hardware_check_payload = {
        "sn": sn,
        "model_code": model_code,
        "hardware_identity": identity,
        "hardware_check_result": hardware_check,
        "checked_at": datetime.now().isoformat(),
    }
    write_json(LOCAL_OUTPUT_DIR / f"hardware_check_{sn}.json", hardware_check_payload)

    burnin_started = False
    burnin_profile = model_spec.get("burnin_profile", {})
    burnin_result = {"status": "SKIP", "detail": "Not started"}
    failure_reason = ""
    overall_result = "PASS"

    if not hardware_check.get("overall_match", False):
        overall_result = "FAIL"
        failure_reason = f"hardware spec mismatch: {summarize_failure(hardware_check)}"
        print(f"[CHECK] mismatch detected: {failure_reason}")
    else:
        cfg_file = burnin_profile.get("cfg_file", "")
        duration_minutes = int(burnin_profile.get("duration_minutes", 0))
        burnin_started = True
        print(f"[BURNIN] starting profile={burnin_profile.get('name', '')}, duration={duration_minutes} min")
        burnin_result = run_burnintest(cfg_file, duration_minutes)
        if burnin_result.get("status") != "PASS":
            overall_result = "FAIL"
            failure_reason = burnin_result.get("detail", "burn-in failed")

    end_time = datetime.now().isoformat()
    final_result = build_final_result(
        sn=sn,
        model_code=model_code,
        hardware_identity=identity,
        hardware_check_result=hardware_check,
        burnin_started=burnin_started,
        burnin_profile=burnin_profile,
        burnin_result=burnin_result,
        overall_result=overall_result,
        failure_reason=failure_reason,
        start_time=start_time,
        end_time=end_time,
    )

    ok, detail = safe_post_json(RESULTS_POST_URL, final_result)
    final_result["result_upload"] = {"status": "SUCCESS" if ok else "FAIL", "detail": detail}
    write_json(LOCAL_OUTPUT_DIR / f"final_result_{sn}.json", final_result)

    print(f"[RESULT] overall={overall_result}")
    print(f"[UPLOAD] {final_result['result_upload']['status']} - {final_result['result_upload']['detail']}")


if __name__ == "__main__":
    main()
