# RFC: task 30 — the egg-laying command is driven by oviEN, held down by oviIN, and not started by pC1

Status: pre-registered 2026-09-15, before the first run on any dataset. Synapse counts from the
wiring; no simulation was run. FlyWire-only: the female twin of task 22.

## The behaviour

Wang et al. 2020 (Nature 579:101): "activation of female-specific oviposition descending
neurons (oviDNs) is necessary and sufficient for egg laying, and is equally potent in virgin
and mated females"; mated females with oviDNs ablated laid no eggs. Their major excitatory
input is the oviposition excitatory neurons (oviENs), and "GABAergic oviposition inhibitory
neurons (oviINs) mediate feed-forward inhibition from pC1 neurons to both oviDNs and their
major excitatory input, the oviENs". Silencing oviINs increases egg laying in virgins. Mating
status enters upstream: sex peptide silences the abdominal sensory neurons and their ascending
targets, "attenuating the abdominal ganglion inputs to pC1 neurons and oviINs, [and] disinhibits
oviDNs to enable egg laying after mating". Wang et al. 2021 (Nature 596:433) add that oviDN
activity ramps to a threshold that triggers the egg-deposition sequence.

## What the task measures

FlyWire v783 only (`dataset_only`): the female brain has the cells; MaleCNS has no oviDN and
its pC1 are the male types (task 22). Cell sets:

- **oviDN**: `oviDNa_a`, `oviDNa_b`, `oviDNb` — 6 cells (MEASURED by type). The label
  "oviDN" also decorates DNpe038 and two CB cells; not used.
- **oviIN**: 2 cells (`oviIN`, GABA, VESa1 lineage; MEASURED by label).
- **oviEN = SMP550**, 2 cells (INFERRED). v783 has no oviEN label. SMP550 is the oviDNs'
  largest excitatory input (185 synapses onto the six) and the oviINs' largest target (−429),
  which is the paper's motif — oviIN inhibits both oviDN and "their major excitatory input" —
  and nothing else in the oviDN input list fits it.
- **pC1**: the female `pC1a–e`, 10 cells (MEASURED). pC1 → oviIN is 25 direct synapses and
  ~41,000 two-hop synapse products; pC1 → oviDN 0; pC1 → SMP550 0.

Conditions (100 Hz, 500 ms, task-02 CONVENTION): oviEN alone; oviEN + oviIN; pC1 alone.
Checks: (1) oviEN → oviDN > 5 Hz; (2) oviDN under oviEN + oviIN over oviEN alone < 0.5
(task-03 suppression convention); (3) pC1 → oviIN > 5 Hz; (4) **null** pC1 → oviDN < 2 Hz.
The output side of oviDN (abdominal ganglion) is outside FlyWire; the task scores the command
neuron, not the egg.

## Pre-registered predictions

At 0.45, SMP550's 185 synapses spread over six oviDNs are ~31 per cell: 31 × 100 Hz × 0.124 ×
5 ms ≈ 1.9 mV, far under threshold. Whether oviDN fires under oviEN depends entirely on what
two SMP550 cells at 100 Hz do to the rest of the brain.

- **FlyWire v783, LIF 0.45, 3 seeds.** Check 1: two cells with modest output — I expect no
  ignition and oviDN under threshold: **fail** (~0–2 Hz). Check 2: both sides silent → **floored
  (S2), fail**. Check 3: ten pC1 cells at 100 Hz with a 41k two-hop route: oviIN fires, **pass**
  (and, at this drive, pC1 probably lights a fair fraction of the brain — RFC 22's P1 lit 12 %
  of the male CNS at 0.65). Check 4: if pC1 ignites the brain, oviDN fires from the event —
  **fail**; if not, pass. **1/4**, or 2/4 without ignition. If SMP550 turns out to be a hub
  and ignites the brain, 1 passes and 2 floors/fails anyway: 2/4.
- **MaleCNS**: not applicable.
- **Adaptive LIF (FlyWire 1.0)**: at gain 1.0 SMP550 puts ~4 mV per oviDN; still under
  threshold on its own; 1–2/4.
- **Rewired control**: two cells through random wiring reach nothing → 1 fails, 2 floored;
  ten pC1 through random wiring — RFC 26's rule for large targets does not apply to a 2-cell
  readout; I expect silence: 3 fails, 4 passes. **1/4**, specificity 0.00.

The interesting outcome would be 1 and 2 passing: an inferred oviEN that actually drives oviDN
and an oviIN that halves it, in a uniform model — the whole circuit reproduced from four cell
types. I put it at one in five.

## What would make this task wrong

- **SMP550 = oviEN** is a motif-based inference. If oviEN is an unlabelled cell elsewhere,
  check 1 drives the wrong pair; the oviIN checks (2–4) do not depend on it except through the
  condition that pairs them.
- **pC1 → oviIN is 25 direct synapses.** The paper's connectivity is from the hemibrain and
  may route through cells v783 labels differently; the two-hop count (41k) says the route
  exists, but check 3 measures a network response, not a synapse.
- **The virgin null is a behaviour-level inference.** pC1 activity suppresses egg laying; the
  task reads that as "pC1 must not excite oviDN". A model in which pC1 excites oviDN *and* oviIN
  more strongly would still be behaviourally right and would fail the null.
- **Toy**: pC1a → oviIN → oviDN and → SMP550; SMP550 → oviDN (MODELED, the paper's diagram).
  The broken-toy test adds pC1 → oviDN and must fail exactly the null.

## Outcome (recorded 2026-09-15, first run after pre-registration; `--jobs 6`)

**MaleCNS:** not applicable, recorded as such.

**FlyWire v783, LIF 0.45, 3 seeds, `--controls rewired`:**

| check | value (3 seeds) | result | predicted |
|---|---|---|---|
| 1. oviEN (SMP550) → oviDN > 5 Hz | **14.3 Hz** (13 / 13 / 17) | pass | fail |
| 2. oviDN with oviIN / without < 0.5 | 0.68 (0.82 / 0.56 / 0.65) | fail | floored fail |
| 3. pC1 → oviIN > 5 Hz | 52 Hz (76 / 17 / 63) | pass | pass |
| 4. pC1 ↛ oviDN (null) | 0 Hz | pass | fail |
| score | **3/4** | | 1/4 |
| rewired | 1/4 (the null), specificity **+0.50** | | 1/4, 0.00 |

Better than pre-registered on both counts that were in doubt:

- **The inferred oviEN drives oviDN, and does so locally.** Two SMP550 cells at 100 Hz fire
  the six oviDNs at 14 Hz with **0.0 % of the brain active** — no ignition, no network route,
  the 185 direct synapses plus whatever SMP550's other 2-hop targets add. The steady-state
  estimate (1.9 mV per oviDN from the direct contact) was wrong because SMP550 also recruits
  the oviDNs' other excitatory inputs without lighting anything else. This is the cleanest
  circuit result in the hard tier: a four-cell-type command pathway that behaves as the paper
  draws it, at the gain where the core reflexes work.
- **oviIN suppresses, but not to half.** Driving the two oviINs at 100 Hz on top of oviEN
  takes oviDN from 14 to 10 Hz (ratio 0.68). The wiring gives oviIN −187 onto the six oviDNs
  and −429 onto SMP550, and SMP550 keeps firing (78 Hz) because it is forced; the suppression
  the fly gets from oviIN also removes oviEN's drive, which a forced oviEN cannot show. The
  check is right to fail; the convention (a forced oviEN) is what limits it.
- **The virgin null holds through an ignition.** pC1 at 100 Hz lights 8 % of the brain, drives
  oviIN to 52 Hz (seed-variable: 17–76), and oviDN stays at exactly 0 Hz on every seed — the
  oviINs (and CB0550/CB0584, the other VESa1 GABA cells onto oviDN) hold the command neuron
  down through a whole-brain event. That is the paper's feed-forward inhibition, in a uniform
  LIF, on the female brain.

Rewired 1/4 (the null only): random wiring does not carry two SMP550 cells or ten pC1 cells
to a six-cell readout. Specificity +0.50, the highest of the day's tasks.
