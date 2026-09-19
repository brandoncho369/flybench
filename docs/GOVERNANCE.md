# Governance

How decisions about the benchmark are made, by whom, and what the benchmark does and does not
claim. ROADMAP items 45–50.

## Maintainer

Brandon Cho (Rice University) — brandon@leafrushmarketing.com, GitHub `brandoncho369`. The
maintainer merges submissions and tasks, runs `flybench verify`, and is the person to write to
when a threshold is wrong. A second maintainer is added the day a second person has merged
three task RFCs; until then every decision below is one person's and is recorded in git so it
can be argued with.

## What the benchmark claims

flybench measures whether a whole-brain simulation reproduces **these cited manipulations**: the
tasks in `tasks/` (35 at the time of writing), each a published stimulus → response with a citation, a threshold with a
`basis`, and a pre-registered RFC. It does not measure "biological realism", "how close to a
fly" a model is, or anything a task does not test. A model that tops the leaderboard reproduces
more of the listed behaviours than the others; it is not thereby more fly-like, and the README,
the site and this file say so. Anyone quoting a flybench score should quote the task list with it.

## The maintainers' model

The reference LIF is a submission with a model card (`flybench/models/reference_lif.py`), a
config in `configs/submissions/`, a declared conflict of interest, and a result evaluated by the
benchmark's own CI path. Its row is tagged `reference_baseline`. Nothing scores the benchmark by
it; "the reference passes / fails task N" is a statement about one submission (item 45).

## Conflicts of interest

Every submission config carries `conflict_of_interest:` — who wrote the model, whether they
wrote tasks it targets, what they stand to gain; `none` is an answer. It is shown on the
leaderboard. Task authors do not review submissions that target their tasks; the maintainer does
not review their own model's row (it is evaluated by CI, and the CI log is the review). Item 49.

## A task's life

1. **Proposed** — an RFC in `docs/rfcs/` from `TEMPLATE.md`: the cited experiment, the checks,
   provenance tags on every constant, and predictions for the reference LIF, the adaptive LIF,
   MaleCNS and the `rewired` control, *before* the first real-brain run.
2. **Audited** — `flybench audit` (CI, on every task a PR touches): rejected if the shuffled
   wiring also passes it; warned if trivial or mis-tiered (item 47).
3. **Active** — in `tasks/` with `status: active` (the default), run by every submission,
   scored in its tier. Tiers are defined against the reference *submission*
   (`configs/submissions/reference-lif-0.45.yaml`, FlyWire v783): `core` is what it passes on
   every seed — a regression test — and `hard` is what it fails or cannot run. A task the
   reference submission skips (a nerve-cord task on a brain-only dataset, task 34) stays `hard`
   whatever it scores elsewhere.
4. **Saturated** — every row that has run it on a connectome passes it with the same margin
   (`flybench lifecycle results/`: passing rows' mean margins within 0.3 decades, at least three
   rows). The task no longer separates models on that connectome.
5. **Retired** — the maintainer sets `status: retired` and `retired: {date, reason}` in the
   YAML. The file, its RFC and every result that ran it stay in the repo and stay citable; the
   task is skipped by `load_tasks` and leaves the tier scores; its slot is offered for a harder
   task on the same pathway (the RFC for the replacement cites the retired one).

Null tasks ("X must not fire") are **guards**, not targets: every row is expected to pass them
and they are never retired for saturation. A core task no row passes on a dataset is **broken**
there — a selector problem or a documented dataset difference (docs/MALECNS.md) — and the task
says which.

Retirement is a decision, not an algorithm: `flybench lifecycle` is the evidence, the commit
that flips `status` is the decision, and both are public.

## Changing a threshold

A threshold changes when a citation changes it. The lint refuses a check without a `basis`; a
PR that moves a number must move the basis with it, and the RFC's outcome section records the
old value and why. Thresholds are never moved to make a model pass.

## Tasks that pass everything (item 48, not yet run)

When at least three verified open-division submissions exist, a "break flybench" round: tasks
are solicited that every current passing model fails, and scored by how far they pull the mean
graded score down. Not before — with one contender the round has no meaning.

## Credit

Accepted task authors are listed in the task's YAML (`authors:`) and in CITATION.cff's
contributor list, and join the reviewer pool for later tasks (item 46's credit model; the
template and review process are in CONTRIBUTING.md).
