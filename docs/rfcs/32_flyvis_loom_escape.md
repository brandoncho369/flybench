# RFC: task 32 — through a real visual front end, a loom reaches the loom detectors and the giant fiber

Status: pre-registered 2026-09-16, before the scored 3-seed runs with controls on either dataset.
**Disclosure:** while building the front end I ran single-seed development simulations on FlyWire
0.45 and 0.65 (loom, flash, recede, dimming) to check that rates arrived at the right cells at
all; their numbers are given below and the predictions are informed by them. This RFC is
therefore a pre-registration of the *scored* outcome, not a blind one.

## The behaviour

A dark object expanding toward the fly with r/v = 40 ms evokes one giant-fiber spike and a
takeoff (von Reyn et al. 2014; Ache et al. 2019). The detectors are the lobula columnar types
LPLC2 (radially expanding motion; Klapoetke et al. 2017) and LC4 (angular size; Ache 2019),
which synapse onto the giant fiber. A full-field luminance step is not a loom and evokes no GF
spike (von Reyn 2014; Klapoetke 2017).

## What the task measures — and what changes

Every escape task so far (4, 11, 13, 16, 21) drives LPLC2 and LC4 *themselves* at 150 Hz: a
convention that assumes the optic lobe has already computed "loom". Here the stimulus is a
rendered movie and the optic lobe is **flyvis** (Lappalainen et al. 2024, Nature 634:1132), a
connectome-constrained model of 65 optic-lobe cell types on a 721-column retina, trained on optic
flow and released with pretrained weights. The movie goes through flyvis; its output-layer types
that both connectomes name identically (T4a–d, T5a–d, T2, T2a, T3, Tm/TmY — 27 types, ~32,000
cells on FlyWire) are driven with flyvis's per-type, per-column rates; the LIF's own wiring from
there to LPLC2, LC4 and the GF does the rest. Nothing downstream of the medulla is driven directly.

The conventions, all in `flybench/frontends/flyvis_frontend.py`:

- **rate = 100 Hz × (activity − resting activity on the grey field)⁺** — 1 flyvis unit above
  rest is the task-02 rate. Nothing fitted.
- **column → neuron**: a type's somata in one hemisphere are projected on their two principal
  axes, normalised to the unit disc and assigned to the nearest flyvis column. INFERRED
  retinotopy, right up to a rotation and a flip; the task's stimuli are radially symmetric and
  centred so the rotation does not matter. 740 FlyWire T5a cells land on ~320 columns.
- **both eyes see the same movie.**
- Front-end outputs are computed once (`flybench frontend flyvis render`) and committed
  (`data/frontends/flyvis/*.npz`, 4 MB), so runs and CI need neither torch nor flyvis.

Conditions: `loom` (dark disc, r/v 40 ms, collision at 1 s, half-angle 22° at 0.9 s and 45° at
0.96 s) and `flash` (grey → white step at 0.2 s), each 1 s at 100 Hz starting at 200 ms. Checks:

1. loom → LPLC2 > 5 Hz in the last 300 ms (the disc grows from 22° to 90°);
2. loom → LC4 > 5 Hz in the last 300 ms;
3. loom → GF ≥ 1 spike per neuron over the run.

The flash is **measured, not scored**. Through flyvis a brightening step gives T4 a 154 Hz onset
transient and — unlike the fly's T5, as far as it is known — T5 a 45 Hz transient across every
column at once. A flash null would then be failed by any model that sums T5 over the eye, and
passed only by one with retinotopic expansion selectivity — which the toy cannot have (its
T4/T5 are 24 cells per subtype on a coarse grid) and which, in the fly, LPLC2 gets from the
layer-specific radial arrangement of its T4/T5 inputs. So a flash null here would score the
front end's flash response, not the connectome. `rate[flash, gf]` is in every result file and
the outcome section reports it.

## Development runs (single seed, no controls; the reason for the predictions)

FlyWire v783, LIF, reading LPLC2 / LC4 / GF over 200–1200 ms:

| gain | loom | flash |
|---|---|---|
| 0.45 | LPLC2 0.0, LC4 0.0, GF 0.0 Hz; 4.6 % of the brain active | LPLC2 0.0, LC4 4.9, **GF 40 Hz**; 22 % active |
| 0.65 | 0.0 / 0.0 / 0.0; 8.5 % | 0.0 / 5.0 / GF 10.5 Hz; 26 % |

The wiring says why. LPLC2's excitatory input is 50 % from the driven types (T5c 7,636, T4c
6,869, T5b, T5d, T4b, T5a …; the rest Tm5f, Y3 and LPLC2 itself, which flyvis does not model),
LC4's 57 % (T2 21,064, TmY3 20,849, Tm4, Tm2). But the loom's T5 rates are *sparse*: even at
the last frame only 10–15 % of columns exceed 20 Hz, and the field mean over the last 500 ms is
~1 Hz per type. An LPLC2 cell's ~110 T5 synapses at ~1 Hz is 0.07 mV. The 150 Hz-on-314-cells
convention of task 4 was doing all of the work. The flash, by contrast, is a synchronous
transient on every column at once (T4 154 Hz, Tm3 tonic 42 Hz), lights a fifth of the brain,
and reaches the GF through LC4 and the network.

## Pre-registered predictions (for the scored runs)

- **FlyWire v783, LIF 0.45, 3 seeds.** Checks 1–3 **fail**: LPLC2 and LC4 stay under 5 Hz in the
  last 300 ms (≤ 1 Hz), the GF does not spike. **0/3.** The flash measurement: GF at tens of Hz,
  ~20 % of the brain active — the model's giant fiber, driven through a real optic-lobe model,
  fires to a flash and not to a loom: the opposite of the fly.
- **MaleCNS v1.0, LIF 0.65.** The same, 0/3; the flash lights more of the CNS.
- **Adaptive LIF 0.45.** 0/3.
- **Rewired control.** 32,000 driven cells at low rates through random wiring: nothing reaches
  LPLC2/LC4/GF → 0/3 on both. Specificity 0.00 — this task, like the size principle, expects the
  reference model and its shuffle to tie at the floor.

The interesting outcome would be LPLC2 firing in the last 300 ms on FlyWire: the 15 % of
columns at 50–85 Hz near collision, summed over an LPLC2's receptive field through the LIF's
own T5 → LPLC2 synapses, being enough. The development run says it is not, by two orders of
magnitude.

## What would make this task wrong

- **1 unit = 100 Hz.** If T4/T5's true peak "rate-equivalent" is several hundred Hz, the loom's
  drive scales up with it — and so does the flash's. The ratio between them does not change:
  the flash is a synchronous transient, the loom a sparse edge.
- **The column mapping** compresses 740 cells onto ~320 columns; a third of the retina is
  unused per type, which weakens the loom (whose late edge is at the periphery) more than the
  flash (everywhere). A column annotation from the datasets would fix it.
- **Only 50–57 % of LPLC2/LC4's input types are modelled by flyvis.** Tm5f, Y3 and TmY3's
  unmodelled inputs are silent here. That biases toward failure; a front end covering the whole
  lobula would be fairer.
- **The loom geometry.** r/v 40 ms with collision at 1 s means most of the expansion is in the
  last 100 ms; slower looms (r/v 70 ms) spend longer at intermediate sizes and would drive more
  columns for longer. The task uses the geometry the reflex tasks already cite.
- **Toy:** 24 cells per T4/T5 subtype on the toy's optic lobe; every T5 subtype onto the toy's
  LPLC2/LC4 with strong contacts, every T4 subtype onto a GABAergic LPi-like layer that inhibits
  them (a dark-loom detector by ON/OFF opposition — MODELED, and not how the fly does it; the
  comment in toy.py says so). It passes the three loom checks on four seeds; its flash response
  (GF 6–28 Hz) is the reason the flash is not a scored null.

## Outcome (2026-09-17, scored runs, 3 seeds, `rewired` control)

| | FlyWire v783, LIF 0.45 | MaleCNS v1.0, LIF 0.65 |
|---|---|---|
| loom → LPLC2, 900–1200 ms | 0.0 Hz (0/3 seeds, sd 0) | 0.0 Hz (0/3 seeds, sd 0) |
| loom → LC4, 900–1200 ms | 0.0 Hz | 0.0 Hz |
| loom → GF spikes/neuron | 0.0 | 0.0 |
| loom, brain active | 4 % | **15 %** |
| flash → GF (measured, unscored) | **37.3 Hz**, every GF; LC4 4.8 Hz; 22 % of the brain active | **5.8 Hz**, every GF; LC4 0.1 Hz; 23 % active |
| score / rewired / specificity | 0/3 · 0/3 · 0.00 | 0/3 · 0/3 · 0.00 |

**Predictions held on both brains, exactly.** Nothing the loom does through flyvis reaches LPLC2, LC4
or the giant fiber at any of three seeds; the flash lights a fifth of the brain and fires the GF
at 37 Hz. The reference model's giant fiber, driven through a real optic-lobe model, fires to a
brightening and not to a loom: the opposite of the fly. The 150 Hz-on-LPLC2/LC4 convention of
tasks 4/11/13/16/21 was doing all the work of "loom detection" — this task shows the connectome
plus a point-neuron LIF does not compute it from T4/T5/Tm rates as this front end delivers them.
Rewired ties at 0/3, specificity 0.00, as pre-registered: the task is at the floor for both.

MaleCNS adds one number FlyWire does not: the loom lights **15 %** of the CNS (FlyWire 4 %) and
still none of it is LPLC2, LC4 or the GF — the drive spreads through the medulla and the rest of
the CNS at 0.65 without ever summing onto the detectors. The flash reaches the GF more weakly
there (5.8 Hz vs 37 Hz on FlyWire; LC4 0.1 Hz vs 4.8 Hz), consistent with task 4/16's weaker
LC4 → GF path on MaleCNS.

The 127 (FlyWire) and 146 (MaleCNS) checks of the 31 older tasks were bit-identical to the
previous files (`flybench diff`: mean graded difference 0.000); the graded scores moved
0.669 → 0.653 and 0.650 → 0.639 only because a 0/3 task was added.

What this does and does not say (see "What would make this task wrong" above): flyvis models
only half of LPLC2/LC4's input types; the inferred column mapping uses a third of the retina per
type; 1 unit = 100 Hz is a convention. Every one of those biases toward failure. What survives
them is the *sign* of the flash-vs-loom comparison: no rescaling of a sparse late edge overtakes
a synchronous full-field transient in a model that sums synapses.
