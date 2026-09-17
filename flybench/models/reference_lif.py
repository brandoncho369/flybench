"""The reference model, packaged and submitted like any third party (ROADMAP item 45).

`flybench.sim.LIFSimulator` is the engine that ships with the benchmark; this module is the
*model card* for the specific submission the leaderboard calls the reference baseline: that
engine with Shiu et al. 2024's constants and one free parameter, the global gain. It goes
through the same path as everyone else's model — a config in `configs/submissions/`, evaluated
by CI (`flybench evaluate`), its result marked `verified` by the benchmark rather than by its
author — and its row is tagged `reference_baseline` so that no reader mistakes the
maintainers' model for the benchmark's answer. A baseline is a floor to beat, not a claim.

Every constant below is MEASURED or a published modelling CONVENTION; none was fitted here.
"""

from __future__ import annotations

from ..sim import LIFSimulator

MODEL_CARD = {
    "name": "reference LIF (Shiu et al. 2024 constants)",
    "engine": "flybench.sim:LIFSimulator",
    "division": "closed",
    "n_free_parameters": 1,
    "free_parameters": {"gain": "global multiplier on every synaptic weight; swept 0.3–1.0 on FlyWire, 0.45 chosen as the widest window in which the five core reflexes pass on every seed. Not fitted to any task."},
    "constants": {
        "v_rest_mv":  {"value": -52.0,  "provenance": "CONVENTION", "basis": "Shiu et al. 2024 (Nature 634:210) leaky integrate-and-fire; resting potential"},
        "v_reset_mv": {"value": -52.0,  "provenance": "CONVENTION", "basis": "Shiu 2024: reset to rest"},
        "v_th_mv":    {"value": -45.0,  "provenance": "CONVENTION", "basis": "Shiu 2024: 7 mV above rest"},
        "tau_m_ms":   {"value": 20.0,   "provenance": "MEASURED",   "basis": "membrane time constant, Shiu 2024 after Gouwens & Wilson 2009"},
        "tau_syn_ms": {"value": 5.0,    "provenance": "CONVENTION", "basis": "Shiu 2024 synaptic current decay"},
        "t_ref_ms":   {"value": 2.2,    "provenance": "MEASURED",   "basis": "absolute refractory period, Shiu 2024"},
        "delay_ms":   {"value": 1.8,    "provenance": "MEASURED",   "basis": "synaptic delay, Shiu 2024"},
        "w_syn_mv":   {"value": 0.275,  "provenance": "MEASURED",   "basis": "unitary PSP per synapse, Shiu 2024; sign from the dataset's transmitter prediction (GABA/glutamate inhibitory)"},
        "dt_ms":      {"value": 0.1,    "provenance": "CONVENTION", "basis": "integration step"},
    },
    "not_modelled": ["neuromodulation", "plasticity", "gap junctions", "dendritic computation", "a body"],
    "fit_data": "gain swept; not fitted to any task",
    "maintainer": "Brandon Cho (flybench maintainer)",
    "conflict_of_interest": "the benchmark's maintainers wrote this model; it is a baseline, and the README never scores the benchmark by it",
}


class ReferenceLIFSimulator(LIFSimulator):
    """`flybench.sim.LIFSimulator`, unchanged, under the name the leaderboard tags as the baseline."""

    reference_baseline = True
    model_card = MODEL_CARD
