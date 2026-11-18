#!/usr/bin/env python3
"""Generate the three required PLE figures from REAL eval results.

Usage: python3 gen_figures.py <results.json> <out_dir> [artifacts_dir]

No simulated numbers: every point comes from a measured dev task. When the
local model is self-hosted there is no USD cost, so Figure 2 plots measured
runtime and says so explicitly instead of inventing a price.
"""

import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    results_path = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    artifacts = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(results_path.read_text())
    tasks = data.get("tasks", [])
    if not tasks:
        raise SystemExit("no measured tasks in results.json")

    # Figure 1: architecture, from the actual modules.
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.axis("off")
    boxes = [
        (0.02, 0.55, 0.28, 0.28, "Task workspace\n(instruction + drawing files)"),
        (0.36, 0.55, 0.26, 0.28, "Model proposes\nbounded parameters"),
        (0.68, 0.55, 0.29, 0.28, "4 closed-form solvers\n-> solution.json + grader file"),
        (0.36, 0.12, 0.26, 0.28, "Hard gate\nindependent recomputation"),
    ]
    for x, y, w, h, label in boxes:
        ax.add_patch(plt.Rectangle((x, y), w, h, fill=True, color="#dceaf7", ec="#245b8a", lw=1.5))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=10)
    ax.annotate("", xy=(0.36, 0.69), xytext=(0.30, 0.69), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.68, 0.69), xytext=(0.62, 0.69), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.49, 0.40), xytext=(0.49, 0.55), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.set_title("Figure 1: Deterministic solver harness with independent pre-submission gate")
    fig.savefig(out / "fig1_architecture.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Figure 2: score vs measured runtime. Local Ollama has no USD cost, so
    # cost_usd is absent; plotting it as zero would be misleading.
    fig, ax = plt.subplots(figsize=(8.5, 5))
    has_cost = any(t.get("cost_usd") is not None for t in tasks)
    if has_cost:
        xs = [t.get("cost_usd") or 0.0 for t in tasks]
        xlabel = "Cost (USD, measured)"
    else:
        xs = [t.get("seconds") or 0.0 for t in tasks]
        xlabel = "Measured runtime (s) - local Ollama has no USD cost"
    ys = [t.get("score") or 0.0 for t in tasks]
    ax.scatter(xs, ys, s=55, alpha=0.8)
    for t, x, y in zip(tasks, xs, ys):
        ax.annotate(t["id"][:11], (x, y), fontsize=6, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Score (0-1, graded)")
    ax.set_title(f"Figure 2: Dev-set score vs {'cost' if has_cost else 'runtime'} ({len(tasks)} real tasks)")
    ax.grid(alpha=0.3)
    fig.savefig(out / "fig2_score_vs_cost.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Figure 3: failure breakdown. The runner's `status` is "ok" for all tasks
    # (the harness ran); the real cause is in each task's final_message.
    causes = {}
    for t in tasks:
        msg = ""
        if artifacts:
            f = artifacts / t["id"] / "final_message.md"
            if f.is_file():
                msg = f.read_text(errors="ignore")
        status = t.get("status", "")
        if "not run" in status:
            kind = "Not run\n(disk limit)"
        elif "judge failed" in status or "RuntimeError" in status:
            kind = "Local judge\nfailed"
        elif "grader dependencies" in status:
            kind = "Grader deps\nfailed"
        elif "No deterministic solver maps" in msg:
            kind = "No solver\nfor task"
        elif "gate FAILED" in msg:
            kind = "Gate rejected\nsolver"
        elif msg:
            kind = "Solver ran,\ngrader rejected"
        else:
            kind = "unknown"
        causes[kind] = causes.get(kind, 0) + 1
    fig, ax = plt.subplots(figsize=(9, 4.5))
    keys = list(causes.keys())
    vals = [causes[k] for k in keys]
    ax.bar(keys, vals, color="#b54a4a")
    for k, v in zip(keys, vals):
        ax.text(k, v + 0.2, str(v), ha="center")
    ax.set_ylabel("Number of dev tasks")
    ax.set_title(f"Figure 3: Failure breakdown on {len(tasks)} dev tasks")
    fig.savefig(out / "fig3_failure_breakdown.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Media Gallery cover: a clean title card, no invented data.
    fig, ax = plt.subplots(figsize=(12, 6.3))
    ax.axis("off")
    fig.patch.set_facecolor("#0f2233")
    ax.text(0.5, 0.66, "Deterministic Engineering Solvers\nBehind an Independent Gate",
            ha="center", va="center", fontsize=24, color="white", weight="bold",
            transform=ax.transAxes)
    ax.text(0.5, 0.36, "PLE harness  |  FiscalMindset/ple-harness-agentos",
            ha="center", va="center", fontsize=13, color="#9fc6e8", transform=ax.transAxes)
    ax.text(0.5, 0.22, f"Measured on {len(tasks)} public dev tasks - honest negative result",
            ha="center", va="center", fontsize=11, color="#c9d7e3", transform=ax.transAxes)
    fig.savefig(out / "cover.png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    print(f"wrote cover + 3 figures from {len(tasks)} measured tasks to {out}")
    print("failure breakdown:", causes)


if __name__ == "__main__":
    main()
