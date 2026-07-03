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


def safe_int(raw: str, default: int = 0) -> int:
    stripped = (raw or "").strip()
    return int(stripped) if stripped.isdigit() else default


def safe_float(raw: str, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


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
    rows = parse_csv_rows(run_wmic(["cpu", "get", "Name,NumberOfCores,Status,LoadPercentage", "/format:csv"]))
    if not rows:
        return {
            "detected_name": "",
            "core_count": 0,
            "status": "FAIL",
            "health_status": "UNKNOWN",
            "load_percentage": 0,
        }
    row = rows[-1]
    name = row.get("Name", "")
    status = row.get("Status", "")
    return {
        "detected_name": name,
        "core_count": safe_int(row.get("NumberOfCores", "0")),
        "status": "PASS" if name else "FAIL",
        "health_status": status or "UNKNOWN",
        "load_percentage": safe_int(row.get("LoadPercentage", "0")),
    }


def get_memory_info() -> dict:
    rows = parse_csv_rows(
        run_wmic(["memorychip", "get", "Capacity,DeviceLocator,PartNumber,Manufacturer,Status", "/format:csv"])
    )
    total_bytes = 0
    modules = []
    status_values = []
    vendors = set()
    for row in rows:
        capacity_raw = row.get("Capacity", "").strip()
        if capacity_raw.isdigit():
            total_bytes += int(capacity_raw)
        vendor = row.get("Manufacturer", "").strip()
        if vendor:
            vendors.add(vendor)
        modules.append(
            {
                "device_locator": row.get("DeviceLocator", ""),
                "part_number": row.get("PartNumber", ""),
                "manufacturer": vendor,
                "capacity_bytes": int(capacity_raw) if capacity_raw.isdigit() else 0,
                "status": row.get("Status", "") or "UNKNOWN",
            }
        )
        if row.get("Status"):
            status_values.append(row["Status"])

    total_gb = round(total_bytes / (1024**3), 2)
    health_ok = all(value.upper() in {"OK", "UNKNOWN"} for value in status_values) if status_values else True
    return {
        "total_gb": total_gb,
        "module_count": len(modules),
        "modules": modules,
        "vendors": sorted(vendors),
        "status": "PASS" if total_gb > 0 else "FAIL",
        "health_status": "OK" if health_ok else "WARN",
    }


def get_disk_info() -> dict:
    rows = parse_csv_rows(run_wmic(["diskdrive", "get", "Model,Size,Status,SerialNumber", "/format:csv"]))
    drives = []
    statuses = []
    vendors = set()
    for row in rows:
        model = row.get("Model", "")
        size_raw = row.get("Size", "").strip()
        size_gb = round(int(size_raw) / (1024**3), 2) if size_raw.isdigit() else 0
        status = row.get("Status", "") or "UNKNOWN"
        serial_number = row.get("SerialNumber", "")
        if model:
            vendors.add(model.split(" ", 1)[0].upper())
        drives.append({"model": model, "size_gb": size_gb, "serial_number": serial_number, "status": status})
        statuses.append(status)

    overall_ok = all(value.upper() in {"OK", "UNKNOWN"} for value in statuses) if statuses else False
    return {
        "drives": drives,
        "vendors": sorted(vendors),
        "status": "PASS" if drives else "FAIL",
        "health_status": "OK" if overall_ok else "WARN" if drives else "UNKNOWN",
    }


def get_network_info() -> dict:
    rows = parse_csv_rows(
        run_wmic(
            [
                "nic",
                "where",
                "PhysicalAdapter=True",
                "get",
                "Name,NetConnectionStatus,Speed,MACAddress,Manufacturer,NetEnabled",
                "/format:csv",
            ]
        )
    )
    adapters = []
    for row in rows:
        speed_raw = row.get("Speed", "").strip()
        speed_bps = safe_int(speed_raw)
        speed_mbps = round(speed_bps / 1_000_000) if speed_bps else 0
        link_status = row.get("NetConnectionStatus", "")
        enabled = (row.get("NetEnabled", "") or "").upper() == "TRUE"
        is_linked = link_status == "2" or speed_mbps > 0
        adapters.append(
            {
                "name": row.get("Name", ""),
                "mac_address": row.get("MACAddress", ""),
                "manufacturer": row.get("Manufacturer", ""),
                "speed_mbps": speed_mbps,
                "net_enabled": enabled,
                "link_status_code": link_status,
                "linked": is_linked,
            }
        )
    linked_count = len([item for item in adapters if item["linked"]])
    return {
        "adapters": adapters,
        "adapter_count": len(adapters),
        "linked_count": linked_count,
        "status": "PASS" if adapters else "FAIL",
    }


def get_serial_port_info() -> dict:
    rows = parse_csv_rows(run_wmic(["path", "Win32_SerialPort", "get", "DeviceID,Description,PNPDeviceID", "/format:csv"]))
    ports = []
    for row in rows:
        device_id = row.get("DeviceID", "")
        ports.append(
            {
                "device_id": device_id,
                "description": row.get("Description", ""),
                "pnp_device_id": row.get("PNPDeviceID", ""),
            }
        )
    return {
        "ports": ports,
        "port_count": len(ports),
        "status": "PASS" if ports else "FAIL",
    }


def get_runtime_telemetry() -> dict:
    cpu = get_cpu_info()
    network = get_network_info()
    temperature_c = []
    try:
        rows = parse_csv_rows(
            run_wmic(
                [
                    "/namespace:\\\\root\\wmi",
                    "PATH",
                    "MSAcpi_ThermalZoneTemperature",
                    "get",
                    "CurrentTemperature,InstanceName",
                    "/format:csv",
                ],
                timeout=10,
            )
        )
        for row in rows:
            raw_value = safe_float(row.get("CurrentTemperature"))
            if raw_value > 0:
                temperature_c.append(round((raw_value / 10.0) - 273.15, 2))
    except Exception:
        temperature_c = []

    return {
        "cpu_load_percentage": cpu.get("load_percentage", 0),
        "linked_network_ports": network.get("linked_count", 0),
        "max_link_speed_mbps": max([item.get("speed_mbps", 0) for item in network.get("adapters", [])] or [0]),
        "thermal_zone_celsius": temperature_c,
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


def contains_any(source: str, keywords: list[str]) -> bool:
    source_upper = (source or "").upper()
    return any(keyword.upper() in source_upper for keyword in keywords)


def cpu_matches(cpu_name: str, cpu_rule: dict) -> bool:
    if not cpu_name:
        return False
    if cpu_rule.get("match_type") == "contains_any":
        return contains_any(cpu_name, cpu_rule.get("keywords", []))
    return False


def vendor_keywords_match(values: list[str], keywords: list[str]) -> bool:
    if not keywords:
        return True
    upper_values = [value.upper() for value in values]
    upper_keywords = [keyword.upper() for keyword in keywords]
    return any(keyword in value for value in upper_values for keyword in upper_keywords)


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

    memory_brand_keywords = spec.get("memory_vendor_keywords", [])
    if memory_brand_keywords:
        memory_ok = memory_ok and vendor_keywords_match(memory_info.get("vendors", []), memory_brand_keywords)

    disk_ok = disk_matches(disk_info.get("drives", []), spec)

    cpu_result = dict(cpu_info)
    cpu_result["matches_spec"] = cpu_ok
    memory_result = dict(memory_info)
    memory_result["matches_spec"] = memory_ok
    memory_result["expected_gb"] = memory_expected
    memory_result["min_gb"] = memory_min
    memory_result["vendor_keywords"] = memory_brand_keywords
    disk_result = dict(disk_info)
    disk_result["matches_spec"] = disk_ok

    overall = cpu_ok and memory_ok and disk_ok
    return {
        "cpu": cpu_result,
        "memory": memory_result,
        "disk": disk_result,
        "overall_match": overall,
    }


def evaluate_lan_check(network_info: dict, lan_spec: dict) -> dict:
    required_linked_ports = int(lan_spec.get("required_linked_ports", 1))
    min_speed_mbps = int(lan_spec.get("min_speed_mbps", 1000))
    linked_adapters = [item for item in network_info.get("adapters", []) if item.get("linked")]
    passing_adapters = [item for item in linked_adapters if item.get("speed_mbps", 0) >= min_speed_mbps]
    overall = len(passing_adapters) >= required_linked_ports
    return {
        "status": "PASS" if overall else "FAIL",
        "required_linked_ports": required_linked_ports,
        "min_speed_mbps": min_speed_mbps,
        "linked_adapters": linked_adapters,
        "passing_adapters": passing_adapters,
        "matches_spec": overall,
    }


def evaluate_serial_presence(serial_info: dict, serial_spec: dict) -> dict:
    required_ports = int(serial_spec.get("required_ports", 1))
    available_ports = serial_info.get("ports", [])
    overall = len(available_ports) >= required_ports
    return {
        "status": "PASS" if overall else "FAIL",
        "required_ports": required_ports,
        "available_ports": available_ports,
        "matches_spec": overall,
        "detail": "" if overall else f"expected at least {required_ports} serial ports",
    }


def attempt_serial_loopback(serial_info: dict, serial_spec: dict) -> dict:
    presence_result = evaluate_serial_presence(serial_info, serial_spec)
    if not presence_result["matches_spec"]:
        return presence_result

    try:
        import serial  # type: ignore
    except Exception:
        presence_result["status"] = "SKIP"
        presence_result["matches_spec"] = True
        presence_result["detail"] = "pyserial not installed, loopback skipped"
        return presence_result

    expected_payload = (serial_spec.get("loopback_payload") or "FACTORY_LOOPBACK").encode("utf-8")
    baudrate = int(serial_spec.get("baudrate", 115200))
    timeout_seconds = safe_float(serial_spec.get("timeout_seconds", 2), 2.0)
    loopback_ports = [item["device_id"] for item in serial_info.get("ports", [])[: int(serial_spec.get("required_ports", 1))]]
    failures = []
    passed_ports = []

    for port in loopback_ports:
        try:
            with serial.Serial(port=port, baudrate=baudrate, timeout=timeout_seconds, write_timeout=timeout_seconds) as handle:
                handle.reset_input_buffer()
                handle.reset_output_buffer()
                handle.write(expected_payload)
                handle.flush()
                readback = handle.read(len(expected_payload))
                if readback != expected_payload:
                    failures.append({"port": port, "readback": readback.decode("utf-8", errors="replace")})
                else:
                    passed_ports.append(port)
        except Exception as exc:
            failures.append({"port": port, "error": f"{type(exc).__name__}: {exc}"})

    overall = not failures and len(passed_ports) == len(loopback_ports)
    return {
        "status": "PASS" if overall else "FAIL",
        "required_ports": int(serial_spec.get("required_ports", 1)),
        "loopback_ports": loopback_ports,
        "passed_ports": passed_ports,
        "failures": failures,
        "matches_spec": overall,
        "detail": "" if overall else "serial loopback mismatch",
    }


def summarize_failure(result: dict) -> str:
    failures = []
    for name in ("cpu", "memory", "disk"):
        if not result.get(name, {}).get("matches_spec", False):
            failures.append(name)
    return ", ".join(failures) if failures else ""
