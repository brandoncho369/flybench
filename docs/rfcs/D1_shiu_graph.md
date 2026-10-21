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