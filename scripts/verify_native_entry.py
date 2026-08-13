#!/usr/bin/env python3
"""Build and verify SimAnt's source-bound Mac68k native slice."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORT_FORGE = ROOT / "port_forge"
LIFT_PLAN = ROOT / "artifacts" / "analysis" / "mac_static_lift_plan.json"
SELECTION = ROOT / "recovery" / "native-selection.json"
GENERATOR = ROOT / "scripts" / "generate_native.py"
SOURCE = ROOT / "tests" / "native_entry_units.cpp"
OUTPUT = ROOT / "build" / "native_entry_units.exe"
REPORT = ROOT / "recovery" / "native-function-conformance.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source_binding() -> None:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    expected = {
        "mac.code.1.4": ["00000312"],
        "mac.code.2.2906": [
            "4e560000",
            "206e0008",
            "20280002",
            "4e5e",
            "4e75",
        ],
    }
    for identity, encodings in expected.items():
        record = next(
            (
                item
                for item in selection.get("functions", [])
                if item.get("code_identity") == identity
            ),
            None,
        )
        if record is None:
            raise RuntimeError(f"selected function disappeared: {identity}")
        if [item.get("bytes") for item in record.get("source_instructions", [])] != encodings:
            raise RuntimeError(f"selected source certificate changed: {identity}")

    if not LIFT_PLAN.is_file():
        return
    if sha256_file(LIFT_PLAN) != selection.get("lift_plan_sha256"):
        raise RuntimeError("retained Mac lift plan does not match native selection")
    plan = json.loads(LIFT_PLAN.read_text(encoding="utf-8"))
    if plan.get("format") != "portforge-mac68k-lift-plan-v1":
        raise RuntimeError("native entry test requires the current Mac lift plan")
    all_instructions = [
        instruction
        for segment in plan.get("segments", [])
        for instruction in segment.get("instructions", [])
    ]
    for identity, encodings in expected.items():
        prefix = identity.rsplit(".", 1)[0] + "."
        resource_id = int(identity.split(".")[2])
        start = int(identity.split(".")[3])
        function = next(
            (
                item
                for item in plan.get("functions", [])
                if item.get("code_identity") == identity
            ),
            None,
        )
        if function is None:
            raise RuntimeError(f"selected function disappeared: {identity}")
        matches = sorted(
            (
                item
                for item in all_instructions
                if item.get("code_identity", "").startswith(prefix)
                and int(item["code_identity"].rsplit(".", 1)[1]) >= start
                and int(item["code_identity"].rsplit(".", 1)[1])
                < function["end_resource_offset"]
                and int(item["code_identity"].split(".")[2]) == resource_id
            ),
            key=lambda item: item["resource_offset"],
        )
        if [item.get("bytes") for item in matches] != encodings:
            raise RuntimeError(f"selected source changed: {identity}")


def load_build_module():
    sys.path.insert(0, str(PORT_FORGE))
    spec = importlib.util.spec_from_file_location(
        "portforge_build", PORT_FORGE / "build.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PortForge build support")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    verify_source_binding()
    subprocess.run(
        [sys.executable, str(GENERATOR)], cwd=ROOT, check=True
    )
    build = load_build_module()
    command = [
        build.CXX,
        *build.CXXFLAGS,
        str(SOURCE),
        "-o",
        str(OUTPUT),
    ]
    build.ensure(
        OUTPUT,
        command,
        explicit_inputs=(SELECTION, GENERATOR),
    )
    result = subprocess.run(
        [str(OUTPUT)], cwd=ROOT, check=True, capture_output=True, text=True
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    match = re.search(
        r"passed \((\d+) instruction cases, (\d+) function cases, "
        r"poison/source guards\)",
        result.stdout,
    )
    if match is None:
        raise RuntimeError("native parity test did not publish its case totals")
    report = {
        "format": "simant-mac-native-function-conformance-v1",
        "result": "passed",
        "source": {
            "lift_plan": "artifacts/analysis/mac_static_lift_plan.json",
            "lift_plan_sha256": json.loads(
                SELECTION.read_text(encoding="utf-8")
            )["lift_plan_sha256"],
            "native_selection": "recovery/native-selection.json",
            "native_selection_sha256": sha256_file(SELECTION),
            "generated_header": "native/simant_mac_generated.hpp",
            "generated_header_sha256": sha256_file(
                ROOT / "native" / "simant_mac_generated.hpp"
            ),
        },
        "oracle_cases": {
            "instruction": int(match.group(1)),
            "linear_function": int(match.group(2)),
        },
        "guards": {
            "exact_source_mutation": "passed",
            "wrong_field_offset": "passed",
            "wrong_endianness": "passed",
        },
        "verified_identities": ["mac.code.1.4", "mac.code.2.2906"],
    }
    REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"native conformance report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
