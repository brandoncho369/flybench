"""Leaky integrate-and-fire simulation of a whole connectome.

Model (Shiu et al., Nature 2024, "A Drosophila computational brain model
reveals sensorimotor processing"):

    tau_m * dV/dt = (V_rest - V) + g          # membrane
    tau_s * dg/dt = -g                        # exponential synapse (in mV)
    on presynaptic spike (after delay):  g_post += w_syn * gain * W[pre, post]

    V >= V_th  ->  spike, V = V_reset, refractory for t_ref

Every neuron shares the same five constants. That is a *feature* of the
benchmark: with no per-neuron tuning, any reflex the network reproduces is
coming from the wiring, not from us.

The integration is event-driven on the synaptic side: only neurons that
spiked propagate, so a 140k-neuron brain steps in a few ms per 0.1 ms tick
when activity is sparse (which, in a healthy fly brain, it is).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

import numpy as np
import scipy.sparse as sp

from .connectome import Connectome


@dataclass
class LIFParams:
    v_rest_mv: float = -52.0
    v_reset_mv: float = -52.0
    v_th_mv: float = -45.0
    tau_m_ms: float = 20.0
    tau_syn_ms: float = 5.0
    t_ref_ms: float = 2.2
    delay_ms: float = 1.8
    w_syn_mv: float = 0.275     # mV of synaptic drive per synapse (Shiu 2024)
    gain: float = 1.0           # global multiplier on all weights
    dt_ms: float = 0.1
    seed: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "LIFParams":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Stimulus:
    """Poisson spike drive applied directly to a set of neurons."""

    neurons: np.ndarray
    rate_hz: float
    t_start_ms: float = 0.0
    t_end_ms: float = float("inf")
    name: str = ""


@dataclass
class SimResult:
    spike_times_ms: np.ndarray      # float32
    spike_neurons: np.ndarray       # int32
    duration_ms: float
    n: int

    def rate_hz(self, neurons: Iterable[int] | None = None, t0: float = 0.0, t1: float | None = None) -> float:
        """Mean firing rate per neuron over the window [t0, t1)."""
        t1 = self.duration_ms if t1 is None else t1
        m = (self.spike_times_ms >= t0) & (self.spike_times_ms < t1)
        if neurons is not None:
            neurons = np.asarray(neurons)
            if len(neurons) == 0:
                return float("nan")
            m &= np.isin(self.spike_neurons, neurons)
            count = len(neurons)
        else:
            count = self.n
        window_s = max(t1 - t0, 1e-9) / 1000.0
        return float(m.sum() / count / window_s)

    def counts(self) -> np.ndarray:
        return np.bincount(self.spike_neurons, minlength=self.n)

    def active_fraction(self, t0: float = 0.0, t1: float | None = None) -> float:
        t1 = self.duration_ms if t1 is None else t1
        m = (self.spike_times_ms >= t0) & (self.spike_times_ms < t1)
        return float(len(np.unique(self.spike_neurons[m])) / self.n)


class LIFSimulator:
    def __init__(self, connectome: Connectome, params: LIFParams | None = None):
        self.c = connectome
        self.p = params or LIFParams()
        self.n = connectome.n
        # rows = pre. Scale once so propagation is a plain row-sum.
        self.Wrow: sp.csr_matrix = (connectome.W * (self.p.w_syn_mv * self.p.gain)).tocsr()
        self.Wrow.sort_indices()
        self.rng = np.random.default_rng(self.p.seed)
        self.reset()

    # ---- state -------------------------------------------------------
    def reset(self) -> None:
        """Fresh state AND a fresh random stream, so every condition in a task sees identical noise."""
        p = self.p
        self.rng = np.random.default_rng(p.seed)
        self.v = np.full(self.n, p.v_rest_mv, dtype=np.float32)
        self.g = np.zeros(self.n, dtype=np.float32)
        self.ref_until = np.full(self.n, -1.0, dtype=np.float32)
        self.t = 0.0
        self.delay_steps = max(1, int(round(p.delay_ms / p.dt_ms)))
        self.queue: list[np.ndarray] = [np.empty(0, dtype=np.int32) for _ in range(self.delay_steps)]
        self.qi = 0
        self._decay_m = np.float32(p.dt_ms / p.tau_m_ms)
        self._decay_s = np.float32(np.exp(-p.dt_ms / p.tau_syn_ms))

    # ---- stepping ----------------------------------------------------
    def step(self, forced: np.ndarray | None = None) -> np.ndarray:
        """Advance one dt. `forced` = neuron indices that spike this tick regardless of V."""
        p = self.p
        # 1. deliver spikes whose delay expired
        arriving = self.queue[self.qi]
        if arriving.size:
            drive = np.asarray(self.Wrow[arriving].sum(axis=0)).ravel()
            self.g += drive.astype(np.float32)
        # 2. integrate
        self.v += (p.v_rest_mv - self.v + self.g) * self._decay_m
        self.g *= self._decay_s
        self.t += p.dt_ms
        # 3. threshold, honouring refractory
        can_fire = self.ref_until < self.t
        fired = np.flatnonzero((self.v >= p.v_th_mv) & can_fire)
        if forced is not None and forced.size:
            fired = np.union1d(fired, forced[can_fire[forced]]).astype(np.int32)
        if fired.size:
            self.v[fired] = p.v_reset_mv
            self.ref_until[fired] = self.t + p.t_ref_ms
        # 4. queue for delayed delivery
        self.queue[self.qi] = fired.astype(np.int32)
        self.qi = (self.qi + 1) % self.delay_steps
        return fired

    def run(
        self,
        duration_ms: float,
        stimuli: list[Stimulus] | None = None,
        on_step: Callable[[float, np.ndarray], None] | None = None,
        reset: bool = True,
    ) -> SimResult:
        if reset:
            self.reset()
        stimuli = stimuli or []
        p = self.p
        n_steps = int(round(duration_ms / p.dt_ms))
        times: list[np.ndarray] = []
        ids: list[np.ndarray] = []
        stim = [(np.asarray(s.neurons, dtype=np.int32), s.rate_hz * p.dt_ms / 1000.0, s.t_start_ms, s.t_end_ms) for s in stimuli if len(s.neurons)]
        for _ in range(n_steps):
            forced_parts = []
            for neurons, prob, t0, t1 in stim:
                if t0 <= self.t < t1:
                    forced_parts.append(neurons[self.rng.random(neurons.size) < prob])
            forced = np.concatenate(forced_parts) if forced_parts else None
            fired = self.step(forced)
            if fired.size:
                times.append(np.full(fired.size, self.t, dtype=np.float32))
                ids.append(fired.astype(np.int32))
            if on_step is not None:
                on_step(self.t, fired)
        st = np.concatenate(times) if times else np.empty(0, dtype=np.float32)
        si = np.concatenate(ids) if ids else np.empty(0, dtype=np.int32)
        return SimResult(spike_times_ms=st, spike_neurons=si, duration_ms=duration_ms, n=self.n)
