# Findings log

Things the benchmark said that were not in a task's pre-registration, dated, so they can be cited
or refuted later. Newest first.

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
