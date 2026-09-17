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

**Easiest: the form at [fly-bench.com/submit](https://www.fly-bench.com/submit).** Pick a model and parameters, click the button; GitHub opens a pull request with a small config file; CI runs the full suite on the real connectome with three seeds and comments the scores; a maintainer merges; your row is live and marked verified. Nothing to install, nothing to download.

From the command line, the same thing is `flybench propose "my label" --gain 0.42 --note "…" --open-pr`, which writes `configs/submissions/<slug>.yaml` and opens the PR. Only the built-in simulators run in CI; custom code is verified by hand (section 3).

If you'd rather run it yourself and submit the finished report (for example with a custom simulator), change parameters, not neurons, then two commands:

```bash
flybench run -c flywire783 --gain 0.42 --seeds 3 --label "LIF gain 0.42" -o results/lif-gain-0.42.json
flybench submit results/lif-gain-0.42.json --note "gain 0.42, otherwise Shiu 2024 defaults"
```

`submit` validates the file, makes a branch, commits, and opens the pull request with the template filled in from the report (it uses the GitHub CLI, `gh`; install it once and run `gh auth login`). `--dry-run` shows the PR text without doing anything. If you'd rather do it by hand, `flybench validate` then a normal PR works too.

Use `--seeds 3` (or more), and `--jobs N` to spread the (task, wiring) units over N cores — the report is bit-identical to a serial run. Single-seed results are accepted but a maintainer will re-run with three, and the knife-edge behaviour near the gain window means single-seed passes sometimes don't survive that. Label rule: letters, digits, spaces, `._()+/-`, at most 60 characters, unique across `results/`. State the Codex data version and connection file you built from; results on different builds are not comparable and the PR template asks for it.

## 2. Add a task

One YAML file in `tasks/`, copied from an existing one. It needs a readout (or several named readouts), one or more stimulus conditions, checks with an operator and threshold, a `citation` to published fly behaviour, a `tier` (`core` if the reference LIF model passes it — it becomes a regression test — `hard` if it does not — it becomes a target), and a `circuit` (`taste`, `escape`, `olfaction`, `stability`, `physiology`, `robustness`, `courtship`, `locomotion`, `optic_flow`, `grooming`, `navigation`, `reproduction`, or propose a new one) so that seven tasks on one pathway count once in the by-circuit score. **Every check needs a `basis`**: either a citation for the number, or `convention: <why this number>` when it is a judgement call. The lint refuses a task without one; a threshold nobody can trace is how a benchmark quietly becomes an opinion. A condition may carry `weight_jitter: 0.25` to run it on a perturbed copy of the connectome (every synapse count multiplied by lognormal noise) — a stand-in for a different individual — or `silence: <selector>` to zero those neurons' outgoing synapses for that condition (the in silico shibire; add `requires_capabilities: [can_silence]`). A stimulus may be a movie through a sensory front end instead of a selector: `{frontend: flyvis, stimulus: loom, t_start_ms: 200}` drives every flyvis output type present on the dataset with the pretrained model's per-column rates (`flybench/frontends/flyvis_frontend.py`; add `requires_frontends: [flyvis]`; new movies go in its `STIMULI` table and are rendered once with `flybench frontend flyvis render`, the `.npz` committed). Then:

```bash
flybench lint tasks/your_task.yaml
flybench select -c flywire783 '<your selector>'      # confirm it matches the neurons you mean
                                                     # (annotation columns, regexes, any/all_of/not, and
                                                     #  `{upstream_of: <selector>, min_synapses: 3}` on the graph)
flybench run -t tasks/your_task.yaml                 # on the toy — wire the toy if needed so CI covers it
flybench run -c flywire783 -t tasks/your_task.yaml   # on the real brain
```

Negative controls ("X should *not* happen") are the most valuable tasks; they are what stop a model from passing by firing everything.

Before opening the PR, audit it (what CI will do on FlyWire for every task a PR adds or changes,
`.github/workflows/audit-tasks.yml`):

```bash
flybench audit tasks/your_task.yaml -c flywire783 --gain 0.45 --seeds 3 --jobs 4
```

It runs the task on the reference LIF with the `rewired` control and **rejects** a task the
shuffled wiring also passes (non-diagnostic: it measures something, but not the connectome).
It **warns** on a `hard` task the reference passes on every seed with ≥ 10× margin (trivial: a
regression test, not a target — make it `core`, and only if no core task guards that pathway), and
on a tier the run contradicts (`core` is by definition what the reference passes). A task the
dataset cannot run is a warning, not a verdict.

## 3. Plug in a different model

The benchmark doesn't care how you simulate, only what fires. A simulator is any callable `Simulator(connectome, params)` returning an object with

```python
def run(self, duration_ms: float, stimuli: list[Stimulus]) -> SimResult: ...
```

(`Stimulus` has `.neurons`, `.rate_hz`, `.t_start_ms`, `.t_end_ms`, and `.rate_end_hz` for a linear ramp — honour `.rate_at(t)` if you read the rate yourself; a class attribute `capabilities = frozenset({"can_silence"})` declares that your simulator honours a connectome whose silenced neurons have no outgoing synapses — tasks that list `requires_capabilities` are skipped, not failed, for simulators that do not declare them; `SimResult` is `flybench.sim.SimResult`, spike times + neuron ids.) Put it under `submissions/<your-name>/` with a `README` and a `requirements.txt`, and run

```bash
flybench run -c flywire783 --simulator submissions.yourname.model:MySim --seeds 3 --label "yourname adaptive-LIF v1" -o results/yourname-adaptive-lif-v1.json
```

Before submitting, run the contract check:

```bash
flybench verify-adapter submissions.yourname.model:MySim
```

It runs your simulator on the toy and names every defect — wrong result types, spikes outside the run, neuron ids out of range, a seed that is ignored, a stimulus that is ignored, a ramp (`rate_end_hz`) that does not ramp, state that leaks between runs, a declared capability that does not hold — and exits 1 if there is one. The contract itself is `flybench.adapter.SimulatorAdapter` (subclassing is optional; duck-typing is fine). The report records the simulator path and its declared capabilities, so rows stay distinguishable. If a maintainer can install it, it gets verified; otherwise it is merged self-reported.

Results are only comparable on the same wiring. Every named connectome is pinned by a fingerprint in `flybench/manifests.json` (SHA-256 over ids, sparse matrix and annotations); `flybench run` refuses a connectome that does not match its pin unless `--allow-unpinned`, which marks the result `unpinned` (ranked last). `flybench fingerprint <name>` prints the value; a deliberate rebuild (new Codex export, different `min_synapses`) is a new pin, recorded with its version string.

## Ground rules

Cite the behaviour. State what you changed. Never tune per-neuron parameters to pass a task: that is fitting the test, and it defeats the point. A small set of unpublished hold-out tasks is run on notable submissions to check that a model generalises rather than memorising the public YAML; a model that passes the public tier and fails the hold-out gets a note on its row, not a removal.

## Use it as a regression test in your own CI

`flybench diff new.json baseline.json --fail-on-regression` exits 1 if the new run fails any check the
baseline passed, drops any task score (beyond `--tolerance`), or lost a task; `--format json` or
`--format markdown` for a bot comment. A lab that keeps its model's result file in its repo can run the
suite on every commit (`--jobs`) and know the moment a change breaks a reflex that used to work:

```bash
flybench run -c flywire783 --gain 0.45 --seeds 3 --jobs 6 --simulator mylab.model:Sim -o new.json
flybench diff new.json results/baseline.json --fail-on-regression --format markdown
```

## Maintainers: verifying

```bash
flybench verify results/x.json            # re-runs, compares per-task scores within 0.05
flybench verify results/x.json --mark     # same, and writes verified: true on success
```

Branch protection on the default branch should require the `ci` check and one review. The `leaderboard` workflow needs a `FLY_EXPLORER_TOKEN` secret (fine-grained PAT, contents: write on fly-explorer) to trigger the website rebuild; without it the site is updated by running `scripts/leaderboard-snapshot.py` there by hand.


## Negative controls, divisions and the hold-out gap

- Run `--controls rewired` (or `all`) before proposing a task: a positive task that the shuffled
  brain also passes is not measuring the wiring. Null tasks ("X must not fire") are expected to
  pass on shuffled wiring and are noted, not flagged. See docs/CONTROLS.md.
- Submissions declare `division: closed` (reference LIF, gain only) or `open`, and open ones must
  give `n_free_parameters` and `fit_data`. `fit_data` that names a benchmark task, the benchmark,
  or the hold-out set is rejected: fit on recordings or literature values, then evaluate.
- CI reports `gap = public − hold-out`. Nobody sees the hold-out thresholds; keep it that way.

## The maintainers' model is a submission, not the answer

The reference LIF is packaged as a model card (`flybench/models/reference_lif.py`: Shiu 2024
constants with provenance, one free parameter) and submitted through the same path as everyone
else's: `configs/submissions/reference-lif-0.45.yaml`, evaluated by `flybench evaluate`, its
result `verified` by the benchmark's CI rather than by its author. Its row is tagged
`reference_baseline` on `LEADERBOARD.md` and shows a *baseline* badge on the site. It is the
floor to beat. Nothing in the README scores the benchmark by it, and "the reference passes /
fails this" is a statement about one submission.

Every submission config may — and the maintainers' must — carry `conflict_of_interest:` (a
sentence; `none` is an answer: who wrote the model, whether they wrote tasks it targets, what
they stand to gain). It is shown on the leaderboard next to the row. Task authors do not review
submissions that target their tasks; the maintainers do not review their own.

## Graded scores and recording-match checks

Every check gets a graded score from its margin (docs/SCORING.md); nothing to do for threshold
checks. A check that compares to a published recording adds `observed: {mean, sd, n, source}`
(sd may be `unknown`), optionally `k` (pass width in z, default 2) and `ceiling` (the animal's own
rate). The lint requires `sd` and `source`. Prefer checks with a reported spread; a mean without one
falls back to the threshold rule and says so. Run with `--seeds 3` or more before proposing; the
leaderboard shows the CI, and a single-seed run shows none.

## Proposing a task: RFC first

Copy docs/rfcs/TEMPLATE.md, fill in the behaviour, the stimulus with provenance tags, the checks,
and the predictions **before** running anything, and open it with the YAML. docs/rfcs/16 is the
worked example.

## Generated files never conflict

`LEADERBOARD.md` here and `src/data/leaderboard.json` in fly-explorer are regenerated by CI after
every push. `.gitattributes` marks them `merge=generated`; enable the driver once per clone so a
rebase keeps whichever copy is already there instead of asking you to merge two generated files:

    git config merge.generated.driver true

Regenerate locally whenever you like (`flybench compare results -o LEADERBOARD.md`, `python
scripts/leaderboard-snapshot.py`); CI will overwrite with the canonical version anyway.
