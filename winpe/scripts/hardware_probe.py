import re
import subprocess


def run_wmic(args: list[str], timeout: int = 15) -> str:
    result = subprocess.run(
        ["wmic", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout.strip()


def clean_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def parse_key_value_block(raw: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in clean_lines(raw):
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def parse_csv_rows(raw: str) -> list[dict[str, str]]:
    lines = clean_lines(raw)
    if len(lines) < 2:
        return []
    headers = [item.strip() for item in lines[0].split(",")]
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = [item.strip() for item in line.split(",")]
        if len(parts) < len(headers):
            parts += [""] * (len(headers) - len(parts))
        rows.append(dict(zip(headers, parts)))
    return rows


def get_identity() -> dict:
    bios = parse_key_value_block(run_wmic(["bios", "get", "SerialNumber", "/value"]))
    system = parse_key_value_block(
        run_wmic(["computersystem", "get", "Manufacturer,Model", "/value"])
    )
    baseboard = parse_key_value_block(
        run_wmic(["baseboard", "get", "Product,SerialNumber,Manufacturer", "/value"])
    )
    csproduct = parse_key_value_block(
        run_wmic(["csproduct", "get", "Name,Vendor,IdentifyingNumber", "/value"])
    )
    return {
        "bios_serial_number": bios.get("SerialNumber", "UNKNOWN"),
        "product_name": csproduct.get("Name") or system.get("Model", "UNKNOWN"),
        "manufacturer": csproduct.get("Vendor") or system.get("Manufacturer", "UNKNOWN"),
        "baseboard_product": baseboard.get("Product", "UNKNOWN"),
        "baseboard_serial": baseboard.get("SerialNumber", "UNKNOWN"),
        "baseboard_manufacturer": baseboard.get("Manufacturer", "UNKNOWN"),
        "identifying_number": csproduct.get("IdentifyingNumber", ""),
    }


def get_cpu_info() -> dict:
    rows = parse_csv_rows(run_wmic(["cpu", "get", "Name,NumberOfCores,Status", "/format:csv"]))
    if not rows:
        return {"detected_name": "", "core_count": 0, "status": "FAIL", "health_status": "UNKNOWN"}
    row = rows[-1]
    name = row.get("Name", "")
    status = row.get("Status", "")
    return {
        "detected_name": name,
        "core_count": int(row.get("NumberOfCores", "0") or 0),
        "status": "PASS" if name else "FAIL",
        "health_status": status or "UNKNOWN",
    }


def get_memory_info() -> dict:
    rows = parse_csv_rows(
        run_wmic(["memorychip", "get", "Capacity,DeviceLocator,PartNumber,Status", "/format:csv"])
    )
    total_bytes = 0
    modules = []
    status_values = []
    for row in rows:
        capacity_raw = row.get("Capacity", "").strip()
        if capacity_raw.isdigit():
            total_bytes += int(capacity_raw)
        modules.append(
            {
                "device_locator": row.get("DeviceLocator", ""),
                "part_number": row.get("PartNumber", ""),
                "capacity_bytes": int(capacity_raw) if capacity_raw.isdigit() else 0,
                "status": row.get("Status", "") or "UNKNOWN",
            }
        )
        if row.get("Status"):
            status_values.append(row["Status"])

    total_gb = round(total_bytes / (1024 ** 3), 2)
    health_ok = all(value.upper() in {"OK", "UNKNOWN"} for value in status_values) if status_values else True
    return {
        "total_gb": total_gb,
        "module_count": len(modules),
        "modules": modules,
        "status": "PASS" if total_gb > 0 else "FAIL",
        "health_status": "OK" if health_ok else "WARN",
    }


def get_disk_info() -> dict:
    rows = parse_csv_rows(run_wmic(["diskdrive", "get", "Model,Size,Status", "/format:csv"]))
    drives = []
    statuses = []
    for row in rows:
        model = row.get("Model", "")
        size_raw = row.get("Size", "").strip()
        size_gb = round(int(size_raw) / (1024 ** 3), 2) if size_raw.isdigit() else 0
        status = row.get("Status", "") or "UNKNOWN"
        drives.append({"model": model, "size_gb": size_gb, "status": status})
        statuses.append(status)

    overall_ok = all(value.upper() in {"OK", "UNKNOWN"} for value in statuses) if statuses else False
    return {
        "drives": drives,
        "status": "PASS" if drives else "FAIL",
        "health_status": "OK" if overall_ok else "WARN" if drives else "UNKNOWN",
    }


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


def cpu_matches(cpu_name: str, cpu_rule: dict) -> bool:
    if not cpu_name:
        return False
    if cpu_rule.get("match_type") == "contains_any":
        upper_name = cpu_name.upper()
        return any(keyword.upper() in upper_name for keyword in cpu_rule.get("keywords", []))
    return False


def disk_matches(drives: list[dict], spec: dict) -> bool:
    if not drives:
        return False
    keywords = [item.upper() for item in spec.get("disk_model_keywords", [])]
    min_capacity = spec.get("disk_min_capacity_gb", 0)

    for drive in drives:
        model = (drive.get("model") or "").upper()
        size_gb = drive.get("size_gb", 0)
        keyword_ok = True if not keywords else any(keyword in model for keyword in keywords)
        size_ok = size_gb >= min_capacity
        if keyword_ok and size_ok:
            return True
    return False


def compare_against_spec(cpu_info: dict, memory_info: dict, disk_info: dict, spec: dict) -> dict:
    cpu_ok = cpu_matches(cpu_info.get("detected_name", ""), spec.get("cpu_match_rule", {}))
    memory_min = spec.get("memory_min_gb", 0)
    memory_expected = spec.get("memory_expected_gb", 0)
    actual_memory = memory_info.get("total_gb", 0)
    memory_ok = actual_memory >= memory_min and (memory_expected == 0 or actual_memory >= memory_expected)
    disk_ok = disk_matches(disk_info.get("drives", []), spec)

    cpu_result = dict(cpu_info)
    cpu_result["matches_spec"] = cpu_ok
    memory_result = dict(memory_info)
    memory_result["matches_spec"] = memory_ok
    memory_result["expected_gb"] = memory_expected
    memory_result["min_gb"] = memory_min
    disk_result = dict(disk_info)
    disk_result["matches_spec"] = disk_ok

    overall = cpu_ok and memory_ok and disk_ok
    return {
        "cpu": cpu_result,
        "memory": memory_result,
        "disk": disk_result,
        "overall_match": overall,
    }


def summarize_failure(result: dict) -> str:
    failures = []
    for name in ("cpu", "memory", "disk"):
        if not result.get(name, {}).get("matches_spec", False):
            failures.append(name)
    return ", ".join(failures) if failures else ""
