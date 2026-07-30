#!/usr/bin/env python3
"""Build a static PortForge requirement frontier for Macintosh SimAnt.

The CODE decoder and trap inventory are game-neutral PortForge facilities.
This launcher owns the SimAnt ISO path, Finder creator, and artifact layout.
"""

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
    PROJECT_ROOT / "artifacts" / "analysis" / "mac_trap_frontier.json"
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
            "Statically decode SimAnt CODE resources and inventory direct "
            "Macintosh Toolbox/OS requirements."
        )
    )
    result.add_argument("--iso", type=Path, default=DEFAULT_ISO)
    selection = result.add_mutually_exclusive_group()
    selection.add_argument(
        "--creator",
        default="SANT",
        help="Finder creator used to select the application (default: SANT)",
    )
    selection.add_argument(
        "--application",
        help="exact HFS application path instead of a Finder creator",
    )
    result.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="JSON artifact path",
    )
    result.add_argument(
        "--no-build",
        action="store_true",
        help="use the existing port_forge/build/pf_mac_traps.exe",
    )
    result.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help=(
            "optional v2 diagnostic snapshot used to rank executed "
            "MPW exports for native replacement"
        ),
    )
    result.add_argument(
        "--no-snapshot",
        action="store_true",
        help="produce only the static frontier",
    )
    return result


def executed(bitmap: bytes, address: int) -> bool:
    return bool(bitmap[address >> 3] & (1 << (address & 7)))


def attach_dynamic_evidence(report: dict, snapshot: Path) -> None:
    manifest_path = snapshot / "snapshot.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != (
        "portforge-mac68k-diagnostic-snapshot-v2"
    ):
        raise RuntimeError(
            f"unsupported diagnostic snapshot: {manifest.get('format')}"
        )
    bitmap = (snapshot / manifest["executed_file"]).read_bytes()
    ranges = {
        item["resource_id"]: item
        for item in manifest["code_ranges"]
    }

    dynamic_sites: list[tuple[int, int, int]] = []
    for site in manifest["trap_coverage"]:
        parts = site["code_identity"].split(".")
        if len(parts) != 4 or parts[:2] != ["mac", "code"]:
            continue
        dynamic_sites.append(
            (int(parts[2]), int(parts[3]), int(site["calls"]))
        )

    candidates = []
    executed_functions = 0
    for function in report["functions"]:
        code_range = ranges.get(function["resource_id"])
        if not code_range:
            continue
        delta = (
            function["resource_offset"]
            - code_range["resource_offset"]
        )
        if delta < 0:
            continue
        runtime_start = code_range["runtime_base"] + delta
        size = min(
            function["byte_span"],
            code_range["size"] - delta,
        )
        if size <= 0 or runtime_start + size > len(bitmap) * 8:
            continue
        executed_bytes = sum(
            executed(bitmap, runtime_start + offset)
            for offset in range(size)
        )
        if not executed_bytes:
            continue
        executed_functions += 1
        resource_start = function["resource_offset"]
        resource_end = resource_start + size
        attributed = [
            calls
            for resource_id, resource_offset, calls in dynamic_sites
            if resource_id == function["resource_id"]
            and resource_start <= resource_offset < resource_end
        ]
        candidate = {
            "code_identity": function["code_identity"],
            "resource_id": function["resource_id"],
            "entry_offset": function["entry_offset"],
            "byte_span": size,
            "executed_bytes": executed_bytes,
            "execution_coverage_percent": (
                100.0 * executed_bytes / size
            ),
            "static_direct_trap_sites": (
                function["direct_trap_sites"]
            ),
            "dynamic_trap_sites": len(attributed),
            "dynamic_trap_calls": sum(attributed),
        }
        if (
            function["direct_trap_free"]
            and not attributed
        ):
            candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            item["executed_bytes"],
            item["execution_coverage_percent"],
        ),
        reverse=True,
    )
    report["simant_dynamic_evidence"] = {
        "snapshot": str(snapshot.relative_to(PROJECT_ROOT)),
        "instruction": manifest["runtime"]["instructions"],
        "timeline_ticks": manifest["runtime"]["timeline_ticks"],
        "memory_sha256": manifest["memory_sha256"],
        "executed_sha256": manifest["executed_sha256"],
        "code_generation": manifest["runtime"]["code_generation"],
        "trap_sites": len(manifest["trap_coverage"]),
        "resource_queries": len(manifest["resource_lookups"]),
        "low_memory_sites": len(manifest["low_memory_accesses"]),
        "executed_code_write_sites": len(
            manifest["executed_code_writes"]
        ),
        "executed_code_writes": manifest["executed_code_writes"],
        "executed_export_ranges": executed_functions,
        "native_replacement_candidates": candidates[:40],
        "candidate_caveat": (
            "An MPW export range with executed bytes and no direct or "
            "observed trap does not prove platform independence. Verify "
            "indirect calls, global-state effects, exact-byte coverage, and "
            "68k/native state parity before replacing it."
        ),
    }


def main() -> int:
    args = parser().parse_args()
    iso = args.iso.resolve()
    if not iso.is_file():
        raise RuntimeError(f"SimAnt ISO not found: {iso}")

    if not args.no_build:
        subprocess.run(
            [
                sys.executable,
                str(PORT_FORGE / "build.py"),
                "--no-tests",
                "--targets",
                "pf_mac_traps",
            ],
            cwd=PORT_FORGE,
            check=True,
        )

    executable = PORT_FORGE / "build" / "pf_mac_traps.exe"
    if not executable.is_file():
        raise RuntimeError(
            f"static analyzer is not built: {executable}"
        )
    command = [str(executable)]
    if args.application:
        command.extend(["--application", args.application])
    else:
        command.extend(["--creator", args.creator])
    command.append(str(iso))
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    report = json.loads(completed.stdout)
    if not args.no_snapshot:
        snapshot = args.snapshot
        if not snapshot.is_absolute():
            snapshot = PROJECT_ROOT / snapshot
        snapshot = snapshot.resolve()
        if snapshot.is_dir():
            attach_dynamic_evidence(report, snapshot)

    output = args.output
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary = report["summary"]
    unsupported = [
        trap
        for trap in report["traps"]
        if trap["reachable_sites"] and not trap["implemented"]
    ]
    print(f"report: {output}")
    print(
        "decoded: "
        f"{summary['decoded_bytes']}/{summary['code_bytes']} bytes "
        f"({summary['decoded_byte_percent']:.2f}%)"
    )
    print(
        "direct requirements: "
        f"{summary['reachable_trap_sites']} sites, "
        f"{summary['reachable_opcode_count']} trap slots"
    )
    print(f"unsupported reachable slots: {len(unsupported)}")
    dynamic = report.get("simant_dynamic_evidence")
    if dynamic:
        print(
            "native candidates: "
            f"{len(dynamic['native_replacement_candidates'])} "
            "executed trap-free MPW export ranges"
        )
    if unsupported:
        print(
            "frontier: "
            + ", ".join(
                f"{trap['canonical_opcode']} {trap['name']}"
                for trap in unsupported
            )
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
        print(f"analyze.py: {error}", file=sys.stderr)
        raise SystemExit(1)
