# RFC: task 16 — the giant fiber fires once, wherever the loom comes from

Status: pre-registered 2026-09-13, before the first run of the task on either dataset.

## The behaviour

A looming object anywhere in the frontal visual field triggers the same escape. The giant fiber
(GF, DNp01) produces **a single spike** per looming presentation, and the timing of that one spike
decides between a short and a long takeoff (Ache et al. 2019, Curr Biol 29:1073; von Reyn et al.
2014, Nat Neurosci 17:962). GF responses to looms at −45°, 0° and +45° azimuth are
indistinguishable: no directional-selectivity index exceeded 0.5, and the DSIs were not different
from a shuffled distribution (J Exp Biol 2023 226:jeb244790, n = 10 flies, r/v 10–80 ms).

## What the task measures (and how the stimulus is built)

The model has no eyes. A loom at azimuth θ is approximated as Poisson drive to the looming
detectors (LPLC2 and LC4) of the eye that sees it: a loom at −45° drives the left-side detectors,
+45° the right-side ones, and 0° both. Per-neuron drive is the same (150 Hz, the task-4 convention)
in every condition; the 0° condition therefore delivers twice as many input neurons, which is what
a frontal object does to a binocular animal.

Provenance: **INFERRED** — the azimuth → hemisphere mapping uses the `side` annotation of the
detector neurons, not their receptive fields. It is the coarsest possible geometry and is stated
here so nobody mistakes it for a retinotopic model. A retinotopic version (LPLC2 receptive-field
centres from Klapoetke et al. 2017) is a later refinement, not this task.

Readout: GF (both hemispheres together), spikes per neuron in the loom window.

Checks:

1. At each azimuth, GF spikes per neuron ≥ 1 (the loom is seen).
2. At each azimuth, GF spikes per neuron ≤ 1 (`observed: mean 1, sd unknown`, Ache 2019).
3. No GF spike before the loom begins.
4. Invariance: rate(−45°) / rate(+45°) < 3 and rate(+45°) / rate(−45°) < 3, which is DSI < 0.5
   written as a ratio (DSI = (a − b)/(a + b) < 0.5 ⇔ a/b < 3).
5. Sanity: rate(0°) ≥ rate(−45°) and rate(0°) ≥ rate(+45°) are **not** required: a single-spike
   neuron has nothing to gain from more input, and the real data show invariance, not summation.
   (This is deliberately not a check; it is recorded here so nobody adds it later as an
   "obvious" one.)

## Pre-registered predictions

- Reference LIF on FlyWire v783 at gain 0.45: checks 1, 3, 4 pass; check 2 **fails** at every
  azimuth (task 13 already shows ~120 spikes per loom). Score 0.75-ish; graded well below 1.
- Adaptive LIF (b 2 mV, τ 200 ms) at 0.45: check 2 still fails (task 13 measured ~116 spikes);
  invariance passes.
- MaleCNS at 0.65: same pattern; the unilateral conditions may produce fewer GF spikes than the
  frontal one, but not by 3×, so invariance passes.
- Shuffled wiring (`rewired`): checks 1 and 2 fail (GF does not receive looming input); invariance
  checks are ratios of near-zero rates and are meaningless there — the task is a positive task and
  will count as diagnostic only if the shuffle fails check 1. Expected: it does.
- A model that passes check 2 without also passing task 13's MN9 ceiling would be surprising and
  worth a look: it would mean the GF is being silenced by something other than a global mechanism.

## What would make this task wrong

If the `side` annotation is missing or unbalanced on a dataset (all detectors "center"), the
unilateral conditions drive 0 neurons and the task must skip, not fail. The task declares
`requires_stimuli` for both sides so that happens. On MaleCNS `side` comes from `somaSide`
(L/R); on FlyWire from the Codex classification (`left`/`right`).

## Outcome (recorded 2026-09-13, first run after pre-registration)

Reference LIF, FlyWire v783, gain 0.45, 3 seeds, `--controls rewired`:

| check | result |
|---|---|
| seen (−45° / 0° / +45°) | 127 / 129 / 120 spikes per neuron, 3/3 seeds — pass |
| one spike (−45° / 0° / +45°) | 127 / 129 / 120, 0/3 seeds — **fail**, as predicted |
| no spike before the loom | 0 — pass |
| invariance (left/right, right/left) | 1.06, 0.95 — pass |
| rewired control | fails "seen"; task not passed → diagnostic |

Score 0.67, graded 0.64. The predictions held.

What the prediction did not say and the numbers do: **the invariance pass is uninformative on
this model.** Left-only and right-only drive produce the same spike count as both eyes together
because the GF is pinned at its 2 ms refractory ceiling in every condition, and a saturated neuron
is invariant to everything. The invariance checks therefore only carry information once the
one-spike checks pass. This is not a flaw in the task (the check is the measured one) but it is a
reading rule, and it argues for the later retinotopic version, where partial drive would leave
room for a difference to show. Still to run: adaptive LIF at 0.45 (predicted: same pattern) and
MaleCNS at 0.65.

Addendum, Shiu gain 1.0 (same day): seen 23.5 / 26.2 / 42.3 spikes per neuron, one-spike fails,
invariance passes (0.90, 1.13). At gain 1.0 the GF is *not* at its ceiling in the unilateral
conditions (23 vs 42 frontal), so here the invariance result is informative — and it still holds
within the 3× band. Rewired control fails "seen".

Addendum, MaleCNS v1.0 gain 0.65 (2026-09-14): seen 68.7 / 129 / 77.2 (left / frontal / right),
one-spike fails, invariance passes (0.89, 1.13), rewired control fails "seen". Unlike FlyWire at
0.45, the male GF is well below its ceiling on unilateral looms and about twice as high on the
frontal loom (both eyes), so the invariance result is informative here — and it holds.
