# RFC: task 24 — DNp15 prefers yaw rotation to forward translation, and bIPS prefers the reverse

Status: pre-registered 2026-09-15, before the first run on any dataset. Synapse counts below are
from the wiring (no simulation); the rate estimates are back-of-envelope LIF steady states.

## The behaviour

The lobula plate tangential cells encode wide-field motion: the three horizontal-system cells
(HSN, HSE, HSS) of each side depolarise to front-to-back (progressive) motion on their own eye
(Schnell et al. 2010, J Neurophysiol 103:1646), and H2 to back-to-front (regressive) motion on
the eye of its dendrite, projecting to the other side (Krapp et al. 2001, J Neurophysiol
85:724). Three descending neurons carry this to the motor centres; DNHS1 — DNp15 in the
connectome nomenclature — responds maximally to yaw rotation and is direction-selective
(Suver et al. 2016, J Neurosci 36:11768).

Nat Neurosci 2025 ("A competitive disinhibitory network for robust optic flow processing in
Drosophila", doi 10.1038/s41593-025-01948-9; bioRxiv 2023.08.06.552150) traced the network
between them: HS and H2 converge on DNp15 and on a middle layer of GABAergic interneurons
(bIPS, uLPTCrn, H2rn) with reciprocal and lateral inhibition. Two physiological results
(two-photon calcium, z-scored):

- DNp15 "demonstrated enhanced selectivity to rotational stimuli than translational-like
  stimuli, unlike HS cells" (Fig. 1e; HS n = 16 ROIs / 12 flies, DNp15 n = 7 / 6). DNp15
  also shows "a small but detectable response to contralateral back-to-front visual motion",
  i.e. it integrates H2.
- bIPS "was most active with binocular symmetric horizontal stimuli" (n = 9 / 7) and, per the
  authors' model, subtracts the symmetric (translational) component at DNp15: removing bIPS
  from the model "reduced the asymmetry between left and right DNp15 cells".

The paper reports z-scores, not rates or mV, so every threshold here is the sign of an effect
with a convention for the number.

## What the task measures

The model has no eyes. Optic flow is the set of tangential cells a given flow would drive,
INFERRED from their preferred directions above, each at the task-02 100 Hz (CONVENTION; HS and
H2 are graded cells in the fly, and a Poisson rate is the model's only currency):

| condition | cells driven | what it stands for |
|---|---|---|
| `ftb_left` | HS_L (3) | front-to-back on the left eye, the monocular reference |
| `yaw_right` | HS_L + H2 with its dendrite on the right | a right yaw turn: left eye front-to-back, right eye back-to-front |
| `yaw_left` | HS_R + H2 (left dendrite) | the mirror |
| `forward` | HS_L + HS_R | forward translation, binocular symmetric |

H2's `side` in both datasets is its soma side, which is its dendritic side; the wiring agrees
(FlyWire: H2_R → DNp15_L 206, → bIPS_L 124, nothing to the right-side cells).

Readouts: DNp15 left and right (MEASURED by type on both datasets), and bIPS. On FlyWire v783
bIPS is the type CB0268, which the paper's own lab labelled "bIPS (bilateral Inferior Posterior
Slope neuron)" — MEASURED. MaleCNS has no such label; PS321 (GABA, hb1963869636) is INFERRED as
the homologue because it has the same motif: HS_L → PS321_L 138, H2_R → PS321_L 102, PS321_L →
DNp15_R −158, nothing to its own side's DNp15 (FlyWire: HS_L → CB0268_L 248, H2_R → 124,
CB0268_L → DNp15_R −103, CB0268 ↔ CB0268 0).

Side-resolved wiring, FlyWire v783 (synapses; MaleCNS in parentheses):

| | DNp15_L | DNp15_R | bIPS_L | bIPS_R |
|---|---|---|---|---|
| HS_L (3) | 240 (218) | 0 | 248 (138) | 18 (46) |
| HS_R (3) | 0 | 283 (283) | 24 (67) | 288 (122) |
| H2_L | 0 | 173 (253) | 0 | 112 (97) |
| H2_R | 206 (201) | 0 | 124 (102) | 0 |
| bIPS_L | 0 | −103 (−158) | | |
| bIPS_R | −72 (−127) | 0 | | |

Checks (500 ms window; 1–3 on rates, 4–6 ratios under the RFC S1 ceiling gate):

1. `yaw_right` → DNp15_L > 5 Hz (Suver 2016; task-02 convention).
2. `yaw_left` → DNp15_R > 5 Hz (mirror).
3. **Null:** `yaw_right` → DNp15_R < 2 Hz. Direction selectivity (Suver 2016): a right turn
   gives the right DNp15 no HS/H2 input and bIPS_L inhibition. Task-05 convention.
4. DNp15_L: `yaw_right` / `forward` > 1 — rotation preferred to translation (Fig. 1e); > 1 is
   the task-18 preference convention.
5. DNp15_L: `forward` / `ftb_left` < 0.8 — the contralateral symmetric component *suppresses*
   DNp15 below its monocular response (the bIPS subtraction). 0.8 = 20 % suppression so that
   "no effect" (1.0) cannot pass on noise. CONVENTION.
6. bIPS (both cells): `forward` / `yaw_right` > 1 — bIPS prefers symmetric flow.

## Pre-registered predictions

Steady-state LIF estimates at gain 0.45 (0.275 mV × 0.45 = 0.124 mV per synapse, τ_syn 5 ms,
threshold 7 mV above rest, τ_m 20 ms, t_ref 2.2 ms), ignoring recurrence, which at 0.45 is
small (RFC 21: an LC type at 150 Hz activates 0.2 % of the brain):

- DNp15_L under `ftb_left`: 240 syn × 100 Hz → 14.9 mV → ~67 Hz. Under `yaw_right`:
  + 206 × 100 Hz → 27.6 mV → ~123 Hz. bIPS_R under `forward`: 306 syn → 19 mV → ~87 Hz, which
  puts −3.7 mV on DNp15_L (72 syn) → 11.2 mV → ~46 Hz. bIPS_L under `yaw_right`: 372 syn →
  ~105 Hz, bIPS_R ~0 (18 syn); under `forward` ~78 / ~87 Hz.
- Nothing is near the 291 Hz ceiling, so the S1 gate should not fire on FlyWire.

**FlyWire v783, LIF 0.45, 3 seeds:** checks 1, 2 pass (123 Hz); 3 passes (DNp15_R has no
excitatory route from HS_L/H2_R and is inhibited); 4 passes, ratio ≈ 2.7; 5 passes, ratio
≈ 0.7 — the closest call, 0.69 estimated against 0.8; 6 passes, ratio ≈ 1.6. **6/6**. If check
5 fails it will be because bIPS_R's 72 synapses onto DNp15_L are too few to take 20 % off at
this gain (ratio 0.8–0.9), not because the sign is wrong. This is a task the wiring is
expected to give the reference model — the middle layer's arithmetic is in the synapse counts.

**Adaptive LIF (FlyWire 1.0):** the same qualitative outcome; at gain 1.0 the DNp15 rates
roughly double and check 5's ratio moves toward 1 as DNp15 approaches its ceiling — 5/6 or 6/6.

**MaleCNS v1.0, LIF 0.65, 3 seeds:** the numbers are similar (0.179 mV per synapse; DNp15_L
under `ftb_left` 218 syn → 19.5 mV → ~90 Hz) but at 0.65 any drive that reaches a descending
neuron becomes a whole-CNS event (RFC 22: 12 %). Prediction: the brain ignites in every
condition; checks 1, 2 pass; 3 (the null) **fails** — DNp15_R fires from the network; 4–6
are ratios between conditions that all look alike, ≈ 1, and if DNp15 sits at the ceiling they
are saturated. **2/6**, possibly 3/6 if bIPS's stronger MaleCNS contacts (−127/−158) keep the
crossed inhibition visible through the ignition.

**Rewired control.** FlyWire 0.45: HS_L through random wiring reaches nothing in particular;
1, 2 fail; 3 passes (null); 4–6 are ratios of silence (1 / 1 → `> 1` false, `< 0.8` false)
and fail. **1/6**, specificity **+0.83**. MaleCNS 0.65: random wiring conducts (RFC 21), so 1
and 2 pass, 3 fails, 4–6 ≈ 1 fail: **2/6**, specificity 0.

The interesting outcome would be check 3 or 5 failing on FlyWire: the first would mean an
excitatory route from HS_L/H2_R to the *right* DNp15 that the paper's three-layer diagram does
not have; the second would mean the middle layer's inhibition is too weak in a uniform model to
do the subtraction the paper attributes to it.

## What would make this task wrong

- **The flow → cell mapping is inferred.** HS = front-to-back on its own eye, H2 = back-to-front
  on its dendritic eye. If H2's dendrite were contralateral to its soma the `yaw_right` condition
  would be driving the wrong H2; the wiring (H2_R projects only to left-side DNp15/bIPS, as a
  heterolateral cell should) says the mapping is right, but it is a mapping, not a recording.
  VS cells are left out: they encode pitch/roll and this task is yaw only.
- **100 Hz on graded cells.** HS and H2 do not spike; the task treats them as the model does
  everything else. The ratios (4–6) are between conditions under the same convention, so the
  convention cancels; the absolute rates in 1–3 do not.
- **PS321 = bIPS on MaleCNS is a homology by motif**, not a label. If PS321 is a different
  GABAergic cell with the same inputs and outputs, the check-6 readout on MaleCNS is mislabelled
  but the DNp15 checks stand.
- **Check 5's 20 %** is a number I chose. The paper's evidence for suppression is a model and a
  z-scored preference, not a fraction.
- **Toy:** the FlyWire motif with three HS and one H2 per side, bIPS, DNp15; contacts sized so
  DNp15 sits at a few tens of Hz and bIPS's crossed inhibition halves it (MODELED). The
  broken-toy test cuts bIPS → DNp15 and must fail exactly check 5.

## Outcome (recorded 2026-09-15, first run after pre-registration)

**FlyWire v783, LIF 0.45, 3 seeds, `--controls rewired`:**

| check | value (3 seeds) | result | predicted? |
|---|---|---|---|
| 1. yaw_right → DNp15_L > 5 Hz | 198 Hz | pass | yes (123 estimated) |
| 2. yaw_left → DNp15_R > 5 Hz | 77 Hz | pass | yes |
| 3. yaw_right → DNp15_R < 2 Hz (null) | **51 Hz** | fail | **no** — the named "interesting outcome" |
| 4. DNp15_L: yaw / forward > 1 | 6.4 | pass | yes (2.7) |
| 5. DNp15_L: forward / ftb_left < 0.8 | 0.52 | pass | yes (0.69, "the closest call") |
| 6. bIPS: forward / yaw > 1 | 8.9 | pass | yes (1.6) |
| rewired control | 1/6 | specificity **+0.67** | yes (1/6, +0.83) |

Score **5/6 = 0.83**, graded 0.78. The wiring does the paper's arithmetic: rotation over
translation 6×, the contralateral symmetric component halves DNp15, bIPS prefers symmetric flow
9×. The one fail is the null, and post-hoc single-condition runs say why:

- **A single H2 at 100 Hz activates 8.6 % of the FlyWire brain at gain 0.45** (HS_L alone:
  0.36 %; an LC type at 150 Hz in RFC 21: 0.2 %). H2 has ~5,000 output synapses per cell
  (HS: ~1,000), 1,860 of them onto the GABAergic CH cells and 469 onto PS047b. This is the first
  whole-brain event seen at 0.45, and it is a property of one cell type. The wrong-side DNp15
  fires from that event (via PS100 and PS235 on its own side), not from any HS/H2 route.
- **H2 silences bIPS.** Under HS_L alone bIPS_L fires at 62 Hz; add H2_R and it drops to 16 Hz;
  H2 alone gives 0. The route is the paper's middle layer — bIPS's strongest inhibitors are
  PS099a (−172/−155), uLPTCrn CB2473 (−85/−72) and H2rn CB3740 (−57), all of which H2
  reaches — not the CH cells (0 synapses onto bIPS). So the "competitive disinhibition" the
  paper describes is visible in the uniform LIF: the rotation signal (H2) suppresses the
  translation-subtracting interneuron. That is why check 6's ratio is 9 rather than the 1.6
  that direct drive predicts.
- Left/right asymmetry: yaw_right → DNp15_L 198 Hz but yaw_left → DNp15_R 77 Hz, from a
  wiring difference of ~15 % (H2_R → DNp15_L 206 vs H2_L → DNp15_R 173). The network amplifies
  a small wiring asymmetry 2.6×.

**MaleCNS v1.0, LIF 0.65, 3 seeds, `--controls rewired`:**

| check | value (3 seeds) | result | predicted? |
|---|---|---|---|
| 1. yaw_right → DNp15_L > 5 Hz | 14 Hz | pass | yes |
| 2. yaw_left → DNp15_R > 5 Hz | 322 Hz | pass | yes |
| 3. yaw_right → DNp15_R < 2 Hz (null) | **292 Hz** | fail | yes |
| 4. DNp15_L: yaw / forward > 1 | 0.37 | fail | yes (≈ 1 predicted; it is < 1) |
| 5. DNp15_L: forward / ftb_left < 0.8 | 1.01 (2.1 / 0.4 / 0.5) | fail, seed-sensitive | yes |
| 6. bIPS: forward / yaw > 1 | 18 | pass | no (≈ 1 predicted) |
| rewired control | 1/6 | specificity **+0.33** | no (2/6, 0 predicted) |

Score **3/6 = 0.50**, graded 0.58 — the "possibly 3/6" branch. The pre-registration said the
brain would ignite in every condition and the null would fail; it did (11.7 % of the CNS from
H2 alone, or from HS alone on one seed of three), and the ignition is **lateralised to the
right DNp15 whatever the turn direction**: yaw_right → DNp15_R 312 Hz / DNp15_L 14 Hz;
yaw_left → 322 / 0; even HS_L alone → 212 / 18. The reason is in the wiring: DNp15's largest
input in MaleCNS is not HS but GNG494 (513 synapses onto the right cell, 293 onto the left),
and the left DNp15 is inhibited by WED203_L (−93) and PS100_L (−111) during the event. The male
brain's right DNp15 wins any ignition; the yaw sign is lost. Check 4 failing *below* 1 (the
forward condition, which does not ignite, leaves DNp15_L at 37 Hz while the yaw ignition
suppresses it to 14) is the same asymmetry. Check 6 passes because bIPS is silenced by the
ignition (6 Hz under yaw) and not under forward (66 Hz): the right sign for the wrong reason.

Not predicted: rewired 1/6 rather than 2/6 — random MaleCNS wiring conducted the HS drive to
DNp15 in RFC 21's LC → DN task but not here; a 3-cell drive is under its threshold. Specificity
+0.33 instead of 0.

Housekeeping: graded 0.720 → 0.709 (MaleCNS), 0.728 → 0.733 (FlyWire); the 23 older tasks are
bit-identical on both.
