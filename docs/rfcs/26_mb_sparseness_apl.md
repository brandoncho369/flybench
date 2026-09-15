# RFC: task 26 — Kenyon cell odour responses are sparse, and less sparse without APL

Status: pre-registered 2026-09-15, before the first run on any dataset. Wiring numbers are from
the graph; no simulation was run.

## The behaviour

Odour representations in the mushroom body are sparse: an odour activates ~5 % of Kenyon cells
(Honegger, Campbell & Turner 2011, J Neurosci 31:11772, population calcium imaging; Turner,
Bazhenov & Laurent 2008, J Neurophysiol 99:734, ~6 % by electrophysiology). Lin et al. 2014
(Nat Neurosci 17:559, "Sparse, decorrelated odor coding in the mushroom body enhances learned
odor discrimination") showed the single GABAergic APL neuron per hemisphere enforces it: APL is
driven by the KC population and inhibits all of it; blocking APL output (shibire^ts) increased
KC odour responses, lowered population sparseness, raised the overlap between the KC
representations of different odours, and impaired learned discrimination of similar (not
dissimilar) odours. The circuit is the textbook normalisation loop, and it is in both
connectomes: FlyWire v783 KC → APL 149,649 synapses, APL → KC 147,021 (91 % of APL's output),
median 28 APL synapses per KC; MaleCNS 209,279 / 195,278 (94 %), median 49.

## What the task measures

- **Silencing.** A condition may carry `silence: <selector>`; those neurons' outgoing synapses
  are zeroed for that condition and nothing else changes (the neuron keeps its inputs; it is
  shibire, not ablation — docs/PLAN.md fixed this convention before the task existed). A task
  that silences must list `requires_capabilities: [can_silence]`; simulators declare their
  capabilities (`LIFSimulator.capabilities`) and one without it skips the task (CONTRIBUTING §3).
  This is the first use of both, and it is what items 18 (silencing phenotypes) and the
  dopamine-plasticity thread need.
- **Stimuli**: the task-18 odour panel — eight glomeruli (DA1, DM1, DM2, DM4, DL1, DL5, VA1v,
  DC1), each the whole ORN type at 100 Hz for 500 ms (CONVENTION, task 18's) — with APL intact
  and with APL silenced: 16 conditions.
- **Readouts**: every `KC*` type (5,177 on FlyWire, 4,064 on MaleCNS; MEASURED) and APL (2).
- **Checks** (500 ms window):
  1–3. `readout_active_fraction` of KCs under DA1, DM4, VA1v with APL intact **< 0.2**. The
     fly's number is 0.05; 0.2 is a CONVENTION loosened for a model whose "odour" is one whole
     glomerulus at 100 Hz rather than a mixture at natural concentration. These are null-type
     checks (a silent mushroom body passes them), which is why they come with 4–8.
  4–6. `ratio` of the active fraction, APL silenced over intact, for the same three odours
     **> 1** (Lin 2014; task-18 direction convention). Not subject to the ceiling gate (the
     gate is for rate ratios).
  7–8. `ratio` of `population_sparseness` (Willmore & Tolhurst 2001, the task-18 formula across
     KCs instead of across odours), intact over silenced, for DA1 and DM4 **> 1** (Lin 2014).

Inter-odour correlation, the paper's third result, is not scored: with single-glomerulus
odours the KC sets are disjoint by construction and a correlation between them says nothing
about APL (the toy showed exactly that: ≈ 0 with and without APL). It would need mixture odours.

## Pre-registered predictions

The wiring: a FlyWire KC receives a median 144 input synapses, 74 of them from uniglomerular
PNs and 28 from APL (MaleCNS 219 / 94 / 49). Task 18's finding is the premise: driving one
glomerulus fires ~84 % of all projection neurons in this model (no lateral inhibition in the
antennal lobe at 0.45), so every KC sees most of its PN input active, ~74 synapses × ~200 Hz
× 0.124 mV × 5 ms ≈ 9 mV — above threshold on its own. APL, driven by the whole population,
sits at its ceiling and gives each KC ~28 × 360 Hz × 0.124 × 5 ≈ −6 mV. Net ≈ +3 mV: many KCs
still fire.

- **FlyWire v783, LIF 0.45, 3 seeds.** Checks 1–3 **fail**: the active fraction with APL
  intact is ~0.5 (the PN broadcast, not the KC wiring, is the problem). 4–6 **pass**: silencing
  APL removes −6 mV from every KC and the fraction rises toward 1 (ratio ~1.5–2). 7–8 **pass**:
  sparseness falls when more KCs fire (ratio > 1, modest, ~1.1). **5/8 = 0.625.** If the APL
  loop happens to hold the population under 20 % — possible if APL's −6 mV lands on KCs whose
  PN drive is near threshold — 1–3 pass and it is 8/8; I put that at one chance in four.
- **MaleCNS v1.0, LIF 0.65.** Every odour ignites 12 % of the CNS; KCs at ~1.0 active with and
  without APL; ratios ≈ 1 → 4–8 fail on noise; 1–3 fail. **0–2/8.** MaleCNS APL is stronger
  (49 synapses per KC, −15 mV at 0.65) — if that keeps the intact fraction visibly under the
  silenced one, 4–6 pass: 3/8.
- **Adaptive LIF (FlyWire 1.0).** As the LIF, 5/8.
- **Rewired control.** APL's 147k output synapses land on random cells; silencing it changes a
  random 0.4 % of the wiring; ratios ≈ 1 → 4–8 fail. At 0.45 random wiring does not carry an
  ORN drive to the KCs (RFC 21) → 1–3 pass as nulls. **3/8**, specificity +0.25 on FlyWire;
  MaleCNS: random wiring conducts, 1–3 fail too, **0/8**.

The interesting outcome would be 1–3 passing on FlyWire — the APL loop doing its job on top of
a broadcast antennal lobe. The other interesting outcome would be 4–6 failing while 1–3 pass:
sparseness that does not depend on APL, i.e. thresholds doing the work Lin 2014 attribute to
inhibition.

## What would make this task wrong

- **The odour convention.** One whole glomerulus at 100 Hz is not an odour; a real odour is a
  concentration-dependent pattern over ~20–50 glomeruli. The model has no receptor model
  (task 18's convention), so this is the panel we have. The 0.2 threshold is chosen for it.
- **The premise of 1–3 is task 18's PN broadcast.** If a later model fixes lateral inhibition,
  these checks measure the mushroom body; until then they measure the antennal lobe. The ratios
  (4–8) are APL-specific either way.
- **Silencing all of APL's outputs** also silences APL → non-KC targets (9 % of its output,
  e.g. onto MBONs and DANs). Lin 2014's shibire did the same. Documented, not a confound.
- **Population sparseness on spike counts** from a 500 ms window is coarse for KCs that fire
  1–3 spikes; the ratio between two conditions on the same window cancels most of that.
- **Toy:** 400 KCs sampling 2–8 random PNs of the eight glomeruli with graded contacts; KC ↔
  APL ~28 synapses each way. Intact: 4–6 % of KCs per odour; APL silenced: 25–30 %; sparseness
  ratio 1.13–1.16. The broken-toy test cuts APL → KC, after which silencing changes nothing and
  every ratio sits at exactly 1.

## Outcome (recorded 2026-09-15, first run after pre-registration; `--jobs 6`, 18 + 16 min)

| check | FlyWire 0.45 | MaleCNS 0.65 | predicted (FW / MC) |
|---|---|---|---|
| 1–3. KCs active with APL intact < 0.2 | **0.60 / 0.60 / 0.61**, fail | 0.85 / 0.85 / 0.86, fail | fail / fail |
| 4–6. active fraction, APL off / intact > 1 | 1.47 / 1.48 / 1.46, pass | 1.17 / 1.18 / 1.17, pass | pass / fail |
| 7–8. population sparseness, intact / off > 1 | 1.89 / 1.89, pass | 3.25 / 3.26, pass | pass / fail |
| score | **5/8** | **5/8** | 5/8 / 0–2 |
| rewired | 3/8, specificity +0.25 | 3/8, +0.25 | 3/8 / 0/8 |

FlyWire went exactly as pre-registered: the antennal-lobe broadcast (task 18) puts 60 % of the
5,177 KCs above threshold under one glomerulus, and APL — at its ceiling, 419 Hz, driven by the
population — is what keeps the other 40 % down: silence it and 89 % fire, KC mean rate doubles
(47 → 98 Hz), sparseness halves. Three seeds agree to four decimals because 5,000 KCs average
the Poisson drive away.

MaleCNS was the wrong prediction: I expected the 0.65 ignition to saturate both conditions and
leave nothing for the ratios. Instead APL's stronger MaleCNS contacts (median 49 synapses per KC
vs 28) hold the intact fraction at 85 % against 99.7 % silenced, and the KC rate at 148 Hz vs
310 — the sparseness ratio is 3.3, larger than FlyWire's. The MaleCNS shuffle also passed the
three nulls (0/8 predicted): degree-preserving rewiring does not carry an ORN drive to the KC
population at 0.65 here, as it did not at 0.45 in RFC 21 — the "random wiring conducts at 0.65"
rule from RFC 21 held for descending neurons, not for a 4,000-cell target.

What this says: **the APL normalisation loop works in a uniform LIF on both connectomes** — the
direction and the mechanism of Lin 2014 are in the wiring — and **the sparseness itself does
not**, because the model's antennal lobe hands the mushroom body 84 % of its PNs for one
glomerulus. Checks 1–3 are a task-18 fail wearing a task-26 label; a model with lateral
inhibition in the antennal lobe is the one that could pass them. Also recorded: silencing APL's
outputs leaves APL itself at 419 Hz (it still gets its KC input), as the shibire analogy intends.
