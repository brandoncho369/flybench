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

## The tasks

| # | task | what it tests | source |
|---|------|---------------|--------|
| 1 | `stability` | no input → (almost) no output. Guards against "everything fires so everything passes" | Shiu et al. 2024 |
| 2 | `sugar_to_proboscis` | sugar GRNs → MN9 (proboscis motor neuron) fires | Dethier 1976; Shiu et al. 2024 Fig. 2 |
| 3 | `bitter_suppression` | sugar + bitter → MN9 fires less than sugar alone | Shiu et al. 2024 Fig. 3; Jaeger et al. 2018 |
| 4 | `looming_to_giant_fiber` | LPLC2 / LC4 → Giant Fiber (escape) fires | von Reyn et al. 2014; Ache et al. 2019 |
| 5 | `taste_specificity` | bitter alone does **not** drive MN9 (negative control) | Shiu et al. 2024 |

Each task is a YAML file in [`tasks/`](tasks/): a readout population, one or more stimulus conditions, and a list of checks. A task passes if every check passes; the suite score is the mean fraction of checks passed. Adding a task is adding a file. PRs with new, *cited* reflexes are the most useful contribution.

## Install

```bash
pip install -e ".[dev]"
flybench toy          # builds a 2k-neuron synthetic connectome for smoke tests
flybench run          # runs the suite on it (≈10 s)
pytest
```

### The real connectome

1. Make a free account at [codex.flywire.ai](https://codex.flywire.ai) and download, for data version **783**: `connections.csv.gz`, `neurons.csv.gz`, `classification.csv.gz`, `labels.csv.gz`.
2. Put them in one directory and build the cache (one-time, a few minutes, ~1 GB RAM):

```bash
flybench build ~/Downloads/flywire783 --name flywire783
flybench run -c flywire783 --config configs/shiu2024.yaml -o results/shiu2024.json
flybench run -c flywire783 --gain 0.65 -o results/gain065.json
flybench compare results/ -o LEADERBOARD.md
```

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
