"""The embodied track (docs/ROADMAP.md item 51, Phase 7a): a brain's spikes drive a physics body.

A task may carry a `body:` block; after the brain run each condition's command spikes (a named
readout — TTMn where the dataset has a nerve cord, else the giant fiber plus the measured
GF → TTM delay) are handed to the body model, which returns what the body did: whether it took
off, when, how high. Those become measurements (`takeoff`, `takeoff_latency_ms`, …) that
ordinary checks score.

The body is a declared, fixed transducer, not a controller: one stereotyped jump program per
command, nothing learned, nothing tuned. So the loop is feed-forward — brain → body — and every
number is a statement about *when the brain commanded*, judged by whether the body left the
ground. Closing the loop (the body's own vision and proprioception back into the brain) is the
next step and is not claimed here. Every embodied task runs with the shuffled-connectome and
random-wiring controls like any other; a body that jumps for a random brain is the "digital
sphinx" failure the roadmap warns about, and the controls are what show it.
"""

from __future__ import annotations

BODIES = ("flygym",)
BODY_METRICS = {
    "takeoff": "takeoff",                        # 1.0 if every foot left the ground within TAKEOFF_WINDOW_MS of a command, else 0.0
    "takeoff_latency": "takeoff_latency_ms",     # ms from the condition's stimulus onset to takeoff; NaN if none
    "n_commands": "n_commands",                  # jump commands the brain issued (after the program's refractory period)
    "thorax_rise": "thorax_rise_mm",             # peak thorax height above standing, mm
}
