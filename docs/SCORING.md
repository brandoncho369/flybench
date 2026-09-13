# Scoring: pass/fail, graded, ceilings, seeds

Every check produces four things: the measured **value**, a **pass** flag, a signed **margin**
(log10 distance from the threshold: +1 = ten times on the passing side), and a **graded** score in
[0, 1] that has no cliff. Task and suite scores exist in both forms; the leaderboard ranks by the
pass-based `core`/`hard` scores (unchanged) and shows `graded` with a confidence interval next
to them.

## Graded score

Two kinds of check:

**Threshold checks** (every check written before September 2026): `graded = 1 / (1 + 10^(−2·margin))`.
On the line → 0.5; 3.2× on the passing side → 0.91; 3.2× on the failing side → 0.09; ten times
either way → 0.99 / 0.01. The pass flag is the threshold comparison, as before, and always agrees
with `graded > 0.5`.

**Recording-match checks** (from Phase 2 on) carry the measurement they are compared to:

```yaml
- type: spikes_per_neuron
  cond: loom
  readout: gf
  op: "<="            # still required: the threshold rule is the fallback when sd is unknown
  value: 1
  observed: {mean: 1.0, sd: 0.2, n: 10, source: "Ache et al. 2019 Curr Biol 29:1073, Fig 2"}
  k: 2                # optional, default 2: |z| < k passes
  ceiling: 0.95       # optional: the score a perfect model of a non-deterministic fly would get
  basis: "..."
```

Then `z = (value − mean) / sd`, `graded = 1 / (1 + exp(2·(|z| − k)))` (|z| = 0 → 0.98, |z| = k → 0.5,
|z| = 2k → 0.02) and **the pass flag is |z| < k**, not the threshold. This is the SciUnit/NeuronUnit
convention. A paper that reports a mean but no spread writes `sd: unknown`; the check then scores
by the threshold rule, and the lint refuses an `observed` block without `sd` or `source`.

**Ceilings.** A real fly does not pass its own tests every time (95 % of flies take off to a loom;
Card & Dickinson 2008). A check with `ceiling: c` reports `graded / c`, capped at 1 and marked
`capped: true` when the model beat the animal — which is not a better fly, and the flag says so.
"A benchmark without a ceiling is not interpretable" (Brain-Score). Ceilings are only set where a
citation gives the animal's own rate; threshold checks have none.

## Seeds

With `--seeds N` every condition runs N times. Per check: the value on each seed is kept
(`per_seed`), the pass flag requires the seed-mean **and every seed** to pass (a reflex that works
on two of three draws is a coin flip), and the description shows `[k/N seeds, sd …]`.

Per run:

- `graded` is the **interquartile mean** over tasks of the task graded score (robust to one
  bad task; rliable, NeurIPS 2021), with `core_graded` / `hard_graded` as plain means per tier.
- `graded_ci95` is a **stratified bootstrap**: seeds are resampled within each task, the run score
  recomputed, 1000 times. `null` with a single seed — there is nothing to resample, and the
  leaderboard shows no interval rather than a fake one.
- `profile` is the fraction of checks whose margin is ≥ τ for τ ∈ {−1, −0.5, −0.25, 0, 0.25, 0.5, 1}
  decades. τ = 0 is the pass rate. Two models with the same pass rate can have very different
  profiles; that is the point of publishing the curve instead of one cut.

Defaults: 3 seeds for CI submissions, 1 for a quick local run. Twenty is the number the literature
recommends for a leaderboard row (Colas et al. 2018); use it for anything you intend to cite.

## Comparing two runs

```bash
flybench diff results/a.json results/b.json
```

pairs every check the two runs share and reports the mean graded difference A − B with its
standard error, the probability that A is better on a randomly chosen check (ties count half), a
seed-bootstrap 95 % CI on the mean difference when both runs carry per-seed values, and the twelve
checks that moved most. Paired differences strip out the shared difficulty of the checks, which is
why two suite scores should never be compared directly (Anthropic 2024, "Adding error bars to
evals"). With fifteen tasks, treat any per-task "A beats B" claim with a Benjamini–Hochberg
correction at q = 0.10 before repeating it.

## What did not change

The pass-based `score`, `core_score`, `hard_score` and the by-circuit scores are computed exactly
as before, so every published number still means what it meant. Result files written before this
change lack `graded`; `flybench rescore results/` fills them in from the stored values without
re-running anything (per-seed values are only available for runs made after the change).
