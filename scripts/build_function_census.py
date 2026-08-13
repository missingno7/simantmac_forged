#!/usr/bin/env python3
"""Build the stable-identity Macintosh function census from lift evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LIFT_PLAN = ROOT / "artifacts/analysis/mac_static_lift_plan.json"
SELECTION = ROOT / "recovery/native-selection.json"
OUTPUT = ROOT / "artifacts/analysis/mac_function_census.json"


STATE_DEFINITIONS = {
    "discovered": "An MPW export boundary identifies the function entry.",
    "statically_reachable": "The entry is the application root or has a proven static path from it.",
    "dynamically_observed": "At least one byte in the export span was executed in the linked lift snapshot.",
    "generated": "A deterministic native emitter owns an exact-source-guarded implementation.",
    "active": "The generated-with-fallback runtime installs this implementation by default.",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path}: expected a JSON object")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update(record["states"])
    return dict(sorted(counts.items()))


def generated_symbol(identity: str) -> str:
    return "native_" + identity.replace(".", "_").replace("-", "neg_")


def build() -> dict[str, Any]:
    plan = load_json(LIFT_PLAN)
    selection = load_json(SELECTION)
    if plan.get("format") != "portforge-mac68k-lift-plan-v1":
        raise SystemExit(f"{LIFT_PLAN}: unsupported lift-plan format")
    if selection.get("format") != "simant-mac-native-selection-v1":
        raise SystemExit(f"{SELECTION}: unsupported native-selection format")
    if selection.get("lift_plan_sha256") != sha256_file(LIFT_PLAN):
        raise SystemExit(f"{LIFT_PLAN}: digest differs from native selection")

    selected = {
        item["code_identity"]
        for item in selection.get("functions", [])
        if isinstance(item, dict) and isinstance(item.get("code_identity"), str)
    }
    dynamic = {
        item["code_identity"]: item
        for item in plan.get("simant_dynamic_evidence", {}).get(
            "ranked_exports", []
        )
        if isinstance(item, dict) and isinstance(item.get("code_identity"), str)
    }
    functions: list[dict[str, Any]] = []
    code_units: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in plan.get("functions", []):
        if not isinstance(item, dict):
            raise SystemExit(f"{LIFT_PLAN}: malformed function record")
        identity = item.get("code_identity")
        if not isinstance(identity, str) or identity in seen:
            raise SystemExit(f"{LIFT_PLAN}: invalid or repeated identity {identity!r}")
        seen.add(identity)
        states = ["discovered"]
        entry_root = identity == "mac.code.1.4"
        if entry_root:
            states.append("statically_reachable")
        observed = dynamic.get(identity, {}).get("executed_bytes", 0) > 0
        if observed:
            states.append("dynamically_observed")
        symbol = None
        if identity in selected:
            states.extend(["generated", "active"])
            symbol = generated_symbol(identity)
        resource_id = int(item["resource_id"])
        end_offset = int(item["end_resource_offset"])
        functions.append(
            {
                "id": identity,
                "states": states,
                "entry_root": entry_root,
                "static_block": int(item.get("decoded_instructions", 0)) > 0,
                "static_callers": [],
                "dynamic": None,
                "generated_symbol": symbol,
                "hook_target": identity in selected,
            }
        )
        code_units.append(
            {
                "id": identity,
                "end": f"mac.code.{resource_id}.{end_offset}",
                "instruction_count": int(item.get("decoded_instructions", 0)),
                "states": list(states),
                "generated_symbol": symbol,
            }
        )

    if selected - seen:
        missing = ", ".join(sorted(selected - seen))
        raise SystemExit(f"{SELECTION}: selected identities absent from lift plan: {missing}")
    program_sha256 = plan.get("resource_sha256")
    if not isinstance(program_sha256, str) or len(program_sha256) != 64:
        raise SystemExit(f"{LIFT_PLAN}: invalid resource_sha256")
    if selection.get("program_sha256") != program_sha256:
        raise SystemExit(f"{SELECTION}: program identity differs from lift plan")

    return {
        "$schema": "port_forge/schemas/portforge-function-census-v1.schema.json",
        "format": "portforge-function-census-v1",
        "scope": {
            "program_sha256": program_sha256,
            "static_completeness": {
                "boundary_authority": "MPW export table",
                "exports": len(functions),
                "decoded_bytes": int(plan.get("summary", {}).get("decoded_bytes", 0)),
                "code_bytes": int(plan.get("summary", {}).get("code_bytes", 0)),
                "indirect_control_transfer_sites": sum(
                    int(item.get("indirect_control_transfers", 0))
                    for item in plan.get("functions", [])
                    if isinstance(item, dict)
                ),
                "unresolved_target_enumeration": "not available in lift plan v1",
            },
            "rule": (
                "Every MPW export is discovered; only the launch entry is "
                "statically reachable without a complete call graph. Dynamic "
                "observation records executed-byte evidence, not invocation counts."
            ),
        },
        "sources": {
            "lift_plan": str(LIFT_PLAN.relative_to(ROOT)).replace("\\", "/"),
            "lift_plan_sha256": sha256_file(LIFT_PLAN),
            "native_selection": str(SELECTION.relative_to(ROOT)).replace("\\", "/"),
            "native_selection_sha256": sha256_file(SELECTION),
        },
        "state_definitions": STATE_DEFINITIONS,
        "summary": {
            "functions": len(functions),
            "code_units": len(code_units),
            "unresolved_indirect_targets": 0,
            "function_states": state_counts(functions),
            "code_states": state_counts(code_units),
        },
        "unresolved_indirect_targets": [],
        "functions": functions,
        "code_units": code_units,
    }


def canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not LIFT_PLAN.is_file():
        if args.write:
            raise SystemExit(
                f"{LIFT_PLAN} is required to regenerate the function census"
            )
        current = load_json(OUTPUT)
        selection = load_json(SELECTION)
        sources = current.get("sources", {})
        scope = current.get("scope", {})
        if (
            current.get("format") != "portforge-function-census-v1"
            or scope.get("program_sha256") != selection.get("program_sha256")
            or sources.get("lift_plan_sha256")
            != selection.get("lift_plan_sha256")
            or sources.get("native_selection_sha256") != sha256_file(SELECTION)
        ):
            raise SystemExit(
                f"{OUTPUT} is not bound to the tracked native selection"
            )
        print(
            f"function census provenance current: {OUTPUT} "
            "(retained lift plan unavailable)"
        )
        return 0
    expected = canonical(build())
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
        print(f"function census written: {OUTPUT}")
        return 0
    if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
        raise SystemExit(
            f"{OUTPUT} is stale; run python scripts/build_function_census.py --write"
        )
    print(f"function census current: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
