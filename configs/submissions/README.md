# Submissions

One YAML file per submission. Open a pull request adding a file here and CI evaluates it on the real connectome (three seeds) and comments the scores on the PR. Nothing to install. The easiest way to create the file is the form at https://www.fly-bench.com/submit.

```yaml
label: LIF gain 0.42          # unique; letters, digits, spaces, ._()+/-
note: what you changed        # one line, shown on the leaderboard hover
connectome: flywire783        # only flywire783 is evaluated automatically for now
seeds: 3
params:                       # any LIFParams field; unlisted ones keep the Shiu 2024 defaults
  gain: 0.42
simulator: flybench.sim:LIFSimulator   # built-in simulators only, in CI; custom code is verified by hand
division: closed              # closed = reference LIF, only gain changed. Anything else is `open` and needs:
# n_free_parameters: 3        #   how many constants were fitted (0 if every value is from the literature)
# fit_data: "..."             #   what they were fitted on. Fitting on benchmark tasks makes a submission ineligible.
# controls: rewired           # negative-control wiring CI also scores (rewired | random | signflip | all | none)
conflict_of_interest: none    # a sentence: who wrote the model, whether you wrote tasks it targets, what you stand to gain
```

`reference-lif-0.45.yaml` is the maintainers' own model going through this same door (CONTRIBUTING.md,
"The maintainers' model is a submission, not the answer"); its row is tagged `reference_baseline`.

CI also runs the unpublished hold-out tasks and reports the **gap** (public − hold-out score) and the
**specificity** (real − shuffled-wiring score). Both appear on the leaderboard; a large gap on an
open-division model means the search found the tests, not the fly.
