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

## 2026-09-15 — task 24 (optic-flow rotation vs translation): the wiring does the paper's arithmetic; one H2 lights 8.6 % of the brain at 0.45

The Nat Neurosci 2025 H2-HS network (HS + H2 → DNp15 and → the GABAergic bIPS, which inhibits the
other DNp15; docs/rfcs/24) on FlyWire 0.45: **5/6**, rewired 1/6, specificity +0.67, four of
the five passes within a factor of two of the pre-registered steady-state estimates. DNp15
prefers a yaw turn to forward translation 6×; adding the contralateral eye's symmetric component
halves DNp15 (0.52); bIPS prefers symmetric flow 9×. MaleCNS 0.65: **3/6**, rewired 1/6.

- **A single H2 at 100 Hz activates 8.6 % of the FlyWire brain at gain 0.45** — the first
  whole-brain event at the gain where the core reflexes are clean (an LC type at 150 Hz: 0.2 %;
  HS_L alone: 0.4 %). H2 carries ~5,000 output synapses per cell, five times an HS cell. The one
  failed check is the lateral null: the wrong-side DNp15 fires at 51 Hz from that event, via
  PS100/PS235, not through anything in the paper's diagram. The whole-network-event finding
  (RFCs 20–23) now has a gain-0.45 example, and it is cell-type-specific.
- **H2 silences bIPS through the paper's own middle layer** (uLPTCrn CB2473, H2rn CB3740,
  PS099a): bIPS_L 62 Hz under HS alone → 16 Hz with H2 → 0 under H2 alone. The "competitive
  disinhibition" of the title is visible in a uniform LIF, and it is why the bIPS symmetric
  preference is 9× rather than the 1.6× direct drive gives.
- **On MaleCNS the ignition is lateralised: the right DNp15 wins every turn.** yaw_right →
  DNp15_R 312 Hz / DNp15_L 14; yaw_left → 322 / 0. DNp15's largest input in the male brain is
  GNG494 (513 synapses onto the right cell, 293 onto the left), not HS, and the left DNp15 is
  inhibited by WED203/PS100 during the event. Whether this asymmetry is in the animal or in the
  reconstruction is a question for the annotators; the female brain's asymmetry is 2.6× in the
  other direction (yaw_right → 198 Hz, yaw_left → 77 Hz) from a 15 % wiring difference.
- The bIPS homologue on MaleCNS (PS321, by motif) behaves as on FlyWire: driven by HS, silenced
  by the H2 ignition.

Housekeeping: new `optic_flow` circuit; FlyWire graded 0.728 → 0.733, MaleCNS 0.720 → 0.709;
23 older tasks bit-identical on both.

## 2026-09-15 — task 25 (antennal grooming vs backward walking): the feeding-restraint DN DSOG1 shuts the grooming command; FlyWire 0/4

Hampel 2020's JON split (JO-C/E and JO-F → antennal grooming via aBN1 → aDN1/aDN2; JO-F alone →
backward walking, MDN by the authors' hypothesis; JO-C/E ↛ MDN) as task 25 (docs/rfcs/25), the
JON stand-in for the roadmap's bristle somatotopy, which waits for BM-* annotations. Pre-registered
3/4 on both brains (ignition passes the positives, fails the null). Measured: **FlyWire 0/4**,
rewired 1/4, specificity −0.25; **MaleCNS 1/4**, rewired 1/4. Runs took 12 and 6 minutes with
`--jobs 6` (previously ~45 each).

- **DNg98 = DSOG1 (Pool et al. 2014, GABAergic feeding-restraint DN) makes 597 / 948 inhibitory
  synapses onto the four antennal-grooming DNs** — 3–5× their largest excitatory input — and is
  recruited by every ignition (not by JONs: 0 direct contacts). On FlyWire inhibition onto the aDNs
  outweighs excitation 7:1 under a 433-cell antennal drive and the grooming command is silent.
  On MaleCNS JO-C/E's relay SAD093 is strong enough to overpower it (aDN 402 Hz, ceiling) and
  JO-F's is not (0 Hz). The wiring for grooming is all there; the model's brain-wide state
  recruits a real gate on top of it.
- **MDN is inhibition-dominated in every condition** (AOTU019, LAL, LT51), and fires only where
  one excitatory input punches through — under JO-C/E, the null, on both brains. The two-hop
  synapse counts (JO-F 4× JO-C/E on FlyWire) predicted nothing.
- Second task where the shuffle beats the brain (after 23): random wiring does not deliver DSOG1
  onto the aDNs.

Housekeeping: new `grooming` circuit; FlyWire graded 0.733 → 0.710, MaleCNS 0.709 → 0.698; the
24 older tasks are bit-identical on both.

## 2026-09-15 — task 26 (MB sparseness with APL, first silencing task): the APL loop works on both brains; sparseness does not, for task 18's reason

Lin 2014's APL result as task 26 (docs/rfcs/26), with the first condition-level `silence:` (outgoing
synapses zeroed, the in silico shibire) and the first `requires_capabilities: [can_silence]` —
simulators declare capabilities and skip what they cannot do. Eight odours × {intact, APL off}
over every KC (5,177 / 4,064). **5/8 on both brains**, rewired 3/8 (the three nulls), specificity
+0.25. FlyWire exactly as pre-registered; MaleCNS predicted 0–2/8.

- **APL's normalisation is in the wiring and the uniform LIF reproduces it**: silencing APL takes
  the responding fraction from 60 % → 89 % of KCs on FlyWire (KC rate 47 → 98 Hz) and 85 % →
  99.7 % on MaleCNS (148 → 310 Hz), and halves / thirds the population sparseness. APL sits at
  its ceiling (419 Hz) driven by the population, as Lin 2014 describe. Three seeds agree to four
  decimals: a 5,000-cell readout averages the noise out.
- **Sparseness itself fails on both** (60 % / 85 % active for one glomerulus, the fly's 5 %): the
  model's antennal lobe broadcasts (task 18: one glomerulus → 84 % of PNs), so every KC sees most
  of its PN input. A model with antennal-lobe lateral inhibition is the one that could pass 1–3;
  APL alone cannot rescue a broadcast.
- MaleCNS's shuffle passed the nulls too: random wiring did not deliver an ORN drive to 4,000 KCs
  at 0.65, unlike to single descending neurons (RFC 21). The "random wiring conducts at 0.65"
  floor is target-size-dependent.

Housekeeping: `ratio` checks take a `metric` (rate, readout_active_fraction, spikes_per_neuron,
population_sparseness); new `population_sparseness` metric (Willmore–Tolhurst across neurons);
inter-odour correlation deliberately not scored (single-glomerulus odours give disjoint KC sets by
construction — verified on the toy). FlyWire graded 0.710 → 0.690, MaleCNS 0.698 → 0.689; 25
older tasks bit-identical on both.

## 2026-09-15 — task 27 (CO2 pathway specificity): 4/7 on both as pre-registered; LN23 is the only CO2-private node in the model

The "Structural basis of CO2 valence coding" circuit (bioRxiv 2026.01.05.697655) mapped onto both
datasets by name — PNvbi = V_ilPN, LN23 = l2LN23, PNm1 = M_smPNm1, LHPD5c1 — as task 27
(docs/rfcs/27). Four positives on the CO2 drive pass at ceiling on both brains; the three nulls
(DA1/DM1 must not reach PNm1, DA1 must not reach V_ilPN) fail on both, exactly as predicted from
task 18's antennal-lobe broadcast: cVA drives the CO2 PN at 417 Hz. Rewired 3/7, specificity
+0.14.

- **LN23 is the one CO2-private element**: 187 Hz under CO2 vs 20 Hz under cVA or DM1 on FlyWire
  (9×), 326 vs 59–75 Hz on MaleCNS (5×). It is the only cell in the circuit with no PN-side input
  — its excitatory input is ORN_V alone — so the broadcast reaches it only through the residual
  network. The extraglomerular channel's entry is specific in the model even though its exit
  (PNm1, which also takes multiglomerular PNs) is not.
- **MaleCNS labels LN23 GABAergic; the paper's anti-GABA staining says it is not.** On MaleCNS
  the LN23 → PNm1 edge is therefore inhibitory in W, and PNm1 still fires at 374 Hz under CO2 —
  driven by the ignition, not the pathway. Recorded as a dataset annotation to raise, not
  corrected in the task.
- Third task in a row (26, 27) whose nulls are task 18 in another costume: a model with
  antennal-lobe lateral inhibition is what all three are waiting for.

Housekeeping: FlyWire graded 0.690 → 0.678, MaleCNS 0.689 → 0.680; 26 older tasks bit-identical.

## 2026-09-15 — task 28 (steering, DNa02 vs DNa01, MaleCNS-only): one steering DN moves nothing; the RFC 22 ignition was pIP10's, not every DN's

Rayshubskiy 2025's steering pair as task 28 (docs/rfcs/28): MaleCNS confirms the paper's wiring
claim (right DNa02 → 490 direct synapses on 11 right leg MNs, DNa01 104 on 6, all ipsilateral,
no twin contact). Pre-registered 2/6 on the assumption that any DN at 100 Hz ignites the cord
at 0.65 (RFC 22). Measured **3/6**, rewired 1/6, specificity +0.33 — with every check wrong for
the same reason:

- **A single steering DN at 100 Hz activates 0.0 % of the male CNS** and fires its own motor
  pool at 0.12 Hz (eight spikes in 500 ms across 136 MNs). 490 synapses over 11 MNs is ~4 mV per
  MN at 0.65, under threshold; DNa02's biggest targets are GABAergic premotor interneurons. The
  whole-CNS event of RFC 22 was a property of pIP10's targets (and of the sensory drives), not
  of descending neurons as a class. The "any drive to a DN becomes a whole-CNS event" rule
  written after RFC 22 is withdrawn: it is drive-specific.
- **The contralateral pool moves more** (0.34 vs 0.12 Hz) through IN07B006, DNa02's one strong
  excitatory premotor target, which makes 1,043 synapses on the *left* leg MNs and none on the
  right. A two-hop crossing route beats the one-hop ipsilateral wiring at these rates.
- **The latency and gain ratios pass on 8 vs 3 spikes.** Direction as predicted, every seed,
  and meaningless. There is no floor counterpart to the S1 ceiling gate; proposed as **RFC S2**:
  a comparison check whose every side is below the task's own response threshold is not a
  pass. To be applied to all archived results with S1-style accounting, not silently.

Housekeeping: `latency` as a ratio metric, `over_readout` for cross-readout ratios; MaleCNS
graded 0.680 → 0.668, hard-by-circuit 0.558 → 0.551; 27 older tasks bit-identical; FlyWire
records 28 as not applicable, otherwise bit-identical.

## 2026-09-15 — RFC S2 (response floor) applied; task 29 (ring attractor, expected-fail tier): one transmitter label decides which way the compass fails

**RFC S2** (docs/rfcs/S2_response_floor.md): a comparison whose every side is under 2 Hz is
floored and fails, the mirror of S1's ceiling gate. Applied by rerun: exactly task 28's two
ratios on MaleCNS (8 vs 3 spikes) changed, 3/6 → 1/6, specificity +0.33 → 0.00; every other
check on both brains bit-identical. The S1 gate now covers every ratio metric.

**Task 29** (docs/rfcs/29), the first `expected_fail:` task: eight EPG wedges by PB glomerulus
(labelled identically on both datasets), a new `bump` check (population-vector length and
angle), a cue on one wedge, a dark window, two competing cues. FlyWire **1/7**, MaleCNS **2/7**,
shuffle 2/7 on both (specificity −0.14 / 0.00) — the third task where random wiring beats the
brain. The model fails as the tier says, but in opposite directions:

- **FlyWire: the compass is a floodlight.** Six EPGs at 100 Hz light 9 % of the brain; all
  eight wedges sit at 260–380 Hz through the cue and the dark (R = 0.02). The route is a
  506 / 218 reciprocal loop between the EPGs and the right ExR6, whose `nt_type` is blank in
  v783 (→ excitatory by default) while the left ExR6 is glutamatergic.
- **MaleCNS: the compass is shut.** 0.0 % active; ExR6 is glutamatergic on both sides and, with
  the GABAergic ER4m, is the EPGs' largest input (−446 / −436 onto the cued wedge). The PEN → EPG
  loop never starts; the ring is silent in the dark.
- Hulse et al. 2021 list ExR6 as glutamatergic: MaleCNS's label is the supported one and the
  FlyWire blank is an annotation to raise. Second time today a single transmitter label
  (LN23 in task 27) sets a task's outcome on one dataset.

Housekeeping: FlyWire graded 0.678 → 0.661, MaleCNS 0.668 → 0.655 (S2 and task 29 together);
new `navigation` circuit; 28 older tasks bit-identical apart from the S2 change on task 28.

## 2026-09-15 — tasks 30 (egg laying, FlyWire-only) and 31 (halting): Phase 3 complete; the egg-laying command is the cleanest circuit in the hard tier

**Task 30** (docs/rfcs/30, Wang 2020's oviDN circuit; oviEN = SMP550 by motif): FlyWire 0.45
**3/4** against a pre-registered 1/4, rewired 1/4, specificity +0.50 — the day's highest.

- **SMP550 drives oviDN at 14 Hz with 0.0 % of the brain active.** Two cells, six targets, no
  ignition: a command pathway that behaves as the paper draws it at the gain where the core
  reflexes work. The inferred oviEN identity is now also a functional one.
- **The virgin null holds through an ignition**: pC1 at 100 Hz lights 8 % of the brain and
  drives oviIN to 52 Hz, and oviDN stays at 0 Hz on every seed — feed-forward inhibition in a
  uniform LIF on the female brain.
- oviIN on top of a *forced* oviEN takes oviDN only to 0.68 of its rate: the fly's oviIN also
  silences oviEN, which a forced stimulus cannot show. The check fails on the convention.

**Task 31** (docs/rfcs/31, Sapkal 2024's walk-OFF): the paper's neurons are all in v783 under
community labels; P9 dropped (no halt-neuron contact on DNp09); a declared walking stand-in
(PVLP137 + CB0529). FlyWire **3/6** against 4/6 predicted, rewired 0/6, specificity +0.50.
Sugar → Foxglove 66 Hz with Bluebell at 1 Hz (the paper's asymmetry). The walking stand-in
ignites 9 % of the brain and recruits Foxglove on its own (48 Hz), so adding it suppresses BDN2
to 0.69 — real but seed-sensitive (0.53 / 1.00 / 0.53); oDN1 is untouched by either halt
neuron, as its −136 / −206 synapses predicted. MaleCNS skipped: no Foxglove under any name.

**Phase 3 (roadmap items 19–30) is complete**: twelve tasks (20–31) in two days, every one
pre-registered. Running tally of the hard tier on the reference LIF: FlyWire 0.45 graded 0.669,
MaleCNS 0.65 0.655. Across the twelve: the wiring was right about the circuit in ten; the
model's failures were gain (ignition on sensory drives, silence on single DNs) in nine, a
transmitter annotation in two (LN23, ExR6), and an intrinsic property the model lacks in one
(the size principle). Three tasks where the shuffle beats the brain (23, 25, 29).

## 2026-09-16 — the stale rows refreshed on all 31 tasks: adaptation beats the reference on the hard tier

Every result file predating 2026-09-14 has been rerun on the current task set with `--jobs 6`
(Adaptive LIF 0.45, Shiu 1.0, the reference-labelled 0.45, MaleCNS 0.45 / 0.50 / 0.55). The first
cross-model comparison over the whole set, FlyWire v783, 25 applicable tasks, 3 seeds:

| model | core | hard | graded | specificity |
|---|---|---|---|---|
| reference LIF, gain 0.45 | 1.00 | 0.526 | 0.669 | +0.21 |
| **adaptive LIF (b 2 mV, τ 200 ms), gain 0.45** | 1.00 | **0.681** | **0.791** | **+0.34** |
| Shiu 2024, gain 1.0 | 0.77 | 0.51 | 0.626 | +0.19 |

- **One documented mechanism with two literature-range constants moves the hard tier by
  +0.15** and passes the core tier untouched. Adaptation wins where the reference's failure was
  ignition or saturation: return to rest (0.25 → 1.00, its original purpose), DA1 sparseness
  (0.11 → 0.89), PN transfer function (0.14 → 0.71), dose response (0.40 → 0.80), looming DN
  ensemble (0.67 → 1.00), LC → DN matrix (0.69 → 0.81), GF azimuth (0.44 → 0.67), grooming
  (0 → 0.25). A neuron that tires is a neuron that leaves the refractory ceiling, and half the
  hard tier's failures were ceilings.
- **It is not uniformly better**, which is the point of a task-level table: it loses on the ring
  attractor (0.14 → 0, the silence outcome), egg laying (0.75 → 0.50), optic flow (0.83 → 0.67)
  and halting (0.50 → 0.33) — the tasks whose pass depended on a sustained response that
  adaptation now cuts short. Unchanged on the tasks task 18's broadcast decides (26, 27) and on
  the wiring-only nulls.
- Shiu 1.0 fails the core tier (0.77) as the gain-window result says, and scores below the
  reference on the hard tier except on grooming (0.75: at gain 1.0 the aDNs punch through DSOG1).
- Cost column now populated (item 43): the reference run is 5.4× real time per CPU (2,200 CPU-s
  for 410 simulated seconds), 0.4 GB peak per worker on FlyWire, 0.5 GB on MaleCNS.

Nothing about this says adaptation is how flies do it (docs/models: "a hypothesis, not a
correction"). It says which listed behaviours it buys and which it costs, per task, with the
shuffle next to it — and that the leaderboard now has a second row worth arguing about.

## 2026-09-16 — QA pass: every result file rerun on one code version (v0.1.0 + review fixes)

All 14 result files were rerun on commit `d1bd750` with `--jobs 6` so that every leaderboard row
is on the 31-task set and one scoring version. Accounting, against the previously committed files:

- The gate fix from the review (S1/S2 judged on a check's own window rather than the task's)
  changed one archived check: Shiu 1.0's adaptation ratio (windows 950–1300 vs 250–600 ms) had
  been marked saturated on whole-window rates and now passes on its own windows — Shiu graded
  0.626 → 0.645. The four MaleCNS rows moved by ≤ 0.005 for the same reason. Every other check
  on FlyWire 0.45, MaleCNS 0.65 and the adaptive LIF is bit-identical.
- The six gain-sweep rows (0.3–0.7, single seed, and 0.4 × 3 seeds) were on 12 tasks from
  2026-09-13 and are now on 31 (and on the every-seed and S2 rules). Their core columns — the
  README's reflex-window table — are unchanged: 0.40 is still the knife edge (sugar reaches MN9
  on 2 of 3 seeds), 0.45 still passes every core task on every seed.
- Cost column populated on every row: ~5× real time per CPU on FlyWire, 0.4–0.6 GB per worker.

## 2026-09-17 — task 32 (first sensory front end): through flyvis, the reference model's giant fiber fires to a flash and not to a loom

Roadmap item 44. Every escape task so far drove LPLC2 and LC4 *themselves* at 150 Hz — a
convention that assumes the optic lobe has already computed "loom". Task 32 replaces the
convention with a published optic-lobe model: a rendered dark disc (r/v 40 ms, collision at 1 s)
goes through the pretrained flyvis network (Lappalainen et al. 2024), and the 27 output types
both connectomes name identically (T4a–d, T5a–d, T2, T2a, T3, Tm/TmY; ~32,000 FlyWire cells) are
driven column by column with flyvis's rates above rest (1 unit = 100 Hz, an inferred PCA
retinotopy — `flybench/frontends/flyvis_frontend.py`). The connectome's own wiring has to carry
it from there to LPLC2, LC4 and the GF. Front-end outputs are cached and committed
(`data/frontends/flyvis/*.npz`, 4 MB), so runs and CI need neither torch nor flyvis.

Pre-registered (docs/rfcs/32, informed by disclosed single-seed development runs): 0/3 on both
brains, rewired ties at 0/3, and the *unscored* flash fires the GF at tens of Hz.

| | FlyWire 0.45 | MaleCNS 0.65 |
|---|---|---|
| loom → LPLC2 / LC4 (900–1200 ms) / GF spikes | 0.0 / 0.0 Hz / 0.0 | 0.0 / 0.0 Hz / 0.0 |
| loom, brain active | 4 % | **15 %** |
| flash (unscored) → GF / brain active | **37 Hz** / 22 % | 5.8 Hz / 23 % |
| score · rewired · specificity | 0/3 · 0/3 · 0.00 | 0/3 · 0/3 · 0.00 |

- **The loom never arrives.** The loom's T5 drive is *sparse*: at the last frames 10–15 % of
  columns exceed 20 Hz and the field mean over the last 500 ms is ~1 Hz per type; an LPLC2's
  ~110 T5 synapses at 1 Hz is 0.07 mV. The flash is a synchronous transient on every column
  (T4 154 Hz, Tm3 tonic 42 Hz), lights 22 % of the brain and reaches the GF through LC4 (4.8 Hz)
  and the network. A point-neuron LIF that sums synapses cannot prefer a sparse late edge to a
  full-field step; the fly's LPLC2 does it with the layer-specific radial arrangement of its
  T4/T5 inputs (Klapoetke 2017), which is a dendritic computation, not a synapse count.
- **Why the flash is measured, not scored.** Through this front end a brightening step gives
  T5 as well as T4 a synchronous transient, so a flash null would be failed by any model that
  sums T5 over the eye and passed only by one with retinotopic expansion selectivity — a test of
  the front end rather than the connectome. `rate[flash, gf]` is in every result file.
- **What survives the caveats.** flyvis models only 50–57 % of LPLC2/LC4's input types; the
  column mapping uses about a third of the retina per type; 1 unit = 100 Hz is a convention.
  All three bias toward failure. The *sign* of flash-vs-loom does not depend on them.
- **First task at the floor for both the model and its shuffle** (with task 23): specificity
  0.00 by construction, which is the honest number — the task discriminates nothing yet. It
  becomes diagnostic the day a model passes it.

The 127 checks of tasks 1–31 were bit-identical on FlyWire (`flybench diff`, mean graded
difference 0.000); graded 0.669 → 0.653 only because a 0/3 task joined the denominator.
MaleCNS likewise (146 checks identical; 0.650 → 0.639). One MaleCNS-only number: the loom
lights 15 % of the CNS at 0.65 and still none of it is LPLC2, LC4 or the GF — the drive spreads
without summing onto the detectors; the flash reaches the GF more weakly there (5.8 Hz), as
tasks 4 and 16 already showed for the LC4 → GF path.

Housekeeping: the toy has 3,790 neurons (T4/T5 subtypes on a coarse grid, an LPi-like layer;
its MODELED dark-loom detector passes 3/3 and is the reason the task exists in CI, and proves
nothing about the fly). Runs were done at `--jobs 4`: a `--jobs 6` attempt was killed for
memory with a browser holding 9 GB, and 4 workers finish FlyWire in 30 min.

## 2026-09-17 — task 33 (first embodied task): given an eye and a body, the reference model jumps at a flash and not at a loom

Roadmap item 51, Phase 7a. The embodied track exists: a task's `body:` block hands a readout's
spikes — TTMn where the dataset has a nerve cord, the GF plus Augustin 2019's 0.93 ms where it
does not — to NeuroMechFly in FlyGym 2.1 / MuJoCo, which runs one fixed middle-leg extension per
command; takeoff is a physics event (all six feet off the ground within 30 ms of a command).
Feed-forward: nothing returns to the brain. The body is a transducer, and the `rewired` control
runs the same body, so a jump the shuffle also makes is not the connectome's.

Pre-registered (docs/rfcs/33, no development run on a real brain): loom → takeoff ~20–25 ms
after drive onset; rest → nothing; flash through the eye → **a jump** (task 32's 37 Hz GF flash
response, now acted on); loom through the eye → nothing (unscored). 3/4 on both brains.

| | FlyWire 0.45 (GF + 0.93 ms) | MaleCNS 0.65 (real TTMn) |
|---|---|---|
| loom → takeoff, latency | yes, **17.1 ms** (sd 0.17), 4 commands | yes, **23.1 ms** (sd 0.13), TTMn 62 Hz |
| rest → takeoff | no | no |
| flash through the eye → takeoff | **yes, 257 ms** after onset, 2.7 commands | **yes, 264 ms**, GF 5.8 Hz → TTMn 0.7 Hz |
| loom through the eye → takeoff (unscored) | no | **yes, 499 ms, GF silent** (TTMn 3.3 Hz) |
| score · rewired · specificity | 3/4 · 2/4 · +0.25 | 3/4 · 2/4 · +0.25 |

- **The escape works end to end, when the loom is handed to the detectors.** LPLC2/LC4 at
  150 Hz → GF first spike at ~6 ms → +0.93 ms → the legs clear the ground ~10 ms later: 17 ms,
  every seed within 0.2 ms. That is the pipeline, not a discovery; the real fly's GF spike comes
  near collision and the takeoff ~10 ms after it (Card & Dickinson 2008).
- **The flash jump is the finding.** Task 32 reported the flash GF response as a rate; here the
  body takes off a quarter-second after the lights come up. And it is a property of the *real*
  wiring: on the degree-matched shuffle the flash does not reach the GF (control checks
  `[loom ✗, latency ✗, rest ✓, flash ✓]`) — the prediction that "a fifth of the brain lit at
  random probably fires the GF" was wrong, specificity +0.25 not +0.50. The path from the
  flyvis-driven medulla types to the GF is specific to FlyWire's wiring, and it is the wrong
  path: it carries a brightening, not a loom.
- **What the body cannot say.** One program per command: a GF at 430 Hz and a GF that fires
  once produce the same jump (task 13 scores the difference). The transducer's ~0.7 mm and
  ~11 ms are the body model's; a different body changes the numbers, not the structure.
- **MaleCNS, unasked for: the loom through the eye does make the body jump — without the GF.**
  With the real TTMn as the command, the flyvis loom (GF 0 Hz, as task 32 found) fires TTMn at
  3.3 Hz and the body takes off 499 ms after loom onset on every seed. Task 32's 15 %-of-the-CNS
  loom response reaches the jump muscle's motor neuron by a GF-independent path: the long-latency
  escape pathway (Engel & Wu 1996; Card & Dickinson 2008) is wired in the male CNS. Unscored here;
  the next task on this track is TTMn-without-GF with the GF silenced.

The 130 (FlyWire) and 149 (MaleCNS) older checks are bit-identical (`flybench diff`); graded
0.653 → 0.655 and 0.639 → 0.641 (a 3/4 task joined). FlyWire's row is the reference submission
evaluated through `flybench evaluate` (verified, `reference_baseline`).

Housekeeping: result files now record which checks each control passes
(`controls.<name>.checks`); the toy gained TTMn (3,792 neurons); `pip install -e .[embodied]`
(FlyGym needs Python ≥ 3.12; CI moved to 3.12); a task with `body:` is skipped without it.

## 2026-09-18 — task 34 (the jump without the giant fiber): the flash's road to the jump muscle is the GF; the loom's is not

Follows task 33's unasked-for observation (a flyvis loom made the MaleCNS body jump with the GF
silent). Task 34 zeroes the GF's outgoing synapses (`silence:`) and asks the body directly, with
TTMn as the command. Pre-registered 5/6 (docs/rfcs/34): the eye loom and the convention loom
would still reach TTMn and jump; rest quiet; and the flash — which lights 23 % of the CNS, more
than the loom's 15 % — would reach TTMn too, GF or no GF.

| MaleCNS 0.65, GF silenced | TTMn | takeoff, latency | predicted |
|---|---|---|---|
| loom through the eye | 3.3 spikes/neuron | yes, **499 ms** (411–558) | ✓ |
| convention loom | 27 | yes, **30 ms** (23 ms with the GF) | ✓ |
| flash through the eye | **0.0** (the GF itself still 6 Hz) | **no** | ✗ predicted a jump |
| rest | 0 | no | ✓ |

**6/6, rewired 1/6, specificity +0.83** — the highest in the suite. Older 153 checks identical.

- **The dissociation.** Silencing the GF removes the flash's jump entirely and leaves the loom's
  untouched (same seeds, same 3.3 Hz, same 499 ms). Task 32/33's wrong-way escape — the model
  jumping at a brightening — is GF-borne end to end; the loom's route to TTMn does not use the
  GF at all. Two stimuli that both light a sixth to a quarter of the CNS take different roads to
  one motor neuron; "non-specific spread" does not describe either. Which descending neurons
  carry the GF-free loom route is the next task (`upstream_of: TTMn` minus the GF, silenced in
  turn).
- **Fast and slow.** The GF-free route carries the convention loom in 30 ms (7 ms slower than
  with the GF) and the eye loom in 411–558 ms — slow and variable, as the fly's long mode is.
- **The shuffle fails the flash null** (on rewired wiring the flash reaches TTMn without the GF):
  the real wiring's flash null is specific.
- **Tier stays hard** although the reference passes 6/6 here: tiers are defined against the
  reference submission on FlyWire, which cannot run a TTMn task (docs/GOVERNANCE.md, added).

Housekeeping: the toy's DNp02/DNp11 → TTMn (MODELED) carries the convention loom but its
eye-driven detectors fire only at collision, so the toy scores 3/6 by design (docs/rfcs/34); the
toy's new wiring is appended after every older draw so tasks 1–33 are bit-identical on it.
Runs are back to one at a time — pytest and a 4-worker run together were killed for memory with
a browser at 11.6 GB.

## 2026-09-19 — task 35 (which DNs carry the GF-free loom route): nine descending types converging on the GF-coupled interneurons — and ascending neurons run backwards in a point-neuron CNS

Pre-registered in two disclosed stages (docs/rfcs/35): the anatomy and the test before any run,
the candidate set from one spike dump by a procedure fixed in advance, then the scored run.
MaleCNS 0.65, GF silenced throughout, loom through the flyvis eye, TTMn commanding the body.

- **The route.** Nine DN types (DNge048, DNa02, DNbe007, DNge006, DNg45, DNpe002, DNa11, DNb05,
  DNge053 — none a loom DN of the literature; DNa02 is task 28's steering DN) converge on the
  giant-fiber-coupled interneurons GFC2 and IN20A.22A, which drive TTMn. Silencing the nine
  abolishes TTMn and the jump on every seed; silencing any one of the top five alone does not
  (1.7–9.5 spikes/neuron remain) — redundancy, as predicted. The three direct loom-DN inputs to
  TTMn (DNp02/DNp06/DNp10) never fire and do not matter, as predicted from anatomy. 465 of
  1,314 DNs fire to this loom; the route is a diffuse convergence, not a labelled line.
- **The failed sanity check is a model defect worth a check of its own.** Silencing *every*
  DN does not abolish the response (3.2 spikes/neuron, takeoff at 873 ms) although silencing
  nine of them does. The residual carrier is the **ascending neurons**: 22 % of their input
  synapses are in the brain (axo-axonic), a point neuron cannot tell a terminal input from a
  dendritic one, so the loom's brain activity fires 437 ANs and their nerve-cord outputs reach
  GFC2/TTMn. Every DN + every AN silenced → 0.0; GF + every AN silenced → the DN route still
  works (6.5). No fly has this route. Check 2 stays: a compartmental model passes it, the
  point-neuron LIF fails it. **9/10, rewired 3/10, specificity +0.60.**
- **Two consequences for the rest of the suite.** (1) Any whole-CNS point-neuron result that
  involves the nerve cord may carry antidromic AN drive; tasks 33–34's DN routes were checked
  and stand without the ANs, but the caveat belongs on every VNC readout until a model places
  axo-axonic synapses where they are. (2) The cheapest documented fix — treat synapses onto a
  neuron's axon terminal as modulating its output rather than its membrane — needs synapse
  positions relative to the soma, which the datasets have and the connectome cache does not
  yet carry. A task that fails without it now exists (check 2); the mechanism can follow.

Older 159 checks bit-identical; MaleCNS graded 0.652 → 0.660.

## 2026-09-20 — RFC M1, the terminal-aware LIF: moving 0.6 % of synapses off the soma passes task 35 and repairs three older MaleCNS tasks

The first mechanism admitted by the "task before mechanism" rule since adaptation: task 35's
failed check (ascending neurons firing backwards) earned it. `flybench fetch-terminals` reads
neuPrint's per-connection ROI counts into a signed terminal matrix (555,960 axo-axonic synapses on
MaleCNS's neck-spanning neurons — 11.6 % of the ascending classes' input); `flybench.models.
terminal_lif` keeps them off the soma and lets inhibitory ones scale release (floor 0.3, Olsen &
Wilson 2008). Open division, no free parameters; bit-identical to the reference wherever there is
no terminal data (FlyWire, the toy, every shuffled control).

| MaleCNS 0.65 | reference | terminal-aware | predicted |
|---|---|---|---|
| task 35 (all DNs silenced → cord silent) | 9/10 | **10/10** | ✓ |
| tasks 33, 34 | 3/4, 6/6 | 3/4, 6/6 | ✓ |
| task 20 taste_modalities | 2/4 | **4/4** (high salt → MN9 183 → 0 Hz) | ✗ "unchanged" |
| task 24 optic_flow_rotation | 3/6 | 4/6 | ✗ |
| task 23 leg_mn_size_principle | 0/3 | 1/3 | ✗ |
| hard · graded · specificity | 0.574 · 0.660 · +0.218 | **0.613 · 0.669 · +0.252** | graded ✓, spec ✗ |
| control scores | | identical, 33/33 | ✓ |

- **It does what it was built for**: the first model to pass task 35; the GF-free loom route is
  thinner (1.5 spikes/neuron at the low seed) but on every seed.
- **It repairs things it was not built for.** The 2026-09-14 "high salt → MN9 is seed-bistable
  on MaleCNS" result was in part ascending neurons driven at their SEZ terminals and igniting
  the feeding circuit from below; with the terminals where they belong the null holds on every
  seed and salt halves the sugar response. Three unrelated tasks moved toward the fly, none
  away, the shuffled controls did not move, and the network fires *less*. docs/MALECNS.md's
  "no gain does both taste and vision" stands, but one of its examples was the model, not the male.
- **What it is not.** Only neck-spanning neurons are treated; within-brain axo-axonic contacts
  still sum into the soma. The floor and slope are one olfactory synapse's numbers. Excitatory
  terminal contacts are ignored, not modelled.
- **Cost.** Half the wall-clock of the reference on the same suite (fewer spikes).

## 2026-09-20 — RFC M1b, terminal synapses for every neuron: the mushroom body goes sparse on both brains, MaleCNS's core tier goes from 0.57 to 0.90, and the GF-free loom route thins to one spike

The neck rule generalised: a neuron's compartments are its neuropils, and an input in a
neuropil where the neuron is ≥ 80 % presynaptic sits on its axon (θ fixed before the run from
the canonical compartments — ORN terminals 0.86, T4 axons 0.90, PN axons 0.93 vs T4 dendrites
0.10, PN dendrites 0.37, the GF 0.03). FlyWire from the Codex per-neuropil table (1.87 M
synapses, 3.7 %); MaleCNS from 9.1 M per-connection neuPrint ROI rows in the same pair units,
unioned with the neck rule (3.78 M, 4.2 %). `flybench fetch-terminals -c flywire783|malecns`.

| | FlyWire 0.45 ref → M1b | MaleCNS 0.65 ref → M1 → M1b |
|---|---|---|
| core | 5/5 → 5/5 | 0.567 → 0.567 → **0.900** |
| hard | 0.513 → **0.573** | 0.574 → 0.613 → 0.594 |
| graded | 0.655 → **0.711** | 0.660 → 0.669 → **0.700** |
| specificity | +0.207 → **+0.256** | +0.218 → +0.252 → **+0.286** |
| spikes / condition | 680 k → 316 k | 1.34 M → 1.26 M → 0.57 M |
| controls | identical | identical |

- **The mushroom body is sparse.** Task 26 goes 5/8 → 8/8 on both brains: Kenyon cells active per
  odour 60 % → 1.3 % (FlyWire), 85 % → 7 % (MaleCNS) — Lin 2014's number is 5–10 %. The first
  README's "no lateral inhibition, the antennal lobe is a broadcast" was, in large part, LN → ORN
  presynaptic inhibition being summed into the ORN soma where it did nothing (ORNs are driven by
  forced spikes) instead of scaling their release. Task 8's cVA active fraction halves too.
- **MaleCNS at 0.65 nearly does taste and vision.** Sugar → MN9 with 7 % of the brain active
  (was 12 %), bitter halves it, looming → GF clean, the other-fly perturbation survives; only
  quinine → MN9 remains. docs/MALECNS.md's headline is now qualified: most of that failure was
  the point neuron.
- **The embodied fly no longer jumps at the flash** (task 33, 4/4 on MaleCNS) — the GF's flash
  response is gone with the axo-axonic drive that fed it.
- **The cost.** The GF-free loom route to TTMn (tasks 34–35) is reduced to a single spike on two
  of three seeds: task 35 reads 3/10 for M1b against 10/10 for M1 (the check it was built for
  passes; the seven route checks no longer do), task 34 5/6; water → MN9 becomes seed-fragile
  (task 20 back to 2/4); task 17 loses one ratio check. No shuffled control moved.
- **What decides between M1 and M1b** is not the score but the data: a per-synapse
  axon/dendrite split (the datasets have coordinates) and a model for excitatory axo-axonic
  contacts, which at 4 % of synapses is now the model's largest stated omission.

## 2026-09-21 — task 36, the closed loop: the male brain jumps before contact through its own eyes — and at a near miss; the female brain never commands

Phase 7b. The brain's visual input is now the body's: NeuroMechFly's two retinas (721 ommatidia
each) are rendered every 10 ms, mapped one-to-one onto flyvis's 721-hexal lattice, run through
flyvis frame by frame with its state carried (bit-identical to a batch run), and drive the
connectome's own optic-lobe cells; TTMn (or the GF + 0.93 ms) starts the jump; the eyes see the
world from wherever the body is. A 2 mm sphere approaches at 50 mm/s (r/v 40 ms); a copy passes
10 mm to the side; a third stands still. Pre-registered (docs/rfcs/36): nobody passes, 2/4 all
round, MaleCNS "some but not all seeds" on the approach.

| | toy | MaleCNS 0.65 (real TTMn) | FlyWire 0.45 (GF + 0.93 ms) |
|---|---|---|---|
| approach → takeoff | 26 ms *after* contact | **yes, 3/3, 10–120 ms before contact** | no |
| near miss → takeoff | no | **yes, 3/3, at 551 ms** | no |
| motionless → takeoff | no | no | no |
| score · rewired · specificity | 3/4 | 3/4 · 2/4 · +0.25 | 2/4 · 2/4 · 0.00 |

- **At real resolution the loom is a late, small event.** The object's half-angle is atan(0.04/τ):
  14° at 160 ms before contact, 34° at 60 ms. flyvis's rates on the driven types reach 13 Hz at
  60 ms and 39 Hz at 10 ms. Anything that needed the cached movie's disc to fill the field gets
  50 ms of it here.
- **MaleCNS closes the loop — through the wrong route.** LPLC2 0 Hz, GF 0.4 Hz, TTMn 4 Hz, 20 %
  of the CNS active: tasks 34–35's diffuse medulla-driven DN route to the GF-coupled interneurons,
  which answers "a dark thing moving on my eye" and therefore also fires, earlier, for the miss.
  Both MaleCNS predictions were wrong in the same direction (every seed, not some). The 60 ms-early
  jump lifts the thorax 0.7 mm; the object still passes 1.08 mm from the eyes — an escape command
  in time and a failed escape in space, which is the body model's jump, not the brain.
- **FlyWire never commands**, as predicted: the live loom does not reach the GF. The nulls pass
  by silence, as they do for the shuffle.
- **Cost.** ~45 s per closed-loop condition on the toy, ~2.5 min on MaleCNS (eye rendering is
  the fixed cost: 2 × 150 frames at 50 ms); the task roughly doubles a suite run.

Older checks bit-identical on both brains (169 / 134). The terminal-aware rows have not run task
36 yet. Loop closed; nobody escapes it properly; that is the target.
