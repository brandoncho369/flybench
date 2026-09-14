# RFC: task 20 — the four labellar taste channels, one motor neuron

Status: pre-registered 2026-09-14, before the first run on any dataset. First task of Phase 3
(taste modality family, ROADMAP item 19).

## The behaviour

The labellum carries four classes of gustatory receptor neuron that the Cell 2026 labellar
typing names LB3a–d and LB1a–e (see docs/MALECNS.md): sugar (LB3b, Gr64f), sugar + low salt
(LB3c, Ir56b), water (LB3a, ppk28), high salt (LB3d, Ir7c / ppk23) and bitter (LB1a–d). Each
has a measured behavioural sign at the proboscis:

- **Water drives extension.** ppk28 water cells are necessary and sufficient for the proboscis
  extension reflex (PER) to water in thirsty flies (Cameron et al. 2010, Nature 465:91; Chen &
  Dahanukar 2017, Cell Rep 18:1140). Shiu et al. 2024 silenced 6 steps of the water pathway in
  their model and 5 matched behaviour.
- **High salt is aversive.** Low salt (≤ 100 mM) is attractive through Ir76b / Ir56b cells,
  which sit in the sugar class; high salt (≥ 250 mM) suppresses feeding and PER through
  ppk23-glutamatergic cells and bitter GRNs (Zhang et al. 2013, Science 340:1334; Jaeger et al.
  2018, eLife 7:e37167). Jaeger et al. report that 500 mM NaCl reduces PER to 100 mM sucrose to a
  fraction of the sucrose-alone rate (their Fig. 1; the exact fraction depends on hunger state —
  `sd: unknown`, threshold rule).

So the same motor neuron (MN9) must fire to water, fire to sugar, stay silent to high salt, and
fire less to sugar-plus-high-salt than to sugar. Task 03 already tests bitter; this task tests the
other three channels the export has carried since Phase 0 and nobody has driven yet.

## What the task measures

Stimuli (each a labellar GRN class at 100 Hz for 600 ms, CONVENTION as in task 02):

| stimulus | selector | provenance |
|---|---|---|
| `sugar_grn` | as task 02 | MEASURED (Gr64f) |
| `water_grn` | label "water" ∧ sensory, or `LB3a` | MEASURED (ppk28) |
| `high_salt_grn` | `LB3d`, or label "high salt" ∧ sensory | MEASURED (Ir7c / ppk23) |

Readout MN9 (task 02 selector). Window 250–800 ms.

Checks:

1. water → MN9 rate > 5 Hz — positive (Cameron 2010).
2. high salt alone → MN9 rate < 5 Hz — **null check**; a dead network passes.
3. sugar + high salt / sugar < 0.5 — positive in the sense that it needs both a sugar response and
   a suppression (Jaeger 2018; 0.5 is the same convention as task 03).
4. sugar → MN9 > 5 Hz — sanity, so check 3 is a ratio of real numbers.

`requires_stimuli: [water_grn, high_salt_grn]`: a dataset without either class skips the task.

## Pre-registered predictions

- **FlyWire v783, LIF 0.45.** v783 has `sub_class = sugar/water` but, as far as I know, no
  LB3a/LB3d types and no "high salt" label — so I predict the task is **skipped** (`high_salt_grn`
  matches nothing). If "water"-labelled cells do exist but salt cells do not, still skipped.
- **Adaptive LIF (FlyWire).** Same: skipped.
- **MaleCNS v1.0, LIF 0.65.** All four classes exist (docs/MALECNS.md). Prediction: check 1
  passes (water reaches MN9 — at 0.65 everything reaches everything); check 2 **fails** (bitter
  alone already drives MN9 at 55 Hz on this setting, task 05 finding; high salt will too); check 3
  **fails** (ratio ≈ 1, no suppression at a gain where MN9 is saturated); check 4 passes.
  Score 2/4, and the two failures are the same failure task 05 already reports.
- **Rewired control (MaleCNS).** Check 1 fails (water does not find MN9 through random wiring);
  check 2 passes (null); checks 3–4 fail. Specificity positive → diagnostic.

The interesting outcome would be MaleCNS passing check 3: that would mean the high-salt → sugar
suppression is wired centrally and survives a gain that breaks bitter suppression. I do not
expect it.

## What would make this task wrong

Jaeger et al. put part of high-salt aversion in the *bitter* GRNs themselves (Ir7c-independent);
the task drives LB3d only, so it under-drives the aversive input — a failure of check 3 is
therefore "central LB3d-driven suppression alone is not enough", not "the fly has no suppression",
exactly the scope note of task 03. The water check depends on the label "water" on FlyWire; if the
export's water set turns out to be a subset of the sugar set on that dataset, checks 1 and 4 are
not independent and the task should require `LB3a` explicitly. Toy: the toy's salt cells drive the
same inhibitory pool as its bitter cells (INFERRED — the second-order salt circuit is not mapped);
the toy exists to prove the task can pass, not to say how the fly does it.

## Outcome (recorded 2026-09-14, first run after pre-registration)

**FlyWire v783, LIF 0.45: skipped**, as predicted, and for the reason predicted: v783 has 122
labellar GRNs typed simply `LB3` — no a/b/c/d split — and no cell carries a "water" or "salt"
label, so `water_grn` matches nothing (and so would `high_salt_grn`). The skip fires on
`water_grn` first only because `requires_stimuli` lists it first. Adaptive LIF: not run (would
skip identically; the skip is a matter of annotations, not dynamics).

**MaleCNS v1.0, gain 0.65, 3 seeds, `--controls rewired`** (17 water, 26 high-salt, 34 sugar GRNs;
readout the L/R MN9 pair):

| check | value (mean of 3 seeds; per seed) | result | predicted? |
|---|---|---|---|
| 1. water → MN9 > 5 Hz | 95.8 Hz (87, 99, 101) | pass | yes |
| 2. high salt → MN9 < 5 Hz (null) | 183 Hz (**273, 0.9, 275**) | fail on 2/3 seeds | yes — but see below |
| 3. sugar + high salt / sugar < 0.5 | 1.04 (0.77, 1.32, 1.04) | fail | yes |
| 4. sugar → MN9 > 5 Hz | 219 Hz (255, 136, 265) | pass | yes |
| rewired control | 0.25 (one check) | diagnostic, specificity +0.25 | yes (1/4) |

Score 0.50 (2/4), graded 0.63. Every pre-registered call was right, including the boring one
(the two failures are task 05's failure again: at 0.65 an aversive GRN class drives MN9 as hard
as sugar does). Two things the prediction did not anticipate:

1. **The high-salt → MN9 path is bistable across Poisson seeds.** Seeds 1 and 3 drive MN9 at
   ~275 Hz; seed 2 drives it at 0.9 Hz, and on that same seed sugar alone drops from ~260 to
   136 Hz and the "suppression" ratio goes *above* 1. Same 26 input neurons, same wiring, same
   100 Hz rate — only the spike times differ. At this gain the labellar circuit sits on a knife
   edge where whether MN9 ignites depends on coincidences in the input train, not on the
   channel. That is a stronger statement than "high salt reaches MN9": the network at 0.65 does
   not have a reproducible answer to the question. The result JSON flags it
   (`seed-sensitive: check 1 passes on 1/3 seeds`, 0-indexed).
2. **Water drives one MN9, not both.** `readout_active_fraction` is 0.5 for water on every seed
   (sugar and sugar+salt: 1.0; high salt: 0.83) although the 17 water GRNs are bilateral
   (9 L / 8 R). So the 96 Hz "water response" is ~190 Hz on one motor neuron and silence on the
   other. Not tested by this task (the readout is the pair mean) and not a prediction I made;
   noted here so the next taste task can ask whether the water → MN9 wiring is genuinely
   lateralised in MaleCNS or whether the sparse water set simply falls below threshold on one side.

Neither observation changes the task. The interesting outcome I said I did not expect —
MaleCNS passing check 3 — did not happen.
