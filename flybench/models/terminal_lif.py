"""Terminal-aware LIF: an input synapse on a neuron's axon does not fire the neuron.

A HYPOTHESIS about *where* synapses act, not a new dynamic. The reference LIF is a point neuron:
every input synapse depolarises the one compartment there is. Task 35 (docs/rfcs/35) showed what
that costs in a whole-CNS model: 12 % of the ascending neurons' input synapses sit on their brain-
side terminals (axo-axonic contacts), the point neuron sums them into the soma, and brain activity
fires ascending neurons *backwards* into the nerve cord — a route no fly has.

The smallest documented correction: a synapse on the axon terminal modulates that terminal's
release and does not depolarise the soma (presynaptic inhibition — Burrows & Laurent 1993 in the
locust; in the fly, GABA-B-mediated presynaptic inhibition at ORN terminals, Olsen & Wilson 2008,
Root et al. 2008; excitatory axo-axonic contacts act on release too, but their sign and gain are
not established for these cells and are here ignored rather than invented). Concretely:

    W_soma   = W − T            somatic input: the connectome minus its terminal synapses
    d_j(t)   = Σ_terminal-inputs of j, same kernel as the somatic drive (tau_syn), mV-equivalent
    m_j(t)   = clip(1 + RELEASE_SLOPE · d_j / V_TH_DIST, RELEASE_FLOOR, 1)   for d_j ≤ 0; 1 otherwise
    spike of j delivers m_j · W_soma[j, :]

    RELEASE_FLOOR  0.3   presynaptic inhibition reduces release to ~30 % at saturation
                         (Olsen & Wilson 2008: ORN → PN transmission scaled down by ~70 % under
                         GABA-B activation; MEASURED, a different synapse — CONVENTION here)
    RELEASE_SLOPE  0.7   linear from 1 to the floor over one threshold distance of terminal
                         drive (V_TH_DIST = v_th − v_rest = 7 mV): CONVENTION

Where the dataset carries no terminal information (`connectome.terminal is None`: FlyWire v783,
the toy, every shuffled control) this is the reference LIF exactly — bit for bit. The mechanism is
applied uniformly to every neuron that has terminal synapses (on MaleCNS: the neck-spanning
classes, from neuPrint's per-connection ROI counts, `flybench fetch-terminals`); nothing is tuned
to a task. Open division, n_free_parameters 0.

What passing more tasks would and would not mean: it would mean brain-side inputs no longer fire
ascending neurons, which is anatomy; it would not mean the constants of presynaptic inhibition in
these cells are known.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from ..connectome import Connectome
from ..sim import LIFParams, LIFSimulator

RELEASE_FLOOR = 0.3
RELEASE_SLOPE = 0.7

MODEL_CARD = {
    "name": "terminal-aware LIF (axo-axonic inputs modulate release, not the soma)",
    "engine": "flybench.sim:LIFSimulator + flybench.models.terminal_lif",
    "division": "open",
    "n_free_parameters": 0,
    "constants": {
        "RELEASE_FLOOR": {"value": RELEASE_FLOOR, "provenance": "CONVENTION", "basis": "Olsen & Wilson 2008 (Nature 452:956): GABA-B presynaptic inhibition scales ORN → PN transmission down by up to ~70 %; taken as the saturating floor for every terminal"},
        "RELEASE_SLOPE": {"value": RELEASE_SLOPE, "provenance": "CONVENTION", "basis": "linear from 1 to the floor over one threshold distance (7 mV) of inhibitory terminal drive"},
        "terminal synapses": {"provenance": "MEASURED", "basis": "neuPrint per-connection ROI counts: a post-synapse on the axon side of a neck-spanning neuron (fetch_neuprint.DENDRITIC_SIDE)"},
    },
    "fit_data": "none — constants from the literature or declared conventions; nothing fitted",
    "conflict_of_interest": "written by the flybench maintainer in response to task 35's failed check; graded by the same CI as any other row",
}


class TerminalLIFSimulator(LIFSimulator):
    capabilities = frozenset({"can_silence"})
    model_card = MODEL_CARD

    def __init__(self, connectome: Connectome, params: LIFParams | None = None):
        super().__init__(connectome, params)
        T = connectome.terminal
        if T is None or T.nnz == 0:
            self.Trow = None
            return
        scale = np.float32(self.p.w_syn_mv * self.p.gain)
        W = connectome.W.tocsr()
        # T is signed like W; its magnitude never exceeds the edge it annotates (a perturbed W may be smaller)
        T = abs(T.tocsr()).minimum(abs(W)).multiply(W.sign()).tocsr()
        T.eliminate_zeros()
        self.Trow = (T * scale).tocsr(); self.Trow.sort_indices()
        self.Wrow = ((W - T) * scale).tocsr(); self.Wrow.sort_indices()        # somatic input only
        self.v_th_dist = np.float32(self.p.v_th_mv - self.p.v_rest_mv)
        self.reset()

    def reset(self) -> None:
        super().reset()
        self.d = np.zeros(self.n, dtype=np.float32)      # terminal drive per neuron (mV-equivalent)

    def release(self, neurons: np.ndarray) -> np.ndarray:
        """Release scale of each neuron's terminals now: 1 with no terminal inhibition, down to the floor."""
        d = self.d[neurons]
        m = 1.0 + RELEASE_SLOPE * np.minimum(d, 0.0) / self.v_th_dist
        return np.clip(m, RELEASE_FLOOR, 1.0).astype(np.float32)

    def step(self, forced: np.ndarray | None = None) -> np.ndarray:
        if getattr(self, "Trow", None) is None:
            return super().step(forced)
        p = self.p
        arriving = self.queue[self.qi]
        if arriving.size:
            m = self.release(arriving)
            rows = self.Wrow[arriving]
            drive = np.asarray(sp.diags(m).dot(rows).sum(axis=0)).ravel()       # each spike delivers m_j · W_soma[j, :]
            self.g += drive.astype(np.float32)
            tdrive = np.asarray(self.Trow[arriving].sum(axis=0)).ravel()       # …and its terminal contacts modulate their targets
            self.d += tdrive.astype(np.float32)
        self.v += (p.v_rest_mv - self.v + self.g) * self._decay_m
        self.g *= self._decay_s
        self.d *= self._decay_s
        self.t += p.dt_ms
        can_fire = self.ref_until < self.t
        fired = np.flatnonzero((self.v >= p.v_th_mv) & can_fire)
        if forced is not None and forced.size:
            fired = np.union1d(fired, forced[can_fire[forced]]).astype(np.int32)
        if fired.size:
            self.v[fired] = p.v_reset_mv
            self.ref_until[fired] = self.t + p.t_ref_ms
        self.queue[self.qi] = fired.astype(np.int32)
        self.qi = (self.qi + 1) % self.delay_steps
        return fired
