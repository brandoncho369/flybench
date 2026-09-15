# RFC: task 22 — P1 drives pIP10 drives the song wing motor neurons, on either wing, not the legs

Status: pre-registered 2026-09-14, before the first run on any dataset.

## The behaviour

Male courtship song is commanded by a three-node chain (von Philipsborn et al. 2011, Neuron
69:509): the male-specific P1 cluster in the brain (fru+/dsx+, the pMP-e / pMP4 lineage of
Cachero et al. 2010 and Yu et al. 2010) → the descending neuron pIP10 (one per hemisphere) →
thoracic song premotor neurons (dPR1, vPR6, and the TN1 population; Lillvis et al. 2024, Curr Biol,
from the MANC connectome) → the wing motor neurons that drive song (hg1–4, ps1, b1, i1, i2, iii1,
iii3; O'Sullivan et al. 2018, Curr Biol 28:2705; Lillvis et al. 2024). Thermogenetic activation of
P1 or of pIP10 elicits pulse song; pIP10 is necessary and sufficient. Unilateral pIP10 activation
elicits song from either wing with no ipsilateral or contralateral bias (10/13 unilateral flies;
von Philipsborn et al. 2011). pIP10 activation produces wing extension and song, not walking
(Cande et al. 2018, eLife 7:e34275, descending-neuron optogenetic screen).

The chain is sexually dimorphic: P1 and pIP10 exist only in males. FlyWire v783 is a female brain
(its pC1a–e are the female pC1 types, 10 cells, no pMP-e lineage) and has no nerve cord, so the
task cannot run there and should say **not applicable**, not "matches no neurons". This is the
first task that is defined on one dataset only — the `dataset_only:` field — and the first
brain-to-nerve-cord chain longer than one descending hop.

## What the task measures

MaleCNS v1.0 only (`dataset_only: [malecns, toy]`). Cell sets, all MEASURED from the annotations:

- P1 = `pC1_*` types whose synonyms carry the pMP-e / pMP4 lineage: 86 neurons, 43 per side.
- pIP10: 2 (one per side). Song wing MNs: the ten types above, 20 neurons, 10 per side.
- Leg MNs: the 275 leg motor neurons the export already names (flexor/extensor/… MN types).

Three conditions: P1 driven bilaterally at 100 Hz for 500 ms (CONVENTION: the task-02 sensory
drive; no P1 firing rate under courtship is published); the left pIP10 alone at 100 Hz; the right
pIP10 alone. Checks (readout rates in the 500 ms drive window):

1. P1 → pIP10 fires (> 5 Hz, task-02 convention). MEASURED contact: 1,444 synapses onto the pair.
2. P1 → song MNs fire (> 5 Hz). von Philipsborn 2011: P1 activation elicits song.
3. P1 → at least half the song MNs fire (`readout_active_fraction` > 0.5, CONVENTION): a song
   is several muscles, not one; the exact set per song mode is O'Sullivan 2018's figure, not a
   threshold I can cite as a number.
4. **Null:** pIP10 → leg MNs < 2 Hz (task-05 convention). INFERRED from behaviour: pIP10
   activation gives song, not walking. In the wiring pIP10 makes 0 direct synapses on leg MNs;
   its two-hop drive to song MNs is ~40× its two-hop drive to leg MNs (via IN18B009/IN18B029).
   Scored on the left-pIP10 condition.
5. Left pIP10 alone → song MNs fire (> 5 Hz). von Philipsborn 2011: one pIP10 suffices.
6. Right pIP10 alone → song MNs fire (> 5 Hz).
7–8. **No side bias:** the left song MNs' rate under left-pIP10 drive over their rate under
   right-pIP10 drive is < 3, and the reverse < 3 (the task-16 DSI < 0.5 rule). INFERRED from
   the unilateral-activation result; the wiring agrees (each pIP10's two-hop drive splits
   464k / 380k and 407k / 384k synapse-products between the two wings). Both ratio checks are
   subject to the RFC S1 ceiling gate: if the MNs sit at the refractory ceiling under both
   drives the comparison is saturated and fails.

Nothing about song rhythm, pulse vs sine, or inter-pulse interval: a static LIF has no business
being scored on those (ROADMAP: "never song rhythm").

## Pre-registered predictions

- **FlyWire v783 (any model).** Not applicable, by construction. Adaptive LIF: same.
- **MaleCNS v1.0, LIF 0.65.** Checks 1, 2, 3, 5, 6 pass — the chain is heavily wired (pIP10 →
  dPR1 1,112, → TN1 3,460 synapses; those → song MNs ~5,800) and at 0.65 everything downstream
  of a 100 Hz drive fires. Check 4 **fails**: at this gain the loom reaches MN9 and bitter reaches
  MN9; pIP10's 18 two-hop routes into leg MNs will carry it. Checks 7–8: the MNs will be at the
  refractory ceiling under either pIP10 (the GF reaches 436 Hz on a loom) → **saturated, fail**.
  Score **5/8 = 0.625**. If the MNs are *not* at ceiling, 7–8 pass and it is 7/8.
- **Rewired control.** Checks 1, 2, 3, 5, 6 fail (a single pIP10 through random wiring reaches
  nothing in particular); 4 passes (null); 7–8 pass vacuously (0/0 → ratio 1) — the reason the
  "seen" checks 5–6 exist. **3/8**, specificity ≈ +0.25.

The interesting outcome would be check 4 passing at 0.65 — a descending command that stays in
its own motor pool at a gain where sensory drives do not. I do not expect it. The second
interesting outcome would be a side bias: a wiring asymmetry the behaviour does not show.

## What would make this task wrong

- P1 identification rests on the pMP-e / pMP4 synonym on `pC1_*` types. If the annotators
  meant the whole pC1 cluster and only some of its types are P1 proper, the P1 set is too large
  (86 vs the ~40 of the literature); the P1 → pIP10 result would still hold but "P1" would be
  overstated. Recorded as MEASURED-by-annotation, not by fru expression.
- 100 Hz P1 drive is a convention. P1 activation in the papers is thermogenetic/optogenetic,
  not rate-controlled; if 100 Hz on 86 cells is a much larger drive than a courting male's P1,
  check 4's leak is overstated. The single-pIP10 conditions do not share this problem (one
  neuron at 100 Hz is a modest drive).
- The leg-MN null is inferred from "pIP10 gives song, not walking". A courting male walks while
  singing; if leg MN firing under pIP10 reflects a real coordination pathway rather than leak,
  the null is wrong. The two-hop synapse count (40:1 song:leg) says the wiring does not intend
  it, but a wiring ratio is not a behavioural measurement.
- `dataset_only` is a declaration, not a detection: if MaleCNS is renamed the task skips
  everywhere. The lint checks the list against the known dataset names.
- Toy: a P1 → pIP10 → TN1 → song MN chain wired to pass (MODELED); the leg MN pool receives
  nothing, so the null passes trivially. The broken-toy test adds a pIP10 → leg MN edge and must
  fail check 4.

## Outcome (recorded 2026-09-15, first run after pre-registration)

**FlyWire v783, LIF 0.45:** not applicable, by construction — the results file records
`skipped: not applicable: courtship_song_chain is defined on malecns/toy only`, and the explorer
shows it as a dotted "not applicable" dot rather than "not run yet".

**MaleCNS v1.0, gain 0.65, 3 seeds, `--controls rewired`** (86 P1, one pIP10 per side, 20 song
MNs, 275 leg MNs):

| check | value (3 seeds) | result | predicted? |
|---|---|---|---|
| 1. P1 → pIP10 | 72 Hz | pass | yes |
| 2. P1 → song MNs | 67 Hz | pass | yes |
| 3. P1 → ≥ ½ of song MNs active | 0.88 | pass | yes |
| 4. left pIP10 → leg MNs < 2 Hz (null) | **16 Hz** | fail | yes |
| 5. left pIP10 → song MNs | 71 Hz | pass | yes |
| 6. right pIP10 → song MNs | 77 Hz | pass | yes |
| 7. left MNs: left-pIP10 / right-pIP10 < 3 | 0.93 | pass | alternative outcome |
| 8. left MNs: right-pIP10 / left-pIP10 < 3 | 1.08 | pass | alternative outcome |
| rewired control | 3/8 | specificity +0.50 | yes (3/8) |

Score **7/8 = 0.875**, graded 0.82. The pre-registration called 5/8 with 7–8 saturated and
named 7/8 as the outcome if the motor neurons were *not* at ceiling: they are not (65–83 Hz,
well under the 364 Hz gate), so the symmetry checks were live and the wiring reproduces
von Philipsborn's either-wing result almost exactly — a unilateral pIP10 drives the left wing's
motor neurons at 0.93× and the right at 1.08× of what the other pIP10 does. The two-hop synapse
counts (464k / 380k and 407k / 384k) said the split would be within 20 %; the simulation agrees.

Three things worth keeping:

1. **One neuron at 100 Hz activates 11.8 % of the male CNS.** A single pIP10 recruits the same
   fraction of the network as 86 P1 cells or a full sugar drive at this gain. The song chain is
   the first task where the command neuron is literally one cell, and it shows what 0.65 means:
   the gain is set so that any drive that reaches a descending neuron becomes a whole-CNS event.
   The leg-MN leak (16 Hz, via IN18B009 / IN18B029, the two-hop routes the RFC identified) is
   that event, not a song-specific pathway.
2. **The undriven pIP10 fires at ~55–65 Hz when its partner is driven.** Direct pIP10 ↔ pIP10
   contacts exist but are weak (6 and 12 synapses); two-hop routes run through ANXXX152 (an
   ascending neuron) and AVLP718m. At 0.65 the recurrent activity does the rest. Behaviourally
   one wing sings at a time, so whether both pIP10 fire together in a singing male is a
   recording question; the wiring allows it.
3. **The "either wing" symmetry is in the descending wiring, not downstream of it.** Both pIP10
   reach both wings' premotor pools with near-equal weight, so wing choice — which the fly makes
   (the wing nearer the female) — has to come from somewhere other than which pIP10 fires.
   That is consistent with von Philipsborn's no-bias result and says the choice is made in the
   nerve cord or by a different descending input. A future task could ask which.

Nothing about this outcome changes the task. The P1 identification (pC1 ∩ pMP-e, 86 cells)
stands as MEASURED-by-annotation.
