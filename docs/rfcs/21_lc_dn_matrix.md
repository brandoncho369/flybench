# RFC: task 21 — each lobula columnar type drives its own descending neuron, and not the others

Status: pre-registered 2026-09-14, before the first run on any dataset.

## The behaviour

Optogenetic activation of single lobula columnar (LC) types in freely walking flies evokes
type-specific behaviours (Wu et al. 2016, eLife 5:e21022, 22 LC types screened): LC4, LC6, LPLC1
and LPLC2 evoke takeoff / jumping; LC16 evokes backward walking; most other types, LC10 among
them, evoke neither. The descending neurons behind two of those behaviours are known:

- **Escape.** LC4 and LPLC2 synapse directly onto the giant fiber (GF = DNp01) and its spiking
  drives the jump (von Reyn et al. 2017, Neuron 94:1190; Klapoetke et al. 2017, Nature 551:237;
  Ache et al. 2019, Curr Biol 29:1073). LC4 also synapses directly onto DNp02, DNp04 and DNp11,
  and the LC4 → DNp02 / DNp11 synapse-number gradients turn stimulus azimuth into backward vs
  forward takeoffs (Dombrovski et al. 2023, Nature 613:534).
- **Retreat.** LC16 acts through the four moonwalker descending neurons (MDN) in an excitatory
  feed-forward circuit; MDN activation drives backward walking (Sen et al. 2017, Curr Biol 27:766;
  Bidaye et al. 2014).
- **Courtship tracking.** LC10a drives male pursuit of a moving target (Ribeiro et al. 2018, Curr
  Biol 28:2211); it does not evoke takeoff or retreat in the Wu et al. screen.
- LC6 is looming-responsive and, like LC4/LPLC2/LC16, evokes avoidance, but its output is a
  separate glomerulus read out by its own targets (Morimoto et al. 2020, eLife 9:e57685); whether
  it reaches the GF is not established, so those cells are not scored.

This is a *matrix* of expected signs, which is what makes it a new task type: the signal is not
the diagonal (task 04 already tests loom → GF) but the off-diagonal — an LC type must not drive a
DN that serves a different behaviour.

## What the task measures

Six conditions, one per LC type, each driven at 150 Hz for 300 ms (the task-04 loom drive,
CONVENTION: the same drive for every row so the rows are comparable), four descending readouts
(GF, DNp02, DNp11, MDN), and a `matrix` check that expands to one `spikes_per_neuron` check per
scored cell: "+" means ≥ 1 spike per readout neuron in the stimulus window, "−" means < 1 (the
task-16 "nothing before the loom" rule, CONVENTION). The LC → DN drive is MEASURED where a
paper shows the synapse and the behaviour; a "−" is INFERRED from the behavioural screen (the
type evokes no takeoff / no retreat, so it should not drive that behaviour's DN).

| drive \ readout | GF | DNp02 | DNp11 | MDN |
|---|---|---|---|---|
| LC4   | + | + | + | − |
| LPLC2 | + | ? | ? | − |
| LC6   | ? | ? | ? | − |
| LPLC1 | ? | ? | ? | − |
| LC16  | − | − | − | + |
| LC10a | − | − | − | − |

16 scored cells: 5 positives, 11 negatives. **Every "−" is a null check**: a dead network passes
11/16 = 0.69, so the rewired control sets a high floor and the number that matters is the
specificity, not the score. The score is the plain fraction of cells (same rule as every other
task; no re-weighting — that would be tuning the task to the result I expect).

Skips: `requires_stimuli` on all six LC types and `requires_readouts` on all four DNs. Both
FlyWire v783 and MaleCNS v1.0 carry all ten types (verified with `flybench select` before this
RFC: LC4 104/126, LPLC2 210/185, LC6 125/124, LPLC1 140/134, LC16 152/182, LC10a 237/275;
GF, DNp02, DNp11 pairs; MDN 4 on both).

## Pre-registered predictions

Calibration from the existing runs: on FlyWire 0.45 a loom activates 30 % of all descending
neurons but sugar does not reach the GF (tasks 10, 09); on MaleCNS 0.65 a loom activates 39 % of
DNs and drives MN9 at 58 Hz.

- **FlyWire v783, LIF 0.45.** All five positives pass (loom → GF is 436 Hz; DNp02/DNp11 receive
  LC4 directly; LC16 → MDN is a direct excitatory contact). Of the negatives, LC4 → MDN and
  LPLC2 → MDN **fail**: a loom lights up a third of the DNs and MDN, a hub of the walking
  network, will be among them. The other nine negatives pass — at 0.45 an off-pathway drive
  does not reach the GF (sugar does not). Score **14/16 = 0.875**.
- **Adaptive LIF (FlyWire).** Fewer multi-hop leaks: 15/16 or 16/16. If LC4 → MDN is a direct
  or two-hop path it will survive adaptation and stay a fail.
- **MaleCNS v1.0, LIF 0.65.** Positives pass. Negatives: LC4/LPLC2 → MDN fail; LC16 → GF and
  LC10a → GF fail (at 0.65 bitter reaches MN9 and the loom reaches MN9; the GF is the most
  reachable neuron in the brain); LC10a → MDN fails (275 cells at 150 Hz). Score **9/16 ≈ 0.56**.
- **Rewired control.** Positives fail (task 04's rewired run does not reach the GF), negatives
  pass: **11/16 = 0.69** on both datasets. So on MaleCNS the shuffled brain **outscores** the real
  one (specificity ≈ −0.13) and on FlyWire the real brain wins by ~+0.19. A negative specificity
  on a null-heavy task is the expected shape, not a defect; the finding would be the *which*
  cells leak.

The interesting outcome would be a leak into MDN from LC10a but not from LC4: that would say the
leak is about population size, not about looming. I do not expect it.

## What would make this task wrong

- The "−" cells are inferred from behaviour, not from recordings of the DN. A DN can fire a
  spike without the behaviour following (DNp02/DNp11 backward vs forward takeoff is a *gradient*,
  not a switch), so a "−" fail is "the model's DN fires when the fly's behaviour says it should
  not", one step short of a recording mismatch. If a DN recording under LC activation exists it
  should replace the behavioural inference.
- The threshold "< 1 spike per neuron" on a four-neuron MDN allows one MDN to spike three times
  and still pass. It is the same rule task 16 uses; if it turns out to hide a real leak the
  matrix should get a per-cell `rate` metric.
- Type names: LC10 is split a–d on both datasets and only LC10a has the courtship citation, so
  the row is LC10a. If a dataset renames it (`LC10a-1`?) the task skips, which is the right
  outcome.
- Same-drive convention: 150 Hz on 275 LC10a cells is a larger total drive than 150 Hz on 104
  LC4 cells. A leak that scales with population size is a property of the model, and the task
  reports it as such; it is not normalised away.
- Toy: LC16 → MDN and LC4 → DNp02/DNp11 are wired directly (MODELED — the toy exists to prove
  the task can pass); LC6/LPLC1/LC10a project nowhere in the toy, which passes the negatives
  trivially. A broken toy with an LC16 → GF edge must fail the LC16 → GF cell (tested).

## Outcome (recorded 2026-09-14, first run after pre-registration)

Both datasets, 3 seeds, `--controls rewired`. Values are spikes per readout neuron in the 300 ms
window (mean of 3 seeds); the threshold is 1.

| cell | expected | FlyWire 0.45 | MaleCNS 0.65 |
|---|---|---|---|
| LC4 → GF | + | 128 pass | 51 pass |
| LC4 → DNp02 | + | 93 pass | 129 pass |
| LC4 → DNp11 | + | 45 pass | 83 pass |
| LC4 → MDN | − | **19 fail** (predicted) | 0 pass (predicted fail) |
| LPLC2 → GF | + | 124 pass | 55 pass |
| LPLC2 → MDN | − | **14 fail** (predicted) | 0 pass (predicted fail) |
| LC6 → MDN | − | **15 fail** | **1.5 fail** |
| LPLC1 → MDN | − | **0.9 fail** (2/3 seeds) | **40 fail** |
| LC16 → GF, DNp02, DNp11 | − | 0 pass | 0 pass |
| LC16 → MDN | + | **0 fail** | 1.3 pass (4 Hz) |
| LC10a → GF, DNp02, DNp11, MDN | − | 0 pass | 0 pass (predicted GF, MDN fail) |
| **score** | | **11/16 = 0.69** (predicted 0.875) | **14/16 = 0.875** (predicted 0.56) |
| rewired | | 0.69 → specificity **0.00** (predicted +0.19) | 0.44 → specificity **+0.44** (predicted −0.13) |

Nearly every prediction was wrong, and the wiring says why. Three findings:

1. **LC16 → MDN is not a synapse.** In both connectomes LC16 makes zero direct synapses onto the
   four MDNs, and in v783 there is no excitatory two-hop path either (the shortest excitatory
   route is ≥ 3 hops). Sen et al. 2017 showed functional connectivity and proposed a feed-forward
   circuit; the wiring says the circuit has at least two interneurons in it. At 0.45 the 152 LC16
   cells at 150 Hz activate 0.2 % of the brain and MDN never fires; at 0.65 a two-hop route via
   pIP1 (≈ 18 synapses per MDN) gets it to 1.3 spikes. The one positive cell I was surest of is
   the one that fails, and it fails because the task's "+" was written as if the pathway were
   monosynaptic. The `basis` on that cell now says "polysynaptic".
2. **The MDN leaks are two-hop and dataset-specific.** LC4 → PVLP141 → MDN (57–63 synapses per
   MDN in v783, 76–127 in MaleCNS) carries the LC4 leak on FlyWire; on MaleCNS the same path
   exists but MDN stays silent at 0.65 — the PVLP141 → MDN hop is there and the model does not
   cross it, which is not explained by gain alone and is a lead. LPLC1 → PVLP201m → MDN
   (≈ 100 synapses per MDN) exists only in MaleCNS and drives MDN at 133 Hz — harder than LC16
   ever does. If that path is real, LPLC1 activation should evoke backward walking in males;
   Wu et al. 2016 report takeoff. Either the wiring diagram has a retreat pathway the
   behaviour screen missed, or PVLP201m is inhibitory in life and cholinergic in the annotation.
   Worth a look before believing either.
3. **LC10a leaks nowhere.** 237–275 cells at 150 Hz and not one spike in any of the four DNs on
   either dataset. The size-of-population worry in "what would make this task wrong" did not
   materialise; leak follows the wiring, not the drive.

On the controls: FlyWire's real brain ties the shuffled one (0.69 vs 0.69, the null floor I
computed in advance) because it wins the five diagonal cells and loses four MDN cells the
shuffled brain keeps silent. MaleCNS's shuffled brain scores 0.44, not 0.69, because at 0.65
random wiring conducts a 150 Hz drive into DNs it should not reach — the null floor is
gain-dependent, which I did not anticipate.

Unscored "?" cells, for the record: LC6 → GF fires on both datasets (412 Hz FlyWire, 153 Hz
MaleCNS) with zero direct LC6 → GF synapses; LPLC1 → GF is silent on both; LPLC1 → DNp11 fires
on both (45 Hz / 18 Hz). If a DN recording under LC6 or LPLC1 activation is published these
become scored cells.

Adaptive LIF: not run this round. Prediction stands (fewer multi-hop leaks), but given finding 1
it would also lose LC16 → MDN and end near 12/16.
