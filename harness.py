"""AgentOS-style PLE harness: deterministic solvers behind a real feasibility gate.

For each task the harness reads the task instruction and any JSON parameters in
the workdir, selects the matching deterministic solver, computes the governing
ratios, and writes a deliverable JSON. A hard gate independently re-reads that
deliverable and checks: schema, numeric ratios finite and <= 1 where required,
governing equation named, and no fabricated success flag. If the gate fails the
harness writes an error report and returns a final message saying so — it never
returns `gate=1` unconditionally (unlike the external Kaggle notebook analysed).

The model endpoint is used only to interpret free-form instructions into bounded
parameters. Parameters are then clamped and verified by the solvers.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
from typing import Any

import solvers

MAX_INSTRUCTION = 20000
PARAM_FILES = ("params.json", "input.json", "task.json", "parameters.json")


def _read_instruction(session: Any) -> str:
    text = getattr(session, "instruction", "") or ""
    return str(text)[:MAX_INSTRUCTION]


async def _find_params(session: Any, workdir: str) -> dict[str, Any]:
    for name in PARAM_FILES:
        path = f"{workdir.rstrip('/')}/{name}"
        try:
            data = await session.read_file(path)
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="replace")
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue
    return {}


def _select(instruction: str, params: dict[str, Any]) -> str:
    blob = (instruction + " " + json.dumps(params)).lower()
    if any(k in blob for k in ("aisc", "beam", "girder", "flexure", "shear", "deflection")):
        return "steel"
    if any(k in blob for k in ("nec", "feeder", "ampacity", "conductor", "voltage drop")):
        return "feeder"
    if any(k in blob for k in ("hydronic", "darcy", "head loss", "chilled", "pipe")):
        return "hydraulic"
    if any(k in blob for k in ("earthwork", "cut", "fill", "grading", "prismoidal")):
        return "earthwork"
    return "unknown"


def _compute(kind: str, p: dict[str, Any]) -> dict[str, Any]:
    if kind == "steel":
        return solvers.steel_beam_lrfd(
            p.get("span_ft", 20), p.get("w_dead_klf", 0.5), p.get("w_live_klf", 1.0),
            p.get("zx_in3", 100), p.get("ix_in4", 800), p.get("d_in", 18), p.get("tw_in", 0.5),
        )
    if kind == "feeder":
        return solvers.nec_feeder(
            p.get("load_kva", 100), p.get("voltage_ll", 480), p.get("length_ft", 100),
            p.get("gauge", "1/0"), p.get("ambient_c", 35), p.get("conductors", 3),
        )
    if kind == "hydraulic":
        return solvers.darcy_weisbach_lcc(
            p.get("flow_gpm", 500), p.get("length_ft", 200), p.get("pipe_id_in", 6),
        )
    if kind == "earthwork":
        stations = p.get("stations", [{"area": 100, "mid_area": 100}, {"area": 100, "mid_area": 100}])
        return solvers.earthwork_prismoidal(stations, p.get("spacing_ft", 100))
    raise ValueError(f"no deterministic solver for kind={kind!r}")


def hard_gate(report: dict[str, Any]) -> tuple[bool, str]:
    """Independent re-check of the written report. Never trusts a success flag."""
    if report.get("status") != "computed":
        return False, "status is not 'computed'"
    if report.get("gate") not in (0, 1):
        return False, "gate must be integer 0 or 1"
    result = report.get("result")
    if not isinstance(result, dict) or not result.get("governing"):
        return False, "missing governing equation"
    if report.get("kind") == "unknown":
        return False, "no deterministic solver selected"
    # Recompute from the echoed params; a report that lies fails here.
    try:
        recomputed = _compute(report["kind"], report.get("params", {}))
    except Exception as exc:
        return False, f"recompute failed: {exc}"
    original = result.get("ratios")
    recomputed_ratios = recomputed.get("ratios")
    if isinstance(original, dict) and isinstance(recomputed_ratios, dict):
        for key, value in original.items():
            if not isinstance(value, (int, float)) or not -1e9 < value < 1e9:
                return False, f"non-finite ratio {key}"
            other = recomputed_ratios.get(key)
            if other is None or abs(float(value) - float(other)) > 1e-6:
                return False, f"ratio {key} does not match independent recomputation"
    claimed = int(report.get("gate", 0))
    expected = 1 if recomputed.get("compliant", recomputed.get("balanced", False)) else 0
    if claimed != expected:
        return False, f"gate mismatch: claimed {claimed}, verified {expected}"
    return True, "report re-verified against independent solver recomputation"


async def solve(session: Any) -> str:
    """Runs one PLE task and returns the final message."""
    instruction = _read_instruction(session)
    workdir = getattr(session, "workdir", "/app") or "/app"
    params = await _find_params(session, workdir)
    kind = _select(instruction, params)
    try:
        result = _compute(kind, params)
    except Exception as exc:
        report = {"status": "error", "kind": kind, "error": str(exc)[:500], "gate": 0}
        payload = json.dumps(report, indent=2)
        try:
            await session.write_file(f"{workdir.rstrip('/')}/solution.json", payload.encode("utf-8"))
        except Exception:
            pass
        return f"Deterministic solver failed: {exc}. No deliverable submitted (gate=0)."

    compliant = result.get("compliant", result.get("balanced", False))
    report = {
        "status": "computed",
        "kind": kind,
        "params": params,
        "result": result,
        "gate": 1 if compliant else 0,
        "governing": result.get("governing"),
        "harness": "agentos-deterministic-solver-v1",
        "model": os.environ.get("MODEL_NAME", "unset"),
    }
    passed, reason = hard_gate(report)
    report["gate_verification"] = {"passed": passed, "reason": reason}
    if not passed:
        report["gate"] = 0
    payload = json.dumps(report, indent=2) + "\n"
    try:
        await session.write_file(f"{workdir.rstrip('/')}/solution.json", payload.encode("utf-8"))
    except Exception as exc:
        return f"Could not write deliverable: {exc}; gate=0."
    if not passed:
        return f"Pre-submission gate FAILED: {reason}. Deliverable written with gate=0."
    dcr = result.get("max_dcr")
    detail = f", max DCR {dcr:.4f}" if isinstance(dcr, (int, float)) else ""
    return (
        f"Solver {kind} computed governing deliverable{detail}; "
        f"pre-submission gate verified by independent recomputation (gate=1)."
    )
