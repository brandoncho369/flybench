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

A `matrix` check is sugar for one check per (condition, readout) cell with an expected sign:

      - {type: matrix, metric: spikes_per_neuron, value: 1, basis: "...",
         expect: {lc16: {mdn: "+", gf: "-"}, lc4: {gf: "+", mdn: {sign: "-", basis: "..."}}}}

"+" expands to `op: ">="` (the readout must respond), "-" to `op: "<"` (a null check: it must
stay silent), "?" is not scored. See expand_checks().

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
from .scoring import grade_check, iqm, performance_profile, run_score, stratified_bootstrap_ci
from .sim import LIFParams, LIFSimulator, SimResult, Stimulus

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq}
EPS = 1e-3
CEILING_FRACTION = 0.8   # a readout at ≥ 80 % of its refractory-limited rate is "at ceiling" (docs/rfcs/S1_ceiling_gate.md)
FLOOR_HZ = 2.0           # a readout under 2 Hz is silent (the task-05 null convention); a comparison between silences is not a pass (docs/rfcs/S2_response_floor.md)
TASK_DIR = Path(__file__).resolve().parent.parent / "tasks"


@dataclass
class CheckResult:
    description: str
    value: float
    passed: bool
    margin: float = float("nan")   # signed log10 distance from the threshold: +1 = 10x on the passing side, -1 = 10x on the failing side
    basis: str = ""                # where the threshold comes from (citation, or "convention: ...")
    graded: float = 0.0            # [0, 1] score without the cliff (flybench.scoring); divided by `ceiling` when one is set
    z: float = float("nan")        # (value − observed mean) / observed sd when the check carries a recording; NaN otherwise
    ceiling: float | None = None   # the score a perfect model of the (non-deterministic) fly would get
    capped: bool = False           # graded exceeded the ceiling and was clipped to 1
    per_seed: list[float] = field(default_factory=list)   # the value on each seed (multi-seed runs)
    op: str = ""                   # the check's comparison and target, so a result file can be re-scored
    target: float = float("nan")
    saturated: bool = False        # comparison check whose every side sat at the refractory ceiling: failed, uninformative (RFC S1)
    floored: bool = False          # comparison check whose every side was silent (< FLOOR_HZ): failed, uninformative (RFC S2)


def _graded_check(desc: str, value: float, passed: bool, chk: dict, per_seed: list[float] | None = None) -> CheckResult:
    """Build a CheckResult with margin and graded score. For a check with a recording (`observed`
    with a finite sd) the pass flag comes from |z| < k; otherwise it is the threshold pass."""
    margin = margin_of(value, chk["op"], float(chk["value"]))
    g, z, pass_z, ceiling, capped = grade_check(value, margin, chk.get("observed"), chk.get("ceiling"), float(chk.get("k", 2.0)))
    if np.isfinite(z):
        passed = pass_z
    return CheckResult(desc, float(value), bool(passed), margin, str(chk.get("basis", "")), g, z, ceiling, capped, list(per_seed or []),
                       str(chk["op"]), float(chk["value"]))


def margin_of(value: float, op: str, target: float) -> float:
    """Effect size for a check: how far the measurement sits from the line, in decades, sign = pass side."""
    if not np.isfinite(value):
        return float("nan")
    if target < 0:
        # mirror a negative target (rho < -0.5, say) onto the positive axis with the op flipped, so
        # the rules below only ever see target > 0
        flipped = {">": "<", ">=": "<=", "<": ">", "<=": ">=", "==": "=="}[op]
        return margin_of(-value, flipped, -target)
    # a value on the other side of zero from the target (a negative rank correlation against a
    # positive threshold) is as far from the line as a zero response, not |value| away from it
    v, t = (EPS if value <= 0 else max(abs(value), EPS)), max(abs(target), EPS)
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
    graded: float = 0.0            # mean graded score over checks
    graded_per_seed: list[float] = field(default_factory=list)
    # negative controls (flybench.controls): score of the same task on shuffled wiring
    controls: dict[str, dict[str, float | bool]] = field(default_factory=dict)
    specificity: float | None = None      # score(real) - max(score(control)); None when no controls ran
    non_diagnostic: bool = False          # some control also passed: the task is not measuring the wiring


BODY_METRIC_TYPES = ("takeoff", "takeoff_latency", "n_commands", "thorax_rise")   # flybench.embodied.BODY_METRICS

MATRIX_SIGNS = {"+": ">=", "-": "<", "−": "<"}      # a cell's expected sign -> the op of its expanded check
MATRIX_UNSCORED = {"?", ".", "", None}


def expand_checks(task: dict) -> dict:
    """Return the task with every `matrix` check replaced by its per-cell checks (a task without
    one is returned as is). A cell is `expect[cond][readout]`: "+" -> `{type: metric, cond, readout,
    op: ">=", value}`, "-" -> the same with `op: "<"`, "?" -> no check. A cell may be a mapping
    `{sign, basis}` to carry its own citation; otherwise the matrix's `basis` is used. Cells are
    emitted in the YAML's row-major order so results line up with the grid in the task file."""
    if not any(ch.get("type") == "matrix" for ch in task.get("checks", []) or []):
        return task
    out: list[dict] = []
    for ch in task["checks"]:
        if ch.get("type") != "matrix":
            out.append(ch)
            continue
        metric = ch.get("metric", "spikes_per_neuron")
        for cond, row in (ch.get("expect") or {}).items():
            for rname, cell in (row or {}).items():
                sign, basis = (cell.get("sign"), cell.get("basis")) if isinstance(cell, dict) else (cell, None)
                if sign in MATRIX_UNSCORED:
                    continue
                if sign not in MATRIX_SIGNS:
                    raise ValueError(f"matrix cell {cond}/{rname}: sign must be '+', '-' or '?', not {sign!r}")
                op = MATRIX_SIGNS[sign]
                cell_chk = {"type": metric, "cond": cond, "readout": rname, "op": op, "value": ch["value"],
                            "basis": basis or ch.get("basis", ""), "cell": [cond, rname, "+" if op == ">=" else "-"]}
                for key in ("window", "observed", "ceiling", "k"):
                    if key in ch:
                        cell_chk[key] = ch[key]
                out.append(cell_chk)
    return {**task, "checks": out}


def load_tasks(paths: list[Path] | None = None, tier: str = "all", include_retired: bool = False) -> list[dict]:
    """tier: 'core' (reflexes the reference LIF must pass), 'hard', or 'all'. A task with `status: retired`
    (docs/GOVERNANCE.md) is skipped unless asked for by path or with include_retired."""
    explicit = paths is not None
    paths = paths or sorted(TASK_DIR.glob("*.yaml"))
    tasks = [expand_checks(yaml.safe_load(Path(p).read_text(encoding="utf-8"))) for p in paths]
    if tier != "all":
        tasks = [t for t in tasks if t.get("tier", "core") == tier]
    if not explicit and not include_retired:
        tasks = [t for t in tasks if t.get("status", "active") != "retired"]
    return tasks


def _stimuli(c: Connectome, spec_list: list[dict], sizes: dict[str, int], duration_ms: float = float("inf"), seed: int = 0) -> list[Stimulus]:
    out = []
    for i, s in enumerate(spec_list):
        if s.get("frontend"):
            # a sensory front end (flybench.frontends): the stimulus is a named movie, the neurons are
            # every driven cell type present here, the rates are the front end's per-column output
            if s["frontend"] != "flyvis":
                raise ValueError(f"unknown frontend {s['frontend']!r}")
            from .frontends.flyvis_frontend import stimuli_from_cache
            stims, fsizes = stimuli_from_cache(c, s["stimulus"], float(s.get("t_start_ms", 0.0)), scale=float(s.get("scale", 1.0)), seed=seed)
            name = s.get("name", f"{s['frontend']}:{s['stimulus']}")
            sizes[name] = int(sum(fsizes.values()))
            out.extend(stims)
            continue
        neurons = c.select(s["select"])
        name = s.get("name", f"stim{i}")
        sizes[name] = int(neurons.size)
        # a ramp needs a finite end to ramp towards: the run's end unless the task says otherwise
        t_end_default = duration_ms if s.get("rate_end_hz") is not None else float("inf")
        out.append(Stimulus(neurons=neurons, rate_hz=float(s.get("rate_hz", 100.0)),
                            t_start_ms=float(s.get("t_start_ms", 0.0)),
                            t_end_ms=float(s.get("t_end_ms", t_end_default)), name=name,
                            rate_end_hz=None if s.get("rate_end_hz") is None else float(s["rate_end_hz"])))
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
    if name == "population_sparseness":
        # Willmore & Tolhurst 2001 sparseness of one condition's response *across the readout's
        # neurons* (lifetime_sparseness is the same formula across conditions): 1 = one neuron
        # carries all the spikes, 0 = every neuron fires equally; NaN if the readout is silent
        if readout.size < 2:
            return float("nan")
        m = (res.spike_times_ms >= w0) & (res.spike_times_ms < w1)
        return lifetime_sparseness(np.bincount(res.spike_neurons[m], minlength=res.n)[readout])
    raise ValueError(f"unknown metric {name}")


def first_spike_ms(res: SimResult, readout: np.ndarray, t0: float, t1: float) -> float:
    """Median over the readout's neurons of each neuron's first spike time in [t0, t1); NaN if none spike."""
    if readout.size == 0:
        return float("nan")
    m = (res.spike_times_ms >= t0) & (res.spike_times_ms < t1) & np.isin(res.spike_neurons, readout)
    if not m.any():
        return float("nan")
    t, n = res.spike_times_ms[m], res.spike_neurons[m]
    order = np.argsort(t, kind="stable")
    _, first_idx = np.unique(n[order], return_index=True)
    return float(np.median(t[order][first_idx]))


def first_spikes_per_neuron(res: SimResult, readout: np.ndarray, t0: float, t1: float) -> np.ndarray:
    """Each readout neuron's first spike time in [t0, t1), NaN for a neuron that never fires there."""
    out = np.full(readout.size, np.nan)
    if readout.size == 0:
        return out
    m = (res.spike_times_ms >= t0) & (res.spike_times_ms < t1) & np.isin(res.spike_neurons, readout)
    if not m.any():
        return out
    t, n = res.spike_times_ms[m], res.spike_neurons[m]
    order = np.argsort(t, kind="stable")
    first_n, first_idx = np.unique(n[order], return_index=True)
    lookup = {int(nid): i for i, nid in enumerate(readout)}
    out[[lookup[int(x)] for x in first_n]] = t[order][first_idx]
    return out


MIN_RANK_N = 10   # a recruitment order needs at least this many neurons (docs/PLAN.md: >= 10 MNs per leg)
RANK_ATTRIBUTES = ("input_synapses",)


def recruitment_order(first_ms: np.ndarray, attribute: np.ndarray) -> float:
    """Spearman rho between a per-neuron attribute (MN size) and recruitment time: the Henneman
    size principle is rho > 0 (smaller neurons fire first). A neuron that never fires is ranked
    last (tied), as an unrecruited unit is in a ramp. NaN with fewer than MIN_RANK_N neurons or
    fewer than two recruited: an order over nothing is not a fail with a number, it is undefined."""
    from scipy.stats import spearmanr
    t = np.asarray(first_ms, dtype=float)
    a = np.asarray(attribute, dtype=float)
    if t.size < MIN_RANK_N or np.isfinite(t).sum() < 2 or np.unique(a).size < 2:
        return float("nan")
    t = np.where(np.isfinite(t), t, np.inf)
    rho = spearmanr(a, t).statistic
    return float(rho) if np.isfinite(rho) else float("nan")


def recruitment_spread(first_ms: np.ndarray) -> float:
    """Interquartile range (ms) of the recruited neurons' first-spike times: a graded recruitment
    spreads over the ramp, a single ignition collapses to ~0. NaN with fewer than four recruited."""
    t = np.asarray(first_ms, dtype=float)
    t = t[np.isfinite(t)]
    if t.size < 4:
        return float("nan")
    q25, q75 = np.percentile(t, [25, 75])
    return float(q75 - q25)


BUMP_STATS = ("resultant", "error_deg")


def bump_statistics(rates: dict[str, float], angles: dict[str, float]) -> tuple[float, float]:
    """Population vector of a ring: readouts at angles (degrees) with mean rates. Returns
    (resultant length R in [0, 1], resultant angle in degrees). R = 1 is one readout carrying all
    the activity, ~0.85 a single cosine bump of 90 deg FWHM, 0 uniform activity or two opposite
    bumps. NaN when the ring is silent."""
    total = 0.0; x = 0.0; y = 0.0
    for name, deg in angles.items():
        r = float(rates.get(name, float("nan")))
        if not np.isfinite(r) or r <= 0:
            continue
        th = np.deg2rad(float(deg))
        x += r * np.cos(th); y += r * np.sin(th); total += r
    if total <= 0:
        return float("nan"), float("nan")
    return float(np.hypot(x, y) / total), float(np.rad2deg(np.arctan2(y, x)) % 360.0)


def angular_error_deg(a: float, b: float) -> float:
    if not (np.isfinite(a) and np.isfinite(b)):
        return float("nan")
    d = abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)
    return float(d)


def lifetime_sparseness(rates: "np.ndarray") -> float:
    """Willmore & Tolhurst 2001 lifetime sparseness of one readout across N stimuli:
    S = (1 − (Σr/N)² / (Σr²/N)) / (1 − 1/N). 1 = responds to one stimulus only, 0 = equally to all.
    Undefined (NaN) when the readout is silent for every stimulus or N < 2."""
    r = np.asarray(rates, dtype=float)
    r = r[np.isfinite(r)]
    n = r.size
    if n < 2 or not (r > 0).any():
        return float("nan")
    return float((1.0 - (r.mean() ** 2) / np.mean(r ** 2)) / (1.0 - 1.0 / n))


KNOWN_DATASETS = ("toy", "flywire783", "malecns")   # names `dataset_only` may list (connectome.name)


from .adapter import CAPABILITIES as _CAPS  # noqa: E402

KNOWN_CAPABILITIES = tuple(_CAPS)   # what `requires_capabilities` may list; simulators declare theirs in `.capabilities` (flybench.adapter)


def simulator_capabilities(simulator: Any) -> frozenset:
    return frozenset(getattr(simulator, "capabilities", ()) or ())


def task_unavailable(task: dict, c: Connectome, simulator: Any = None) -> str | None:
    """A task may declare `requires_readouts: [name, ...]`; if any of those readouts matches no
    neuron on this connectome, the task cannot be run here and is skipped (not failed).
    `dataset_only: [name, ...]` declares the task defined on those connectomes alone (a sexually
    dimorphic circuit, say): elsewhere it is "not applicable" — skipped before any selector runs,
    and the reason says so, because "matches no neurons" would be the wrong story.
    `requires_capabilities: [can_silence, ...]` names what the simulator must declare (its
    `.capabilities`); a simulator without them skips the task."""
    only = task.get("dataset_only")
    if only and c.name not in list(only):
        return f"not applicable: {task['name']} is defined on {'/'.join(only)} only (this is {c.name})"
    for fe in task.get("requires_frontends", []) or []:
        # a front end's cached output must exist (or the front end itself, to render it)
        from .frontends import FRONTENDS
        if fe not in FRONTENDS:
            return f"unknown frontend {fe!r}"
        from .frontends.flyvis_frontend import available, cached
        names = {st.get("stimulus") for cond in task.get("conditions", {}).values() for st in cond.get("stimuli", []) if st.get("frontend") == fe}
        missing = [n for n in names if n and not cached(n)]
        if missing and not available():
            return f"frontend {fe!r} output not cached for {sorted(missing)} and {fe} is not installed"
        if missing:
            from .frontends.flyvis_frontend import render_to_cache
            for n in missing:
                render_to_cache(n)
        # the driven types must exist here
        from .frontends.flyvis_frontend import OUTPUT_TYPES
        if not any(c.select({"cell_type": t}).size for t in OUTPUT_TYPES):
            return f"frontend {fe!r}: none of its output cell types exist on {c.name}"
    if task.get("body"):
        from .embodied import BODIES
        model = task["body"].get("model")
        if model not in BODIES:
            return f"unknown body model {model!r}"
        from .embodied.flygym_body import available as body_available
        if not body_available():
            return "body 'flygym' is not installed (pip install -e .[embodied])"
    needed = set(task.get("requires_capabilities", []) or [])
    if needed and simulator is not None:
        have = simulator_capabilities(simulator)
        missing = sorted(needed - have)
        if missing:
            sname = getattr(simulator, "__name__", type(simulator).__name__)
            return f"simulator {sname} does not declare capability {', '.join(missing)}"
    for name in task.get("requires_readouts", []) or []:
        spec = task.get("readouts", {}).get(name) or (task.get("readout") if name == "default" else None)
        if spec is None:
            return f"requires readout {name!r} which the task does not define"
        if c.select(spec["select"]).size == 0:
            return f"readout {name!r} matches no neurons on {c.name}"
    # `requires_stimuli: [name, ...]`: every stimulus with that name (in any condition) must match
    # at least one neuron here, e.g. a per-hemisphere stimulus on a dataset without side labels
    for name in task.get("requires_stimuli", []) or []:
        specs = [st for cond in task.get("conditions", {}).values() for st in cond.get("stimuli", []) if st.get("name") == name]
        if not specs:
            return f"requires stimulus {name!r} which no condition defines"
        for st in specs:
            if st.get("frontend"):
                continue          # checked above by requires_frontends
            if c.select(st["select"]).size == 0:
                return f"stimulus {name!r} matches no neurons on {c.name}"
    return None


def silence_neurons(c: Connectome, neurons: np.ndarray) -> Connectome:
    """Same neurons, the selected ones' outgoing synapses zeroed: the neuron is still there and
    still receives input (so its own readout stays defined), it just no longer talks — the in
    silico analogue of blocking transmitter release (shibire / TNT), not of ablation."""
    W = c.W.copy().tocsr()
    idx = np.asarray(neurons, dtype=int)
    if idx.size:
        mask = np.zeros(c.n, dtype=bool); mask[idx] = True
        rows = np.repeat(np.arange(c.n), np.diff(W.indptr))
        W.data[mask[rows]] = 0.0
        W.eliminate_zeros()
    T = c.terminal
    if T is not None and idx.size:
        # a silenced neuron's terminal contacts onto others go too (they are its outgoing synapses)
        T = T.copy().tocsr(); trows = np.repeat(np.arange(c.n), np.diff(T.indptr)); T.data[mask[trows]] = 0.0; T.eliminate_zeros()
    return Connectome(root_ids=c.root_ids, W=W, positions=c.positions, annotations=c.annotations, name=c.name,
                      meta={**c.meta, "silenced": int(idx.size)}, terminal=T)


def dump_spikes(res: SimResult, c: Connectome, path: Path, trial: int = 0) -> Path:
    """Write every spike of one simulation as a table (ROADMAP items 54, 40): columns `time_ms`,
    `trial`, `neuron_index`, `root_id` — the spike schema shared by the fly-brain backends. Parquet
    when pyarrow is installed, else gzipped CSV with the same columns; the extension says which."""
    import pandas as pd
    df = pd.DataFrame({"time_ms": np.asarray(res.spike_times_ms, dtype=np.float32),
                       "trial": np.full(len(res.spike_times_ms), int(trial), dtype=np.int32),
                       "neuron_index": np.asarray(res.spike_neurons, dtype=np.int32)})
    df["root_id"] = c.root_ids[df["neuron_index"].to_numpy()]
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import pyarrow  # noqa: F401
        out = path.with_suffix(".parquet"); df.to_parquet(out, index=False)
    except ImportError:
        out = path.with_suffix(".csv.gz"); df.to_csv(out, index=False)
    return out


def perturb_weights(c: Connectome, sigma: float, seed: int) -> Connectome:
    """Same neurons, same edges, every synapse count multiplied by lognormal(0, sigma) noise."""
    rng = np.random.default_rng(10_000 + seed)
    W = c.W.copy()
    W.data = (W.data * rng.lognormal(0.0, sigma, size=W.data.shape)).astype(np.float32)
    # the terminal counts stay as they are (they say *where* a synapse is, not how strong); TerminalLIF clips them to the edge
    return Connectome(root_ids=c.root_ids, W=W, positions=c.positions, annotations=c.annotations, name=c.name, terminal=c.terminal,
                      meta={**c.meta, "weight_jitter": sigma})


def run_task(task: dict, c: Connectome, params: LIFParams, verbose: bool = False,
             simulator: SimulatorFactory = LIFSimulator, seeds: int = 1, dump_dir: Path | str | None = None) -> TaskResult:
    """Run one task. With seeds > 1 every condition is simulated `seeds` times (seed, seed+1, ...);
    a check passes only if it holds on the mean AND on every individual seed, and the per-seed
    pass count is reported, so a knife-edge result cannot masquerade as a robust one.
    `dump_dir`: write every condition's spikes to <dir>/<task>/<condition>_seed<k> (dump_spikes)."""
    task = expand_checks(task)
    if seeds > 1:
        return _run_task_multiseed(task, c, params, verbose, simulator, seeds, dump_dir)
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
    silenced: dict[tuple, Any] = {}      # (jitter, sorted silenced indices) -> simulator on the silenced wiring

    results: dict[str, SimResult] = {}
    measurements: dict[str, dict[str, float]] = {}
    stim_sizes: dict[str, int] = {}
    for cond_name, cond in task["conditions"].items():
        stims = _stimuli(c, cond.get("stimuli", []), stim_sizes, duration, seed=params.seed)
        for s in stims:
            if s.neurons.size == 0:
                notes.append(f"{cond_name}: stimulus {s.name!r} matched 0 neurons")
        jit = float(cond.get("weight_jitter", 0.0))
        if jit > 0 and jit not in jittered and cond.get("silence") is None:
            # "a different individual": every synapse count scaled by an independent lognormal factor
            # (sigma = jit, in log units), same wiring diagram. Seeded so conditions are comparable.
            jittered[jit] = simulator(perturb_weights(c, jit, params.seed), params)
        if cond.get("silence") is not None:
            # `silence: <selector>`: those neurons' outgoing synapses are zeroed for this condition
            # (silence_neurons); the task must list `requires_capabilities: [can_silence]`
            sil = c.select(cond["silence"])
            stim_sizes[f"silence[{cond_name}]"] = int(sil.size)
            if sil.size == 0:
                notes.append(f"{cond_name}: silence selector matched 0 neurons")
            key = (jit, tuple(sil.tolist()))
            if key not in silenced:
                base = perturb_weights(c, jit, params.seed) if jit > 0 else c
                silenced[key] = simulator(silence_neurons(base, sil), params)
            res: SimResult = silenced[key].run(duration, stims)
        elif jit > 0:
            res = jittered[jit].run(duration, stims)
        else:
            res = sim.run(duration, stims)
        results[cond_name] = res
        if dump_dir is not None:
            dump_spikes(res, c, Path(dump_dir) / task["name"] / f"{cond_name}_seed{params.seed}", trial=params.seed)
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

    if task.get("body"):
        # the embodied track (flybench.embodied): the command readout's spikes drive a physics body,
        # and what the body did becomes measurements ordinary checks can score
        from .embodied import BODY_METRICS
        from .embodied.flygym_body import run_body
        cmd = task["body"].get("command", {})
        cmd_readout = cmd.get("readout", default_readout)
        delay = 0.0
        if readouts.get(cmd_readout, np.empty(0, dtype=int)).size == 0 and cmd.get("fallback"):
            # no nerve cord here: the fallback readout (the GF) plus the measured delay to the muscle
            cmd_readout, delay = cmd["fallback"], float(cmd.get("fallback_delay_ms", 0.0))
            notes.append(f"body: command readout {cmd.get('readout')!r} absent, using {cmd_readout!r} + {delay} ms")
        cidx = readouts.get(cmd_readout, np.empty(0, dtype=int))
        for cond_name, cond in task["conditions"].items():
            res = results[cond_name]
            spikes = res.spike_times_ms[np.isin(res.spike_neurons, cidx)] + delay if cidx.size else np.empty(0)
            trace = run_body(spikes.tolist(), duration)
            onsets = [float(st.get("t_start_ms", 0)) for st in cond.get("stimuli", [])]
            onset = min(onsets) if onsets else 0.0
            measurements[cond_name][BODY_METRICS["takeoff"]] = 1.0 if trace.takeoff else 0.0
            measurements[cond_name][BODY_METRICS["takeoff_latency"]] = float(trace.takeoff_ms - onset) if trace.takeoff else float("nan")
            measurements[cond_name][BODY_METRICS["n_commands"]] = float(trace.n_commands)
            measurements[cond_name][BODY_METRICS["thorax_rise"]] = float(trace.thorax_rise_mm)
            if verbose:
                print(f"  {cond_name:>16}: body takeoff={trace.takeoff} at {trace.takeoff_ms - onset if trace.takeoff else float('nan'):.1f} ms, {trace.n_commands} commands")

    checks: list[CheckResult] = []
    input_synapses: np.ndarray | None = None
    for chk in task.get("checks", []):
        typ = chk["type"]; op = OPS[chk["op"]]; target = float(chk["value"])
        rname = chk.get("readout", default_readout)
        ridx = readouts.get(rname, np.empty(0, dtype=int))
        w = chk.get("window", window)
        per_readout = typ in ("rate", "ratio", "readout_active_fraction", "rank_order", "recruitment_spread", "population_sparseness") or "cell" in chk   # a matrix cell always names its readout
        tag = f"[{chk.get('cond', '')}" + (f", {rname}" if (rname != "default" and per_readout) else "") + (f", {w[0]:g}-{w[1]:g}ms" if w != window else "") + "]"
        if typ == "ratio":
            w2 = chk.get("over_window", w)
            metric = chk.get("metric", "rate")        # rate (default), readout_active_fraction, spikes_per_neuron, population_sparseness, latency
            ridx2 = readouts.get(chk.get("over_readout", rname), np.empty(0, dtype=int))   # `over_readout`: compare two readouts (e.g. left vs right pool)
            if metric == "latency":
                # first-spike latency of the readout after each condition's own stimulus onset
                def _lat(cn, idx):
                    onsets = [float(st.get("t_start_ms", 0)) for st in task["conditions"][cn].get("stimuli", [])]
                    t0 = min(onsets) if onsets else float(w[0])
                    return first_spike_ms(results[cn], idx, t0, duration) - t0
                a, b = _lat(chk["cond"], ridx), _lat(chk["over"], ridx2)
            else:
                a = _metric(results[chk["cond"]], ridx, metric, *w)
                b = _metric(results[chk["over"]], ridx2, metric, *w2)
            val = (a + EPS) / (b + EPS)
            mname = metric.replace("_", " ")
            over_tag = f"{chk['over']}, {chk['over_readout']}" if "over_readout" in chk else chk["over"]
            desc = f"{mname}{tag} / {mname}[{over_tag}] {chk['op']} {target}"
        elif typ == "latency":
            # first-spike latency (ms) of the readout after the condition's stimulus onset, or, with
            # `from`, after another readout's first spike (conduction time along a pathway)
            res_c = results[chk["cond"]]
            onsets = [float(st.get("t_start_ms", 0)) for st in task["conditions"][chk["cond"]].get("stimuli", [])]
            t0 = min(onsets) if onsets else float(w[0])
            to_t = first_spike_ms(res_c, ridx, t0, duration)
            if "from" in chk:
                from_t = first_spike_ms(res_c, readouts.get(chk["from"], np.empty(0, dtype=int)), t0, duration)
                val = to_t - from_t
                desc = f"latency[{chk['cond']}, {chk['from']} → {rname}] {chk['op']} {target} ms"
            else:
                val = to_t - t0
                desc = f"latency[{chk['cond']}, {rname}] {chk['op']} {target} ms"
        elif typ == "lifetime_sparseness":
            # one readout's rate across a panel of conditions (an odour panel), Willmore & Tolhurst 2001
            val = lifetime_sparseness([_metric(results[cn], ridx, "rate", *w) for cn in chk["conds"]])
            desc = f"lifetime sparseness[{rname}, {len(chk['conds'])} stimuli] {chk['op']} {target}"
        elif typ == "bump":
            # a ring of readouts at known angles: `stat: resultant` is the population-vector length
            # (one bump vs spread or two bumps), `stat: error_deg` its angle's distance from `cue_deg`
            angles = chk["angles"]
            rates = {rn: _metric(results[chk["cond"]], readouts.get(rn, np.empty(0, dtype=int)), "rate", *w) for rn in angles}
            R, theta = bump_statistics(rates, angles)
            stat = chk.get("stat", "resultant")
            if stat == "resultant":
                val = R
                desc = f"bump resultant[{chk['cond']}, {len(angles)} wedges] {chk['op']} {target}"
            elif stat == "error_deg":
                val = angular_error_deg(theta, float(chk["cue_deg"]))
                desc = f"bump error[{chk['cond']}, vs {float(chk['cue_deg']):g}°] {chk['op']} {target} deg"
            else:
                raise ValueError(f"bump stat must be one of {BUMP_STATS}, not {stat!r}")
        elif typ == "rank_order":
            # recruitment order: Spearman rho between a per-neuron attribute and first-spike time in the window
            by = chk.get("by", "input_synapses")
            if by not in RANK_ATTRIBUTES:
                raise ValueError(f"rank_order `by` must be one of {RANK_ATTRIBUTES}, not {by!r}")
            if input_synapses is None:
                # MN "size" = total input synapse count (Lesser et al. 2024: r = 0.94 with dendritic surface area)
                input_synapses = np.asarray(abs(c.W).sum(axis=0)).ravel()
            val = recruitment_order(first_spikes_per_neuron(results[chk["cond"]], ridx, *w), input_synapses[ridx])
            desc = f"rank order{tag} rho({by.replace('_', ' ')}, recruitment time) {chk['op']} {target}"
        elif typ == "recruitment_spread":
            val = recruitment_spread(first_spikes_per_neuron(results[chk["cond"]], ridx, *w))
            desc = f"recruitment spread{tag} {chk['op']} {target} ms"
        elif typ in BODY_METRIC_TYPES:
            # what the body did (flybench.embodied): takeoff (0/1), takeoff latency (ms from stimulus onset), …
            from .embodied import BODY_METRICS
            val = measurements[chk["cond"]].get(BODY_METRICS[typ], float("nan"))
            unit = " ms" if typ == "takeoff_latency" else (" mm" if typ == "thorax_rise" else "")
            desc = f"body {typ.replace('_', ' ')}[{chk['cond']}] {chk['op']} {target}{unit}"
        else:
            val = _metric(results[chk["cond"]], ridx, typ, *w)
            unit = " Hz" if typ.endswith("rate") else (" spikes/neuron" if typ == "spikes_per_neuron" else "")
            desc = f"{typ.replace('_', ' ')}{tag} {chk['op']} {target}{unit}"
        passed = bool(not np.isnan(val) and op(val, target))
        cr = _graded_check(desc, float(val), passed, chk)
        # RFC S1: a comparison between conditions that all sit at the refractory ceiling is not a pass
        # the compared sides, each as (condition, readout indices, window) — the check's own windows and
        # readouts, so a transient inside a short check window is judged on that window, not the task's
        if typ == "ratio":
            compared = [(chk["cond"], ridx, w), (chk["over"], readouts.get(chk.get("over_readout", rname), np.empty(0, dtype=int)), chk.get("over_window", w))]
        elif typ == "lifetime_sparseness":
            compared = [(cn, ridx, w) for cn in chk["conds"]]
        else:
            compared = []
        if compared:
            ceiling_hz = CEILING_FRACTION * 1000.0 / max(float(getattr(params, "t_ref_ms", 2.2)), 1e-3)
            rates = [_metric(results[cn], idx, "rate", *win) for cn, idx, win in compared]
            if rates and all(np.isfinite(x) and x >= ceiling_hz for x in rates):
                cr.saturated, cr.passed, cr.graded, cr.margin = True, False, 0.0, -10.0   # margin −10: a fail at every τ of the profile
                cr.description += "  [saturated: all compared conditions at ceiling]"
            # RFC S2: the same at the bottom — every compared side silent is a ratio of noise
            elif rates and all(np.isfinite(x) and x < FLOOR_HZ for x in rates):
                cr.floored, cr.passed, cr.graded, cr.margin = True, False, 0.0, -10.0
                cr.description += "  [floored: every compared condition silent]"
        checks.append(cr)

    score = sum(ch.passed for ch in checks) / max(len(checks), 1)
    graded = float(np.mean([ch.graded for ch in checks])) if checks else 0.0
    return TaskResult(
        task=task["name"], title=task.get("title", task["name"]), passed=all(ch.passed for ch in checks) and bool(checks),
        score=float(score), checks=checks, measurements=measurements, readout_size=int(readouts[default_readout].size),
        stimulus_sizes=stim_sizes, seconds=time.time() - t0, notes=notes, graded=graded, graded_per_seed=[graded],
    )


def _run_task_multiseed(task, c, params, verbose, simulator, seeds: int, dump_dir=None) -> TaskResult:
    from dataclasses import replace
    t0 = time.time()
    runs = [run_task(task, c, replace(params, seed=params.seed + k), verbose=False, simulator=simulator, dump_dir=dump_dir) for k in range(seeds)]
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
        sat = all(r.checks[i].saturated for r in runs)
        flo = all(r.checks[i].floored for r in runs)
        base_desc = ch.description.replace("  [saturated: all compared conditions at ceiling]", "").replace("  [floored: every compared condition silent]", "")
        desc = f"{base_desc}  [{passes}/{seeds} seeds, sd {nstd(vals):.3g}]" + ("  [saturated: all compared conditions at ceiling]" if sat else "") + ("  [floored: every compared condition silent]" if flo else "")
        cr = _graded_check(desc, mean, passed, chk, per_seed=[float(v) for v in vals])
        if sat:
            cr.saturated, cr.passed, cr.graded, cr.margin = True, False, 0.0, -10.0
        if flo:
            cr.floored, cr.passed, cr.graded, cr.margin = True, False, 0.0, -10.0
        checks.append(cr)
    notes = list(dict.fromkeys(n for r in runs for n in r.notes))
    flaky = [f"check {i}: passes on {sum(r.checks[i].passed for r in runs)}/{seeds} seeds" for i in range(len(base.checks))
             if 0 < sum(r.checks[i].passed for r in runs) < seeds]
    if flaky:
        notes.append("seed-sensitive: " + "; ".join(flaky))
    score = sum(ch.passed for ch in checks) / max(len(checks), 1)
    # graded score: the mean over checks of the graded score of the seed-mean value; per seed, the same on each seed
    # task graded = mean over seeds of the per-seed graded score (the same statistic the run-level
    # IQM and its bootstrap use); the per-check `graded` is the score of the seed-mean value
    graded_per_seed = [r.graded for r in runs]
    graded = float(np.mean(graded_per_seed))
    if verbose:
        for cond, m in measurements.items():
            print(f"  {cond:>16}: readout {m['rate']:.2f} Hz (mean of {seeds} seeds), network {m['network_rate']:.3f} Hz, active {m['active_fraction']:.3%}")
    return TaskResult(task=task["name"], title=base.title, passed=all(ch.passed for ch in checks) and bool(checks), score=float(score),
                      checks=checks, measurements=measurements, readout_size=base.readout_size, stimulus_sizes=base.stimulus_sizes,
                      seconds=time.time() - t0, notes=notes, graded=graded, graded_per_seed=graded_per_seed)


def peak_rss_mb() -> float:
    """Peak resident set size of this process in MB (ROADMAP item 43, the cost column). Windows via
    the Win32 process counters, POSIX via getrusage; NaN if neither is available."""
    try:
        import resource
        ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        import sys
        return float(ru) / (1024.0 if sys.platform != "darwin" else 1024.0 * 1024.0)   # KB on Linux, bytes on macOS
    except ImportError:
        pass
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
        k32 = ctypes.WinDLL("kernel32", use_last_error=True); psapi = ctypes.WinDLL("psapi", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE          # a pseudo-handle; the default int restype truncates it
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return float(pmc.PeakWorkingSetSize) / (1024.0 * 1024.0)
    except Exception:  # noqa: BLE001
        pass
    return float("nan")


def simulated_seconds(task: dict, seeds: int, n_wirings: int) -> float:
    """Biological seconds this task simulates: conditions × seeds × wirings × duration."""
    return len(task.get("conditions", {})) * seeds * n_wirings * float(task.get("duration_ms", 1000)) / 1000.0


# ---- parallel workers (`--jobs`): one process per (task, wiring) unit -------------------------
# Windows has no fork, so each worker loads the connectome by name/path itself and rebuilds the
# seeded control wiring; the units are independent simulations with their own seeds, so the
# report is bit-identical to a serial run, only the wall-clock changes.
_worker: dict[str, Any] = {}


def _init_worker(connectome_ref: str, cache: str | None, controls: list[str], seed: int, simulator_spec: str | None) -> None:
    from .connectome import load_connectome
    from .controls import make_control
    c = load_connectome(connectome_ref, cache) if cache else load_connectome(connectome_ref)
    _worker["c"] = c
    _worker["controls"] = {name: make_control(c, name, seed=seed) for name in controls}
    _worker["simulator"] = resolve_simulator(simulator_spec)


def _run_unit(task: dict, control: str | None, params: LIFParams, seeds: int, dump_dir=None) -> tuple[str, str | None, TaskResult, float]:
    cc = _worker["c"] if control is None else _worker["controls"][control]
    r = run_task(task, cc, params, verbose=False, simulator=_worker["simulator"], seeds=seeds, dump_dir=(None if control else dump_dir))
    return task["name"], control, r, peak_rss_mb()


def run_suite(c: Connectome, params: LIFParams, tasks: list[dict] | None = None, verbose: bool = False,
              simulator: SimulatorFactory = LIFSimulator, seeds: int = 1,
              controls: list[str] | None = None, jobs: int = 1, connectome_ref: str | None = None,
              cache: str | None = None, simulator_spec: str | None = None, dump_dir: Path | str | None = None) -> dict[str, Any]:
    """controls: names from flybench.controls.CONTROLS. Each task is then also run on that shuffled
    wiring; the task's `specificity` is score(real) - max(score(control)), and a task some control
    also passes is marked `non_diagnostic`.
    jobs > 1 runs the (task, wiring) units in that many processes; it needs `connectome_ref` (the
    name or directory `load_connectome` accepts) so each worker can load the wiring itself."""
    from .controls import make_control
    t_start = time.time()
    tasks = tasks or load_tasks()
    controls = list(controls or [])
    results = []
    skipped: dict[str, str] = {}
    runnable: list[dict] = []
    worker_rss: list[float] = []
    cpu_seconds = 0.0            # simulation time summed over units (wall-clock of a serial run)
    for task in tasks:
        why = task_unavailable(task, c, simulator)
        if why:
            # a task that needs neurons this dataset does not have (e.g. VNC motor neurons on a
            # brain-only connectome), or a capability this simulator does not declare, is not run
            # and not scored, rather than failed
            skipped[task["name"]] = why
            if verbose:
                print(f"[{task['name']}] skipped: {why}")
            continue
        runnable.append(task)
    if jobs > 1 and connectome_ref and runnable:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        if not simulator_spec and simulator is not LIFSimulator:
            # workers import the simulator by name; a module-level class can be found from the object itself
            simulator_spec = f"{simulator.__module__}:{getattr(simulator, '__name__', type(simulator).__name__)}"
        units = [(t, ctl) for t in runnable for ctl in [None, *controls]]
        real: dict[str, TaskResult] = {}
        ctl_scores: dict[str, dict[str, dict[str, float | bool]]] = {t["name"]: {} for t in runnable}
        with ProcessPoolExecutor(max_workers=min(jobs, len(units)), initializer=_init_worker,
                                 initargs=(connectome_ref, cache, controls, params.seed, simulator_spec)) as pool:
            futures = [pool.submit(_run_unit, t, ctl, params, seeds, dump_dir) for t, ctl in units]
            for f in as_completed(futures):
                name, ctl, r, rss = f.result()
                worker_rss.append(rss)
                cpu_seconds += r.seconds
                if ctl is None:
                    real[name] = r
                else:
                    ctl_scores[name][ctl] = {"score": r.score, "passed": r.passed, "checks": [c.passed for c in r.checks]}   # which checks the shuffle passes
                if verbose:
                    print(f"[{name}] {'control: ' + ctl if ctl else 'done'}: {r.score:.2f}")
        pairs = [(t, real[t["name"]]) for t in runnable]
        for t, r in pairs:
            r.controls = {name: ctl_scores[t["name"]][name] for name in controls if name in ctl_scores[t["name"]]}   # declared order, not completion order
    else:
        control_cs = {name: make_control(c, name, seed=params.seed) for name in controls}
        pairs = []
        for task in runnable:
            if verbose:
                print(f"[{task['name']}] {task.get('title', '')}")
            r = run_task(task, c, params, verbose=verbose, simulator=simulator, seeds=seeds, dump_dir=dump_dir)
            cpu_seconds += r.seconds
            for name, cc in control_cs.items():
                if verbose:
                    print(f"[{task['name']}] control: {name}")
                rc = run_task(task, cc, params, verbose=False, simulator=simulator, seeds=seeds)
                cpu_seconds += rc.seconds
                r.controls[name] = {"score": rc.score, "passed": rc.passed, "checks": [c.passed for c in rc.checks]}
            pairs.append((task, r))
    for task, r in pairs:
        if r.controls:
            r.specificity = float(r.score - max(v["score"] for v in r.controls.values()))
            # a task whose checks all say "X must NOT happen" is passed by a dead network too; only
            # tasks that require a response somewhere can be non-diagnostic in the shuffle sense
            positive = any(str(ch.get("op", "")) in (">", ">=") for ch in task.get("checks", []))
            r.non_diagnostic = bool(positive and r.passed and any(v["passed"] for v in r.controls.values()))
            if not positive and r.passed:
                r.notes.append("null task (no check requires a response): shuffled wiring is expected to pass it too")
        results.append(r)
    tasks = [t for t in tasks if t["name"] not in skipped]
    total = float(np.mean([r.score for r in results])) if results else 0.0
    # graded: IQM over tasks of the task graded score; CI by resampling seeds within each task
    graded_total = run_score([r.graded_per_seed for r in results]) if results else 0.0
    ci = stratified_bootstrap_ci([r.graded_per_seed for r in results], seed=params.seed) if results else None
    profile = performance_profile([ch.margin for r in results for ch in r.checks])
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
        "graded": graded_total,                       # IQM over tasks of the cliff-free graded score (flybench.scoring)
        "graded_ci95": list(ci) if ci else None,      # stratified bootstrap over seeds; None with a single seed
        "core_graded": float(np.mean([r.graded for r in results if tiers.get(r.task) == "core"])) if any(tiers.get(r.task) == "core" for r in results) else None,
        "hard_graded": float(np.mean([r.graded for r in results if tiers.get(r.task) == "hard"])) if any(tiers.get(r.task) == "hard" for r in results) else None,
        "profile": profile,                           # fraction of checks with margin ≥ τ decades, τ = -1 … 1
        "circuits": {t["name"]: circuits[t["name"]] for t in tasks},
        "skipped": skipped,   # task -> reason; these are absent from `tasks` and from every score
        "controls": controls,  # negative-control connectomes that were run (flybench.controls)
        "specificity": float(np.mean([r.specificity for r in results])) if controls and results else None,
        "non_diagnostic": [r.task for r in results if r.non_diagnostic],
        "tier": sorted({t.get("tier", "core") for t in tasks}),
        "connectome": c.name,
        "connectome_meta": {k: c.meta.get(k) for k in ("source", "min_synapses", "n", "n_edges")},
        "n_neurons": c.n,
        "n_edges": c.n_edges,
        "params": asdict(params),
        "simulator": f"{simulator.__module__}.{getattr(simulator, '__name__', type(simulator).__name__)}",
        "simulator_capabilities": sorted(simulator_capabilities(simulator)),   # what the adapter declared (flybench.adapter); tasks needing more were skipped
        # ROADMAP item 45: the maintainers' own model is a submission like any other, tagged so the
        # leaderboard shows it as the floor to beat and never as the benchmark's answer
        "reference_baseline": bool(getattr(simulator, "reference_baseline", False)),
        "model_card": getattr(simulator, "model_card", None),
        "score": total,
        "passed": sum(r.passed for r in results),
        "n_tasks": len(results),
        # cost (ROADMAP item 43): wall-clock of this run, CPU seconds summed over units (a serial
        # run's wall-clock), peak RSS of the heaviest process, and simulated biological seconds
        "cost": {
            "wall_seconds": float(time.time() - t_start),
            "cpu_seconds": float(cpu_seconds),
            "jobs": int(jobs if (jobs > 1 and connectome_ref and runnable) else 1),
            "peak_rss_mb": float(np.nanmax([peak_rss_mb(), *worker_rss])) if worker_rss else float(peak_rss_mb()),
            "bio_seconds": float(sum(simulated_seconds(t, seeds, 1 + len(controls)) for t in runnable)),
        },
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
    head = "| run | role | connectome | simulator | gain | w_syn | seeds | verified | core | hard | core by circuit | hard by circuit | graded (95% CI) | specificity | hold-out gap | division | conflict of interest | max brain active | cost | " + " | ".join(task_names) + " |"
    sep = "|" + "---|" * (19 + len(task_names))
    rows = []
    fmt = lambda v: "–" if v is None else f"{v:.2f}"  # noqa: E731
    # rank by pinned first, then core score, then hard score, then more seeds (more evidence), then verified
    for r in sorted(reports, key=lambda r: (int(bool(r.get("unpinned"))), -(r.get("core_score") or 0), -(r.get("hard_score") or 0), -int(r.get("seeds", 1)), -int(bool(r.get("verified"))))):
        by_name = {t["task"]: t for t in r["tasks"]}
        cells = [("✅" if by_name[n]["passed"] else f"{by_name[n]['score']:.0%}") if n in by_name else "–" for n in task_names]
        p = r["params"]
        sim = r.get("simulator", "flybench.sim.LIFSimulator").replace("flybench.sim.", "")
        max_active = max((m["active_fraction"] for t in r["tasks"] for m in t["measurements"].values()), default=0.0)
        ver = ("✅" if r.get("verified") else "self-reported") + (" · unpinned" if r.get("unpinned") else "")
        # specificity: real minus best shuffled-wiring score (flybench.controls); "–" when no controls ran
        spec = "–" if r.get("specificity") is None else f"{r['specificity']:+.2f}"
        g = r.get("graded"); gci = r.get("graded_ci95")
        graded = "–" if g is None else (f"{g:.2f} [{gci[0]:.2f}, {gci[1]:.2f}]" if gci else f"{g:.2f}")
        gap = (r.get("holdout") or {}).get("gap")
        gap_s = "–" if gap is None else f"{gap:+.2f}"
        div = r.get("division") or ("closed" if sim == "LIFSimulator" and not r.get("n_free_parameters") else "open")
        if r.get("n_free_parameters") is not None:
            div += f" ({r['n_free_parameters']}p)"
        # ROADMAP items 45 and 49: baseline rows are the maintainers' reference model; every row may declare a conflict of interest
        role = "reference baseline" if r.get("reference_baseline") else "submission"
        coi = r.get("conflict_of_interest") or "–"
        cost = r.get("cost") or {}
        # CPU seconds per simulated biological second, and peak memory: "–" for results written before the cost column
        if not cost or not cost.get("bio_seconds"):
            cost_s = "–"
        else:
            slow = cost["cpu_seconds"] / cost["bio_seconds"]
            cost_s = (f"{slow:.1f}×" if slow < 10 else f"{slow:.0f}×") + f" real time, {cost.get('peak_rss_mb', float('nan')) / 1024:.1f} GB"
        rows.append(f"| {r.get('label', '')} | {role} | {r['connectome']} | {sim} | {p['gain']} | {p['w_syn_mv']} | {r.get('seeds', 1)} | {ver} | {fmt(r.get('core_score'))} | {fmt(r.get('hard_score'))} | {fmt(r.get('core_by_circuit'))} | {fmt(r.get('hard_by_circuit'))} | {graded} | {spec} | {gap_s} | {div} | {coi} | {max_active:.1%} | {cost_s} | " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *rows])
