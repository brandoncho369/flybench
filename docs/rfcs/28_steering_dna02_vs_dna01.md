# RFC: task 28 — DNa02 reaches the leg motor neurons faster and harder than DNa01, on its own side, without waking its twin

Status: pre-registered 2026-09-15, before the first run on any dataset. Synapse counts from the
wiring; no simulation was run.

## The behaviour

DNa01 and DNa02 are the two best-characterised steering descending neurons (Bidaye et al. 2020,
Neuron 108:469; Chen et al. 2018, Nat Neurosci 21:1290). Rayshubskiy et al. 2025 (eLife
13:RP102230) recorded both during walking: the right–left difference in firing rate predicts
rotational velocity "essentially linearly", but "rotational velocity was a relatively steep
function of DNa02 activity, but a comparatively shallower function of DNa01 activity"; DNa02's
steering filters are larger and biphasic (transient), DNa01's monophasic (sustained); "spike
rate fluctuations in DNa02 typically preceded the spike rate fluctuations in DNa01"; and in the
connectome "DNa02 makes more direct synaptic connections onto motor neurons, as compared to
DNa01", with "very few of the postsynaptic cells targeted by these two DN types shared in
common". Inputs are organised as "see-saw" steering: "excitation of one DN copy is accompanied
by inhibition of the contralateral copy". Unilateral DNa02 activation gives "a small average
steering bias in the ipsilateral direction".

## What the task measures

MaleCNS v1.0 only (`dataset_only`), where the leg motor neurons are. The wiring (MEASURED):

| | out synapses | direct → leg MNs | MNs contacted | side of those MNs | two-hop products → leg MNs | → contralateral twin |
|---|---|---|---|---|---|---|
| DNa02_R | 6,399 | **490** | 11 | all right | 278,539 | 0 |
| DNa01_R | 4,879 | 104 | 6 | all right | 402,505 | 0 |
| DNa02_L | 6,677 | 509 | 15 | all left | 353,173 | 0 |
| DNa01_L | 5,502 | 98 | 7 | all left | 467,746 | 0 |

The paper's claim holds on the male: DNa02 makes ~5× the direct MN contacts, and DNa01's
influence is mostly polysynaptic (its two-hop route is larger). Every direct contact is
ipsilateral; neither DN touches its twin.

Conditions: the right DNa02 alone, then the right DNa01 alone, each at the task-02 100 Hz for
500 ms (CONVENTION; the paper's rates are natural walking rates of tens of Hz). Readouts: the
right and left leg motor pools (136 / 139 MNs, the task-22 selector by side) and the left
DNa02. Checks:

1. DNa02 → right leg MNs > 5 Hz.
2. DNa01 → right leg MNs > 5 Hz.
3. `ratio` of first-spike **latency** (new ratio metric: the median over the pool of each MN's
   first spike after its own condition's onset), DNa02 / DNa01 **< 1** — the more direct route
   recruits the pool sooner. INFERRED from the wiring and from DNa02 leading DNa01 in the
   recordings; the paper does not measure MN latency.
4. `ratio` of pool rate DNa02 / DNa01 **> 1** — high gain vs low gain, INFERRED to MN rate.
   Ceiling-gated.
5. `ratio` of right-pool rate over left-pool rate under DNa02 (`over_readout`, new) **> 1** —
   the ipsilateral bias; every direct synapse is ipsilateral. Ceiling-gated.
6. **Null:** the left DNa02 under right-DNa02 drive < 2 Hz — see-saw, not co-activation.

## Pre-registered predictions

- **MaleCNS v1.0, LIF 0.65, 3 seeds.** One descending neuron at 100 Hz is a whole-CNS event
  at this gain (RFC 22: one pIP10 → 11.8 %; RFC 21: any DN drive). Then: 1, 2 **pass**;
  3: the direct DNa02 targets fire within a few ms, but the median over 136 MNs is set by when
  the ignition reaches the pool, which is about the same for either DN — ratio ≈ 1, **fail**
  (coin flip; if DNa02's 11 direct MNs pull the median enough, pass); 4 and 5: both pools at
  the refractory ceiling → **saturated, fail**; 6: the left DNa02 fires from the event, **fail**.
  **2/6 = 0.33.** If the single-DN drive does *not* ignite the cord — if pIP10's ignition in RFC
  22 was a property of pIP10's targets, not of any DN — then 3, 4, 5 pass on the direct wiring
  and 6 passes: 6/6. I put that at one in five.
- **FlyWire v783:** not applicable (no leg MNs).
- **Rewired control.** Random wiring conducts a single DN to single targets at 0.65 (RFC 21),
  so 1, 2 pass; 3–5 sit at 1 and fail; 6 fails: **2/6, specificity 0.00.** If the random
  wiring happens not to reach the leg pools (a 275-cell target, cf. RFC 26's 4,000 KCs): 0/6
  + the null = 1/6, specificity +0.17.

The interesting outcome is check 3 passing while 4–6 fail: the wiring's directness surviving
in the timing when the rates have long since saturated. That is the one number the ceiling
gate cannot take away.

## What would make this task wrong

- **Turn direction vs MN pool.** "Ipsilateral steering bias" is a body rotation; which leg
  pool moves more during an ipsilateral turn depends on the gait. Check 5 scores the wiring's
  ipsilaterality, and says so; it does not score a turn.
- **Latency as median first spike over the pool** is dominated by the pool's slowest members;
  a more honest DNa02-specific latency would read only its direct targets, which would be
  selecting the readout by the answer. Recorded as a limitation.
- **100 Hz on a steering DN** is several times its natural rate; the ratios cancel the
  convention, the rates in 1–2 do not.
- **Toy:** DNa02_R → the right T1 MNs directly (90 synapses each), DNa01_R → a 20-cell
  premotor pool → the same MNs; nothing crosses the midline, and the left T1 pool (task 23's
  readout, whose premotor pool is selected from the graph) is untouched. The broken-toy test
  adds a right → left DNa02 contact and must fail exactly the see-saw null.

## Outcome (recorded 2026-09-15, first run after pre-registration; `--jobs 6`)

**FlyWire v783:** not applicable, recorded as such.

**MaleCNS v1.0, LIF 0.65, 3 seeds, `--controls rewired`:**

| check | value (3 seeds) | result | predicted |
|---|---|---|---|
| 1. DNa02 → right leg MNs > 5 Hz | **0.12 Hz** (0.13 / 0.12 / 0.10) | fail | pass |
| 2. DNa01 → right leg MNs > 5 Hz | **0.04 Hz** | fail | pass |
| 3. latency ratio DNa02 / DNa01 < 1 | 0.34 (0.08 / 0.45 / 0.49) | pass | fail (coin flip) |
| 4. rate ratio DNa02 / DNa01 > 1 | 2.9 (3.0 / 3.9 / 1.7) | pass | saturated fail |
| 5. right pool / left pool under DNa02 > 1 | **0.37** (0.26 / 0.46 / 0.40) | fail | saturated fail |
| 6. left DNa02 silent (null) | 0 Hz | pass | fail |
| score | **3/6** | | 2/6 |
| rewired | 1/6, specificity **+0.33** | | 2/6, 0.00 |

Every line of the prediction was wrong in the same way: **a single steering DN at 100 Hz does
not ignite the male CNS at 0.65** — 0.0 % of the network is active in either condition — and
does not even fire its own motor pool. The whole-CNS event of RFC 22 was a property of pIP10
(and of the sensory drives), not of "any descending neuron". Three things from the wiring:

- **490 direct synapses over 11 MNs is 45 per MN, ~4 mV at 0.65: sub-threshold.** Only the two
  sternal anterior rotator MNs with 134 and 102 synapses (12 and 9 mV) are within reach, and
  DNa02's largest targets are GABAergic premotor interneurons (IN08A006 ×2, IN19A003, PS100;
  glutamatergic DNge026, PS137) that inhibit the pool. The right pool's 0.12 Hz is ~8 spikes in
  500 ms across 136 cells. Rayshubskiy's DNa02 fires at tens of Hz *in a walking fly* whose
  premotor network is already active; a lone DN on a silent cord moves nothing in this model.
- **The pool that does move is the contralateral one** (left 0.34 Hz vs right 0.12): DNa02_R's
  one strong excitatory premotor target, IN07B006 (109 synapses), makes 1,043 synapses onto
  *left* leg MNs and none onto right ones. Check 5 fails in the direction opposite to the
  direct wiring — a two-hop crossing route beats a one-hop ipsilateral one, at these rates.
- **Checks 3 and 4 pass on spike counts of 8 vs 3.** The latency ratio (0.34) and the rate
  ratio (2.9) are in the predicted direction and hold on every seed, but they are ratios
  between two nearly silent pools. The RFC S1 ceiling gate has no floor counterpart: a ratio
  whose both sides are below the task's own response threshold (5 Hz) should not count as a
  pass. Proposed as RFC S2 (a response floor on comparison checks), to be applied to every
  archived result with the same before/after accounting as S1 — not changed here.

The see-saw null passes for the same reason everything else fails: nothing propagates. The
shuffle scores 1/6 (that null), so specificity is +0.33 on the strength of two ratios over a
handful of spikes. Read the task as: **the reference model cannot move a leg pool from one
steering DN**, and the direct-wiring differences the paper reports are visible only in the
timing and ratio of a few stray spikes.
