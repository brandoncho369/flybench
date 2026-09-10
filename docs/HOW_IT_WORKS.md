# How flybench and fly-explorer actually work

This is the full walkthrough of what was built, why each piece exists, and what it does under the hood, written so you can explain every part yourself. It goes from the biology down to the individual lines of code. Read it top to bottom once, then use it as a reference.

## 1. The one-paragraph version

A connectome is a wiring diagram: a list of "neuron A makes N synapses onto neuron B." FlyWire published that list for an entire adult fruit fly brain, about 140,000 neurons and 50 million synapses. A wiring diagram on its own does nothing, so to make it *compute* you attach a tiny model of a neuron to every node and let spikes flow along the edges. The simplest respectable model is the leaky integrate-and-fire (LIF) neuron, and Shiu et al. (Nature, 2024) showed that if you use the same five constants for every one of the 140k neurons, the network reproduces several real fly reflexes, most famously "sugar on the tongue makes the proboscis extend." **flybench** turns that observation into a test suite: a set of known reflexes, each with a stimulus, a readout, and a pass/fail threshold, so any set of model parameters gets a score. **fly-explorer** runs the identical model in a Web Worker in the browser and draws the brain as a point cloud so you can press "sugar" and watch the activity travel to the motor neuron. The two repos share one binary export format, which is how the browser gets the graph.

## 2. The data

### 2.1 What FlyWire Codex gives you

FlyWire's data portal (codex.flywire.ai, unrelated to any AI coding tool that shares the name) lets you download a few CSVs per data version. Version 783 is the one the Shiu paper calibrated on. The files flybench reads:

`connections.csv.gz` has one row per (presynaptic neuron, postsynaptic neuron, brain region) with a `syn_count` column, the number of individual synapses found between that pair in that region, and an `nt_type` column, the predicted neurotransmitter of the presynaptic neuron. `neurons.csv.gz` has one row per neuron with its `root_id` (a 64-bit integer that uniquely names a reconstructed neuron in that data version), its predicted neurotransmitter, and a soma or centroid position in nanometres. `classification.csv.gz` has the hierarchical annotation for each neuron: `super_class` (sensory, central, motor, descending, visual_projection and so on), `class`, `cell_type` (e.g. `MN9`, `LPLC2`), `hemibrain_type` (the matching name in the older hemibrain dataset), and `side`. `labels.csv.gz` is the community annotation: free-text labels that hundreds of scientists attached to neurons during proofreading, like "sugar GRN" or "bitter GRN, Gr66a". Those labels are the only way to find some populations, which matters later because free text is messy.

### 2.2 From CSVs to a matrix

`flybench/connectome.py` has `build_from_codex()`, which does five things in order. It sums synapse counts across brain regions so each (pre, post) pair becomes one edge. It drops edges with fewer than 5 synapses, because reconstruction has false positives and the Shiu paper found 5 a reasonable floor; this takes ~15 million pairs down to ~2.7 million. It builds a sorted array of all root_ids and uses its position in that array as the neuron's integer index from then on, since a 64-bit ID is a terrible array index. It looks up the presynaptic neuron's transmitter and applies a sign: acetylcholine +1, GABA −1, glutamate −1 (in flies glutamate is usually inhibitory), dopamine/octopamine/serotonin +1, unknown +1. Then it builds a `scipy.sparse.csr_matrix` W of shape (N, N) with **rows = presynaptic, columns = postsynaptic**, so `W[pre, post]` is the signed synapse count. CSR (compressed sparse row) stores three flat arrays: `indptr` (where each row starts), `indices` (column of each nonzero), `data` (the value). It is exactly the layout you want when you repeatedly ask "given that neuron `pre` spiked, who does it hit?" because that is one contiguous slice of `indices`.

The result is a `Connectome` dataclass: `root_ids`, `W`, `positions` (float32, N×3), `annotations` (a pandas DataFrame with the classification and label columns), and a `meta` dict. `Connectome.save()` writes these to a cache directory as `.npz`/`.npy`/parquet so the CSV parse only happens once.

### 2.3 Selectors

Every task needs to say "the sugar-sensing neurons" or "MN9" without hard-coding root IDs that change between data versions. `select()` in `connectome.py` implements a tiny query language over the annotation columns, expressed as YAML/dict so tasks stay declarative:

```yaml
{cell_type: MN9}                                   # exact match on a column
{hemibrain_type: [LC4, LPLC2]}                     # is-in
{labels_regex: "sugar"}                            # case-insensitive regex on a column
{all_of: [{labels_regex: sugar}, {super_class: sensory}, {not: {labels_regex: bitter}}]}
{any: [{cell_type: GF}, {hemibrain_type: "Giant Fiber"}]}
{all: true}                                        # every neuron
```

It returns a NumPy array of integer indices. The `_mask()` helper recursively builds a boolean mask, ANDing keys inside one dict and handling `any`, `all_of`, `not` as combinators. The `super_class: sensory` guard on the taste selectors exists because an interneuron labelled "sugar 2nd order" would otherwise be treated as a receptor; that exact bug showed up in testing and is a preview of what will happen on the real labels.

### 2.4 The toy connectome

`flybench/toy.py` builds a 2,004-neuron synthetic network with the same annotation columns as Codex. It exists for three reasons: the tests and CI must run without a 300 MB download, the browser app needs a dataset it can ship in the repo, and it is a sanity check on the benchmark itself. If a task cannot pass on a network hand-wired to pass it, the task definition is broken. The populations are: sugar/bitter/water GRNs (receptors), an excitatory "taste interneuron" layer, a GABAergic "bitter local" layer that inhibits the taste interneurons and MN9, two MN9 motor neurons, LPLC2 and LC4 looming detectors converging on two Giant Fiber neurons, an olfactory ORN→PN→LHN chain that nothing tests, and 1,500 background neurons with sparse balanced excitation/inhibition so the "stability" task has something to check. Positions are Gaussian blobs per population so it looks brain-ish. It proves nothing about biology and the README says so.

## 3. The neuron model, and why the constants are what they are

### 3.1 The equations

Every neuron has two state variables: membrane voltage V (mV) and synaptic drive g (mV). Two differential equations:

```
tau_m · dV/dt = (V_rest − V) + g        # voltage leaks toward rest, pushed by g
tau_s · dg/dt = −g                      # synaptic drive decays exponentially
```

When a presynaptic neuron spikes, after a conduction delay, every postsynaptic neuron's g jumps by `w_syn × gain × W[pre, post]`. When V crosses threshold V_th the neuron spikes, V is reset, and the neuron is refractory (cannot spike) for t_ref. That is the entire model. The constants, from Shiu et al.:

| constant | value | intuition |
|---|---|---|
| V_rest, V_reset | −52 mV | where voltage sits with no input, and where it snaps back after a spike |
| V_th | −45 mV | so a neuron needs 7 mV of net push to fire |
| tau_m | 20 ms | how fast voltage forgets its input; a "leaky bucket" time constant |
| tau_s | 5 ms | how long one synaptic kick lasts |
| t_ref | 2.2 ms | caps firing at ~450 Hz |
| delay | 1.8 ms | axonal conduction time |
| w_syn | 0.275 mV | voltage kick per synapse |

The number to internalise is 7 mV ÷ 0.275 mV ≈ 25: a neuron fires if roughly 25 synapses' worth of excitation arrive within a few milliseconds of each other. A single strong connection in the fly is 20–100 synapses, so one upstream neuron firing a burst can drive its target; a weak 5-synapse connection cannot on its own. That is what makes the network selective rather than a firework: sugar reaches MN9 through a chain of strong connections, while the sparse background stays quiet.

`gain` is a global multiplier on every weight. It is the knob every viral demo tuned by hand. flybench exposes it because it is the single most important parameter and the benchmark exists to say what values of it still behave like a fly.

### 3.2 Discretising it

Computers step in discrete time. flybench uses forward Euler with dt = 0.1 ms, which is small relative to the 5 ms and 20 ms time constants, so the error is negligible. In code (`sim.py`, `LIFSimulator.step()`):

```python
self.v += (p.v_rest_mv - self.v + self.g) * self._decay_m   # _decay_m = dt / tau_m
self.g *= self._decay_s                                      # _decay_s = exp(-dt / tau_s)
```

The g decay uses the exact exponential because it is a one-line closed form; V uses Euler because g makes it inhomogeneous.

### 3.3 One time step, in four phases

`step()` runs once per 0.1 ms:

1. **Deliver.** A ring buffer `queue` holds `delay_steps` (= 18) slots of "who spiked". The slot whose delay just expired is `arriving`. `self.Wrow[arriving].sum(axis=0)` takes those rows of the (pre-scaled) CSR matrix and sums them into one length-N vector: the total kick every postsynaptic neuron receives this step. That is added to g. Only neurons that actually spiked touch the matrix, which is why the cost scales with activity, not with the 2.7 M edges. A silent brain is nearly free to simulate.
2. **Integrate.** The two lines above.
3. **Threshold.** `fired = (v >= v_th) & (ref_until < t)`. Stimulated neurons are added here too: for each stimulus, every neuron in the set spikes this step with probability `rate_hz × dt / 1000` (100 Hz → 1 % per step), which is how you generate a Poisson spike train. Forced spikes still respect the refractory period. Fired neurons get `v = v_reset` and `ref_until = t + t_ref`.
4. **Queue.** The fired indices go into the ring buffer slot that will be delivered 18 steps from now.

`run()` loops `step()` for `duration_ms / dt` steps and records `(time, neuron)` for every spike into a `SimResult`, which knows how to compute a mean firing rate per neuron over a window for any set of neurons (`rate_hz`), the whole-network rate, and the fraction of neurons that fired at all (`active_fraction`).

## 4. flybench: the benchmark

### 4.1 A task file

`tasks/02_sugar_to_proboscis.yaml`, abbreviated:

```yaml
name: sugar_to_proboscis
duration_ms: 1000
window: [250, 800]                       # score over this interval
readout:
  select: {any: [{cell_type: MN9}, {hemibrain_type: MN9}]}
conditions:
  baseline: {stimuli: []}
  sugar:
    stimuli:
      - select: {all_of: [{labels_regex: sugar}, {super_class: sensory}, {not: {labels_regex: bitter}}]}
        rate_hz: 100
        t_start_ms: 200
        t_end_ms: 800
checks:
  - {type: rate,   cond: sugar, op: ">", value: 5}               # MN9 > 5 Hz
  - {type: ratio,  cond: sugar, over: baseline, op: ">", value: 5}  # ≥5× baseline
  - {type: active_fraction, cond: sugar, op: "<", value: 0.2}    # <20% of brain woke up
```

A task has a readout population, one or more named conditions (each a list of stimuli), and checks. `bench.py:run_task()` builds one `LIFSimulator`, runs every condition from a fresh reset, records readout rate / network rate / active fraction per condition, then evaluates each check. Check types are `rate` (readout Hz in a condition), `network_rate`, `active_fraction`, and `ratio` (readout rate in one condition divided by another, with a small epsilon so 0/0 is defined). A task passes if all checks pass; its `score` is the fraction of checks passed so partial credit is visible. The suite score is the mean over tasks.

The five core tasks and the reasoning behind each (six harder tasks were added later as a `hard` tier; see the README): `stability` is silence in, silence out, the guard against "everything fires so everything passes". `sugar_to_proboscis` is the headline reflex. `bitter_suppression` checks that sugar+bitter drives MN9 less than half as much as sugar alone, which requires the inhibitory signs to be right. `looming_to_giant_fiber` is the escape pathway, a different circuit entirely. `taste_specificity` is a negative control: bitter alone must not drive MN9. Two positive tests, one interaction, one negative control, one sanity guard is the minimum that makes the score meaningful.

### 4.2 What the gain sweep showed

On the toy connectome with the default weight, gain 0.3 fails the taste tasks (MN9 at 1.8 Hz, the signal does not make it through), 0.6 to 2.0 pass everything, and 4.0 fails the active-fraction check on the sugar task because 45 % of the brain lights up. So even the toy demonstrates the benchmark's job: there is a window of parameters that behaves like a fly, and both edges are detectable. Expect the window to be different and narrower on the real connectome.

### 4.3 The CLI

`flybench toy` builds and caches the synthetic network. `flybench build <codex_dir>` parses the real CSVs into the cache. `flybench run -c <name> [--gain X | --config file.yaml] [-o results/x.json]` runs the suite and prints a table. `flybench compare results/` reads the JSON reports and prints a markdown leaderboard. `flybench select '{labels_regex: sugar}'` shows what a selector matches, which is the tool you will use to fix selectors against real labels. `flybench export -c <name> -o <dir>` writes the browser format. `configs/` holds two parameter files: the Shiu 2024 defaults and the gain=0.65 value the Minecraft demo used on the male connectome, included so the first interesting result is "what does that gain do on FlyWire".

### 4.4 The export format

`export.py` writes six files: `positions.bin` (float32 ×3 per neuron), `indptr.bin` / `indices.bin` / `weights.bin` (the CSR arrays as int32/int32/float32), `classes.bin` (one byte per neuron, the super_class index, used for colour), and `meta.json` (N, edge count, the class list, and `populations`, a dict of name → list of indices produced by running the default selectors like "sugar GRNs" and "MN9 (proboscis)"). For the real brain that is about 35 MB, dominated by the 2.7 M edges × 8 bytes. The browser never sees CSVs or pandas; it gets flat typed arrays it can use directly.

## 5. fly-explorer: the browser

### 5.1 Structure

Next.js App Router, TypeScript, Tailwind, three.js via react-three-fiber. Five files matter: `src/lib/types.ts` (the message protocol and the constants), `src/lib/lif.ts` (the simulation core, pure TypeScript with unit tests), `src/workers/lif.worker.ts` (the Web Worker that loads data and drives the core), `src/components/Brain.tsx` (rendering), `src/app/page.tsx` (UI and plumbing, with a `?` help popover on every control). `public/data/toy/` is the shipped export; `public/data/flywire783/` is where the real one goes and is git-ignored.

### 5.2 Why a Web Worker

JavaScript on the main thread shares one event loop with rendering and input. Stepping 140k neurons ten times per frame would freeze the UI. A Web Worker is a separate thread with its own memory; the page and the worker talk only by `postMessage`. So the worker owns the whole simulation state and the page owns the UI, and the only thing that crosses per frame is one `Uint8Array` of activity, 140 KB, sent as a *transferable* (ownership moves rather than copies). The messages are typed in `types.ts`: page→worker `load`, `params`, `stim`, `run`, `speed`, `reset`; worker→page `loaded`, `progress`, `frame`, `error`.

### 5.3 The worker

`load()` fetches `meta.json` and the five binaries in parallel and wraps each `ArrayBuffer` in a typed array (`new Int32Array(buf)`), which costs nothing because it is a view, not a copy. It precomputes a `Uint8Array` membership mask per population so "did neuron i belong to MN9" is one array read, then calls `reset()` to allocate `v`, `g`, `refUntil`, `act` (a decaying activity trace used only for display) and the delay ring buffer.

`step()` is a line-for-line port of the Python, with the one change that matters: instead of the sparse-matrix row-sum, it walks the CSR rows directly.

```ts
for (const pre of arriving)
  for (let k = indptr[pre]; k < indptr[pre + 1]; k++)
    g[indices[k]] += weights[k] * wScale;
```

Then one loop over all N neurons integrates, decays the display trace by 0.97, and thresholds. Then forced stimulus spikes, same Poisson trick as Python. Then bookkeeping: this step's spike count goes into a 1,000-step (100 ms) ring buffer for the whole network and one per population, which is how the readout panel gets "mean Hz per neuron over the last 100 ms" without storing every spike.

`frame()` runs `stepsPerFrame` steps (default 10, so one animation frame = 1 ms of brain time), converts `act` to bytes, posts a `frame` message with the activity buffer, the rates, and how many ms of compute one step took, then schedules itself again with `setTimeout(frame, 16)`. Changing `gain` only recomputes `wScale`, so it applies live without a reset; changing `dt` or `delay` would change the array shapes and does trigger a reset.

### 5.4 The page

`page.tsx` creates the worker once (`new Worker(new URL("../workers/lif.worker.ts", import.meta.url))`, which is the pattern Next.js/webpack recognises to bundle a worker), sends `load` for the toy, and on `loaded` stores `meta`, `positions`, `classes` in React state and tells the worker to run. Each `frame` message writes the activity array into a `useRef` (not state, so it does not re-render React 60 times a second) and updates the small numeric state the sidebar shows, plus a 120-sample history per readout for the sparklines. Stimulus buttons look up the population's indices from `meta.populations`, copy them into an `Int32Array`, and send a `stim` message with the current rate slider and a 500 ms duration. The highlight toggle (the ◉ button) builds a `Set` of indices that `Brain` paints cyan, so you can see where a population sits before you stimulate it.

### 5.5 Rendering

`Brain.tsx` normalises positions once (centre at origin, longest axis = 2 units, flip Y so the brain is upright in FlyWire's coordinate convention) and builds a `THREE.BufferGeometry` with four per-vertex attributes: `position`, `base` (RGB by super_class), `activity` (float, updated every frame), and `highlight`. A `THREE.Points` object draws all N vertices in one GPU draw call, which is why 140k points is trivial.

A custom `ShaderMaterial` does the visual work. The vertex shader mixes the base colour toward warm yellow by `activity`, mixes toward cyan by `highlight`, sets alpha from the larger of the two, and sets `gl_PointSize` to grow up to 4× with activity and to shrink with distance from the camera (`2.6 / -mv.z`). The fragment shader turns each square point into a soft disc by discarding pixels outside radius 0.5 and fading with `smoothstep`. Blending is additive with depth-write off, so overlapping active neurons brighten rather than occlude, which is what gives the "glow". Every frame, r3f's `useFrame` copies the latest activity bytes from the ref into the `activity` attribute and marks it `needsUpdate`, and that is the only per-frame CPU work on the main thread. `OrbitControls` from drei gives drag-to-rotate and a slow auto-rotate.

### 5.6 Performance

The toy steps in ~0.01 ms. On the real brain, cost is dominated by the integrate loop (140k neurons × 10 steps per frame = 1.4 M simple float ops, well under a millisecond) plus propagation, which depends on how many neurons spiked and their out-degree. Quiet brain: close to real time at 10 steps/frame. Strong stimulus: the per-step cost rises and the speed slider is there to trade brain-time per frame for smoothness. A next optimisation, if you want one, is moving the integrate loop to WebAssembly or WebGPU; the architecture would not change.

## 6. What's real and what isn't, for when someone asks

Real: the graph, the synapse counts, the neurotransmitter predictions, the cell-type labels, and the fact that the same five constants everywhere reproduce named reflexes. Nothing per neuron is tuned; if sugar lights up MN9 the wiring did it.

Not real: no neuromodulators or neuropeptides (a huge part of how a real fly changes state), no gap junctions (electrical synapses), no plasticity or learning, no spontaneous activity, no body or sensory transduction ("sugar" is forcing spikes on ~60 labelled cells), no ion-channel biophysics. Absolute firing rates are not meaningful, only the pattern of which populations respond and roughly in what order. Nothing in the simulation experiences anything. The interesting philosophical question is where on the fidelity curve that stops being obviously true, and this is far below it. Saying that plainly is a feature; it is what separates the project from the viral demos.

## 7. What happens next, and what will break

Getting the real data: free Codex account, download the four v783 CSVs, `flybench build`, `flybench run`, `flybench export`. Then expect two things. First, some selectors will match zero or wrong neurons because the community labels are free text; the task runner reports "matched 0 neurons" in the notes column and `flybench select` lets you iterate until "sugar GRNs" returns roughly the 60-ish cells the literature expects. Fixing those and committing the corrected selectors (or explicit root_id lists) is the first real contribution. Second, thresholds like "MN9 > 5 Hz" were set on the toy; the real MN9 response in Shiu et al. is in the same ballpark but you may have to move the numbers and should document why.

For fly-bench.com: fly-explorer deploys to Vercel as-is (import the repo, done), and a leaderboard page is a natural addition, reading a `results/*.json` folder that CI regenerates. Note the repo is named `flybench` and the domain has a hyphen; pick one spelling for the product name before you print it anywhere.
