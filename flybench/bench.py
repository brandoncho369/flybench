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


def load_tasks(paths: list[Path] | None = None) -> list[dict]:
    paths = paths or sorted(TASK_DIR.glob("*.yaml"))
    return [yaml.safe_load(Path(p).read_text()) for p in paths]


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


def run_task(task: dict, c: Connectome, params: LIFParams, verbose: bool = False,
             simulator: SimulatorFactory = LIFSimulator) -> TaskResult:
    t0 = time.time()
    notes: list[str] = []
    readout = c.select(task["readout"]["select"])
    if readout.size == 0:
        notes.append("readout selector matched 0 neurons")
    duration = float(task.get("duration_ms", 1000))
    window = task.get("window", [0, duration])
    sim = simulator(c, params)

    measurements: dict[str, dict[str, float]] = {}
    stim_sizes: dict[str, int] = {}
    for cond_name, cond in task["conditions"].items():
        stims = _stimuli(c, cond.get("stimuli", []), stim_sizes)
        for s in stims:
            if s.neurons.size == 0:
                notes.append(f"{cond_name}: stimulus {s.name!r} matched 0 neurons")
        res: SimResult = sim.run(duration, stims)
        measurements[cond_name] = {
            "rate": res.rate_hz(readout, window[0], window[1]),
            "network_rate": res.rate_hz(None, window[0], window[1]),
            "active_fraction": res.active_fraction(window[0], window[1]),
            "spikes": float(len(res.spike_times_ms)),
        }
        if verbose:
            print(f"  {cond_name:>14}: readout {measurements[cond_name]['rate']:.2f} Hz, "
                  f"network {measurements[cond_name]['network_rate']:.3f} Hz, "
                  f"active {measurements[cond_name]['active_fraction']:.3%}")

    checks: list[CheckResult] = []
    for chk in task.get("checks", []):
        typ = chk["type"]; op = OPS[chk["op"]]; target = float(chk["value"])
        if typ == "rate":
            val = measurements[chk["cond"]]["rate"]
            desc = f"readout rate[{chk['cond']}] {chk['op']} {target} Hz"
        elif typ == "network_rate":
            val = measurements[chk["cond"]]["network_rate"]
            desc = f"network rate[{chk['cond']}] {chk['op']} {target} Hz"
        elif typ == "active_fraction":
            val = measurements[chk["cond"]]["active_fraction"]
            desc = f"active fraction[{chk['cond']}] {chk['op']} {target}"
        elif typ == "ratio":
            a = measurements[chk["cond"]]["rate"]; b = measurements[chk["over"]]["rate"]
            val = (a + EPS) / (b + EPS)
            desc = f"rate[{chk['cond']}] / rate[{chk['over']}] {chk['op']} {target}"
        else:
            raise ValueError(f"unknown check type {typ}")
        passed = bool(not np.isnan(val) and op(val, target))
        checks.append(CheckResult(desc, float(val), passed))

    score = sum(ch.passed for ch in checks) / max(len(checks), 1)
    return TaskResult(
        task=task["name"], title=task.get("title", task["name"]), passed=all(ch.passed for ch in checks) and bool(checks),
        score=float(score), checks=checks, measurements=measurements, readout_size=int(readout.size),
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
    return {
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
    task_names = [t["task"] for t in reports[0]["tasks"]]
    head = "| run | connectome | simulator | gain | w_syn | score | max brain active | " + " | ".join(task_names) + " |"
    sep = "|" + "---|" * (7 + len(task_names))
    rows = []
    for r in sorted(reports, key=lambda r: -r["score"]):
        cells = ["✅" if t["passed"] else f"{t['score']:.0%}" for t in r["tasks"]]
        p = r["params"]
        sim = r.get("simulator", "flybench.sim.LIFSimulator").replace("flybench.sim.", "")
        max_active = max((m["active_fraction"] for t in r["tasks"] for m in t["measurements"].values()), default=0.0)
        rows.append(f"| {r.get('label', '')} | {r['connectome']} | {sim} | {p['gain']} | {p['w_syn_mv']} | {r['score']:.2f} | {max_active:.1%} | " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *rows])
