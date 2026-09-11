# flybench

**A reflex benchmark for whole-brain fruit fly connectome simulations.**

In 2024 the [FlyWire](https://flywire.ai) consortium published the complete wiring diagram of an adult *Drosophila* brain: ~140,000 neurons, ~50 million synapses. Since then people have dropped that graph into a leaky integrate-and-fire model and wired it to Minecraft, Doom and Beat Saber. Every one of those demos had to make the same undocumented choices — synaptic weight, a global gain knob, which transmitters count as inhibitory, how many synapses an edge needs to exist — and then hand-tune them until something looked alive.

flybench asks the one question that keeps those choices honest:

> **Does the simulated fly still do the things a real fly is known to do?**

It ships a small suite of reflexes with citations, a reference LIF simulator, and a scoring harness, so any set of model parameters (or any alternative simulator that can run the tasks) gets a number you can compare.

```
$ flybench run -c flywire783 --config configs/shiu2024.yaml
flywire783: 139,255 neurons, 2,7xx,xxx edges · gain=1.0 w_syn=0.275 mV
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ task                                   ┃ result ┃ checks                              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Silence in, silence out                │ PASS   │ ✓ network rate[baseline] < 0.5 Hz   │
│ Sugar → proboscis extension            │ PASS   │ ✓ readout rate[sugar] > 5 Hz  [..]  │
│ Bitter suppresses the sugar response   │ ...    │                                     │
│ Looming → giant fiber escape           │ ...    │                                     │
│ Bitter alone does not extend proboscis │ ...    │                                     │
└────────────────────────────────────────┴────────┴─────────────────────────────────────┘
```

## First result: the reflex window on FlyWire v783

Run against the real connectome (Codex v783, Princeton-filtered connections, ≥5 synapses, 139,255 neurons / 3.7 M edges), sweeping only the global gain:

| gain | sugar → MN9 | bitter cancels sugar | looming → GF | brain awake during sugar | verdict |
|---|---|---|---|---|---|
| 0.30 | no | – | yes | 0.1 % | taste pathway never ignites |
| 0.35 | no | – | yes | 0.2 % | same |
| **0.40** | **yes** | **yes (to 0 Hz)** | **yes** | **8 %** | **passes everything** |
| **0.45** | **yes** | **yes** | **yes** | **9 %** | **passes everything** |
| 0.50 | yes | partially | yes | 10 % | bitter can't hold it down |
| 0.70 | yes | yes | yes | 14 % | too much of the brain firing |
| 1.00 (Shiu 2024) | yes | yes | yes | 19 % | a fifth of the brain at 29 Hz — not a reflex, a seizure |

So on the July-2025 synapse predictions the working window is around **gain 0.45**, less than half of the 1.0 that Shiu et al. calibrated on the earlier Buhmann predictions. That is the kind of thing this benchmark exists to catch: the connectome got re-predicted, the weights shifted, and a parameter that used to be right silently stopped being right.

Re-running with three random seeds (`--seeds 3`) sharpened it further: **0.40 is a knife edge** — sugar reaches the proboscis on only 2 of 3 seeds, and it "passed" the adaptation task purely because one seed's second pulse failed to ignite. **0.45 passes every core task on every seed.** With more than one seed a check only counts as passed if it holds on every seed, so single-seed luck cannot climb the leaderboard.

Inside that window the reference model then fails most of the **hard** tier. The failures are informative, not embarrassing: MN9 ignition is all-or-nothing (0 Hz or ~430 Hz, nothing in between — no dose response); a second sugar pulse gets exactly the response of the first (no adaptation, because the model has no state that outlives 20 ms); driving one olfactory glomerulus fires ~84 % of all projection neurons (no lateral inhibition, the antennal lobe is a broadcast); looming recruits ~30 % of all descending neurons rather than a takeoff ensemble. Each of those is a concrete thing a better model has to add — adaptation currents, per-transmitter weights, gap junctions, neuromodulation — and each one is now a number you can move. Full table in [`LEADERBOARD.md`](LEADERBOARD.md).

## The tasks

Two tiers. **Core** is the reflexes the reference LIF model is known to reproduce; a model that fails these is broken. **Hard** is behaviours a real fly shows that a static wiring diagram with five constants is *not* expected to reproduce; these are the research agenda, and the reference model fails most of them on purpose.

| tier | task | what it tests | source |
|---|------|---------------|--------|
| core | `stability` | no input → (almost) no output. Guards against "everything fires so everything passes" | Shiu et al. 2024 |
| core | `sugar_to_proboscis` | sugar GRNs → MN9 (proboscis motor neuron) fires | Dethier 1976; Shiu et al. 2024 Fig. 2 |
| core | `bitter_suppression` | sugar + bitter → MN9 fires less than sugar alone | Shiu et al. 2024 Fig. 3; Jaeger et al. 2018 |
| core | `looming_to_giant_fiber` | LPLC2 / LC4 → Giant Fiber (escape) fires | von Reyn et al. 2014; Ache et al. 2019 |
| core | `taste_specificity` | bitter alone does **not** drive MN9 (negative control) | Shiu et al. 2024 |
| hard | `dose_response` | weak sugar → weaker MN9 than strong sugar, and MN9 is graded, not saturated | Dethier 1976; Dahanukar et al. 2007 |
| hard | `adaptation` | a second sugar pulse evokes a smaller response than the first | Duerr & Quinn 1982; Paranjpe et al. 2012 |
| hard | `olfactory_sparse_coding` | one glomerulus's ORNs (DA1) fire their own PNs, not most of the antennal lobe | Olsen & Wilson 2008; Wilson 2013 |
| hard | `crosstalk` | sugar does not fire the Giant Fiber; looming does not extend the proboscis | von Reyn et al. 2014 |
| hard | `looming_dn_ensemble` | looming drives DNp02/DNp11 but not most of the ~1300 descending neurons | Ache et al. 2019; Namiki et al. 2018 |
| hard | `flash_is_not_loom` | a full-field flash on every photoreceptor does not fire the Giant Fiber | von Reyn et al. 2014; Klapoetke et al. 2017 |

`flybench run --tier core` / `--tier hard` / `--tier all`. Each task is a YAML file in [`tasks/`](tasks/): a readout population, one or more stimulus conditions, and a list of checks. A task passes if every check passes; the suite score is the mean fraction of checks passed. Adding a task is adding a file. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit results, tasks, or a different simulator (`--simulator mymodule:MyModel`).

## Install

```bash
pip install -e ".[dev]"
flybench toy          # builds a 2k-neuron synthetic connectome for smoke tests
flybench run          # runs the suite on it (≈10 s)
pytest
```

### The real connectome

1. Sign in at [codex.flywire.ai](https://codex.flywire.ai) (free, Google account), open **Download Data**, dataset FAFB v783, and grab: *Connections (Filtered)*, *Neurotransmitter Type Predictions*, *Classification / Hierarchical Annotations*, *Community Labels (Raw)*, *Marked Neuron Coordinates*, *Cell Types*.
2. Save them as `connections.csv.gz`, `neurons.csv.gz`, `classification.csv.gz`, `labels.csv.gz`, `coordinates.csv.gz`, `cell_types.csv.gz` in one directory and build the cache (one-time, ~30 s, ~2 GB RAM):

```bash
flybench build data/ --name flywire783
flybench run -c flywire783 --gain 0.45 -v -o results/gain0.45.json
flybench run -c flywire783 --config configs/shiu2024.yaml -o results/shiu2024.json
flybench compare results/ -o LEADERBOARD.md
```

Each full run is ~45 s on a laptop. Real neuron sets the tasks resolve to on v783: sugar GRNs = `sub_class: sugar/water` (129), bitter GRNs = `sub_class: bitter` (65), MN9 = `cell_type: CB0701` (2, labelled "Motor neuron 9; MN9"), Giant Fiber = `cell_type: DNp01` (2), looming = `LPLC2` + `LC4` (314).

Edges with fewer than 5 synapses are dropped (`--min-synapses`), matching Shiu et al.

## The model

Every neuron is the same leaky integrate-and-fire unit, parameters from [Shiu et al. 2024, *Nature*](https://www.nature.com/articles/s41586-024-07763-9):

| | |
|---|---|
| resting / reset potential | −52 mV |
| threshold | −45 mV |
| membrane τ | 20 ms |
| synaptic τ | 5 ms |
| refractory | 2.2 ms |
| synaptic delay | 1.8 ms |
| weight per synapse | 0.275 mV × `gain` |
| sign | ACh +, GABA −, glutamate −, monoamines + |

No per-neuron tuning, on purpose. If the network reproduces a reflex, the wiring did it.

Stimuli are Poisson spike trains forced onto a selected population (e.g. "all sensory neurons whose community label contains *sugar*"). Readouts are mean firing rates of a selected population over a window. Selectors are small YAML expressions over the Codex annotation columns — run `flybench select '{labels_regex: sugar, super_class: sensory}'` to see what one matches on your build. **The FlyWire community labels are free text and evolve between data versions; if a task reports "matched 0 neurons", the fix is to update the selector in the YAML, and a PR with the corrected root IDs is very welcome.**

The simulator is event-driven on the synaptic side (only neurons that spiked propagate), so a full-brain run at 0.1 ms resolution takes seconds to low minutes on a laptop depending on how much of the brain you wake up.

## What this is not

* **Not a fly.** No neuromodulation, no neuropeptides, no gap junctions, no plasticity, no spontaneous activity, no body. Absolute firing rates from this model should not be trusted; only which populations respond, and roughly in what order.
* **Not evidence of anything about consciousness.** A static graph with a five-constant neuron model is closer to a very large truth table than to an experience. The interesting ethical question is where on the fidelity curve that stops being obviously true; this project is nowhere near it, and says so.
* **Not a leaderboard of "who made the most lifelike fly".** It's a regression suite. The point is to notice when a parameter choice breaks something that used to work.

## Use it from Python

```python
from flybench import load_connectome, LIFSimulator, LIFParams, Stimulus

c = load_connectome("flywire783")
sim = LIFSimulator(c, LIFParams(gain=1.0))
sugar = c.select({"labels_regex": "sugar", "super_class": "sensory"})
mn9 = c.select("MN9")
res = sim.run(1000, [Stimulus(sugar, rate_hz=100, t_start_ms=200, t_end_ms=800)])
print(res.rate_hz(mn9, 250, 800), "Hz")
```

`flybench export -c flywire783 -o ../fly-explorer/public/data/flywire783` writes the compact binary layout that [fly-explorer](../fly-explorer) (sibling repo) loads to run the same model live in the browser.

## Citations

* Dorkenwald, S. et al. *Neuronal wiring diagram of an adult brain.* Nature 634, 124–138 (2024).
* Schlegel, P. et al. *Whole-brain annotation and multi-connectome cell typing of Drosophila.* Nature 634, 139–152 (2024).
* Shiu, P. K. et al. *A Drosophila computational brain model reveals sensorimotor processing.* Nature 634, 210–219 (2024).
* von Reyn, C. R. et al. *A spike-timing mechanism for action selection.* Nat. Neurosci. 17, 962–970 (2014).
* Ache, J. M. et al. *Neural basis for looming size and velocity encoding in the Drosophila giant fiber escape pathway.* Curr. Biol. 29, 1073–1081 (2019).
* Jaeger, A. H. et al. *A complex peripheral code for salt taste in Drosophila.* eLife 7, e37167 (2018).

MIT © Brandon Cho
