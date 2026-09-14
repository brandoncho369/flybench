# RFC S1: a comparison check is not a pass when every side of it is at the ceiling

Status: proposed 2026-09-14 after tasks 16, 17 and 18 each produced the same artefact; applied to
new runs from the next release; not applied retroactively to stored results (they say `schema`
1 and predate it; a rerun applies it).

## The problem, three times

- Task 16: GF left / right / frontal = 127 / 120 / 129 spikes per loom → "invariant" passes.
- Task 17: PN 10 / 30 / 100 Hz input = 379 / 421 / 434 Hz → "compressive" passes.
- Task 18: DA1 PN to its own vs seven other glomeruli = 434 vs ~398 Hz → "cVA strongest" passes.

In all three the readout is pinned at its refractory ceiling (1000 / t_ref ≈ 455 Hz at t_ref
2.2 ms, ~430 Hz realised under Poisson drive) in every condition being compared. A neuron that
cannot fire faster is invariant to everything, compresses everything, and prefers nothing by
more than noise. The comparison is between two ceilings, not two responses, and it carries no
information about the wiring. Yet it passed, three times, and each pass was quoted in a result
table before the RFC outcome section corrected it.

## The rule

For every check that **compares conditions** — `ratio` and `lifetime_sparseness` — compute the
readout's rate in each compared condition. If every one of them is ≥ `CEILING_FRACTION` × 1000 /
t_ref_ms (fraction 0.8, convention; with the reference t_ref 2.2 ms that is 364 Hz), the check
is marked `saturated: true`, its pass flag is set to **false**, its graded score to 0, and the
description gains `[saturated: all compared conditions at ceiling]`.

Rationale for failing rather than flagging: a benchmark score is read as "the model does this";
a saturated comparison is a model that *cannot* do this, so a pass would be false. Flagging alone
(a warning next to a green tick) is how the three quotes above happened.

Checks that compare a condition to a silent one (`ratio ... over baseline`) are unaffected:
baseline is ~0 Hz, not at ceiling. Absolute-rate checks (`rate`, `spikes_per_neuron`) are
unaffected: a ceiling check *should* fail when the rate is at ceiling, and it already does.

t_ref comes from the run's parameters; a custom simulator without a refractory period declares
`t_ref_ms` in its params as usual (LIFParams carries it), or the gate uses the default 2.2 ms.

Multi-seed runs: a check is saturated when it is saturated on every seed; if some seeds are
below ceiling the comparison had information on those seeds and the ordinary rule applies.

## Effect on existing results (predicted before rerun)

- Task 16 on FlyWire 0.45: both invariance checks become saturated → task 3/9 instead of 6/9.
  On MaleCNS 0.65 (GF 69 / 77 / 129) they stay informative and pass.
- Task 17 on FlyWire 0.45: all four ratio checks saturated → task 1/7. On MaleCNS 0.65 (244 /
  ~300 / 435) the 30/10 ratio stays informative; the 100/30 ratio (both > 364) saturates.
- Task 18 on FlyWire 0.45: seven ratio checks saturated → task 1/9.
- Task 3 (bitter suppression, ratio sugar+bitter / sugar): sugar is 405 Hz at 0.45, so the gate
  fires only if sugar+bitter is *also* ≥ 364 — i.e. only when bitter fails to suppress, which is
  already a fail. No false negatives expected. Task 6 (weak/strong): weak is 0 Hz; unaffected.
- Task 12 (return to rest) uses absolute rates; unaffected.

Graded suite scores drop for the reference model. That is the point.

## What would make this rule wrong

A model whose *real* dynamic range sits above 364 Hz (t_ref shorter than 2.2 ms) — the gate is
relative to the model's own t_ref, so it moves with it. A readout that legitimately fires at
ceiling in two conditions and is still informative through timing rather than rate — the gate
looks at rate only; a timing-based task would use latency checks, which are not gated.

## Outcome (2026-09-14, FlyWire v783 gain 0.45, 3 seeds, tasks 16–18 rerun with the gate)

| task | before | after | predicted |
|---|---|---|---|
| 16 gf_azimuth_invariance | 6/9 | **4/9** (both invariance checks saturated) | 3/9 — miscounted; the "no spike before the loom" check is a fourth pass |
| 17 pn_transfer_function | 6/7 → 5/7 with the amendment | **1/7** (four ratio checks saturated; only "responds at 10 Hz" passes) | 1/7 |
| 18 da1_sparseness | 8/9 | **1/9** (sparseness and all seven "strongest" checks saturated) | 1/9 |

Run graded for the three tasks: 0.27 [0.24, 0.32]. Every saturated check is labelled in the
output. The rule did what it was written to do and nothing else: no absolute-rate check and no
baseline comparison changed.
