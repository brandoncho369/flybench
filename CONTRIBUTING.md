# Contributing

Everything goes through a pull request. There is no upload form and no server: GitHub is the queue, CI is the gatekeeper, and a maintainer is the final click. That is deliberate. It rate-limits abuse for free, keeps every submission reviewable, and means the leaderboard can only change through a commit you can `git blame`.

## What a submission is

A submission is **one JSON file** written by `flybench run … -o results/<label>.json`. You never write it by hand. It records the connectome, every model parameter, the simulator's import path, how many seeds were run, and every check's measured value. `flybench validate` checks it against [`flybench/schema/result.schema.json`](flybench/schema/result.schema.json) and recomputes every score from its parts, so a hand-edited or truncated file is rejected before a human sees it.

Optionally the PR also carries what produced the file: a config YAML under `configs/`, or a simulator module under `submissions/<your-name>/`.

## The flow, step by step

```
you                              CI (automatic)                     maintainer
────────────────────────────     ───────────────────────────────    ───────────────────────────
flybench run … -o results/x.json
flybench validate results/x.json
open PR  ───────────────────────▶ pytest · lint · validate
                                  ✗ → PR shows what's wrong; fix & push
                                  ✓ ───────────────────────────────▶ flybench verify results/x.json
                                                                     (re-runs your params; scores must
                                                                      match within 0.05 per task)
                                                                     ✓ → --mark sets verified: true, merge
                                                                     ✗ → asks you what's different
merged ─────────────────────────▶ leaderboard workflow regenerates
                                  LEADERBOARD.md and pings the
                                  website, which rebuilds /bench
```

Results that a maintainer could not re-run (custom simulators we cannot install, connectome builds we do not have) are merged as **self-reported** and shown that way on the leaderboard. Verified rows rank above self-reported rows at equal scores.

## 1. Submit a result

Change parameters, not neurons. Then:

```bash
flybench run -c flywire783 --gain 0.42 --seeds 3 --label "LIF gain 0.42" -o results/lif-gain-0.42.json
flybench validate results/lif-gain-0.42.json
```

Use `--seeds 3` (or more). Single-seed results are accepted but a maintainer will re-run with three, and the knife-edge behaviour near the gain window means single-seed passes sometimes don't survive that. Label rule: letters, digits, spaces, `._()+/-`, at most 60 characters, unique across `results/`. State the Codex data version and connection file you built from; results on different builds are not comparable and the PR template asks for it.

## 2. Add a task

One YAML file in `tasks/`, copied from an existing one. It needs a readout (or several named readouts), one or more stimulus conditions, checks with an operator and threshold, a `citation` to published fly behaviour, and a `tier`: `core` if the reference LIF model passes it (it becomes a regression test), `hard` if it does not (it becomes a target). Then:

```bash
flybench lint tasks/your_task.yaml
flybench select -c flywire783 '<your selector>'      # confirm it matches the neurons you mean
flybench run -t tasks/your_task.yaml                 # on the toy — wire the toy if needed so CI covers it
flybench run -c flywire783 -t tasks/your_task.yaml   # on the real brain
```

Negative controls ("X should *not* happen") are the most valuable tasks; they are what stop a model from passing by firing everything.

## 3. Plug in a different model

The benchmark doesn't care how you simulate, only what fires. A simulator is any callable `Simulator(connectome, params)` returning an object with

```python
def run(self, duration_ms: float, stimuli: list[Stimulus]) -> SimResult: ...
```

(`Stimulus` has `.neurons`, `.rate_hz`, `.t_start_ms`, `.t_end_ms`; `SimResult` is `flybench.sim.SimResult`, spike times + neuron ids.) Put it under `submissions/<your-name>/` with a `README` and a `requirements.txt`, and run

```bash
flybench run -c flywire783 --simulator submissions.yourname.model:MySim --seeds 3 --label "yourname adaptive-LIF v1" -o results/yourname-adaptive-lif-v1.json
```

The report records the simulator path, so rows stay distinguishable. If a maintainer can install it, it gets verified; otherwise it is merged self-reported.

## Ground rules

Cite the behaviour. State what you changed. Never tune per-neuron parameters to pass a task: that is fitting the test, and it defeats the point. A small set of unpublished hold-out tasks is run on notable submissions to check that a model generalises rather than memorising the public YAML; a model that passes the public tier and fails the hold-out gets a note on its row, not a removal.

## Maintainers: verifying

```bash
flybench verify results/x.json            # re-runs, compares per-task scores within 0.05
flybench verify results/x.json --mark     # same, and writes verified: true on success
```

Branch protection on the default branch should require the `ci` check and one review. The `leaderboard` workflow needs a `FLY_EXPLORER_TOKEN` secret (fine-grained PAT, contents: write on fly-explorer) to trigger the website rebuild; without it the site is updated by running `scripts/leaderboard-snapshot.py` there by hand.
