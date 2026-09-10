# Contributing

There are three ways to contribute, in increasing effort.

## 1. Submit a result

Run the suite with your parameters and add the report:

```bash
flybench run -c flywire783 --gain 0.42 --label "my-run" -o results/my-run.json
flybench compare results/ -o LEADERBOARD.md
```

Open a PR with the JSON and the regenerated `LEADERBOARD.md`. Say in the PR what you changed and why. Results are only comparable if they use the same connectome build (`flybench build` with the same Codex files and `--min-synapses`), so mention the Codex data version and connection file you used.

## 2. Add a task

A task is one YAML file in `tasks/`. Copy an existing one. It needs:

* a `readout` selector (which neurons you measure)
* one or more `conditions`, each a list of stimuli (selector + Poisson rate + window)
* `checks`, each `rate` / `network_rate` / `active_fraction` / `ratio` with an operator and threshold
* a `citation` for the behaviour you're testing — published fly work, not a hunch
* a `tier`: `core` if the reference LIF model passes it (it becomes a regression test), `hard` if it doesn't (it becomes a target)

Tasks can have several named `readouts`, and checks can name a `readout` and a `window`; see `tasks/07_adaptation.yaml` and `tasks/10_looming_dn_ensemble.yaml` for the full grammar.

Run `flybench select '<selector>' -c flywire783` to confirm your selectors match the neurons you think they do, and run the task on the toy (`flybench run -t tasks/your_task.yaml`) — if the toy can't be wired to pass it, add the wiring in `flybench/toy.py` so CI covers it. Tasks that include a negative control (X should *not* happen) are especially valuable.

## 3. Plug in a different model

The benchmark doesn't care how you simulate, only what fires. A simulator is any callable `Simulator(connectome, params)` returning an object with

```python
def run(self, duration_ms: float, stimuli: list[Stimulus]) -> SimResult: ...
```

where `Stimulus` has `.neurons` (int indices), `.rate_hz`, `.t_start_ms`, `.t_end_ms` and `SimResult` is `flybench.sim.SimResult` (spike times + neuron ids). Put it in a module and run

```bash
flybench run -c flywire783 --simulator mypkg.mymodel:MySimulator --label "conductance-based v1" -o results/mine.json
```

`params` is the standard `LIFParams`; ignore whatever doesn't apply to your model. Examples of models people could try: conductance-based synapses, per-neurotransmitter weights, gap junctions from the electrical-synapse tables, neuromodulator gain fields, learned weight corrections. The leaderboard records the simulator's import path so runs stay distinguishable.

## Ground rules

Cite the behaviour. State what you changed. Never tune per-neuron parameters to pass a task — that's fitting the test, and it defeats the point. Scores are self-reported until a maintainer re-runs them; a small set of unpublished hold-out tasks is run on notable submissions to check that a model generalises rather than memorising the public YAML.
