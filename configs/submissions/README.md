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
```
