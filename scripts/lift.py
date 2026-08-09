#!/usr/bin/env python3
"""Generate SimAnt's stable Macintosh CODE-resource lift plan."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORT_FORGE = PROJECT_ROOT / "port_forge"
DEFAULT_ISO = PROJECT_ROOT / "assets" / "SimAnt_CD.iso"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "artifacts" / "analysis" / "mac_static_lift_plan.json"
)
DEFAULT_SNAPSHOT = (
    PROJECT_ROOT
    / "artifacts"
    / "snapshots"
    / "determinism_30000000"
    / "run_a.pfmacsnapshot"
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Decode SimAnt CODE resources into a stable, source-authenticated "
            "control-flow lift plan."
        )
    )
    result.add_argument("--iso", type=Path, default=DEFAULT_ISO)
    result.add_argument("--creator", default="SANT")
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help="snapshot used to rank dynamically executed exports",
    )
    result.add_argument(
        "--no-snapshot",
        action="store_true",
        help="generate only the static lift plan",
    )
    result.add_argument("--no-build", action="store_true")
    return result


def executed(bitmap: bytes, address: int) -> bool:
    return bool(bitmap[address >> 3] & (1 << (address & 7)))


def attach_dynamic_evidence(plan: dict, snapshot: Path) -> None:
    manifest = json.loads(
        (snapshot / "snapshot.json").read_text(encoding="utf-8")
    )
    if manifest.get("format") not in {
        "portforge-mac68k-diagnostic-snapshot-v2",
        "portforge-mac68k-restorable-snapshot-v2",
    }:
        raise RuntimeError(
            f"unsupported snapshot: {manifest.get('format')}"
        )
    bitmap = (snapshot / manifest["executed_file"]).read_bytes()
    ranges = {
        item["resource_id"]: item for item in manifest["code_ranges"]
    }
    dynamic_traps: dict[str, int] = {}
    for site in manifest["trap_coverage"]:
        dynamic_traps[site["code_identity"]] = site["calls"]

    candidates = []
    for function in plan["functions"]:
        code_range = ranges.get(function["resource_id"])
        if code_range is None:
            continue
        resource_start = function["entry_resource_offset"]
        delta = resource_start - code_range["resource_offset"]
        if delta < 0:
            continue
        runtime_start = code_range["runtime_base"] + delta
        size = min(
            function["byte_span"], code_range["size"] - delta
        )
        if size <= 0 or runtime_start + size > len(bitmap) * 8:
            continue
        executed_bytes = sum(
            executed(bitmap, runtime_start + offset)
            for offset in range(size)
        )
        if not executed_bytes:
            continue
        resource_end = resource_start + size
        observed_trap_calls = sum(
            calls
            for identity, calls in dynamic_traps.items()
            if identity.startswith(
                f"mac.code.{function['resource_id']}."
            )
            and resource_start <= int(identity.rsplit(".", 1)[1])
            < resource_end
        )
        candidate = dict(function)
        candidate.update(
            {
                "executed_bytes": executed_bytes,
                "execution_coverage_percent": (
                    100.0 * executed_bytes / size
                ),
                "observed_trap_calls": observed_trap_calls,
                "native_candidate": (
                    function["direct_trap_sites"] == 0
                    and function["indirect_control_transfers"] == 0
                    and observed_trap_calls == 0
                ),
            }
        )
        candidates.append(candidate)
    candidates.sort(
        key=lambda item: (
            item["native_candidate"],
            item["executed_bytes"],
            item["execution_coverage_percent"],
        ),
        reverse=True,
    )
    plan["simant_dynamic_evidence"] = {
        "snapshot": str(snapshot.relative_to(PROJECT_ROOT)),
        "instruction": manifest["runtime"]["instructions"],
        "timeline_ticks": manifest["runtime"]["timeline_ticks"],
        "machine_event_cursor": manifest.get("machine_event_cursor"),
        "executed_exports": len(candidates),
        "ranked_exports": candidates,
        "candidate_rule": (
            "Executed MPW export span with no decoded direct trap, no "
            "unresolved indirect transfer in the span, and no dynamically "
            "attributed trap. This is a triage signal, not semantic proof."
        ),
    }


def main() -> int:
    args = parser().parse_args()
    iso = args.iso.resolve()
    if not iso.is_file():
        raise RuntimeError(f"Macintosh image not found: {iso}")
    if not args.no_build:
        subprocess.run(
            [
                sys.executable,
                str(PORT_FORGE / "build.py"),
                "--no-tests",
                "--targets",
                "pf_mac_lift",
            ],
            cwd=PORT_FORGE,
            check=True,
        )
    executable = PORT_FORGE / "build" / "pf_mac_lift.exe"
    completed = subprocess.run(
        [str(executable), "--creator", args.creator, str(iso)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    plan = json.loads(completed.stdout)
    if not args.no_snapshot and args.snapshot:
        snapshot = args.snapshot
        if not snapshot.is_absolute():
            snapshot = PROJECT_ROOT / snapshot
        attach_dynamic_evidence(plan, snapshot.resolve())
    output = args.output
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    dynamic = plan.get("simant_dynamic_evidence", {})
    native = sum(
        item["native_candidate"]
        for item in dynamic.get("ranked_exports", [])
    )
    print(f"lift plan: {output}")
    print(
        f"decoded: {plan['summary']['decoded_bytes']}/"
        f"{plan['summary']['code_bytes']} bytes, "
        f"{plan['summary']['decoded_instructions']} instructions"
    )
    if dynamic:
        print(
            f"executed exports: {dynamic['executed_exports']}; "
            f"conservative native candidates: {native}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        print(f"lift.py: {error}", file=sys.stderr)
        raise SystemExit(1)
