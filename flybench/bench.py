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

from . import __version__
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
    margin: float = float("nan")   # signed log10 distance from the threshold: +1 = 10x on the passing side, -1 = 10x on the failing side
    basis: str = ""                # where the threshold comes from (citation, or "convention: ...")


def margin_of(value: float, op: str, target: float) -> float:
    """Effect size for a check: how far the measurement sits from the line, in decades, sign = pass side."""
    if not np.isfinite(value):
        return float("nan")
    v, t = max(abs(value), EPS), max(abs(target), EPS)
    m = float(np.log10(v / t))
    return m if op in (">", ">=") else -m


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
    tasks = [yaml.safe_load(Path(p).read_text(encoding="utf-8")) for p in paths]
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
    if name == "spikes_per_neuron":
        if readout.size == 0:
            return float("nan")
        m = (res.spike_times_ms >= w0) & (res.spike_times_ms < w1)
        return float(np.isin(res.spike_neurons[m], readout).sum() / readout.size)
    raise ValueError(f"unknown metric {name}")


def perturb_weights(c: Connectome, sigma: float, seed: int) -> Connectome:
    """Same neurons, same edges, every synapse count multiplied by lognormal(0, sigma) noise."""
    rng = np.random.default_rng(10_000 + seed)
    W = c.W.copy()
    W.data = (W.data * rng.lognormal(0.0, sigma, size=W.data.shape)).astype(np.float32)
    return Connectome(root_ids=c.root_ids, W=W, positions=c.positions, annotations=c.annotations, name=c.name,
                      meta={**c.meta, "weight_jitter": sigma})


def run_task(task: dict, c: Connectome, params: LIFParams, verbose: bool = False,
             simulator: SimulatorFactory = LIFSimulator, seeds: int = 1) -> TaskResult:
    """Run one task. With seeds > 1 every condition is simulated `seeds` times (seed, seed+1, ...);
    a check passes only if it holds on the mean AND on every individual seed, and the per-seed
    pass count is reported, so a knife-edge result cannot masquerade as a robust one."""
    if seeds > 1:
        return _run_task_multiseed(task, c, params, verbose, simulator, seeds)
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
    jittered: dict[float, Any] = {}

    results: dict[str, SimResult] = {}
    measurements: dict[str, dict[str, float]] = {}
    stim_sizes: dict[str, int] = {}
    for cond_name, cond in task["conditions"].items():
        stims = _stimuli(c, cond.get("stimuli", []), stim_sizes)
        for s in stims:
            if s.neurons.size == 0:
                notes.append(f"{cond_name}: stimulus {s.name!r} matched 0 neurons")
        jit = float(cond.get("weight_jitter", 0.0))
        if jit > 0:
            # "a different individual": every synapse count scaled by an independent lognormal factor
            # (sigma = jit, in log units), same wiring diagram. Seeded so conditions are comparable.
            if jit not in jittered:
                jittered[jit] = simulator(perturb_weights(c, jit, params.seed), params)
            res: SimResult = jittered[jit].run(duration, stims)
        else:
            res = sim.run(duration, stims)
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
            unit = " Hz" if typ.endswith("rate") else (" spikes/neuron" if typ == "spikes_per_neuron" else "")
            desc = f"{typ.replace('_', ' ')}{tag} {chk['op']} {target}{unit}"
        passed = bool(not np.isnan(val) and op(val, target))
        checks.append(CheckResult(desc, float(val), passed, margin_of(float(val), chk["op"], target), str(chk.get("basis", ""))))

    score = sum(ch.passed for ch in checks) / max(len(checks), 1)
    return TaskResult(
        task=task["name"], title=task.get("title", task["name"]), passed=all(ch.passed for ch in checks) and bool(checks),
        score=float(score), checks=checks, measurements=measurements, readout_size=int(readouts[default_readout].size),
        stimulus_sizes=stim_sizes, seconds=time.time() - t0, notes=notes,
    )


def _run_task_multiseed(task, c, params, verbose, simulator, seeds: int) -> TaskResult:
    from dataclasses import replace
    t0 = time.time()
    runs = [run_task(task, c, replace(params, seed=params.seed + k), verbose=False, simulator=simulator) for k in range(seeds)]
    base = runs[0]
    def nmean(v):  # all-NaN (an empty selector) is a legitimate "no measurement", not a warning
        v = np.asarray(v, dtype=float); return float(v[np.isfinite(v)].mean()) if np.isfinite(v).any() else float("nan")
    def nstd(v):
        v = np.asarray(v, dtype=float); return float(v[np.isfinite(v)].std()) if np.isfinite(v).any() else float("nan")
    # mean of every measurement across seeds
    measurements = {cond: {k: nmean([r.measurements[cond][k] for r in runs]) for k in base.measurements[cond]} for cond in base.measurements}
    checks: list[CheckResult] = []
    for i, ch in enumerate(base.checks):
        vals = np.array([r.checks[i].value for r in runs], dtype=float)
        passes = sum(r.checks[i].passed for r in runs)
        chk = task["checks"][i]
        op = OPS[chk["op"]]; target = float(chk["value"])
        mean = nmean(vals)
        # robust pass: the mean must satisfy the check AND every seed must. A reflex that fires on
        # 2 of 3 random draws is a coin flip, not a reproduced behaviour.
        passed = bool(np.isfinite(mean) and op(mean, target) and passes == seeds)
        desc = f"{ch.description}  [{passes}/{seeds} seeds, sd {nstd(vals):.3g}]"
        checks.append(CheckResult(desc, mean, passed, margin_of(mean, chk["op"], target), str(chk.get("basis", ""))))
    notes = list(dict.fromkeys(n for r in runs for n in r.notes))
    flaky = [f"check {i}: passes on {sum(r.checks[i].passed for r in runs)}/{seeds} seeds" for i in range(len(base.checks))
             if 0 < sum(r.checks[i].passed for r in runs) < seeds]
    if flaky:
        notes.append("seed-sensitive: " + "; ".join(flaky))
    score = sum(ch.passed for ch in checks) / max(len(checks), 1)
    if verbose:
        for cond, m in measurements.items():
            print(f"  {cond:>16}: readout {m['rate']:.2f} Hz (mean of {seeds} seeds), network {m['network_rate']:.3f} Hz, active {m['active_fraction']:.3%}")
    return TaskResult(task=task["name"], title=base.title, passed=all(ch.passed for ch in checks) and bool(checks), score=float(score),
                      checks=checks, measurements=measurements, readout_size=base.readout_size, stimulus_sizes=base.stimulus_sizes,
                      seconds=time.time() - t0, notes=notes)


def run_suite(c: Connectome, params: LIFParams, tasks: list[dict] | None = None, verbose: bool = False,
              simulator: SimulatorFactory = LIFSimulator, seeds: int = 1) -> dict[str, Any]:
    tasks = tasks or load_tasks()
    results = []
    for task in tasks:
        if verbose:
            print(f"[{task['name']}] {task.get('title', '')}")
        results.append(run_task(task, c, params, verbose=verbose, simulator=simulator, seeds=seeds))
    total = float(np.mean([r.score for r in results])) if results else 0.0
    tiers = {t["name"]: t.get("tier", "core") for t in tasks}
    circuits = {t["name"]: t.get("circuit", t["name"]) for t in tasks}
    tier_scores, circuit_scores = {}, {}
    for tier in ("core", "hard"):
        rs = [r.score for r in results if tiers.get(r.task) == tier]
        tier_scores[tier] = float(np.mean(rs)) if rs else None
        # by circuit: seven tasks that all hinge on sugar->MN9 count once, so one pathway cannot dominate the score
        by_c: dict[str, list[float]] = {}
        for r in results:
            if tiers.get(r.task) == tier:
                by_c.setdefault(circuits[r.task], []).append(r.score)
        circuit_scores[tier] = float(np.mean([np.mean(v) for v in by_c.values()])) if by_c else None
    return {
        "schema": 1,
        "flybench_version": __version__,
        "seeds": seeds,
        "verified": False,          # flipped to true by a maintainer who re-ran it (see CONTRIBUTING.md)
        "core_score": tier_scores["core"],
        "hard_score": tier_scores["hard"],
        "core_by_circuit": circuit_scores["core"],   # mean over circuits of the mean task score in that circuit
        "hard_by_circuit": circuit_scores["hard"],
        "circuits": {t["name"]: circuits[t["name"]] for t in tasks},
        "tier": sorted({t.get("tier", "core") for t in tasks}),
        "connectome": c.name,
        "connectome_meta": {k: c.meta.get(k) for k in ("source", "min_synapses", "n", "n_edges")},
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
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
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
    head = "| run | connectome | simulator | gain | w_syn | seeds | verified | core | hard | core by circuit | hard by circuit | max brain active | " + " | ".join(task_names) + " |"
    sep = "|" + "---|" * (12 + len(task_names))
    rows = []
    fmt = lambda v: "–" if v is None else f"{v:.2f}"  # noqa: E731
    # rank by core score, then hard score, then more seeds (more evidence), then verified
    for r in sorted(reports, key=lambda r: (-(r.get("core_score") or 0), -(r.get("hard_score") or 0), -int(r.get("seeds", 1)), -int(bool(r.get("verified"))))):
        by_name = {t["task"]: t for t in r["tasks"]}
        cells = [("✅" if by_name[n]["passed"] else f"{by_name[n]['score']:.0%}") if n in by_name else "–" for n in task_names]
        p = r["params"]
        sim = r.get("simulator", "flybench.sim.LIFSimulator").replace("flybench.sim.", "")
        max_active = max((m["active_fraction"] for t in r["tasks"] for m in t["measurements"].values()), default=0.0)
        ver = "✅" if r.get("verified") else "self-reported"
        rows.append(f"| {r.get('label', '')} | {r['connectome']} | {sim} | {p['gain']} | {p['w_syn_mv']} | {r.get('seeds', 1)} | {ver} | {fmt(r.get('core_score'))} | {fmt(r.get('hard_score'))} | {fmt(r.get('core_by_circuit'))} | {fmt(r.get('hard_by_circuit'))} | {max_active:.1%} | " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *rows])
