"""`flybench audit tasks/x.yaml -c flywire783` — is a proposed task worth having? (ROADMAP item 47)

A task earns its place by discriminating. Two ways a task can fail to:

- **non-diagnostic**: a positive check passes on the real wiring *and* on the degree-preserving
  shuffle. Whatever it measures, it is not the connectome. Rejected.
- **trivial**: the reference model passes every check on every seed with at least a decade of
  margin (10× the threshold). It is a regression test, not a target: allowed only in the core
  tier, and only if it guards a pathway no core task already guards.

And one bookkeeping error the lint cannot catch without a run: the tier. `core` means the
reference passes it; a task the reference fails at every seed is `hard` (or `expected_fail`),
and a task it passes cleanly is not.

The audit runs the task on the reference LIF with the `rewired` control (three seeds by default)
and says which of these apply. CI runs it on FlyWire for every task a pull request adds or
changes (.github/workflows/audit-tasks.yml) and refuses non-diagnostic ones.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from .bench import load_tasks, run_suite, task_unavailable
from .connectome import Connectome
from .sim import LIFParams

TRIVIAL_MARGIN_DECADES = 1.0    # 10× the threshold on every check: CONVENTION, the same decade the graded score saturates at


@dataclass
class Audit:
    task: str
    tier: str
    ran: bool
    reason: str = ""                       # why it did not run (skipped on this dataset)
    score: float | None = None
    passed: bool | None = None
    control_scores: dict[str, float] = field(default_factory=dict)
    specificity: float | None = None
    non_diagnostic: bool = False           # REJECT
    trivial: bool = False                  # warn unless tier == core
    min_margin: float | None = None        # smallest margin (decades) over checks; margins of null checks count too
    tier_mismatch: str = ""                # a tier claim the run contradicts
    verdict: str = "ok"                    # ok | warn | reject
    problems: list[str] = field(default_factory=list)   # what decides the verdict
    notes: list[str] = field(default_factory=list)      # information only


def audit_task(task: dict, c: Connectome, params: LIFParams, seeds: int = 3, controls: tuple[str, ...] = ("rewired",),
               jobs: int = 1, connectome_ref: str | None = None, cache=None) -> Audit:
    a = Audit(task=task["name"], tier=str(task.get("tier", "core")), ran=False)
    why = task_unavailable(task, c)
    if why:
        a.reason = why
        a.problems.append(f"not run on {c.name}: {why}")
        a.verdict = "warn"
        return a
    rep = run_suite(c, params, [task], seeds=seeds, controls=list(controls), jobs=jobs, connectome_ref=connectome_ref, cache=cache)
    if not rep["tasks"]:
        a.reason = "; ".join(f"{k}: {v}" for k, v in rep.get("skipped", {}).items()) or "skipped"
        a.problems.append(f"not run on {c.name}: {a.reason}")
        a.verdict = "warn"
        return a
    t = rep["tasks"][0]
    a.ran = True
    a.score, a.passed = float(t["score"]), bool(t["passed"])
    a.control_scores = {k: float(v["score"]) for k, v in (t.get("controls") or {}).items()}
    a.specificity = t.get("specificity")
    a.non_diagnostic = bool(t.get("non_diagnostic"))
    margins = [ch.get("margin") for ch in t["checks"] if ch.get("margin") is not None and ch.get("margin") == ch.get("margin")]
    a.min_margin = min(margins) if margins else None
    every_seed = bool(t["checks"]) and all(ch["passed"] for ch in t["checks"])    # a multi-seed pass already means every seed passed
    # a null-only task ("X must not fire") has no response to be trivial about; the shuffle passes it by design
    positive = any(str(ch.get("op", "")) in (">", ">=") for ch in task.get("checks", []))
    a.trivial = bool(positive and a.passed and every_seed and a.min_margin is not None and a.min_margin >= TRIVIAL_MARGIN_DECADES)

    if a.non_diagnostic:
        also = ", ".join(k for k, v in (t.get("controls") or {}).items() if v.get("passed"))
        a.problems.append(f"non-diagnostic: passes on the real wiring and on {also} — it is not measuring the connectome")
    if a.trivial and a.tier != "core":
        a.problems.append(f"trivial: the reference passes every check on every seed with ≥ {TRIVIAL_MARGIN_DECADES:.0f} decade of margin "
                          f"(min {a.min_margin:+.2f}); that is a regression test, not a target — tier: core, and only if no core task guards this pathway")
    elif a.trivial:
        a.notes.append(f"trivial (core): every check ≥ {TRIVIAL_MARGIN_DECADES:.0f} decade clear (min {a.min_margin:+.2f}); fine for a regression test if the pathway is new")
    if not positive:
        a.notes.append("null task (no check requires a response): the shuffle is expected to pass it; it cannot be non-diagnostic")
    if task.get("expected_fail"):
        if a.passed:
            a.tier_mismatch = "expected_fail but the reference passes it: drop expected_fail or fix the task"
    elif a.tier == "core" and not a.passed:
        a.tier_mismatch = f"tier: core but the reference scores {a.score:.2f}: core means the reference passes; use hard"
    elif a.tier == "hard" and a.passed and every_seed and not a.non_diagnostic:
        a.tier_mismatch = "tier: hard but the reference passes on every seed: hard is for what it fails; use core (or tighten the checks)"
    if a.tier_mismatch:
        a.problems.append(a.tier_mismatch)
    a.verdict = "reject" if a.non_diagnostic else ("warn" if a.problems else "ok")
    return a


def audit_paths(paths: list[Path], c: Connectome, params: LIFParams, **kw) -> list[Audit]:
    return [audit_task(t, c, params, **kw) for t in load_tasks(paths)]


def markdown(audits: list[Audit], connectome: str, gain: float, seeds: int) -> str:
    icon = {"ok": "✅", "warn": "⚠️", "reject": "❌"}
    lines = [f"## Task audit — {connectome}, reference LIF gain {gain}, {seeds} seeds, `rewired` control", "",
             "| task | tier | reference | rewired | specificity | min margin | verdict |", "|---|---|---|---|---|---|---|"]
    for a in audits:
        ref = "–" if a.score is None else f"{a.score:.2f}" + (" ✓" if a.passed else "")
        ctl = "–" if not a.control_scores else ", ".join(f"{v:.2f}" for v in a.control_scores.values())
        spec = "–" if a.specificity is None else f"{a.specificity:+.2f}"
        mm = "–" if a.min_margin is None else f"{a.min_margin:+.2f}"
        lines.append(f"| {a.task} | {a.tier} | {ref} | {ctl} | {spec} | {mm} | {icon[a.verdict]} {a.verdict} |")
    for a in audits:
        for p in a.problems:
            lines.append(f"- **{a.task}**: {p}")
        for n in a.notes:
            lines.append(f"- {a.task}: _{n}_")
    lines.append("")
    lines.append("_A rejected task passes on shuffled wiring: it measures something, but not this connectome. docs/CONTROLS.md._")
    return "\n".join(lines)


def to_dict(a: Audit) -> dict:
    return asdict(a)
