"""The simulator adapter contract, and `flybench verify-adapter`.

flybench does not care how a model simulates, only what fires. An adapter is anything that can be
called as ``Simulator(connectome, params)`` and returns an object with

    run(duration_ms, stimuli) -> SimResult

where ``stimuli`` is a list of :class:`flybench.sim.Stimulus` and :class:`flybench.sim.SimResult`
holds spike times (ms, float32) and neuron indices (int32, in the connectome's row order).
:class:`SimulatorAdapter` below is the contract written down as a base class; subclassing it is
optional — the reference :class:`flybench.sim.LIFSimulator` does, an external model may duck-type.

Capabilities (a class attribute ``capabilities``, a frozenset of names from :data:`CAPABILITIES`)
say what the adapter honours beyond running a connectome. A task lists ``requires_capabilities``;
an adapter without them is *skipped* on that task, never failed (docs/rfcs/26_mb_sparseness_apl.md).

``flybench verify-adapter module:Class`` runs the contract against the toy connectome and names
every defect: wrong result types, spikes outside the run, neuron ids out of range, a model that
ignores its seed or ignores its stimuli, a ramp that does not ramp, a declared capability that
does not hold. It is the check a maintainer runs before a submission is merged (CONTRIBUTING §3).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .connectome import Connectome
from .sim import LIFParams, SimResult, Stimulus

# The vocabulary of `capabilities` / `requires_capabilities`. Every name has a verify-adapter test.
CAPABILITIES: dict[str, str] = {
    "can_silence": "honours a connectome whose silenced neurons have no outgoing synapses (condition-level `silence:`)",
}


class SimulatorAdapter(ABC):
    """What a simulator must provide. The constructor receives the connectome (W is CSR, rows =
    presynaptic, signed synapse counts) and a :class:`LIFParams` (gain, seed, dt and the reference
    constants; model-specific constants live in ``params.extra``). ``run`` must be deterministic
    under ``params.seed`` and must reset its state at every call unless told otherwise."""

    capabilities: frozenset = frozenset()

    def __init__(self, connectome: Connectome, params: LIFParams | None = None):
        self.c = connectome
        self.p = params or LIFParams()

    @abstractmethod
    def run(self, duration_ms: float, stimuli: list[Stimulus] | None = None) -> SimResult:
        """Simulate `duration_ms` with the given Poisson drives; return every spike."""


# the reference simulators satisfy the contract by duck-typing; register them so isinstance() agrees
from .sim import LIFSimulator as _LIF  # noqa: E402

SimulatorAdapter.register(_LIF)


@dataclass
class Defect:
    name: str
    detail: str


@dataclass
class VerifyReport:
    simulator: str
    capabilities: list[str]
    defects: list[Defect] = field(default_factory=list)
    seconds: float = 0.0
    spikes_per_second: float = 0.0     # throughput on the toy: spikes simulated per wall-clock second

    @property
    def ok(self) -> bool:
        return not self.defects


def _check_result(res: Any, duration: float, n: int, defects: list[Defect], where: str) -> bool:
    """Type and range checks on a SimResult; returns False if the result is unusable."""
    if not isinstance(res, SimResult):
        defects.append(Defect("result_type", f"{where}: run() returned {type(res).__name__}, not flybench.sim.SimResult"))
        return False
    t, ids = np.asarray(res.spike_times_ms), np.asarray(res.spike_neurons)
    if t.ndim != 1 or ids.ndim != 1 or t.shape != ids.shape:
        defects.append(Defect("result_shape", f"{where}: spike_times_ms {t.shape} and spike_neurons {ids.shape} must be 1-d and equal"))
        return False
    if res.n != n:
        defects.append(Defect("result_n", f"{where}: SimResult.n is {res.n}, connectome has {n} neurons"))
    if res.duration_ms != duration:
        defects.append(Defect("result_duration", f"{where}: SimResult.duration_ms is {res.duration_ms}, run asked for {duration}"))
    if t.size and (t.min() < 0 or t.max() >= duration):
        defects.append(Defect("spike_times_range", f"{where}: spike times must lie in [0, {duration}); got [{t.min():.3g}, {t.max():.3g}]"))
    if ids.size and (ids.min() < 0 or ids.max() >= n):
        defects.append(Defect("neuron_ids_range", f"{where}: neuron ids must lie in [0, {n}); got [{ids.min()}, {ids.max()}]"))
    if not np.issubdtype(ids.dtype, np.integer):
        defects.append(Defect("neuron_ids_dtype", f"{where}: spike_neurons dtype is {ids.dtype}, expected an integer type"))
    return True


def _same(a: SimResult, b: SimResult) -> bool:
    return a.spike_times_ms.shape == b.spike_times_ms.shape and np.array_equal(a.spike_times_ms, b.spike_times_ms) and np.array_equal(a.spike_neurons, b.spike_neurons)


def verify_adapter(simulator: Any, connectome: Connectome, gain: float = 1.0) -> VerifyReport:
    """Run the contract against `connectome` (the toy, normally). Every defect is named; an empty
    list means the adapter can be used for a run whose results are comparable to the reference."""
    from .bench import silence_neurons

    name = f"{getattr(simulator, '__module__', '?')}.{getattr(simulator, '__name__', type(simulator).__name__)}"
    caps = getattr(simulator, "capabilities", None)
    defects: list[Defect] = []
    if caps is None:
        defects.append(Defect("capabilities_missing", "no `capabilities` attribute: declare `capabilities = frozenset()` (or the names you honour) so tasks that need more can skip you"))
        caps = frozenset()
    else:
        try:
            caps = frozenset(caps)
        except TypeError:
            defects.append(Defect("capabilities_type", f"`capabilities` must be a set of names, got {type(caps).__name__}"))
            caps = frozenset()
        for cap in sorted(caps):
            if cap not in CAPABILITIES:
                defects.append(Defect("capabilities_unknown", f"declared capability {cap!r} is not one of {sorted(CAPABILITIES)}"))
    rep = VerifyReport(simulator=name, capabilities=sorted(caps), defects=defects)

    n = connectome.n
    duration = 600.0
    grn = connectome.select("GRN_sugar") if connectome.select("GRN_sugar").size else np.arange(min(20, n))
    drive = [Stimulus(neurons=grn, rate_hz=100.0, t_start_ms=100.0, t_end_ms=500.0, name="drive")]

    # 1. construct and run
    t0 = time.time()
    try:
        sim = simulator(connectome, LIFParams(gain=gain, seed=1))
    except Exception as e:  # noqa: BLE001
        defects.append(Defect("construct", f"Simulator(connectome, params) raised {type(e).__name__}: {e}"))
        return rep
    if not hasattr(sim, "run") or not callable(sim.run):
        defects.append(Defect("no_run", "the simulator object has no callable run(duration_ms, stimuli)"))
        return rep
    try:
        res = sim.run(duration, drive)
    except Exception as e:  # noqa: BLE001
        defects.append(Defect("run_raises", f"run() raised {type(e).__name__}: {e}"))
        return rep
    rep.seconds = time.time() - t0
    if not _check_result(res, duration, n, defects, "driven run"):
        return rep
    rep.spikes_per_second = float(len(res.spike_times_ms) / max(rep.seconds, 1e-9))

    # 2. the drive is honoured: driven neurons fire near the requested rate inside the window, not outside it
    inside = res.rate_hz(grn, 100.0, 500.0)
    before = res.rate_hz(grn, 0.0, 100.0)
    if not (50.0 <= inside <= 150.0):
        defects.append(Defect("stimulus_ignored", f"neurons driven at 100 Hz fire at {inside:.1f} Hz in the stimulus window (expected 50–150)"))
    if before > 5.0:
        defects.append(Defect("stimulus_timing", f"driven neurons fire at {before:.1f} Hz before the stimulus starts"))

    # 3. silence in, silence out: no drive, no spikes (a model with spontaneous activity must say so — it is a different model)
    quiet = sim.run(duration, [])
    if _check_result(quiet, duration, n, defects, "quiet run") and quiet.rate_hz(None, 0.0, duration) > 0.5:
        defects.append(Defect("spontaneous_activity", f"with no stimulus the network fires at {quiet.rate_hz(None, 0.0, duration):.2f} Hz per neuron; the reference is silent"))

    # 4. determinism: same seed -> identical spikes; the seed is used -> a different seed differs
    again = simulator(connectome, LIFParams(gain=gain, seed=1)).run(duration, drive)
    if isinstance(again, SimResult) and not _same(res, again):
        defects.append(Defect("nondeterministic", "two runs with the same seed gave different spikes; results would not be reproducible"))
    other = simulator(connectome, LIFParams(gain=gain, seed=2)).run(duration, drive)
    if isinstance(other, SimResult) and _same(res, other):
        defects.append(Defect("seed_ignored", "seeds 1 and 2 gave identical spikes; `--seeds N` would not sample anything"))
    # 4b. state resets between calls: the second call on the same object matches a fresh object
    rerun = sim.run(duration, drive)
    if isinstance(rerun, SimResult) and not _same(res, rerun):
        defects.append(Defect("state_leaks", "a second run() on the same object differs from the first; run() must reset state (or accept reset=True)"))

    # 5. ramps: rate_end_hz is honoured (late rate > early rate)
    ramp = simulator(connectome, LIFParams(gain=0.01, seed=1)).run(1200.0, [Stimulus(neurons=grn, rate_hz=0.0, t_start_ms=200.0, t_end_ms=1200.0, rate_end_hz=100.0)])
    if isinstance(ramp, SimResult):
        early, late = ramp.rate_hz(grn, 200.0, 400.0), ramp.rate_hz(grn, 1000.0, 1200.0)
        if not (late > 3 * early + 5):
            defects.append(Defect("ramp_ignored", f"a 0 → 100 Hz ramp gave {early:.1f} Hz early and {late:.1f} Hz late; Stimulus.rate_end_hz (see Stimulus.rate_at) is not honoured"))

    # 6. declared capabilities hold
    if "can_silence" in caps:
        # silence the driven neurons: their targets must go quiet while the driven cells still spike (they are forced)
        targets = np.flatnonzero(np.asarray(abs(connectome.W[grn]).sum(axis=0)).ravel() > 0)
        targets = targets[~np.isin(targets, grn)]
        if targets.size:
            sil = simulator(silence_neurons(connectome, grn), LIFParams(gain=gain, seed=1)).run(duration, drive)
            if isinstance(sil, SimResult):
                if sil.rate_hz(targets, 100.0, 500.0) > 0.5:
                    defects.append(Defect("can_silence_false", f"with the driven neurons' outgoing synapses zeroed their targets still fire at {sil.rate_hz(targets, 100.0, 500.0):.1f} Hz; the adapter reads weights from somewhere other than the connectome it was given"))
                if sil.rate_hz(grn, 100.0, 500.0) < 50.0:
                    defects.append(Defect("can_silence_removes_neuron", "silenced neurons stopped firing under drive; silencing zeroes outputs, it does not remove the neuron"))
    return rep
