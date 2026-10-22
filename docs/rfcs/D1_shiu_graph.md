# RFC D1: the published Shiu graph as a second pinned FlyWire connectome

Status: pre-registered 2026-10-20, before any flybench run on `flywire783_shiu`. Reported by
Daniel Culotta (email, 2026-10-19), who ran an unpinned version of this comparison on 25 tasks.

## The problem

The leaderboard row "Shiu 2024 (gain 1.0)" ran Shiu's constants on flybench's graph, not on the
graph of the published model. README said our ≥ 5 threshold was "matching Shiu et al."; it does not.
Measured today (`Connectivity_783.parquet` from github.com/philshiu/Drosophila_brain_model against
`data/connections.csv.gz`, the Codex v783 download):

| | Codex build (flywire783) | Shiu 2024 file |
|---|---|---|
| edges | 3,732,460 | 15,091,983 |
| threshold | ≥ 5 synapses per pair | none (82 % of pairs, 37 % of synapses are in pairs < 5) |
| shared pairs | 3,667,935 | |
| count ratio on shared pairs (Codex / Shiu) | median 1.33 (p10 1.00, p90 2.50) | |
| ≥ 5 pairs only in one file | 64,525 Codex | 132,301 Shiu |
| sign source | Codex `neurons.csv` nt_type; **blank → excitatory** | per-neuron call for every neuron |
| neurons whose sign differs | 6,195 of 138,005 presynaptic: **5,722 blank in Codex, inhibitory in Shiu**; 231 ACH→−, 199 GLUT→+, 43 GABA→+ | |
| total excitatory / inhibitory input | 33.0 M / 17.7 M (E/I 1.87) | 32.5 M / 22.0 M (E/I 1.48) |

Three causes, all MEASURED: the threshold; a different synapse table (Codex counts higher on shared
pairs); and 19,658 neurons whose Codex `nt_type` is blank (8,352 optic, 8,123 sensory of which 6,262
visual), which `build_from_codex` treats as excitatory. By the synapse-majority transmitter in the
Codex connection rows, 5,493 of them are GLUT or GABA. My guess before measuring (the Codex
table thresholds per neuropil row, so summing loses thinly spread pairs) was wrong: every pair in
the download sums to ≥ 5, and rows of 1–4 synapses exist only as parts of such pairs.

Net effect: Shiu's graph has about the same excitation and **25 % more inhibition**.

## The change

- `flybench build-shiu <parquet>` builds `flywire783_shiu`: Shiu's edges and signs (Connectivity ×
  sign(Excitatory)), flywire783's neuron index, annotations and positions (all 138,639 Shiu neurons
  are in it), so every selector resolves to the same cells. No terminal matrix (it is aligned to
  Codex edges). Pinned `fd8ac1e5…`.
- `meta.dataset = flywire783`: `dataset_only` tasks treat it as the female brain (task 30 runs on
  it; Daniel's unpinned build lost it, one of the reasons he had 25 tasks and we have 28).
- The existing row is relabelled "Shiu constants, gain 1.0 (Codex ≥5 graph)"; nothing is rerun
  for that. Neither graph is declared the reference until the runs are in.

## Runs

`flywire783_shiu`, 3 seeds, rewired control, LIF: gain 1.0 (Shiu config), 0.7 (Daniel's choice),
0.45 (the Codex reference gain).

## Pre-registered predictions

Codex numbers from FINDINGS 2026-09-21 (28 tasks). Daniel's 25-task numbers: Shiu 1.0 0.685 on his
graph vs 0.605; LIF 0.7 0.718. On the 28-task set:

| row on flywire783_shiu | core | graded | spec. | reasoning |
|---|---|---|---|---|
| Shiu 1.0 | **1.00** (Codex 0.77) | 0.66–0.71 (Codex 0.629) | ≥ +0.18 | the core failure on Codex is promiscuity (bitter does not suppress, 19 % of the brain at 29 Hz); 25 % more inhibition removes it |
| LIF 0.7 | 0.87–1.00 | 0.68–0.73 | ≈ +0.20 | **most of Daniel's +0.11 over Codex 0.45 is gain, not graph**: Codex 0.7 is already 0.70 (1 seed). Predict the graph adds ≤ +0.03 at matched gain |
| LIF 0.45 | 0.67–0.87 | 0.58–0.64 | lower | more inhibition at the gain where Codex is just above silence → taste pathways under-driven; below Codex 0.45 |
| rewired (each) | — | within ±0.05 of the Codex rewired at the same gain | | the shuffle keeps degree and sign; E/I is what moved, and it moves on both |

Task-level: `epg_ring_attractor` rises on Shiu's graph at every gain (Daniel: 0.12–0.20 → 0.26–0.51),
because a bump needs the ring's inhibition and the blank-nt fix restores some of it. Low confidence
which neurons carry it. Task 36 (closed-loop escape): Shiu 1.0 stops jumping at the near miss
(1/4 → 2/4) for the same reason as the core prediction.

## What would make this wrong

- The gain/graph split rests on a single-seed Codex 0.7 row; if the 3-seed Shiu-graph 0.7 row beats
  it by > 0.03 at matched gain, the graph matters more than predicted.
- If the core prediction fails, the extra inhibition is in the wrong place (optic/sensory) to stop
  central promiscuity, and the E/I story is too coarse.
- Selection: three gains on a new graph after seeing Daniel's numbers is a small search; the result
  is reported for all three, and no single one is promoted to reference here.

## Outcome (2026-10-20/21; the 0.45 row was rerun with `--jobs 3` after the first was killed for low memory)

| row on flywire783_shiu | core | hard | graded | spec. | predicted |
|---|---|---|---|---|---|
| Shiu 1.0 | 0.87 | 0.620 | **0.709** | +0.27 | core 1.00 ✗, graded 0.66–0.71 ✓, spec ≥ +0.18 ✓ |
| LIF 0.7 | **1.00** | **0.647** | **0.764** | **+0.33** | core ✓, graded 0.68–0.73 ✗ (higher), spec ≈ +0.20 ✗ (higher) |
| LIF 0.45 | 0.67 | 0.547 | 0.585 | +0.18 | core 0.67–0.87 ✓, graded 0.58–0.64 ✓, below Codex 0.45 (0.644) ✓ |

Against the Codex graph: Shiu 1.0 0.629 → 0.709; LIF 0.7 0.695 (1 seed) → 0.764 (3 seeds).

- **The main prediction was wrong: the graph matters more than the gain.** At matched gain 0.7 the
  published graph adds +0.07 graded, not ≤ +0.03, and passes all five core tasks where the Codex
  graph at 0.7 fails sugar and loom (0.87). Its 0.764 is a hair above the adaptive LIF on Codex
  (0.754) with no added mechanism.
- **Bitter suppression is the clearest single effect** (Shiu 1.0: 0.50 → 1.00): the extra
  inhibition lets bitter pull MN9 down, as reasoned. Core still fails at 1.0 (sugar and loom each
  miss one check), so "inhibition removes the promiscuity" was too strong.
- **Return to rest** 0.25 → 1.00 at 0.7; **ring attractor** 0.14 → 0.43 at both gains (predicted
  to rise; Daniel 0.26–0.51); task 36 1/4 → 2/4 at 1.0 (predicted).
- Losses at 0.7: GF azimuth invariance 0.67 → 0.44, dose response 0.80 → 0.60, grooming graded
  0.61 → 0.41.
- **The window moves up.** At 0.45 the Shiu graph is under-driven, as predicted: sugar 1.00 → 0.33,
  bitter suppression 1.00 → 0.00 (nothing left to suppress), adaptation 0.50 → 0.00. Applying the
  reference rule (the widest gain at which all five core reflexes pass on every seed) to the three
  gains run, the window on this graph is 0.7, the gain Daniel reported. A finer sweep (0.6, 0.8)
  would say how wide it is.
- Not yet separated: threshold vs synapse table vs the blank-nt signs. The cheapest next test is
  a Codex build with blank nt_type signed by its connection-row majority (no new data).

## Addendum: separating the causes (pre-registered 2026-10-21, before any run on it)

`flywire783_ntfix` = the Codex build with only one change: the 19,658 neurons with a blank Codex
`nt_type` take the synapse-weighted majority `nt_type` of their own connection rows
(`flybench build --blank-nt-from-connections`; pinned `27dc0261…`). Same 3,732,460 edges and counts.
Measured before running: E/I 1.87 (Codex) → **1.59** (ntfix) → 1.48 (Shiu). Signs alone move it
about 60 % of the way to Shiu's graph.

Runs: LIF 0.45 and 0.7, 3 seeds, rewired.

| row on flywire783_ntfix | core | graded | reasoning |
|---|---|---|---|
| LIF 0.45 | 0.83 (one core reflex lost to the extra inhibition) | 0.60–0.65 | partway toward the under-driven Shiu 0.45 (0.67 / 0.585) |
| LIF 0.7 | 1.00 | 0.71–0.75 | partway from Codex 0.7 (0.87 / 0.695) to Shiu 0.7 (1.00 / 0.764) |
| task 37, both | 3/5 | | signs fix inhibition, not valence |

If ntfix 0.7 lands within 0.02 of Shiu 0.7, the blank signs are most of the graph effect; within
0.02 of Codex 0.7, the threshold and synapse table are.
### Addendum outcome (2026-10-21)

| row on flywire783_ntfix | core | hard | graded | spec. | predicted |
|---|---|---|---|---|---|
| LIF 0.45 | 0.67 | 0.603 | 0.665 | +0.23 | core 0.83 ✗ (lower), graded 0.60–0.65 ✗ (higher) |
| LIF 0.7 | 0.90 | **0.681** | **0.749** | **+0.34** | core 1.00 ✗, graded 0.71–0.75 ✓ |
| task 37, both | 3/5 | | | | 3/5 ✓ |

- **The blank signs are most of the graph effect.** At 0.7: Codex 0.695 → signs fixed 0.749 → Shiu
  0.764. By the criterion written above (within 0.02 of Shiu), the signs carry it: about 80 % of
  the gap, with the same edges and counts. The threshold and synapse table carry the rest, and
  the core tier (Shiu's graph passes bitter suppression on every seed at 0.7; this one on 2 of 3).
- **The antennal lobe gets its channels back, in part.** DA1 PNs: 413 Hz to cVA, 80 Hz to DM1 at
  0.45 (was 434 / 400); lifetime sparseness 0.001 → 0.50 (measured 0.90; still a fail), task 18 score
  0.11 → 0.89; PN transfer function task 0.14 → 0.86 at 0.7. FINDINGS 2026-09-14 ("at the window gain the antennal lobe
  carries no channel identity") was in part this build's default: blank-transmitter neurons,
  read as excitatory, include inhibitory cells of the olfactory system.
- **The hard tier is the best on the board** (0.681 at 0.7, above the adaptive LIF's 0.647), with
  no mechanism added. The window moves up with the inhibition, as on Shiu's graph: at 0.45 the
  taste reflexes are under-driven (sugar 0.33, bitter suppression 0.00).
- **What this means for the reference.** The current reference row runs on a graph whose sign
  default is wrong for 19,658 neurons. Which graph the reference uses is a maintainer decision for
  v1.0 (it moves tasks between tiers); this RFC records the evidence, not the decision.
### Reference window on flywire783_ntfix (pre-registered 2026-10-21, before the sweep)

Decision (maintainer, 2026-10-21): the v1.0 reference runs on `flywire783_ntfix`. Its gain is set by
the existing rule — the widest window in which all five core reflexes pass on every seed — from a
sweep at 0.5, 0.55, 0.6, 0.65 (3 seeds, rewired), alongside the 0.45 and 0.7 rows above (both fail
core on at least one seed).

Prediction: core passes on every seed at 0.55 and 0.6; 0.5 fails a taste reflex (under-driven, as
at 0.45) and 0.65 fails bitter suppression on one seed (as at 0.7). The window is then 0.55–0.6
and the reference gain the lower edge, 0.55, by analogy with 0.45 on the old graph. If no gain
passes core on every seed, there is no window on this graph and that is the finding; the reference
does not move until there is one.
### Sweep outcome (2026-10-21): no window on flywire783_ntfix

| gain | sugar → proboscis | bitter suppression | core on every seed |
|---|---|---|---|
| 0.45 / 0.5 / 0.55 / 0.6 | fails: MN9 all-or-none (0.55: 435 Hz on one seed, 0 Hz on two) | fails (nothing to suppress) | ✗ |
| 0.65 | passes | fails (score 0.5) | ✗ |
| 0.7 | passes (163–291 Hz) | fails: sugar + bitter is 53–73 % of sugar, needs < 50 % | ✗ |

Pre-registered: window 0.55–0.6, reference 0.55. **Wrong: there is no window.** On the Codex graph
with its transmitters signed, the proboscis reflex switches from silent to saturated over 0.6–0.65,
and by the gain at which sugar fires on every seed, bitter no longer halves it. On the old
(mis-signed) Codex graph the window was 0.4–0.45; on Shiu's graph 0.7 passes every core reflex.
Per the rule written above, the reference does not move to this graph. The choice for v1.0 goes
back to the maintainer.
Decision (maintainer, 2026-10-21): v1.0 keeps the Codex ≥ 5 reference at gain 0.45. Shiu's graph
passes at 0.7 but narrowly (sugar 11.8 Hz against a 5 Hz bar on two of three seeds); the three
builds are reported side by side. Why the signed graph has no window (which neurons make MN9
all-or-none) is the open question this RFC leaves.

Full sweep rows (graded / hard / spec.): 0.5 0.688 / 0.624 / +0.25; 0.55 0.686 / 0.579 / +0.21;
0.6 0.727 / 0.601 / +0.24; 0.65 **0.761** / 0.668 / +0.33. At 0.65 bitter suppression fails on one
seed only (sugar+bitter / sugar = 0.03, 0.95, 0.00): the window is missed by one seed in three.
Task 37 on this graph is 4/5 at 0.5, 0.6 and 0.65 — it turns away from CO2 (RFC 37 addendum),
contrary to the 3/5 predicted above.