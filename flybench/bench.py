"""Task definitions, execution and scoring.

A task is a YAML file:

    name: sugar_to_proboscis
    title: Sugar on the leg → proboscis extension
    citation: Shiu et al. 2024; Dethier 1976
    duration_ms: 1000
    readout:
      select: {cell_type: MN9}
    conditions:
      baseline: {stimuli: []}
      sugar:
        stimuli:
          - {select: {labels_regex: "sugar"}, rate_hz: 100, t_start_ms: 200, t_end_ms: 800}
    window: [200, 800]                 # scoring window (defaults to whole run)
    checks:
      - {type: rate, cond: sugar, op: ">", value: 5}          # Hz per readout neuron
      - {type: ratio, cond: sugar, over: baseline, op: ">", value: 5}
      - {type: active_fraction, cond: sugar, op: "<", value: 0.2}

Each check yields pass/fail plus the measured value; a task passes if every
check passes. `score` is the fraction of checks passed, so partial credit
shows up in the leaderboard.
"""

from __future__ import annotations

import importlib
import json
import operator
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import yaml

from .connectome import Connectome
from .sim import LIFParams, LIFSimulator, SimResult, Stimulus

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq}
EPS = 1e-3
TASK_DIR = Path(__file__).resolve().parent.parent / "tasks"


@dataclass
class CheckResult:
    description: str
    value: float
    passed: bool


@dataclass
class TaskResult:
    task: str
    title: str
    passed: bool
    score: float
    checks: list[CheckResult]
    measurements: dict[str, dict[str, float]]
    readout_size: int
    stimulus_sizes: dict[str, int]
    seconds: float
    notes: list[str] = field(default_factory=list)


def load_tasks(paths: list[Path] | None = None, tier: str = "all") -> list[dict]:
    """tier: 'core' (reflexes the reference LIF must pass), 'hard', or 'all'."""
    paths = paths or sorted(TASK_DIR.glob("*.yaml"))
    tasks = [yaml.safe_load(Path(p).read_text()) for p in paths]
    if tier != "all":
        tasks = [t for t in tasks if t.get("tier", "core") == tier]
    return tasks


def _stimuli(c: Connectome, spec_list: list[dict], sizes: dict[str, int]) -> list[Stimulus]:
    out = []
    for i, s in enumerate(spec_list):
        neurons = c.select(s["select"])
        name = s.get("name", f"stim{i}")
        sizes[name] = int(neurons.size)
        out.append(Stimulus(neurons=neurons, rate_hz=float(s.get("rate_hz", 100.0)),
                            t_start_ms=float(s.get("t_start_ms", 0.0)),
                            t_end_ms=float(s.get("t_end_ms", float("inf"))), name=name))
    return out


SimulatorFactory = Callable[[Connectome, LIFParams], Any]


def resolve_simulator(spec: str | None) -> SimulatorFactory:
    """'pkg.module:ClassOrFactory' -> callable(connectome, params) returning an object with .run()."""
    if not spec:
        return LIFSimulator
    mod, _, attr = spec.partition(":")
    obj = getattr(importlib.import_module(mod), attr or "Simulator")
    return obj


def _metric(res: SimResult, readout: np.ndarray, name: str, w0: float, w1: float) -> float:
    if name == "rate":
        return res.rate_hz(readout, w0, w1)
    if name == "network_rate":
        return res.rate_hz(None, w0, w1)
    if name == "active_fraction":
        return res.active_fraction(w0, w1)
    if name == "readout_active_fraction":
        if readout.size == 0:
            return float("nan")
        m = (res.spike_times_ms >= w0) & (res.spike_times_ms < w1)
        return float(len(np.intersect1d(res.spike_neurons[m], readout)) / readout.size)
    raise ValueError(f"unknown metric {name}")


def run_task(task: dict, c: Connectome, params: LIFParams, verbose: bool = False,
             simulator: SimulatorFactory = LIFSimulator) -> TaskResult:
    t0 = time.time()
    notes: list[str] = []
    # readouts: either `readout: {select: ...}` (named "default") or `readouts: {name: {select: ...}}`
    readouts: dict[str, np.ndarray] = {}
    if "readout" in task:
        readouts["default"] = c.select(task["readout"]["select"])
    for name, spec in task.get("readouts", {}).items():
        readouts[name] = c.select(spec["select"])
    for name, idx in readouts.items():
        if idx.size == 0:
            notes.append(f"readout {name!r} matched 0 neurons")
    default_readout = next(iter(readouts))
    duration = float(task.get("duration_ms", 1000))
    window = task.get("window", [0, duration])
    sim = simulator(c, params)

    results: dict[str, SimResult] = {}
    measurements: dict[str, dict[str, float]] = {}
    stim_sizes: dict[str, int] = {}
    for cond_name, cond in task["conditions"].items():
        stims = _stimuli(c, cond.get("stimuli", []), stim_sizes)
        for s in stims:
            if s.neurons.size == 0:
                notes.append(f"{cond_name}: stimulus {s.name!r} matched 0 neurons")
        res: SimResult = sim.run(duration, stims)
        results[cond_name] = res
        m = {
            "rate": _metric(res, readouts[default_readout], "rate", *window),
            "network_rate": _metric(res, readouts[default_readout], "network_rate", *window),
            "active_fraction": _metric(res, readouts[default_readout], "active_fraction", *window),
            "spikes": float(len(res.spike_times_ms)),
        }
        for name, idx in readouts.items():
            m[f"rate[{name}]"] = _metric(res, idx, "rate", *window)
            m[f"readout_active_fraction[{name}]"] = _metric(res, idx, "readout_active_fraction", *window)
        measurements[cond_name] = m
        if verbose:
            extra = " ".join(f"{n}={m[f'rate[{n}]']:.1f}Hz" for n in readouts if n != "default")
            print(f"  {cond_name:>16}: readout {m['rate']:.2f} Hz, network {m['network_rate']:.3f} Hz, "
                  f"active {m['active_fraction']:.3%} {extra}")

    checks: list[CheckResult] = []
    for chk in task.get("checks", []):
        typ = chk["type"]; op = OPS[chk["op"]]; target = float(chk["value"])
        rname = chk.get("readout", default_readout)
        ridx = readouts.get(rname, np.empty(0, dtype=int))
        w = chk.get("window", window)
        per_readout = typ in ("rate", "ratio", "readout_active_fraction")
        tag = f"[{chk['cond']}" + (f", {rname}" if (rname != "default" and per_readout) else "") + (f", {w[0]:g}-{w[1]:g}ms" if w != window else "") + "]"
        if typ == "ratio":
            w2 = chk.get("over_window", w)
            a = _metric(results[chk["cond"]], ridx, "rate", *w)
            b = _metric(results[chk["over"]], ridx, "rate", *w2)
            val = (a + EPS) / (b + EPS)
            desc = f"rate{tag} / rate[{chk['over']}] {chk['op']} {target}"
        else:
            val = _metric(results[chk["cond"]], ridx, typ, *w)
            unit = " Hz" if typ.endswith("rate") else ""
            desc = f"{typ.replace('_', ' ')}{tag} {chk['op']} {target}{unit}"
        passed = bool(not np.isnan(val) and op(val, target))
        checks.append(CheckResult(desc, float(val), passed))

    score = sum(ch.passed for ch in checks) / max(len(checks), 1)
    return TaskResult(
        task=task["name"], title=task.get("title", task["name"]), passed=all(ch.passed for ch in checks) and bool(checks),
        score=float(score), checks=checks, measurements=measurements, readout_size=int(readouts[default_readout].size),
        stimulus_sizes=stim_sizes, seconds=time.time() - t0, notes=notes,
    )


def run_suite(c: Connectome, params: LIFParams, tasks: list[dict] | None = None, verbose: bool = False,
              simulator: SimulatorFactory = LIFSimulator) -> dict[str, Any]:
    tasks = tasks or load_tasks()
    results = []
    for task in tasks:
        if verbose:
            print(f"[{task['name']}] {task.get('title', '')}")
        results.append(run_task(task, c, params, verbose=verbose, simulator=simulator))
    total = float(np.mean([r.score for r in results])) if results else 0.0
    tiers = {t["name"]: t.get("tier", "core") for t in tasks}
    tier_scores = {}
    for tier in ("core", "hard"):
        rs = [r.score for r in results if tiers.get(r.task) == tier]
        tier_scores[tier] = float(np.mean(rs)) if rs else None
    return {
        "core_score": tier_scores["core"],
        "hard_score": tier_scores["hard"],
        "tier": sorted({t.get("tier", "core") for t in tasks}),
        "connectome": c.name,
        "n_neurons": c.n,
        "n_edges": c.n_edges,
        "params": asdict(params),
        "simulator": f"{simulator.__module__}.{getattr(simulator, '__name__', type(simulator).__name__)}",
        "score": total,
        "passed": sum(r.passed for r in results),
        "n_tasks": len(results),
        "tasks": [asdict(r) for r in results],
    }


def save_report(report: dict, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))
    return path


def leaderboard(reports: list[dict]) -> str:
    """Markdown table across many result files."""
    if not reports:
        return "_no results_"
    task_names: list[str] = []
    for r in reports:
        for t in r["tasks"]:
            if t["task"] not in task_names:
                task_names.append(t["task"])
    head = "| run | connectome | simulator | gain | w_syn | core | hard | max brain active | " + " | ".join(task_names) + " |"
    sep = "|" + "---|" * (8 + len(task_names))
    rows = []
    fmt = lambda v: "–" if v is None else f"{v:.2f}"  # noqa: E731
    # rank by core score, then hard score: a model must reproduce the known reflexes before its hard-tier wins count
    for r in sorted(reports, key=lambda r: (-(r.get("core_score") or 0), -(r.get("hard_score") or 0))):
        by_name = {t["task"]: t for t in r["tasks"]}
        cells = [("✅" if by_name[n]["passed"] else f"{by_name[n]['score']:.0%}") if n in by_name else "–" for n in task_names]
        p = r["params"]
        sim = r.get("simulator", "flybench.sim.LIFSimulator").replace("flybench.sim.", "")
        max_active = max((m["active_fraction"] for t in r["tasks"] for m in t["measurements"].values()), default=0.0)
        rows.append(f"| {r.get('label', '')} | {r['connectome']} | {sim} | {p['gain']} | {p['w_syn_mv']} | {fmt(r.get('core_score'))} | {fmt(r.get('hard_score'))} | {max_active:.1%} | " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *rows])
