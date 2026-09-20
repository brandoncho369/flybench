# RFC M1b: terminal synapses for every neuron, by neuropil polarity

Status: pre-registered 2026-09-20, before any scored run. Extends RFC M1 (which treated only the
neck-spanning classes, using the brain/cord split) to every neuron in both datasets, using the
same idea one level finer: a neuron's *compartments are its neuropils*. Disclosure: the
classification statistics below were computed on the FlyWire connection table before this RFC
(they are data description, no simulation); no run with the extended model preceded it.

## The rule

For neuron j and neuropil r, with out_j(r) presynaptic and in_j(r) postsynaptic sites there,
polarity p_j(r) = out / (out + in). An input synapse onto j in r is **terminal** (axo-axonic) if

    p_j(r) ≥ 0.8   and   out_j(r) + in_j(r) ≥ 20

— j is overwhelmingly presynaptic in that neuropil, so its arbor there is axon. CONVENTION, fixed
here: 0.8 is the polarity above which the canonical axonal compartments sit and the canonical
dendritic ones do not (FlyWire v783, ≥ 20 synapses per neuron per neuropil):

| compartment | n | median p | fraction ≥ 0.8 |
|---|---|---|---|
| ORN terminals in the AL (the Olsen & Wilson 2008 synapse) | 4,110 | 0.86 | 0.70 |
| T4 axons in the lobula plate | 6,091 | 0.90 | 0.94 |
| uniglomerular PN axons in the LH | 259 | 0.93 | 0.97 |
| KC axons in the MB lobes (mixed: APL/DAN input) | 11,952 | 0.69 | 0.16 |
| T4 dendrites in the medulla | 6,169 | 0.10 | 0.00 |
| PN dendrites in the AL | 274 | 0.37 | 0.00 |
| the GF in the brain | 19 | 0.03 | 0.00 |

Sensitivity, so nobody has to trust the choice: θ = 0.7 → 7.65 % of FlyWire synapses terminal
(3.88 M), θ = 0.8 → **3.69 % (1.87 M, on 59,915 neurons)**, θ = 0.9 → 0.91 %. The rule is
conservative for mixed compartments (KC lobes stay somatic) and the number is fixed before the run.

Data: FlyWire from the Codex per-neuropil connection table already in `data/` (MEASURED per
neuropil, compartment INFERRED); MaleCNS from neuPrint per-neuron and per-connection ROI counts
(the same rule; the M1 neck split is the special case where the neuropils are "brain" and
"cord"). The model is RFC M1's, unchanged: terminal inputs off the soma, inhibitory ones scale
release to a floor of 0.3.

## Predictions

**FlyWire v783, gain 0.45, 3 seeds, `rewired`** — the terminal-aware LIF's first row that differs
from the reference (row "Terminal LIF 0.45"):

- **Core 5/5 holds.** The reflexes run dendrite to dendrite (GRN → second order → MN9; LPLC2/LC4
  → GF, whose brain arbor is all dendrite).
- **No task worsens; at least one olfactory task improves.** LN → ORN inhibition in the AL is
  now presynaptic (it scaled nothing before: ORNs are driven by forced spikes, so somatic
  inhibition of them did nothing; now it scales their release). Less ORN drive per spike → less
  PN recruitment. Task 8 (`olfactory_sparse_coding`, 84 % of PNs firing) and tasks 17–18 (PN
  transfer, DA1 sparseness) should move toward the fly; I predict **at least one check among
  them flips to pass** and none flips to fail.
- Graded 0.655 → within [0.65, 0.69]; specificity +0.21 → unchanged or higher; fewer spikes;
  max active fraction ≤ the reference's 22 %.
- Controls: the shuffle has no terminal matrix (edges are new), so control scores are
  identical to the reference's. This is a known asymmetry, declared in M1.

**MaleCNS v1.0, gain 0.65** (row "Terminal LIF 0.65 (MaleCNS)" replaced by the polarity rule):
task 35 stays 10/10; task 20 stays 4/4; graded ≥ M1's 0.669; the neck-rule terminal set is a
subset of the polarity set (checked, reported below).

## What would make this wrong

- **Neuropil granularity.** A neuron whose axon and dendrite share a neuropil (local neurons,
  KCs in the lobes) is scored somatic everywhere; the rule under-calls terminals there. Synapse
  coordinates plus a skeleton split would do better; the datasets have them, the cache does not.
- **Excitatory terminal contacts are still ignored.** With 1.87 M terminal synapses on FlyWire,
  many cholinergic, this is now a larger omission than in M1: a neuron whose axon is driven by
  excitatory axo-axonic input loses that input entirely rather than gaining release.
- **θ.** 0.7 would call twice as many synapses terminal, 0.9 a quarter. The table above is why
  0.8; the runs are not repeated at other θ to pick a winner.

## Amendment before the MaleCNS run (2026-09-20)

Two things learned while building the MaleCNS table, both before its scored run:

1. **Units.** neuPrint's per-*neuron* ROI counts are sites (T-bars vs PSDs) and give a different
   polarity scale from FlyWire's pair counts (a T4 in the lobula plate reads 0.55, not 0.90).
   The MaleCNS table is therefore built from per-*connection* ROI counts (9.1 M rows, one count per
   pre–post pair per synapse, as Codex publishes for FlyWire); in those units the T4 reads 0.92
   and the θ = 0.8 table transfers. No θ was changed.
2. **The neck rule is not a subset of the polarity rule** — the prediction above was wrong. Only
   38 % of M1's 555,960 neck-side terminal synapses fall in neuropils where the ascending or
   descending neuron is ≥ 80 % presynaptic; the rest are in mixed neuropils (the GNG above all,
   where ANs both send and receive). An AN's brain arbor is axon whatever its local polarity —
   its dendrites are in the cord — so for MaleCNS the terminal set is the **union** of the two
   rules: 3,782,429 synapses (4.19 % of all) on 76,457 neurons. FlyWire has no neck rule to add
   (1,868,931 synapses, 3.69 %, 59,915 neurons). Decided from the overlap count alone, before
   any simulation with the extended table.

## Outcome (2026-09-20; FlyWire 0.45 row "Terminal LIF 0.45", MaleCNS 0.65 row "Terminal LIF 0.65 (MaleCNS)" now on the union table)

### FlyWire v783, gain 0.45

| | reference | terminal-aware (M1b) | predicted |
|---|---|---|---|
| core | 5/5 | 5/5 | ✓ |
| hard · graded · specificity | 0.513 · 0.655 · +0.207 | **0.573 · 0.711 · +0.256** | graded [0.65, 0.69] ✗ (higher), spec ✓ |
| tasks worsened | | **none** | ✓ |
| tasks improved | | 4: task 26 `mb_sparseness_apl` 5/8 → **8/8** (KCs active per odour 60 % → 1.3 %); task 8 `olfactory_sparse_coding` 2/4 → 3/4 (cVA active fraction 8.1 % → 4.0 %); task 25 `antennal_grooming` 0/4 → 2/4 (JO-F → aDN 5.3 → 7.5 Hz, JO-C/E → MDN 11 → 0 Hz); task 6 `dose_response` 2/5 → 3/5 | "≥ 1 olfactory check flips" ✓ |
| controls | | identical, 27/27 | ✓ |
| spikes per condition · max active | 680 k · 22 % | **316 k · 17 %** | ✓ |

### MaleCNS v1.0, gain 0.65 (union of the polarity and neck rules)

| | reference | M1 (neck only) | M1b (union) |
|---|---|---|---|
| core | 0.567 | 0.567 | **0.900** — sugar → MN9 4/4 (active fraction 11.6 % → 7.1 %), bitter suppression 2/2 (ratio 0.39 → 0.31), looming → GF 3/3, wiring robustness 5/5; taste specificity 0/2 → 1/2 (quinine → MN9 stays) |
| hard · graded · specificity | 0.574 · 0.660 · +0.218 | 0.613 · 0.669 · +0.252 | 0.594 · **0.700 · +0.286** |
| task 26 mb_sparseness_apl | 5/8 | 5/8 | **8/8** (KCs 85 % → 7 %) |
| task 33 embodied_loom_escape | 3/4 | 3/4 | **4/4** — the flash through the eye no longer makes the body jump |
| task 35 gf_free_route_to_ttmn | 9/10 | 10/10 | **3/10** — check 2 passes (all DNs silenced → cord silent), but the GF-free eye-loom route itself thins to 0.5–1.0 spikes/neuron, below every "survives" check |
| task 34 ttmn_without_gf | 6/6 | 6/6 | 5/6 (the same single TTMn spike; the body still takes off on every seed at 412–560 ms) |
| task 20 taste_modalities | 2/4 | 4/4 | 2/4 — high salt stays at 0, but water → MN9 is now seed-fragile (115 / 122 / **0** Hz) and sugar + salt / sugar 0.67 on one seed |
| task 17 pn_transfer_function | 4/7 | 4/7 | 3/7 (orn10 / orn100 ratio 0.56 → 0.61 across the 0.6 line) |
| controls | | identical | identical, 33/33 |
| spikes per condition | 1.34 M | 1.26 M | **0.57 M** |

### Reading it

On both datasets the extended rule does what M1 did and more: fewer spikes, unchanged shuffled
controls, higher specificity, the mushroom body's sparseness restored on both brains (this was
the "no lateral inhibition, the antennal lobe is a broadcast" failure of the first README), the
MaleCNS core tier from 0.57 to 0.90 — the "no gain at which the reference does both taste and
vision" finding of docs/MALECNS.md is mostly the point neuron's, not the male's — and the flash
no longer makes the embodied fly jump. The predictions held in direction and were too timid in
size on FlyWire.

It also costs something the neck-only rule did not: on MaleCNS the GF-free loom route to TTMn
(tasks 34–35) is reduced to a single TTMn spike on two of three seeds — enough to command the
body's jump, not enough for the ≥ 1 spike-per-neuron checks — and water → MN9 becomes
seed-fragile. Task 35 therefore reads 3/10 for M1b against 10/10 for M1: the check it was built
to pass now passes, and the seven route checks it used to pass no longer do. Which of the two
tables is "right" is not for the score to decide: the polarity rule removes 3.4 M more synapses
from somata than the neck rule, some of them dendritic inputs mis-called in mixed neuropils, and
the missing excitatory axo-axonic drive (still ignored) is now a 4 % omission. Both rows stand;
the M1 numbers are in its RFC; the row of record is M1b, because it is the more general rule and
the more honest count.

Two consequences. (1) The datasets have synapse coordinates; the next data step is a per-synapse
axon/dendrite split, which would settle the mixed-neuropil cases the polarity rule guesses at.
(2) Excitatory terminal contacts need a model; with 4 % of synapses now off the soma, "ignored" is
the largest single assumption in the model.
