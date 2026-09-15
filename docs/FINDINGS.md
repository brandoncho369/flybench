# Findings log

Things the benchmark said that were not in a task's pre-registration, dated, so they can be cited
or refuted later. Newest first.

## 2026-09-14 — GF → muscle latency on MaleCNS 0.65 (task 19) and the ceiling gate on FlyWire 0.45

- **The jump motor neuron fires 11.8 ms after the giant fiber's first spike, not 0.6 ms**, and the
  flight motor neurons fire 1.2 ms *before* it. One GF spike through the model's chemical GF →
  TTMn synapse is not enough; TTMn integrates ~5 GF spikes. In the fly the contact is a giant
  electrical synapse and one spike suffices. The missing mechanism is a gap junction, and the
  benchmark now says so with a number (RFC 19). Falsifiable prediction on record: treating that
  one edge as electrical drops the latency under 1.5 ms and restores leg-before-wing order.
- **The ceiling gate (RFC S1) removed the three vacuous passes** — tasks 16, 17, 18 on FlyWire
  0.45 now score 4/9, 1/7, 1/9 (graded 0.27 [0.24, 0.32] over the three) — and touched nothing
  else. Latencies across seeds vary by microseconds: the model's timing is set by the wiring,
  not by the input noise.

## 2026-09-14 — DA1 sparseness on FlyWire 0.45 (task 18, first run)

- **Lifetime sparseness of the DA1 projection neurons across eight single-glomerulus odours is
  0.0009** (measured: 0.90). They fire at 434 Hz to their own glomerulus and ~398 Hz to each of the
  seven others. At the window gain the antennal lobe carries no channel identity: any glomerulus
  drives every projection neuron to its ceiling.
- **Three recording-match tasks, one pattern.** In 16 (azimuth invariance), 17 (compression) and
  18 (cVA strongest) the secondary checks passed vacuously because the readout sat at its
  refractory ceiling in every condition. Per-task patches (17's dynamic-range check) work but do
  not scale; the honest statement is a suite-level rule: a check that compares conditions is only
  reported as informative when the readout is below ceiling in at least one of them. To be
  designed as a Phase 1 follow-up, not bolted on per task.

## 2026-09-14 — MaleCNS v1.0, gain 0.65 (Minecraft setting), 3 seeds, rewired control, receptor-line taste sets

- **The corrected sugar set still conducts.** With LB3b–c only (34 neurons; LB3a water and LB3d
  high-salt removed per the Cell 2026 gustatory paper) sugar drives MN9 at 219 Hz, up from 175 Hz
  with the 77-cell wiring-inferred set. docs/MALECNS.md had predicted the opposite; corrected.
- **Bitter alone extends the proboscis (55 Hz) and the shuffled brain does not** (specificity
  −1.00 on a null task): random wiring conducts bitter nowhere, the real wiring conducts it to MN9
  at this gain. Bitter suppression fails on 1 of 3 seeds (ratio 0.39, sd 0.14).
- **Brain → nerve cord works and saturates.** Loom: GF 128, TTMn 57.7, DLMn 124 spikes per neuron;
  baseline and sugar give TTMn 0. Task 15 fails only the ≤ 4-spike ceiling.
- **Less saturated than FlyWire at its window.** GF 69 / 77 unilateral vs 129 frontal (task 16's
  invariance is informative here and holds); PNs 244 Hz at 10 Hz input vs 435 at 100 Hz (56 %,
  would pass the task-17 dynamic-range check that FlyWire fails). Both still fail the ceilings.
- **One odour activates 91 % of all projection neurons** (task 8, up from 84 % on FlyWire).
- Run-level: score 0.64, 2/17 tasks, specificity +0.15; every passing task fails on rewired wiring.

## 2026-09-14 — reference LIF, FlyWire v783, gain 0.45, 3 seeds, rewired control (17 tasks)

- **Sugar conducts only at the 100 Hz convention.** With GRNs driven at the recorded ~80 Hz
  (Zhang, Guo & Montell 2016) MN9 fires on 1 of 3 seeds (mean 73.6 Hz, sd 100); at 20 Hz it is
  silent. The window gain 0.45 was found with a 100 Hz stimulus; at the rate a real sugar GRN fires
  the reference model sits on the threshold of its own reflex. Task 6 now fails at 0.45 for this
  reason (score 0.40, graded 0.67).
- **The antennal-lobe PNs are saturated at 10 Hz of ORN input** (379 Hz; 434 Hz at 100 Hz). Every
  ratio check in task 17 passed vacuously; the task gained a dynamic-range check (RFC 17).
- **Shuffled wiring is quieter than the real wiring after a stimulus.** Return-to-rest: real 25 %,
  rewired 75 % (specificity −0.50). The recurrent structure that keeps the real network ringing is
  destroyed by rewiring, so this null-heavy task is one where the shuffle "wins". Same sign, weaker,
  on the physiological-rate ceilings.
- Run-level: score 0.76, 7/16 tasks (15 skipped: no VNC), specificity +0.24; every passing task
  fails on rewired wiring. Profile: 76 % of checks pass at τ = 0, 58 % still pass at ten times the
  margin.

## 2026-09-14 — Shiu 2024 gain 1.0, same protocol

- 4/16 tasks. Sugar and looming conduct but recruit 20 % of the brain; a uniform flash now fires
  the GF (19 Hz) — the flash-is-not-loom null fails, which the shuffled brain passes (specificity
  +0.33 for a null task, an unusual and informative case).
- All three PN input rates give 435 Hz exactly: monotonic checks fail on some seeds with ratio
  1.000. A pinned neuron is constant, not monotonic.
- GF at 1.0 is *below* ceiling for unilateral looms (23–26 spikes vs 42 frontal), so task 16's
  invariance is informative there and still holds.

## 2026-09-14 — task 20 (taste modalities) written, toy passes

Pre-registered in docs/rfcs/20_taste_modalities.md: predicted **skipped** on FlyWire v783 (no
high-salt type or label), **2/4 on MaleCNS 0.65** (water reaches MN9, but so does high salt, and
no suppression — the task-05 failure again), rewired 1/4 (null check only). Toy: 4/4, rewired
1/4, specificity +0.75. The toy had to be changed to pass (water drive topped up, salt wired into
the bitter inhibitory pool — INFERRED, documented in toy.py) and the change was made additively so
every older population's random draws are bit-identical; task 17's toy numbers did not move.
Side finding: a stale toy cache silently served a 2,004-neuron toy after toy.py had grown to
2,428; `load_connectome("toy")` now rebuilds when `TOY_VERSION` differs.

## 2026-09-14 — task 20 real-brain runs: every prediction held; high salt → MN9 is seed-bistable

FlyWire v783 0.45: **skipped** as predicted (v783 types all 122 labellar GRNs as bare `LB3`; no
water or salt label exists). MaleCNS 0.65: **2/4** as predicted — water → MN9 96 Hz (pass), sugar
219 Hz (pass), high salt → MN9 183 Hz (null check fails), sugar + high salt / sugar = 1.04 (no
suppression). Rewired 0.25, specificity +0.25. Full table in docs/rfcs/20_taste_modalities.md.

Two things not predicted. (1) The high-salt response is *bistable across seeds*: 273 / 0.9 / 275 Hz
from the same 26 neurons at the same rate, and on the quiet seed sugar alone also halves. At 0.65
whether the labellar circuit ignites MN9 depends on spike-time coincidences, not on which GRN class
is driven. (2) Water drives one MN9 and not the other (readout_active_fraction 0.5 on every seed)
from a bilateral 9 L / 8 R water set. Neither is a task failure; both are written down as leads.

Housekeeping from the same rerun: the committed result files predated the RFC S1 ceiling gate, so
this rerun is the first to apply it to the real brains — measured values are bit-identical to the
previous run (deterministic seeds), but saturated comparison checks on tasks 07, 16, 17 now grade 0.
FlyWire graded 0.775 → 0.729 (17 tasks), MaleCNS 0.741 → 0.711 (20 tasks). Also: `flybench run`
now saves the report *before* rendering the console table; a cp1252 console that cannot encode "✓"
crashed the print and threw away a finished 40-minute run.

## 2026-09-14 — task 21 (LC → DN matrix): LC16 → MDN is not a synapse; leaks are two-hop and dataset-specific

First `matrix` task (docs/rfcs/21): six LC types × four descending neurons, 16 scored cells, 11 of
them null. FlyWire 0.45 scored 11/16 and **tied its rewired control (specificity 0.00)**; MaleCNS
0.65 scored 14/16 with specificity +0.44. Both predictions were wrong (0.875 / 0.56 predicted).

- **LC16 makes zero synapses onto MDN in either connectome**, and v783 has no excitatory two-hop
  path either. Sen et al. 2017's "feed-forward circuit" has at least two interneurons in it. On
  FlyWire LC16 at 150 Hz activates 0.2 % of the brain and MDN never fires; on MaleCNS a weak
  LC16 → pIP1 → MDN route gives 4 Hz.
- **The MDN leaks are specific paths, not diffuse spread.** LC4 → PVLP141 → MDN (both datasets)
  carries the FlyWire leak; LPLC1 → PVLP201m → MDN exists only in MaleCNS and drives MDN at
  133 Hz. If that path is real, LPLC1 should evoke retreat in males; Wu et al. 2016 report takeoff.
- **LC10a leaks nowhere** on either dataset despite being the largest population driven. Leak
  follows wiring, not drive size.
- The rewired null floor is gain-dependent: 0.69 at 0.45 (silent), 0.44 at 0.65 (random wiring
  conducts). A null-heavy task's control is not a constant.

Unscored: LC6 → GF fires on both datasets with no direct synapse; LPLC1 → DNp11 fires on both.

## 2026-09-15 — task 22 (courtship song chain, MaleCNS-only): 7/8 as pre-registered; one pIP10 lights 12 % of the CNS

First `dataset_only` task (docs/rfcs/22): P1 (pC1 ∩ pMP-e lineage, 86 cells) → pIP10 → song
premotor → the ten song wing MNs, MaleCNS only; FlyWire records it as **not applicable**, which the
explorer now shows distinctly from "not run yet". MaleCNS 0.65: **7/8**, rewired 3/8, specificity
+0.50 — every prediction held, including the one fail (pIP10 → leg MNs 16 Hz, the null).

- A unilateral pIP10 drives the left wing's MNs at 0.93× and the right's at 1.08× of what the
  other pIP10 does: the wiring reproduces von Philipsborn 2011's either-wing, no-bias result.
  Wing choice must be made downstream of, or beside, pIP10.
- **A single pIP10 at 100 Hz activates 11.8 % of the male CNS** — the same fraction as 86 P1 cells
  or a full sugar drive. At 0.65 any drive that reaches a descending neuron is a whole-CNS event;
  the leg-MN leak is that event (via IN18B009 / IN18B029), not a song pathway.
- The undriven pIP10 fires at ~60 Hz when its partner is driven (weak direct contacts, 6 and 12
  synapses; two-hop via ANXXX152 / AVLP718m; the rest is recurrence).

Housekeeping: a `courtship` circuit was added for the per-pathway weighting, which moved the
MaleCNS hard-by-circuit score 0.618 → 0.661 (graded 0.720 → 0.729); the 21 older tasks are
bit-identical.

## 2026-09-15 — task 23 (leg MN size principle, MaleCNS-only): largest first as pre-registered; the small half is inhibition-silenced; the shuffle beats the brain

First task pre-registered as an expected fail for the reference model (docs/rfcs/23). Lesser,
Azevedo et al. 2024 showed that leg premotor synapses scale with MN size and inferred that "a
common input [would] first recruit the largest, fastest MNs" unless MN intrinsic properties
compensate; Azevedo et al. 2020 showed the fly recruits smallest first. The task ramps the
front-left leg's 664 excitatory central premotor neurons (a new `upstream_of` graph selector and
`rate_end_hz` ramp) 0 → 100 Hz over 1 s and scores Spearman ρ between MN size (input synapse
count) and first-spike time. MaleCNS 0.65: **0/3**, ρ = **−0.76** (largest first, predicted
−0.9), rewired 1/3, specificity **−0.33**.

- **The ramp silences the small half of the pool.** 28 of 57 MNs — the 28 smallest — never
  fire (predicted 0.95 recruited; measured 0.47). In MaleCNS the inhibitory share of a leg MN's
  input falls with size (ρ = −0.62: 58 % inhibitory below 500 synapses, 40 % above 5,000), and
  for 20 of the 28 smallest the inhibitory input exceeds the excitatory-pool input outright.
  When the cord ignites (~300 ms, 12 % of the CNS active), the inhibitory premotors fire with it
  and the small MNs' net drive goes negative. A common excitatory drive on this wiring does not
  recruit big-first, it recruits *only* big. The size principle needs the inhibition onto the
  small MNs to be patterned with the movement, not just intrinsic compensation.
- **First negative specificity in the benchmark.** Degree-preserving rewiring keeps in-degree
  but scrambles the size-structured inhibition, so 81 % of the pool is recruited on the shuffle
  (check 2 passes there, fails on the brain); order is still big-first (ρ = −0.93). The real
  wiring is what fails the check. Recorded as the correct reading, not as a bug.
- **The leg/wing contrast of Lesser 2024 is in MaleCNS, per premotor neuron, not per pool.**
  Median ρ(premotor weight, target size) is 0.41 in the leg (78 % positive, n = 345 preMNs with
  ≥ 4 targets) vs 0.10 in the wing steering MNs (52 %, n = 235). Pooled excitatory drive scales
  with size in both (0.99 / 0.95), which is why the task does not score a wing null: no model
  could pass it under a common ramp.
- Check 3 (recruitment spread > 50 ms): 173 / 38 / 131 ms — graded recruitment among the MNs
  that do fire on two seeds, one burst on the third; fails by the every-seed rule.

Housekeeping: a value on the wrong side of zero from its target (ρ = −0.8 against > 0.5) used to
grade by |value| (margin +0.2, graded 0.7 for a fail); it now counts as a zero response (margin
−2.7, graded 0.0). No archived check had a negative value, so no old number moved. New
`locomotion` circuit; hard-by-circuit 0.661 → 0.567, graded 0.729 → 0.720; 22 older tasks
bit-identical. FlyWire rerun: bit-identical, records task 23 as not applicable.
