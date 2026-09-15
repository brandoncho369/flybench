# RFC: task 25 — antennal JO-C/E and JO-F both reach the grooming command neurons; only JO-F reaches the moonwalker DN

Status: pre-registered 2026-09-15, before the first run on any dataset. Synapse counts and
two-hop products are from the wiring; no simulation was run.

## The behaviour

Antennal grooming is commanded by a small circuit: Johnston's organ neurons (JONs, the
chordotonal mechanosensors of the antenna) → the brain interneuron aBN1 → the descending pair
aDN1 / aDN2 → the thoracic grooming pattern (Hampel et al. 2015, eLife 4:e08758; aBN1 and the
aDNs are each necessary and sufficient). Hampel et al. 2020 (eLife 9:e59976) split the JONs by
subpopulation with split-GAL4 lines and found that "activation of either JO-C/E or JO-F neurons
elicits grooming", but only JO-F "elicited a backward locomotor response" — "5- to 8-fold more
time in backward locomotion than control flies" — while under JO-C/E activation "the flies were
observed simultaneously grooming and performing wing flapping movements", with no backward
walking. The authors' own hypothesis for the JO-F response is that "the JO-F neurons could
potentially elicit an avoidance response of backward locomotion through functional connections
with MAN/MDN-like neurons" (MDN, the moonwalker descending neurons, Bidaye et al. 2014).

The roadmap item (24) is the bristle version of the same idea — BM-Ant vs BM-InOm onto aBN2
(Eichler et al. 2025, eLife 108044) — but the bristle mechanosensory types are not annotated in
FlyWire v783 or MaleCNS v1.0 (the paper names them by root id), so the JON version, which uses
annotated types on both datasets, goes first.

## What the task measures

- **Stimuli** (MEASURED by type on both datasets): `JO-C*` + `JO-E*` neurons — 433 on FlyWire,
  335 on MaleCNS — and `JO-F*` — 205 / 78. Each at the task-02 100 Hz for 500 ms (CONVENTION;
  the optogenetic activations in the paper are not rate-controlled).
- **Readouts**: aDN1 = DNg62 and aDN2 = DNge078 (Hampel 2015's names are MaleCNS synonyms; the
  same types exist on FlyWire, two cells each) — MEASURED. MDN, 4 cells on each dataset, the
  task-21 selector.
- **Wiring**: no JON makes a direct synapse on MDN in either dataset; JO-F makes 250 direct
  synapses on the aDNs in FlyWire (15 in MaleCNS), JO-C/E none. The relay to the aDNs is
  SAD093 on both datasets (JO-C/E → SAD093 265 + 69, SAD093 → aDN 251 + 147 on FlyWire; 541 +
  183 and 332 + 380 on MaleCNS) — presumably aBN1, but the annotation does not say so
  (INFERRED, not used by any selector). Two-hop excitatory synapse products to MDN: FlyWire
  JO-F 3,027 (via DNge132, DNae007) vs JO-C/E 780 (via DNge132) — 4:1 in the direction the
  behaviour wants; MaleCNS JO-F 7,680 (GNG583, pIP1) vs JO-C/E **23,863** (pIP1 854 + 503 →
  MDN 15 + 18) — 1:3, the wrong way.
- **Checks** (500 ms window):
  1. `jo_ce` → aDN > 5 Hz (Hampel 2015, 2020).
  2. `jo_f` → aDN > 5 Hz (Hampel 2020).
  3. `jo_f` → MDN > 5 Hz. The readout is INFERRED from behaviour: backward locomotion ⇒ MDN
     (Bidaye 2014), which is the authors' hypothesis, not their recording.
  4. **Null:** `jo_ce` → MDN < 2 Hz (Hampel 2020: no backward locomotion).

## Pre-registered predictions

- **FlyWire v783, LIF 0.45, 3 seeds.** JO-C/E is 433 cells with ~300 output synapses each; its
  top targets receive 1,300–1,700 synapses from the population, i.e. ~100 mV of drive at 100 Hz —
  those interneurons go to ceiling, and RFC 24 has just shown one H2 with 5,000 output synapses
  lights 8.6 % of the brain at this gain. I expect both JON drives to be whole-brain events.
  Then: 1 pass, 2 pass, 3 pass (MDN fires from the event, not from the DNge132 route), and the
  null **fails** for the same reason. **3/4.** If the brain does *not* ignite, the wiring says
  1, 2 pass (44k and 45k two-hop products onto the aDNs), 3 is doubtful (3,027 is the order of
  RFC 21's LC16 → MDN, which gave nothing at 0.45) and 4 passes: 3/4 the other way round. Either
  way 3/4; which check fails is the informative part.
- **MaleCNS v1.0, LIF 0.65.** Ignition in both conditions (every drive at 0.65 has been one).
  1, 2, 3 pass, 4 fails — and here the wiring agrees with the failure: JO-C/E → pIP1 → MDN is
  three times JO-F's route. **3/4.**
- **Adaptive LIF (FlyWire 1.0).** Same as the LIF: 3/4.
- **Rewired control.** FlyWire 0.45: a 433-cell drive through random wiring is much larger
  than the single LC types that stayed silent in RFC 21; I expect it to conduct — 1, 2, 3 pass
  and 4 fails on the shuffle too: **3/4, specificity 0.00**. MaleCNS 0.65: the same, 3/4, 0.00.
  If the shuffle does not conduct at 0.45: 0/4 + the null = 1/4, specificity +0.50.

The interesting outcome would be the null passing on FlyWire with the three positives — the
brain not igniting under 433 cells at 100 Hz, and the DNge132 route carrying JO-F to MDN on
its own. I do not expect it; RFC 24's H2 result says the ignition threshold at 0.45 is a few
thousand output synapses, and this drive has 130,000.

## What would make this task wrong

- **MDN as the backward-walking readout is the authors' hypothesis.** If JO-F's backward
  locomotion runs through another descending neuron, check 3 scores the wrong cell and the null
  is against the wrong cell too. The wiring (JO-F → MDN 4× JO-C/E on FlyWire) is consistent
  with the hypothesis on the female brain and inconsistent on the male.
- **The JO-F lines express in JO-EVP too** (Hampel 2020). The task drives the annotated JO-F
  types only, which is cleaner than the experiment; if JO-EVP carried part of the backward
  response the task under-drives it.
- **Whole-brain ignition makes every positive check pass and every null fail** regardless of
  the wiring — the recurring finding of RFCs 20–24. On this task the prediction is exactly that,
  so a 3/4 says nothing about grooming; it is the ignition again. The null is the only check
  the wiring can win.
- **Toy:** JO-C/E and JO-F → aBN1 → aDN, JO-F → MDN directly (MODELED, the real route is
  two-hop); the broken-toy test adds JO-C/E → MDN edges and must fail exactly the null.

## Outcome (recorded 2026-09-15, first run after pre-registration; `--jobs 6`, 12 + 6 min)

| check | FlyWire 0.45 (3 seeds) | MaleCNS 0.65 (3 seeds) | predicted |
|---|---|---|---|
| 1. JO-C/E → aDN > 5 Hz | **0 Hz**, fail | 402 Hz, pass | pass / pass |
| 2. JO-F → aDN > 5 Hz | 5.3 Hz (6 / 4 / 6), fail | **0 Hz**, fail | pass / pass |
| 3. JO-F → MDN > 5 Hz | **0 Hz**, fail | 7.5 Hz (19.5 / 1.5 / 1.5), fail | pass / pass |
| 4. JO-C/E → MDN < 2 Hz (null) | 11 Hz, fail | 53 Hz, fail | fail / fail |
| score | **0/4** | **1/4** | 3/4 / 3/4 |
| rewired | 1/4, specificity **−0.25** | 1/4, specificity 0.00 | 3/4, 0.00 |

The ignition happened as predicted (8.9 % and 9.1 % of the FlyWire brain, 12 % of the male CNS,
in both conditions) and the null failed as predicted. Everything else was wrong, and in the
opposite direction from the wiring counts: on FlyWire the grooming command neurons stay
*silent* under a 433-cell antennal drive, and MDN fires under JO-C/E (the null) and not under
JO-F (the positive). Post-hoc, single-seed, synapse × spike bookkeeping onto the readouts:

- **The antennal grooming command is shut by DNg98 = DSOG1** (Pool et al. 2014, the GABAergic
  descending neuron that imposes feeding restraint; synonym recorded in MaleCNS). DNg98 makes
  **597 inhibitory synapses onto the four aDNs in FlyWire, 948 in MaleCNS** — 3–5× what any
  excitatory input makes — and it fires in every ignition (68–95 spikes per cell per 500 ms on
  FlyWire). No JON contacts it (0 direct, ≤ 3,100 two-hop); it is recruited by the brain-wide
  event through CB0128, DNp104, DNp71. Inhibition onto the aDNs outweighs excitation 7:1 under
  JO-C/E on FlyWire (59k vs 8k synapse·spikes) and 20:1 under JO-F on MaleCNS. The relay SAD093
  (JO-C/E → 265, → aDN 251) is itself held to 17 spikes on FlyWire.
- **On MaleCNS JO-C/E wins the same fight** (832k excitatory vs 572k inhibitory synapse·spikes;
  SAD093 at 289 spikes) and the aDNs sit at their ceiling — 402 Hz — while JO-F, whose relay
  gets 13k, loses it: 0 Hz. Same circuit, same gate, opposite outcome, decided by whether the
  population's own relay is strong enough to overpower DSOG1.
- **MDN is inhibition-dominated in every condition** (AOTU019, LAL112/113, LT51: −278k vs
  +195k on FlyWire under JO-C/E) and fires only where a single excitatory input punches through
  (DNpe023, 333 synapses, under JO-C/E on FlyWire; LAL144/LAL162 on MaleCNS). The 4:1 two-hop
  ratio in JO-F's favour on FlyWire was irrelevant: neither route mattered, the network state
  did.
- **Second negative specificity.** The shuffle scores 1/4 on FlyWire against the brain's 0/4:
  random wiring does not deliver DSOG1 onto the aDNs.

What this says about the task: the two positives are wiring-true (JON → SAD093 → aDN is there,
JO-F → aDN direct is there) and the model still fails them, because the model's ignition
recruits a real gate. Whether a fly's DSOG1 fires during antennal stimulation is a recording
question; Pool 2014 describe it as tonically active and feeding-suppressing, so a gate on
grooming is not implausible — but a *silenced* grooming command under antennal touch is the
opposite of the behaviour, so on this point the model, not the wiring, is wrong.
