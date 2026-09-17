# Negative controls: what a task scores on shuffled wiring

A reflex that a simulated brain performs proves little if a *shuffled* version of that brain
performs it too. In 2026 a 302-neuron *C. elegans* connectome wired to a fly body produced
realistic fly walking (the "digital sphinx", bioRxiv 2026.03.20.713233), and graph-baseline
studies (FlyGM, arXiv 2602.17997) showed degree-preserving rewiring and Erdős–Rényi graphs are the
controls any connectome claim needs. flybench therefore lets every task be scored on the real
wiring and on destroyed wiring, and reports the difference.

```bash
flybench run -c flywire783 --gain 0.45 --seeds 3 --controls all
flybench run -c malecns --config configs/malecns_minecraft.yaml --controls rewired,random
```

| control | what stays the same | what changes |
|---|---|---|
| `rewired` | every neuron's out-degree, synapse weights and transmitter sign; the number of synapses landing on each neuron | which neuron connects to which |
| `random` | neuron count, edge count, distribution of synapse counts, fraction of inhibitory neurons | everything else (Erdős–Rényi) |
| `signflip` | every edge and its magnitude | which neurons are inhibitory (signs permuted) |

Stimuli and readouts still target the same cells (annotations are untouched), so "sugar GRNs →
MN9" is asked of a brain in which the sugar GRNs no longer wire to MN9.

## What the report contains

Per task: `controls: {rewired: {score, passed}, ...}`, `specificity = score(real) − max(score(control))`,
and `non_diagnostic: true` when the task passed on the real wiring *and* on some control. Per run:
`specificity` (mean over tasks) and `non_diagnostic` (the list). The leaderboard shows the run-level
specificity; `–` means no controls were run.

## Reading the result

- **Positive tasks** ("sugar must drive MN9") should fail on every control. If one passes, the
  task is measuring excitability, not wiring, and needs a stricter check or a different readout.
- **Null tasks** ("bitter must *not* drive MN9", "a flash must *not* trigger escape", "the brain is
  quiet at rest") are passed by a dead network too. They are still useful — they catch runaway
  models — but they cannot be diagnostic in the shuffle sense, so they are noted, not flagged.
  A task is only flagged `non_diagnostic` if at least one of its checks requires a response.
- **`signflip` is a weak control for monosynaptic excitatory pathways** (LPLC2 → GF is one edge;
  after permuting signs it is still excitatory with high probability). It is the right control for
  anything that depends on inhibition: bitter suppression, return to rest, adaptation.
- **Read `non_diagnostic`, not only `specificity`.** Specificity compares scores, and a model that
  fails different checks than the shuffle can show specificity 0 while the task is perfectly
  diagnostic (task 16 on the toy: the real brain fails "one spike", the shuffle fails "seen"; both
  score 6/9). The flag asks the right question — did the shuffle *pass* the task — the number is a
  summary.
- A shuffled brain that "passes" everything at a given gain is the strongest possible statement
  that the gain is too high: at that setting any wiring fires.

## Cost

Each control multiplies the run time of the suite by roughly one (three controls ≈ 4× a plain run).
Building the controls themselves takes seconds even on MaleCNS (6.3 M edges); it is the simulation
that costs. Use `--controls rewired` for routine runs and `all` for leaderboard rows.

## The audit (ROADMAP item 47)

`flybench audit tasks/x.yaml -c flywire783` is the controls applied at the door: a proposed task
is run on the reference LIF with the `rewired` control and refused when it is non-diagnostic
(a positive check passes on the real wiring and on the shuffle). It also flags a `hard` task the
reference passes with ≥ 1 decade of margin on every check (trivial — a regression test, not a
target) and a tier the run contradicts. CI runs it for every task a pull request adds or changes.
Existing tasks 1–32 were not audited retroactively at their creation; their `non_diagnostic`
flags in the result files are the same test applied after the fact (task 23 and 32 sit at the
floor for both wirings, which is "not discriminating yet", not "non-diagnostic").
