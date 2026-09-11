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

Inside that window the reference model then fails most of the **hard** tier. The starkest failure is the simplest: after a half-second taste of sugar, ~8 % of the brain keeps firing at a perfectly constant rate *forever* (MN9 at 354 Hz one second after the stimulus ended, unchanged at three seconds). Recurrent excitation sustains itself and nothing in the model can switch it off. A real fly is at rest a second later. The other failures are informative, not embarrassing: MN9 ignition is all-or-nothing (0 Hz or ~400 Hz, nothing in between — no dose response); a second sugar pulse gets exactly the response of the first (no adaptation, because the model has no state that outlives 20 ms); driving one olfactory glomerulus fires ~84 % of all projection neurons (no lateral inhibition, the antennal lobe is a broadcast); looming recruits ~30 % of all descending neurons rather than a takeoff ensemble. Full table in [`LEADERBOARD.md`](LEADERBOARD.md).

**Two things the reflex tasks alone could not see.** Measuring spikes rather than "did it fire" (task 13) shows the giant fiber firing **129 times** per looming stimulus where the real GF fires once, and MN9 at 360 Hz — the reflexes "work" only in the sense that the wire conducts. And re-running the core reflexes on a copy of the connectome with every synapse count jittered ±25 % (task 14, a stand-in for a second individual) shows that at gain 0.45 **escape is robust and taste is a coin flip**: one of three jittered brains never extends the proboscis. At gain 1.0 taste becomes robust across individuals — and a fifth of the brain fires, a flash triggers escape, and bitter no longer reliably cancels sugar. One global gain trades robustness for sparseness; there is no setting that buys both, and every real fly has both. That gap is not in the wiring diagram.

**One real mechanism, and what it does and doesn't buy.** Adding spike-frequency adaptation (a documented property of fly neurons; 2 mV per spike, 200 ms decay, applied identically to every neuron, no per-neuron tuning) changes four things nobody tuned it for: the reflexes survive a different individual's synapse counts on every seed, the brain returns to rest (0 Hz two seconds after sugar), MN9 fires at 48 Hz instead of 360, and looming recruits 13 % of descending neurons instead of 30 %. It does **not** fix dose response (weak sugar still gives 0 Hz), it does not fix habituation (the second pulse is still 2.5× the first — the opposite of biology), the giant fiber still fires 116 times per loom, and 88 % of projection neurons still respond to one odour. That is a research agenda, not a leaderboard win: adaptation explains part of the fly's robustness and none of its selectivity.

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
| hard | `return_to_rest` | one second after a 500 ms taste of sugar, the brain is quiet again | Dethier 1976; Shiu et al. 2024; Benda & Herz 2003 |
| hard | `physiological_rates` | the giant fiber spikes ~once per loom, not 100+ times; MN9 fires at tens of Hz, not at its refractory ceiling | von Reyn et al. 2014; Schwarz et al. 2017 |
| hard | `wiring_robustness` | the core reflexes still work when every synapse count is jittered ±25 % (a different individual) | Schlegel et al. 2024; Marder & Goaillard 2006 |

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

**Other connectomes.** Any neuPrint dataset can be pulled into the same layout, no login needed. The male CNS the viral Minecraft/Beat Saber demos ran on:

```bash
flybench fetch-neuprint data-malecns              # male-cns:v1.0 from neuprint.janelia.org, resumable
flybench build data-malecns --name malecns
flybench run -c malecns --config configs/malecns_minecraft.yaml --seeds 3 -o results/malecns-gain-0.65.json
```

Result (3 seeds each, [docs/MALECNS.md](docs/MALECNS.md)): on the male CNS there is **no gain at which the reference model does both taste and vision**. At 0.45 looming → giant fiber is clean but sugar never reaches the proboscis; at the demo's 0.65 sugar works but so does quinine, a shadow triggers feeding, 39% of descending neurons fire, and the network never quiets. Part of the gap is the dataset's transmitter predictions (13% of the male sugar neurons are called glutamatergic, which the model treats as inhibitory). Selectors for that dataset were identified from wiring onto named second-order neurons; the table is in the doc.

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

## What a score means — and what it doesn't

A score is the fraction of listed behaviours a model reproduces under fixed, cited conditions. **A higher score does not mean a model is closer to a real fly's biology.** A model can pass more tasks by adding a mechanism flies don't have, or a real mechanism with wrong numbers, or by being tuned to the public tasks. Three habits keep the leaderboard honest:

1. Every row carries its constants and a one-line note; read it as a hypothesis with its evidence attached, not as a ranking of truth.
2. Mechanisms added to a model should be ones neuroscience has independent evidence for (spike-frequency adaptation, synaptic depression, gap junctions, neuromodulation) with constants in literature ranges, and the citation goes in the note.
3. A change that fixes one task while breaking a core reflex is a finding, not a failure to hide; it usually means the mechanism is real but the numbers are not.

The reference model is deliberately the simplest thing that works. Every improvement on it is a claim to be argued with, and the benchmark exists so the argument can happen with numbers.

**How good is the ruler itself?** Honestly: calibrated at the coarse end. It reliably tells "this brain is seizing" from "this pathway is dead" from "this reflex works"; it cannot yet rank two nearly-right models. What keeps it honest, and what we changed once we noticed the gaps:

- *Every threshold has a provenance.* Each check carries a `basis`: a citation for the number, or an explicit `convention:` explaining the judgement call. The lint refuses tasks without one. Most of our numbers are conventions and say so.
- *Effect sizes, not just pass/fail.* Every check reports a margin (how far from the line, in decades, e.g. `+3.2x` or `-1.4x`), so two models on either side of 5 Hz are not mistaken for categorically different.
- *Ceilings, not only floors.* The reflex tasks only ask that a pathway conducts; the reference model passes them with the giant fiber at ~430 Hz, its refractory ceiling, when the real GF fires **once** per escape (von Reyn et al. 2014). Task 13 (`physiological_rates`) measures spikes per neuron and fails saturation. The reference model fails it.
- *Circuits count once.* Seven tasks hinge on the sugar → MN9 pathway, so the task-weighted score is dominated by one circuit. Reports also carry `core_by_circuit` / `hard_by_circuit`: the mean over circuits of the mean within each.
- *It's one animal.* A connectome is one fly; synapse counts differ between individuals by tens of percent while behaviour does not. Task 14 (`wiring_robustness`) reruns the core reflexes on a copy where every synapse count is jittered ±25% (lognormal). A model that only works at one specimen's exact counts has fit the specimen, not the species. This is also the answer to "wouldn't a different female's connectome give different results?" — it would, somewhat, and the benchmark now measures how much.
- *Hold-out.* CI can run a small set of unpublished tasks (`FLYBENCH_HOLDOUT_URL` secret) and report only pass/fail, as a check against tuning to the public YAML.

What is still weak: the thresholds are conventions far more often than measurements, four circuits is not a fly, and nothing here is calibrated against real recordings. Contributions that replace a `convention:` with a citation are the most valuable kind.

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
