"""Adaptive leaky integrate-and-fire: the reference model plus spike-frequency adaptation.

A HYPOTHESIS, not a correction. The reference LIF never returns to rest after a stimulus
(task `return_to_rest`). The textbook reason is that real neurons tire: every spike opens
slow potassium currents that pull the membrane down for a few hundred milliseconds
(spike-frequency adaptation; Benda & Herz 2003). Adding that one mechanism is the smallest
change that could plausibly give the network an off switch.

Model (one extra state per neuron):

    tau_m dV/dt = (V_rest − V) + g − a          # a: adaptation, in mV, opposes drive
    tau_a da/dt = −a                            # decays over tau_a
    on spike:  a += b                           # each spike adds b mV of adaptation

`b` and `tau_a` are global like every other constant here: no per-neuron tuning. Ranges
from the literature: tau_a ~ 100–500 ms, b a few mV. Different values are different
hypotheses; the benchmark says which behaviours each one reproduces, not which is "true".

Passing more tasks than the reference does NOT mean this is closer to a real fly. It means
it reproduces more of the listed behaviours. Whether flies actually stop this way is a
question for electrophysiology, not for this file.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..connectome import Connectome
from ..sim import LIFParams, LIFSimulator


@dataclass
class AdaptiveParams:
    b_mv: float = 2.0        # adaptation added per spike (mV)
    tau_a_ms: float = 200.0  # adaptation decay time constant (ms)


class AdaptiveLIFSimulator(LIFSimulator):
    """LIF + spike-frequency adaptation. Extra constants come from `params.extra` if present,
    else from ADAPTIVE_DEFAULTS, so a config can set `params: {gain: 0.45, extra: {b_mv: 3}}`."""

    def __init__(self, connectome: Connectome, params: LIFParams | None = None, adaptive: AdaptiveParams | None = None):
        self.ap = adaptive or AdaptiveParams(**getattr(params, "extra", {}) or {})
        super().__init__(connectome, params)

    def reset(self) -> None:
        super().reset()
        self.a = np.zeros(self.n, dtype=np.float32)
        self._decay_a = np.float32(np.exp(-self.p.dt_ms / self.ap.tau_a_ms))

    def step(self, forced: np.ndarray | None = None) -> np.ndarray:
        p = self.p
        arriving = self.queue[self.qi]
        if arriving.size:
            drive = np.asarray(self.Wrow[arriving].sum(axis=0)).ravel()
            self.g += drive.astype(np.float32)
        # the only change from LIFSimulator.step: "− a" in the membrane equation, and a += b on spike
        self.v += (p.v_rest_mv - self.v + self.g - self.a) * self._decay_m
        self.g *= self._decay_s
        self.a *= self._decay_a
        self.t += p.dt_ms
        can_fire = self.ref_until < self.t
        fired = np.flatnonzero((self.v >= p.v_th_mv) & can_fire)
        if forced is not None and forced.size:
            fired = np.union1d(fired, forced[can_fire[forced]]).astype(np.int32)
        if fired.size:
            self.v[fired] = p.v_reset_mv
            self.ref_until[fired] = self.t + p.t_ref_ms
            self.a[fired] += self.ap.b_mv
        self.queue[self.qi] = fired.astype(np.int32)
        self.qi = (self.qi + 1) % self.delay_steps
        return fired
