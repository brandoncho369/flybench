# RFC: task 29 — the compass keeps one bump, keeps it in the dark, and picks one of two cues

Status: pre-registered 2026-09-15, before the first run on any dataset. Expected-fail tier: the
reference model is expected to fail and the task exists to record how. Wiring numbers from the
graph; no simulation was run.

## The behaviour

The fly's head-direction system is a ring attractor in the ellipsoid body. The EPG ("compass")
neurons carry one bump of activity that tracks heading (Seelig & Jayaraman 2015, Nature
521:186), persists and drifts slowly when the visual cue is removed, and — when two cues
compete — settles on one (Kim et al. 2017, Science 356:849: the bump width is ~90° FWHM and
two simultaneous cues give a single winning bump, not two). The circuit that does it is EPG →
PEN → EPG local recurrent excitation (Turner-Evans et al. 2017, eLife 6:e23496; Green et al.
2017, Nature 546:101) with the glutamatergic Δ7 neurons of the protocerebral bridge supplying
global inhibition (Hulse et al. 2021, eLife 10:e66039).

## What the task measures

- **The ring.** EPGs by protocerebral-bridge glomerulus: FlyWire's community labels carry it
  (`EPG_R4` / `EPG_L4`, two labels per cell that agree on the number and disagree on the side),
  MaleCNS's instance names carry it (`EPG(PB08)_L4`). Both datasets give the same eight groups:
  4, 4, 6, 6, 6, 6, 6, 8 cells for glomeruli 1–8 (47 / 46 EPGs; glomerulus 9 empty). Left and
  right glomerulus k are merged into one wedge at (k − 1) × 45° — INFERRED from the anatomy
  (Wolff, Iyer & Rubin 2015: each PB half tiles the full ring, the two halves interleaved by a
  half-wedge). The map is right up to a constant rotation and the 22.5° interleave; the checks
  are relative to the cued wedge, so the rotation cancels.
- **Readout**: the population vector of the eight wedge rates — its length R (1 = one wedge,
  ~0.85 = a 90° bump, 0 = uniform or two opposite bumps) and its angle. New `bump` check type.
- **Conditions**: cue = the glomerulus-4 EPGs at 100 Hz for 500 ms (CONVENTION: the visual cue
  is stood in for by driving the compass cells it would drive; the ring input neurons ER are
  not used because their wedge map is a further inference); two_cues = glomeruli 4 and 8 (180°
  apart). Duration 1.5 s: the dark window is 900–1400 ms, 200–700 ms after cue offset.
- **Wiring** (FlyWire; MaleCNS): EPG → PEN 10,726 (12,051); PEN → EPG 13,236 (23,780); EPG →
  EPG 4,192 (10,716); EPG → Δ7 6,481 (18,795); Δ7 → EPG −2,512 (−3,933). Per cell: a PEN
  returns ~315 synapses to EPGs; a Δ7 removes ~60.
- **Checks**: (1) R > 0.5 during the cue; (2) angle within 45° of the cue; (3) the ring fires
  > 5 Hz in the dark window; (4) R > 0.5 in the dark; (5) angle within 45° in the dark; (6) R
  > 0.5 with two cues (one winner); (7) R > 0.5 in the dark after two cues. Thresholds: 0.5 is
  the R of a bump half the ring wide; 45° is one wedge. CONVENTION.

## Pre-registered predictions

The loop gain is the whole story. A PEN at 100 Hz puts 315 × 100 × 0.124 × 5 ms ≈ 20 mV on its
EPG targets at gain 0.45 — three times threshold from one cell — and Δ7's −60 per cell cannot
match it. A uniform LIF with a 20 ms membrane, no adaptation and this loop has two states:
silent, or the whole ring on. Nothing in between holds a bump.

- **FlyWire v783, LIF 0.45, 3 seeds.** During the cue the driven wedge dominates before the
  loop has spread: 1, 2 **pass**. After the cue the loop keeps the ring going everywhere:
  3 **passes** (the ring is not silent), 4 and 5 **fail** (R ≈ 0.1–0.2, angle random). Two cues:
  the ring is on everywhere, R ≈ 0: 6, 7 **fail**. **3/7 = 0.43.** Alternative: the loop does
  not sustain and the ring goes silent after the cue — 3 fails and 4, 5 are undefined (NaN,
  fail): 2/7. The distinguishing number is check 3's rate.
- **MaleCNS v1.0, LIF 0.65.** The stronger loop (PEN → EPG 23,780) and the 0.65 gain spread
  the activity within the cue window: 1 borderline, likely **fail** (R < 0.5 as the whole ring
  lights within 500 ms), 2 pass if any bump remains, 3 pass, 4–7 fail. **1–2/7.**
- **Adaptive LIF (FlyWire 1.0).** Adaptation is the one ingredient that can stop a runaway
  loop and could leave a bump; but at gain 1.0 the loop gain is ~45 mV per PEN. 3/7, same as the LIF.
- **Rewired control.** 6 EPGs through random wiring reach nothing at 0.45: during the cue only
  the driven wedge fires (R = 1.0, angle exact) → 1, 2 **pass**; the ring is silent afterwards →
  3 fails, 4, 5 NaN; two cues → R = 0 → 6, 7 fail. **2/7**, specificity +0.14. MaleCNS: the same
  2/7, specificity −0.14 to 0.

The interesting outcome would be 4 passing — a bump that survives 200–700 ms after the cue,
which would mean Δ7's global inhibition is enough to shape the loop into an attractor in a
uniform model. I do not expect it, and the task is labelled accordingly.

## What would make this task wrong

- **The wedge map is inferred.** Merging L_k and R_k into one 45° wedge and ordering wedges by
  glomerulus number is the standard anatomy, but a systematic error in the ordering would move
  the "angle" checks, not the R checks; and both are relative to the cued wedge.
- **Driving EPGs directly** is not a visual cue. The real input is ER neurons → EPG in the
  ellipsoid body; a cue in the fly is a pattern over ER types, whose wedge tuning is learned
  and plastic (Kim et al. 2019, Fisher et al. 2019). Driving the compass cells themselves is
  the least-inferred stand-in.
- **R over 500 ms windows** averages over drift; a bump that moves 90° within the window reads
  as a wider bump. The dark window is 500 ms, over which the fly's bump drifts ≪ 45°.
- **Toy**: a hand-wired ring (eight 6-cell wedges, PEN partners feeding self and both
  neighbours, eight Δ7 inhibiting every wedge) whose bump outlives its cue and resolves two
  cues to one winner — MODELED; it proves the seven checks are computable and passable, and
  its bump EPGs sit at their ceiling, which the fly's do not. The broken-toy test cuts PEN → EPG
  and must fail the dark and two-cue persistence checks while the cue-window checks still pass.

## Outcome (recorded 2026-09-15, first run after pre-registration; `--jobs 6`)

| check | FlyWire 0.45 (3 seeds) | MaleCNS 0.65 (3 seeds) | predicted (FW / MC) |
|---|---|---|---|
| 1. one bump during the cue (R > 0.5) | **0.02**, fail | 1.00, pass | pass / fail |
| 2. bump at the cue (< 45°) | 87°, fail | 0°, pass | pass / pass |
| 3. ring active in the dark (> 5 Hz) | 370 Hz, pass | **0 Hz**, fail | pass / pass |
| 4. one bump in the dark | 0.02, fail | NaN (silent), fail | fail / fail |
| 5. bump still at the cue in the dark | 122°, fail | NaN, fail | fail / fail |
| 6. two cues → one winner | 0.02, fail | 0.03, fail | fail / fail |
| 7. the winner persists | 0.02, fail | NaN, fail | fail / fail |
| score | **1/7** | **2/7** | 3/7 / 1–2 |
| rewired | 2/7, specificity **−0.14** | 2/7, 0.00 | 2/7 / 2/7 |

The reference model fails, as the tier says it should, but in **opposite ways on the two
brains** — and the difference is one transmitter label:

- **FlyWire: the ring ignites inside the cue window.** Six EPGs at 100 Hz light 9 % of the
  brain (11,948 non-driven cells fire); every wedge sits at 260–380 Hz during the cue and after
  it, the cued wedge being the *slowest* (260 Hz — its cells are refractory-limited by the forced
  drive). R = 0.02 everywhere: the compass is a floodlight. The route is not PEN. The g4 EPGs'
  largest target is **ExR6**, and the right ExR6 has no `nt_type` in v783 — which flybench
  treats as excitatory — while the left is glutamatergic. The unlabelled cell makes a 506 / 218
  reciprocal excitatory loop with the EPGs and the ring runs away through it.
- **MaleCNS: nothing propagates.** 0.0 % of the CNS is active; the cued wedge fires only
  because it is forced (81 Hz) and 54 other cells tick. There, ExR6 is labelled glutamatergic
  on both sides and is the EPGs' largest *inhibitory* input (−446 / −436 onto the six g4
  cells), with the GABAergic ER4m behind it; the PEN → EPG loop (23,780 synapses in total)
  never gets started. In the dark the ring is silent, so four checks are undefined and fail.
- **The shuffle scores 2/7 on both**: with random wiring the driven wedge alone fires, which
  is a perfect bump at the right angle. On FlyWire that beats the brain (third negative
  specificity, after 23 and 25).

So the pre-registered mechanism — "the PEN loop's 20 mV per spike cannot be held by Δ7" — was
not what happened. On FlyWire a single unlabelled cell's default sign carried the runaway; on
MaleCNS the labelled inhibition (ExR6, ER4m) onto the compass outweighs the cue and the loop.
What the ring attractor needs from a model is unchanged: something that holds a bump between
"silent" and "everything" — and, before that, an ExR6 transmitter the two datasets agree on.
Hulse et al. 2021 list ExR6 among the glutamatergic ExR types; the MaleCNS label is the one
the literature supports, and the FlyWire blank is worth raising with the annotators.
