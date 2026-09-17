"""`flybench lifecycle results/` — which tasks still discriminate? (docs/GOVERNANCE.md, ROADMAP item 50)

A task's job is to separate models. Once every row that has run it passes it with the same
margin, it separates nothing; it is *saturated*. The policy: a saturated task is not deleted
(its result files and RFC stay citable) but is marked `status: retired` in its YAML, leaves the
scored tiers, and its slot is offered for a harder task on the same pathway. This command is the
evidence for that decision, not the decision: it reads result files and reports, per task, how
many rows ran it, how many passed, and whether the passing rows are indistinguishable (their
per-check margins agree within the seed spread).

Rows are grouped by connectome — a task saturated on FlyWire and failing on MaleCNS is not
saturated. Self-reported rows count; the note says how many were verified.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MIN_ROWS = 3                 # fewer rows than this and "everyone passes" is not evidence of anything: CONVENTION
MARGIN_SPREAD_DECADES = 0.3  # passing rows whose mean margins sit within 0.3 decades (2×) of each other are "the same": CONVENTION


@dataclass
class TaskState:
    task: str
    connectome: str
    rows: int = 0
    passed: int = 0
    verified: int = 0
    margins: list[float] = field(default_factory=list)   # mean check margin per passing row
    state: str = "active"                                # active | saturated | guard | target | broken | thin
    note: str = ""


def _task_meta() -> dict[str, tuple[str, bool]]:
    """task name -> (tier, has a positive check). A null-only task is a guard, never retired for saturation."""
    from .bench import load_tasks
    out = {}
    for t in load_tasks(include_retired=True):
        positive = any(str(ch.get("op", "")) in (">", ">=") for ch in t.get("checks", []))
        out[t["name"]] = (str(t.get("tier", "core")), positive)
    return out


def states(reports: list[dict]) -> list[TaskState]:
    meta = _task_meta()
    by: dict[tuple[str, str], TaskState] = {}
    for r in reports:
        for t in r.get("tasks", []):
            key = (t["task"], r["connectome"])
            s = by.setdefault(key, TaskState(task=t["task"], connectome=r["connectome"]))
            s.rows += 1
            s.verified += int(bool(r.get("verified")))
            if t.get("passed"):
                s.passed += 1
                ms = [c["margin"] for c in t.get("checks", []) if c.get("margin") is not None and np.isfinite(c["margin"])]
                if ms:
                    s.margins.append(float(np.mean(ms)))
    out = []
    for s in by.values():
        tier, positive = meta.get(s.task, ("?", True))
        if s.rows < MIN_ROWS:
            s.state, s.note = "thin", f"{s.rows} row(s): not enough evidence"
        elif s.passed == 0:
            if tier == "hard":
                s.state, s.note = "target", "no row passes it yet: that is what the hard tier is for"
            else:
                s.state, s.note = "broken", "a core task no row passes here: a selector problem on this dataset, or a documented dataset difference (docs/MALECNS.md) — say which in the task"
        elif s.passed == s.rows and not positive:
            s.state, s.note = "guard", "a null task every row passes: kept as the guard against firing everything; never retired for saturation"
        elif s.passed == s.rows and s.margins and (max(s.margins) - min(s.margins)) <= MARGIN_SPREAD_DECADES:
            s.state, s.note = "saturated", f"every row passes with the same margin ({min(s.margins):+.2f}…{max(s.margins):+.2f} decades): candidate for retirement"
        elif s.passed == s.rows:
            s.state, s.note = "active", f"every row passes but margins differ ({min(s.margins):+.2f}…{max(s.margins):+.2f}): still ranks them"
        else:
            s.state, s.note = "active", f"{s.passed}/{s.rows} rows pass"
        out.append(s)
    return sorted(out, key=lambda s: (s.connectome, s.task))


def markdown(ss: list[TaskState]) -> str:
    lines = ["| task | connectome | rows (verified) | pass | state | note |", "|---|---|---|---|---|---|"]
    for s in ss:
        lines.append(f"| {s.task} | {s.connectome} | {s.rows} ({s.verified}) | {s.passed} | **{s.state}** | {s.note} |")
    n_sat = sum(s.state == "saturated" for s in ss)
    lines.append("")
    lines.append(f"_{n_sat} saturated task/connectome pair(s). Retirement is a maintainer decision recorded in the task YAML (`status: retired`, docs/GOVERNANCE.md); this table is the evidence._")
    return "\n".join(lines)


def load_reports(paths: list[Path]) -> list[dict]:
    files = []
    for p in paths:
        files += sorted(p.glob("*.json")) if p.is_dir() else [p]
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]
