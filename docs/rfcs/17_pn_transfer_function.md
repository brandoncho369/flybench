# RFC: task 17 — the antennal-lobe output saturates the way the recording says

Status: pre-registered 2026-09-13, before the first run on any dataset.

## The behaviour

Olsen, Bhandawat & Wilson (2010, Neuron 66:287) recorded ORN and PN firing in four glomeruli
(DM4, DL5, VM7, DM1; 1,299 ORN and 591 PN measurements, 500 ms window) and fitted the ORN → PN
transform with divisive normalisation:

    PN = Rmax · ORN^1.5 / (ORN^1.5 + σ^1.5 + σ′^1.5),   Rmax = 163–170 spikes/s,  σ = 11.8–16.3 spikes/s

σ′ scales with the lateral-inhibition field (LFP) driven by other glomeruli; when only one glomerulus
is driven it is ≈ 0. Two facts follow that any whole-brain model must reproduce: a uniglomerular
PN never fires above ~170 Hz, and its input–output curve is compressive (half-maximal at an ORN
rate of ~14 Hz, near saturation by ~100 Hz).

Schlief & Wilson (2007) is the DA1 companion: the same shape holds for the cVA channel.

## What the task measures

Stimulus: DA1 ORNs (the existing task-8 stimulus) at three input rates — 10, 30 and 100 Hz — one
glomerulus at a time, 500 ms window. Provenance: MEASURED rates (they are the x-axis of the paper's
figure 2), CONVENTION that a single glomerulus stands in for the four recorded ones (DA1 was not in
the fitted set; Schlief & Wilson 2007 shows the same shape for DA1 but gives no fit).

Readout: DA1 PNs (l, v, ad), rate per neuron.

Checks (predicted PN rates from the fit with Rmax 166, σ 14, σ′ 0: **62, 126, 158 Hz**):

1. ceiling: rate at 100 Hz input ≤ 170 (`observed: mean 166.5, sd unknown` — the paper reports a
   range across glomeruli, not an sd).
2. monotonic: rate(30) > rate(10), rate(100) > rate(30).
3. compressive: rate(30)/rate(10) < 3 (a linear neuron gives exactly 3; the fit gives 2.0) and
   rate(100)/rate(30) < 2 (linear 3.3; fit 1.25).
4. not silent: rate(10) ≥ 5 Hz (the fit gives 62; a model that needs 100 Hz input to respond at
   all has the wrong gain in this pathway).

No absolute-rate check other than the ceiling: the model's absolute rates depend on the global
gain, the shape does not. That is the point of a transfer-function task.

## Pre-registered predictions

- Reference LIF, FlyWire 0.45: ceiling **fails** (task 8 already shows PNs near the 430 Hz refractory
  limit at 100 Hz input); monotonic passes; compressive is the open question — a LIF with a hard
  refractory ceiling saturates too, so the 100/30 ratio may pass while the 30/10 ratio fails
  (the LIF is close to linear below saturation). Guess: 30/10 fails, 100/30 passes.
- Adaptive LIF: ceiling closer but likely still above 170; compressive more likely to pass.
- MaleCNS 0.65: everything saturated; ceiling fails, both ratios pass trivially because all three
  rates sit at the ceiling. The task is therefore informative on the male dataset only through
  the ceiling check — recorded here so a "compressive: pass" at 0.65 is not quoted as a success.
- Rewired: "not silent" fails (DA1 ORNs no longer reach DA1 PNs); ratio checks of ~0 rates are
  noise; task not passed → diagnostic.

## What would make this task wrong

The readouts and stimulus are named cell types present in both datasets; the task carries no
`requires_*`. If DA1 PNs have only a handful of neurons on a dataset, per-neuron rates are noisy
across seeds — run with ≥ 3 seeds. A model with no lateral inhibition at all still passes the
single-glomerulus checks here; the multi-glomerulus (σ′) version is a later task.

## Outcome (recorded 2026-09-14, first run after pre-registration)

Reference LIF, FlyWire v783, gain 0.45, 3 seeds, `--controls rewired`:

| check | result |
|---|---|
| ceiling ≤ 170 Hz | **434 Hz, fail** (predicted) |
| not silent at 10 Hz | 379 Hz, pass |
| monotonic | 1.11 and 1.03, pass |
| compressive 30/10 < 3 | 1.11, pass — **prediction wrong** (predicted fail) |
| compressive 100/30 < 2 | 1.03, pass (predicted, but for the wrong reason) |
| rewired control | 50 %, task not passed → diagnostic |

The prediction that the LIF would be linear below saturation was wrong because there is no
"below saturation" on this pathway at this gain: with ~110 ORNs converging on each PN, 10 Hz of
ORN input already drives the DA1 PNs to 379 Hz. Both ratio checks then pass vacuously (1.11 and
1.03 are ratios of two ceilings). This is the same failure mode task 16 exposed for invariance, and
it shows the task as written could not distinguish "compressive like the fly" from "pinned at the
refractory limit".

**Amendment (2026-09-14):** a seventh check, rate(10 Hz) / rate(100 Hz) < 0.6, from the fit's 0.39.
A saturated model gives ~0.9 and fails it; a model with the fly's dynamic range passes. The
amendment is a post-hoc change and is labelled as such in the YAML. Predictions for the amended
task: the reference LIF fails it at 0.45 and at 1.0; the adaptive LIF probably fails it too
(adaptation lowers the ceiling but does not restore the input–output curve).

Also observed on the same run, outside this task's scope but worth recording: at gain 1.0 all
three input rates give 435 Hz exactly, so the ">" monotonic checks fail on some seeds with ratio
1.000 — a pinned neuron is not monotonic, it is constant.

Addendum, MaleCNS v1.0 gain 0.65 (2026-09-14, run on the six-check version, before the amendment):
ceiling fails (435 Hz), 10 Hz input gives 244 Hz, ratios 1.61 (30/10) and 1.11 (100/30), rewired
control 50 %. The pre-registered prediction "everything saturated on the male dataset" was wrong:
at 10 Hz input the PNs are at 56 % of their 100 Hz response, so the amended dynamic-range check
(< 0.6) would *pass* on MaleCNS at 0.65 while failing on FlyWire at 0.45. The male pathway has
some of the fly's dynamic range at this gain; the female pathway at its window has none. The
ceiling check fails on both.
