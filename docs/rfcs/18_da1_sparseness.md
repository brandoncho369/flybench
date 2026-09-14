# RFC: task 18 — one odour channel responds to one odour (lifetime sparseness)

Status: pre-registered 2026-09-14, before the first run on any dataset.

## The behaviour

Schlief & Wilson (2007, Nat Neurosci 10:623) recorded DA1 projection neurons (the cVA pheromone
channel) across an odour panel and report a lifetime sparseness of **S = 0.90** for DA1 PNs and
1.00 for their Or67d ORNs (Willmore & Tolhurst 2001 measure: S = (1 − (Σr/N)²/(Σr²/N)) / (1 − 1/N);
1 = responds to one stimulus only, 0 = equally to all). Response window 500 ms starting 100 ms
after odour onset. No sd is reported, so the check scores by the threshold rule.

Task 8 already asks "does one odour recruit most PNs" (population sparseness). This is the other
axis: does one PN respond to most odours.

## The odour panel — the convention this task rests on

The model has no receptors. An "odour" here is the ORN population of **one glomerulus** driven at
100 Hz (the task-8 convention) for 500 ms; the panel is eight glomeruli, all present by exact
type name on FlyWire v783 and MaleCNS v1.0 and in the toy:

    DA1 (cVA, the cognate channel), DM1, DM2, DM4, DL1, DL5, VA1v, DC1

Provenance: **CONVENTION**. Real odours activate several glomeruli at graded rates; a
single-glomerulus panel is the cleanest possible stand-in and deliberately favours the model (no
odour drives DA1 ORNs except cVA, so any DA1 PN response to the other seven comes from lateral
wiring inside the antennal lobe, which is exactly what the sparseness measure should see). The
panel is fixed and versioned here; changing it is a new task version. A missing glomerulus on a
dataset skips the task (`requires_stimuli` on all eight) rather than silently shrinking the panel,
which would inflate S.

Named alternative, not chosen: use the multi-glomerular odour → ORN rate matrix from the DoOR
database (Münch & Galizia 2016). More realistic, but it makes the task depend on an external
table and on how DoOR's normalised responses are mapped to Hz, two more conventions. Left for a
later version once the single-glomerulus result is on record.

## What the task measures

Readout: DA1 PNs (l, v, ad), rate per neuron, window 250–700 ms (stimulus 200–700 ms).

Checks:

1. lifetime sparseness of the DA1 PN rate across the 8 conditions ≥ 0.90 (`observed: mean 0.90,
   sd unknown`, Schlief & Wilson 2007). With the fallback threshold rule, 0.85 would fail.
2. cVA drives DA1 PNs (rate ≥ 10 Hz, the task-8 threshold), so a silent PN cannot pass by
   having S undefined — S is NaN for an all-zero readout and the check fails.
3. cVA is the strongest of the eight: rate[cva]/rate[other] > 1 for each of the seven other
   glomeruli. (Seven ratio checks; they are the part of S that is easy to read.)

Null-check note: check 3 is passed by a dead network only together with a failed check 2, so the
task is a positive task for the control logic.

## Pre-registered predictions

- Reference LIF, FlyWire 0.45: **fails** S. Task 8 shows 84 % of all PNs respond to cVA; by
  symmetry DA1 PNs will respond to most other glomeruli's drive through lateral excitation, so
  S will be far below 0.9 (guess: 0.2–0.5). cVA is still the strongest (check 3 passes) because
  the direct path is monosynaptic.
- MaleCNS 0.65: same, S lower still (91 % of PNs respond to one odour there).
- Adaptive LIF: S somewhat higher (lateral responses are weaker and adapt) but still < 0.9.
- Rewired: check 2 fails (DA1 ORNs no longer reach DA1 PNs); diagnostic.
- Toy: passes. The toy's glomeruli are wired only through GABAergic local neurons, so DA1 PNs
  are *inhibited*, not excited, by other odours: S ≈ 1. That is the toy proving the check can be
  passed by a network built to pass it, nothing more.

## What would make this task wrong

If FlyWire's ORN types for a panel glomerulus are split (VM7d/VM7v) or renamed, the stimulus
matches 0 and the task skips — that is why the panel avoids VM7. If lateral *inhibition* in the
model is so strong that DA1 PNs are silenced by other odours, S can be high for the wrong reason
(negative responses read as zero); check 3 does not catch that. A later version could use
signed responses relative to baseline.

## Outcome (recorded 2026-09-14, first run after pre-registration)

Reference LIF, FlyWire v783, gain 0.45, 3 seeds, `--controls rewired`:

| check | result |
|---|---|
| lifetime sparseness ≥ 0.90 | **0.0009**, 0/3 seeds — fail (predicted fail; predicted 0.2–0.5) |
| cVA drives DA1 PNs ≥ 10 Hz | 434 Hz — pass |
| cVA strongest of eight (×7) | ratio 1.09 to every other glomerulus — pass, 3/3 seeds |
| rewired control | 0 % (cVA no longer reaches DA1 PNs) — diagnostic |

Score 0.89, graded 0.53. The direction of the prediction held; the magnitude was badly off. S is
not "low", it is zero: the DA1 PNs respond to every glomerulus's drive at ~398 Hz and to their own
at 434 Hz. A single glomerulus at 100 Hz is enough to saturate a projection neuron three synapses
away in a different glomerulus, so at this gain the antennal lobe has no channel identity at all,
and the "strongest" checks pass only because the direct path adds 9 % on top of a ceiling.

Reading rule, same as tasks 16 and 17: the seven ratio checks carry information only when the
sparseness check is somewhere near passing. This is the third recording-match task in a row where
saturation made a secondary check pass vacuously; the pattern is now the finding, and it argues
for a suite-level "not at ceiling" gate rather than a per-task patch. Logged in FINDINGS.md.
