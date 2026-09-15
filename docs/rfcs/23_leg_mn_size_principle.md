# RFC: task 23 — a ramping common drive recruits the front-leg motor neurons smallest first

Status: pre-registered 2026-09-15, before the first run on any dataset. Graph statistics from
the MaleCNS wiring (synapse counts, correlations) were computed before writing this; no
simulation was run.

## The behaviour

Henneman's size principle (Henneman 1957, Science 126:1345; Henneman, Somjen & Carpenter 1965,
J Neurophysiol 28:560): as a common excitatory drive to a motor pool rises, motor neurons are
recruited in order of size, smallest first. Azevedo et al. 2020 (eLife 9:e56754, "A size
principle for recruitment of Drosophila leg motor neurons") showed the same in the fly tibia:
the slow, intermediate and fast tibia flexor MNs are recruited in that order as force rises,
and that order is the order of anatomical size (soma and axon diameter); the slow MN is active
at the lowest force, the fast MN only at the highest.

Lesser, Azevedo et al. 2024 (Nature 631:369, FANC) then asked what the wiring does about it.
Within most leg motor modules **every premotor neuron distributes its synapses onto a muscle's
MNs in proportion to MN size** (total input synapse count correlates with dendritic surface
area at r = 0.94; premotor weights are proportional "regardless of the total number of preMN
synapses, which can range over 100-fold"). They draw the consequence themselves:

> "If MN recruitment were dictated entirely by the magnitude of premotor input, then these
> patterns of proportional connectivity would cause a common input to first recruit the largest,
> fastest MNs. However, MNs controlling the fly tibia follow a conventional recruitment hierarchy
> ... Thus, the intrinsic electrical properties of the largest MNs must compensate for the higher
> number of input synapses to establish a recruitment hierarchy that follows the size principle."

Wing steering modules are different: "preMNs that contact each MN in a wing steering module do
not tend to distribute their synapses in proportion to overall synaptic input" (in module C the
smaller b2 gets the larger share).

So this is a behaviour the connectome alone is *predicted* not to reproduce. A benchmark that
only ever asked for things the wiring gives away would be a graph-statistics benchmark; this
task asks for the thing the wiring gives away wrongly, and scores whether the model put anything
into the motor neurons to fix it.

## What the task measures

MaleCNS v1.0 only (`dataset_only: [malecns, toy]`; the leg MNs are in the nerve cord).

- **Readout**: the front-left leg's motor pool, MEASURED from the annotations
  (`super_class: vnc_motor`, `sub_class: fl`, `side: L`, a leg-muscle type name): **57 MNs**
  (10 accessory tibia flexor, 8 trochanter flexor, 5 tibia flexor, 5 tarsus depressor, …).
  Sizes (total input synapse count at the connectome's ≥ 5-synapse edge threshold) run from
  7 to 11,875; one MN has no inputs at all in the reconstruction.
- **Size** = total input synapse count. CONVENTION, backed by Lesser 2024's r = 0.94 between
  input synapse count and MN surface area; docs/PLAN.md fixed this choice before the task existed.
- **Common drive**: every excitatory (`nt_type: ACH`) central neuron presynaptic to the pool
  with an edge of ≥ 3 synapses (Lesser 2024's premotor threshold — moot here, the connectome
  starts at 5), excluding sensory neurons and motor neurons: **664 neurons** (out of 1,138
  central premotor partners; the rest are GABA 268 / glutamate 197). A new selector,
  `{upstream_of: <spec>, min_synapses: N}`, does this on the graph. Driving the excitatory
  partners is the Henneman paradigm (a graded excitatory input); CONVENTION, and the alternative
  is recorded below.
- **Ramp**: 0 → 100 Hz, linear, over 1,000 ms (t = 200–1200 ms). 100 Hz is the task-02 sensory
  rate; the linear shape and the duration are CONVENTION. A new stimulus field `rate_end_hz`.
- **Checks** (all on the ramp window):
  1. `rank_order`: Spearman ρ between MN size and first-spike time **> 0.5**. The size principle
     is ρ > 0 (small early); 0.5 is the task-16 "DSI < 0.5" rule transposed to a rank correlation
     (CONVENTION). MNs that never fire rank last, tied. Undefined (NaN → fail) below 10 MNs or
     below two recruited.
  2. `readout_active_fraction` **≥ 0.8**: the ramp recruits the pool, so the order is measured
     over the pool (Azevedo 2020: all three flexor MNs are active at high force). CONVENTION;
     0.8 leaves room for the MNs the reconstruction gives no premotor input.
  3. `recruitment_spread`: interquartile range of the recruited MNs' first-spike times
     **> 50 ms** (5 % of the ramp). Azevedo 2020's MNs have distinct force thresholds; on a ramp
     those are distinct times. A single all-at-once ignition of the cord gives ~0 ms. CONVENTION.

Not scored, and why: the roadmap item says "wing steering MNs show no such order". On MaleCNS
the leg/wing contrast of Lesser 2024 holds **per premotor neuron** — the median Spearman
correlation between a premotor neuron's weights and its targets' sizes is 0.41 in the leg
(78 % positive, n = 345 preMNs with ≥ 4 targets) and 0.10 in the wing (52 % positive, n = 235)
— but the *pooled* excitatory drive scales with size in both (ρ = 0.989 leg, 0.953 wing, 16
left wing steering MNs), because the pool is nearly the MN's whole input. Under a common ramp no
model of any kind could show "no order" in the wing, so a wing null would score nothing. The
per-preMN contrast is a wiring finding (docs/FINDINGS.md), not a task.

## Pre-registered predictions

The reference model is a uniform point LIF: every neuron has the same threshold, the same
membrane, and 0.275 mV × gain per synapse. Recruitment time on a ramp is therefore a monotone
function of the pool's summed drive onto each MN, and on this pool that drive correlates with
size at ρ = 0.989. There is no way for it to pass check 1. The predictions:

- **FlyWire v783 (any model).** Not applicable, by construction.
- **MaleCNS v1.0, LIF 0.65, 3 seeds.**
  - Check 1: **fail**, ρ ≈ **−0.9** (largest first). Even if the cord ignites in a burst, the
    biggest MNs cross threshold first inside it.
  - Check 2: **pass**, ≈ 0.95 recruited — 55 of 57 MNs have positive excitatory-pool drive and
    at 0.65 anything that reaches the cord becomes a whole-CNS event (RFC 22: one pIP10 lights
    11.8 % of the CNS).
  - Check 3: **fail**. The largest MN (≈ 6,000 excitatory-pool synapses) needs a pool rate of
    only ~1–2 Hz, i.e. it fires ~10–20 ms into the ramp; the smallest need ~150 Hz and would
    never fire in isolation. But 664 cells at a few Hz plus recurrence should ignite the cord
    early, after which every MN is recruited by the network rather than by the ramp, in one
    burst: IQR < 50 ms. Lower confidence than the other two — if the cord does *not* run away,
    recruitment spreads over hundreds of ms and this passes.
  - Score **1/3 = 0.33**, or 2/3 if the cord stays graded.
- **Adaptive LIF.** Not run on MaleCNS; if it were, first spikes precede adaptation, so the
  same as the LIF.
- **Rewired control.** The pool is re-selected on the rewired graph (random presynaptic
  partners); in-degree is preserved, so the pool's drive is again ∝ size: check 1 fails at
  ρ ≈ −0.9. Random wiring conducts at 0.65 (RFC 21's null floor), so check 2 passes and, being a
  single ignition, check 3 fails. **1/3**, specificity **0.00**. This task is expected to tie
  its shuffle at the floor: it is not measuring the wiring, it is measuring what a model adds
  to the wiring. `non_diagnostic` stays false because the real run does not pass either.

The interesting outcome would be a positive ρ on the real brain — it would mean that inhibitory
or recurrent structure in the cord reverses the order that direct drive sets, which Lesser 2024
does not consider. I do not expect it.

## What would make this task wrong

- **The pool convention.** Driving *all* central premotor partners (excitatory and inhibitory
  together, 1,138 cells) is the other reasonable reading of "common input". On this graph the
  net signed drive then correlates with size at only ρ = 0.44 and 32 of 57 MNs have net drive
  ≤ 0, so the pool would not recruit and check 2 would fail on every model. The excitatory
  pool is the Henneman paradigm and the one that lets a good model pass; it is still a choice.
- **Size at a ≥ 5-synapse threshold.** Lesser counted every synapse; the connectome drops
  edges under 5. Rank order over 57 MNs spanning three orders of magnitude will not change.
- **Sub-class and side labels.** `sub_class: fl` and `side: L` are the annotators' calls; a
  mis-sided MN adds one cell from the other leg to a 57-cell pool. Two MNs carry no side.
- **The ramp shape.** A linear 0–100 Hz ramp reaches the big MNs' threshold in the first 2 % of
  its length. A log ramp would spread recruitment evenly; it is not the convention in the
  literature, so the spread check tolerates it (50 ms of 1,000).
- **Descending and ascending neurons are in the pool** (132 + 92 of the 1,138 partners). They
  are premotor neurons by Lesser's definition; a "local premotor only" pool would be a different
  convention, and would lose the descending drive the real leg uses.
- **Toy.** Twelve MNs per side with size rank k = 0..11; the premotor pool contacts MN k with
  12 − k synapses per edge and the afferents (excluded from the pool) with 2 + 4k, so size
  rises with k while pool drive falls. That is *not* how the fly does it — the fly's wiring is
  size-proportional and the compensation is intrinsic — and the toy says so in its comment. It
  proves the three checks are computable and passable. The broken-toy test rewires the pool
  proportional to size (Lesser's wiring) and must fail exactly check 1, at ρ < −0.5.

## Outcome (recorded 2026-09-15, first run after pre-registration)

**FlyWire v783, LIF 0.45:** not applicable, by construction; the results file records the skip
and the explorer shows it as such.

**MaleCNS v1.0, gain 0.65, 3 seeds, `--controls rewired`** (57 front-left leg MNs, 664
excitatory central premotor neurons ramped 0 → 100 Hz over 1 s):

| check | value (3 seeds) | per seed | result | predicted? |
|---|---|---|---|---|
| 1. ρ(size, recruitment time) > 0.5 | **−0.76** | −0.81 / −0.66 / −0.81 | fail | yes (−0.9) |
| 2. fraction of the pool recruited ≥ 0.8 | **0.47** | 0.49 / 0.44 / 0.49 | fail | **no** (0.95 predicted) |
| 3. recruitment IQR > 50 ms | 114 ms | 173 / 38 / 131 | fail (2/3 seeds) | half: predicted a single burst |
| rewired control | 1/3 (check 2: 0.81 recruited) | | specificity **−0.33** | **no** (1/3 predicted, tie) |

Score **0/3**, graded 0.33. Hard tier 0.66 → 0.61, hard-by-circuit 0.66 → 0.57 (a new
`locomotion` circuit with one task at 0), graded 0.729 → 0.720. The 22 older tasks are
bit-identical.

Check 1 went as the wiring said it would: largest first, ρ ≈ −0.8. The reference model has
nothing in its motor neurons to compensate with, and Lesser 2024's inference stands as a
benchmark result. Two things were not predicted:

1. **The small half of the pool never fires — the ramp silences it.** 28 of 57 MNs stay at
   0 Hz on every seed, and they are the 28 smallest (nothing below ~370 input synapses fires;
   above ~1,000 everything does). The cord ignites at ~300 ms (pool rate ~10 Hz; 12 % of the CNS
   active, whole-network rate 15 Hz from then on), and with it the inhibitory premotor neurons
   (268 GABA + 197 glutamate among the pool's 1,138 central partners, recurrently driven). In
   MaleCNS **the inhibitory share of a leg MN's input falls with its size** — ρ(size, inhibitory
   fraction) = −0.62; the smallest 23 MNs (< 500 synapses) get 58 % of their input from
   inhibitory neurons, the largest 5 (> 5,000) get 40 % — and for 20 of the 28 smallest MNs the
   total inhibitory input exceeds the excitatory-pool input outright. Once the cord is up,
   these MNs' net drive is negative and no ramp on the excitatory pool changes that. So on this
   wiring a common excitatory drive does not merely recruit big-first: it recruits *only* the big
   half. The size principle in the fly needs more than intrinsic excitability — it needs the
   inhibition onto the small MNs to be *withdrawn* or *patterned* with the movement, which is
   a role the GABAergic premotor hemilineages (13A/13B in Lesser 2024's premotor census) are
   placed to play. A common-drive paradigm cannot show that; a task with a patterned
   (phase-specific) inhibitory input could — that is a hypothesis, not a citation.
2. **The shuffle beats the real brain.** Degree-preserving rewiring keeps each MN's in-degree
   but randomises who supplies it, so the small MNs lose their structured inhibitory majority
   and 81 % of the pool is recruited (check 2 passes); the order is still big-first (ρ = −0.93).
   Specificity −0.33: the one check the reference model fails *because of* the real wiring is
   the one the shuffle passes. That is the first negative specificity in the benchmark, and it
   is the correct reading — the real brain's inhibition is size-structured and the shuffle's is
   not. This is a `hard`-tier task with a negative control that outperforms the model; it is not
   `non_diagnostic` (the real run does not pass) and it should not be.

Check 3 is a half-miss: among the MNs that *are* recruited, recruitment is graded over ~120–170
ms on two seeds (the leg pool's rate rises 47 → 75 Hz over the second) rather than collapsing
into one burst; the third seed gives 38 ms. It fails by the every-seed rule and is recorded as
seed-sensitive.

Not scored, but measured: the per-premotor-neuron leg/wing contrast from the pre-registration
(0.41 vs 0.10) stands as a wiring finding in docs/FINDINGS.md.
