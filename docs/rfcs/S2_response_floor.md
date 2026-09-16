# RFC S2: a comparison check is not a pass when every side of it is silent

Status: proposed 2026-09-15 after task 28 passed two ratio checks on eight spikes against
three; applied to new runs from this commit; not applied retroactively to stored results that
predate it (a rerun applies it, with the before/after recorded here as for RFC S1).

## The problem

Task 28 (steering, MaleCNS 0.65): the right DNa02 drives the right leg pool at 0.12 Hz and the
right DNa01 at 0.04 Hz — eight and three spikes in 500 ms across 136 motor neurons. The
first-spike-latency ratio (0.34 < 1) and the rate ratio (2.9 > 1) both "passed", on every seed,
in the pre-registered direction. Neither pool responded by the task's own definition of a
response (its positive checks ask for > 5 Hz and fail). A ratio between two silences is a ratio
of noise, and it was quoted as evidence that "the direct wiring survives in the timing".

RFC S1 gates the top of the dynamic range: a comparison between two ceilings carries no
information. This is the same statement at the bottom.

## The rule

For every check that **compares conditions** — `ratio` (any metric, including `latency` and
`over_readout` comparisons) and `lifetime_sparseness` — compute the readout's rate in each
compared condition (for `over_readout`, the second readout's rate in the second condition). If
**every** one of them is below `FLOOR_HZ` = **2 Hz** — the task-05 convention for silence, the
threshold every null check in the benchmark uses — the check is marked `floored: true`, its
pass flag is set to **false**, its graded score to 0, its margin to −10, and the description
gains `[floored: every compared condition silent]`.

Comparisons against a silent baseline are unaffected when the other side responds (sugar 219 Hz
over baseline 0 Hz: one side above the floor). A comparison where both sides are silent was
never informative; a `> N` ratio against baseline already failed there, and a `< N` suppression
ratio would have passed vacuously — that vacuous pass is what this rule removes.

Absolute checks (`rate`, `spikes_per_neuron`, `readout_active_fraction`, `rank_order`,
`recruitment_spread`, `latency`) are unaffected: a silent readout already fails a positive check
and rightly passes a null.

Multi-seed runs: floored when floored on every seed, as for S1.

## Effect on existing results (predicted before rerun)

Only task 28 should change: checks 3 and 4 (both pools < 2 Hz under both DNs) become floored,
the task goes **3/6 → 1/6** (the see-saw null remains), MaleCNS 0.65 hard score 0.585 → 0.573,
graded 0.668 → ~0.656. Every other ratio in the archived FlyWire 0.45 and MaleCNS 0.65 results
has at least one side above 2 Hz: task 6 strong 400 Hz, task 20 sugar 219 Hz, task 22 song MNs
65–83 Hz, task 24 DNp15 14–198 Hz, task 26 KCs 47–310 Hz, tasks 16–18 at ceiling (S1). The
rewired control on task 28 (1/6, the null) is unchanged, so specificity goes +0.33 → 0.00 —
which is the honest number: the shuffle and the brain both move nothing.

## What would make this rule wrong

A readout whose meaningful response is genuinely sparse — one spike per trial per neuron, as
the giant fiber's is — compared across conditions by ratio. The giant fiber tasks compare spike
counts by absolute check, not ratio, so none is affected; a future sparse-response ratio task
would need to read spikes per neuron, not rate, and the gate reads rate. If such a task appears
the floor should become a per-metric convention; until then 2 Hz over a ≥ 300 ms window (0.6
spikes per neuron) is below any response the benchmark scores.

## Outcome (2026-09-15, FlyWire v783 0.45 and MaleCNS v1.0 0.65 rerun with the floor, 3 seeds, `--jobs 6`)

Exactly the predicted effect and nothing else: task 28 on MaleCNS **3/6 → 1/6** (latency ratio
0.34 and rate ratio 2.9 floored; the right/left ratio, already failing, is floored too),
graded 0.478 → 0.167, specificity +0.33 → **0.00**. Hard score 0.585 → 0.571. Every other
check on both brains is bit-identical. No FlyWire check was floored.

Also folded in: the S1 ceiling gate now covers every `ratio` metric (it had been restricted to
rate ratios when `metric:` was added for task 26); no archived ratio changed, since the task-26
KC rates (47–310 Hz) sit under the 364 Hz ceiling.
