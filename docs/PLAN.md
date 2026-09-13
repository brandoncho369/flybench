# flybench delivery plan

Phases for working through docs/ROADMAP.md, with the edge cases and tests each one owes before it
is called done. Item numbers refer to ROADMAP.md. Each phase ends with a tagged release, a
regenerated leaderboard, and the explorer snapshot updated; nothing merges without its tests.

Conventions used throughout:

- **Definition of done** for any task YAML: passes `flybench lint`; every check has `basis:` with a
  DOI/citation or `convention:`; every constant has a provenance tag (item 41); the toy connectome
  has a synthetic circuit for it so unit tests run in seconds; a shuffled-connectome result is
  recorded (item 8); README task table and CONTRIBUTING updated; snapshot regenerated in fly-explorer.
- **Definition of done** for any scoring change: old and new numbers for every archived result are
  published side by side; `tests/test_validity.py` recomputes the score by hand from the raw JSON.
- **Three test layers**: unit (`pytest`, toy connectome, < 60 s), integration (real FlyWire/MaleCNS,
  nightly or on demand, marked `@pytest.mark.slow`), and end-to-end (explorer Playwright smoke
  against the built site; `scripts/smoke.mjs`).
- **QA checklist per release**: `make reproduce` regenerates every README number; `flybench compare`
  between the previous and new leaderboard shows only intended changes; explorer `npm test` and
  smoke pass; a fresh `pip install flybench && flybench toy && flybench run -c toy` works on a clean
  machine (CI job on Windows + Linux).

---

## Phase 0 — Corrections and the trust floor (items 1–9)

Fix what is wrong, then add the two numbers that make every later score interpretable.

**Deliverables**
- Male sugar set `^LB3[bc]$`, water set `^LB3a$`, bitter unchanged, LB3d moved to a `high_salt` set,
  LB1e to `amino_acid`; MALECNS.md updated; MaleCNS rerun (Brandon's machine).
- Task 13: GF ceiling = 1 spike per loom (Ache 2019); MN9 rate check relabelled `convention:`;
  sugar stimulus rate cites Zhang 2016 (80 Hz) and dose-response sweeps 80/100 Hz.
- Task 3 description notes the peripheral component of bitter suppression (French 2015).
- `flybench.controls`: `rewire_degree_preserving(c, seed)`, `erdos_renyi_matched(c, seed)`,
  `shuffle_signs(c, seed)`. Each run records `controls: {shuffled: score}`; report gains a
  `specificity` per task and a `non_diagnostic` flag when the shuffle passes.
- Hold-out: `public_score`, `holdout_score`, `gap` in the report and leaderboard; hold-out
  evaluation moved to a small endpoint (Vercel function or GitHub App) with a per-lineage cap.
- `n_free_parameters` and `fit_data` required in the submission schema; `division: closed|open`.

**Edge cases to handle**
- A dataset lacking one of the new sets (FlyWire has no LB names): selectors resolve via the
  existing female fallbacks; high-salt/amino-acid sets are `requires_readouts` on FlyWire.
- Rewiring must preserve the *signed* out-degree per neuron and total synapse count; must not
  create self-loops; must be seeded and reproducible; on a 6.3 M-edge matrix must run in < 2 min.
- Erdős–Rényi on 176k nodes: generate sparsely (sample edges, not an n×n matrix).
- Shuffled runs can be slower (denser hubs); cap simulated time equal to the real run.
- Hold-out gap when a task is skipped on a dataset: gap computed over tasks present in both sets.
- Two submissions with the same model lineage but different gains count against one cap.
- `fit_data` referencing a benchmark task by name → submission rejected with an explicit message
  (you fitted on the test).

**Tests**
- `test_controls.py`: degree preservation, sign preservation, synapse-count preservation, seed
  reproducibility, no self-loops, runtime bound on the toy; a task whose circuit is preserved by the
  toy's structure passes real and fails shuffled (build the toy so sugar→MN9 breaks under rewiring).
- `test_holdout.py`: gap arithmetic on synthetic reports; skipped-task handling; cap enforcement.
- `test_schema.py`: submission without `n_free_parameters` fails validation; `fit_data` naming a
  task is rejected.
- Integration: MaleCNS 0.65 rerun with new sets; assert sugar (LB3b/c) still reaches MN9, water
  reaches MN9, high-salt does not.

**QA**: leaderboard before/after diff shows only MaleCNS rows changing; README "How good is the
ruler" section gains specificity and gap; explorer trust line reads the new fields.

---

## Phase 1 — Graded scoring and statistics (items 31–36)

Do this before adding tasks, so every new task is written against the final scoring rules.

**Deliverables**
- Check schema gains `observed: {mean, sd, n, source}`; `score = sigmoid(-|z|)` style graded score
  in [0,1]; `pass = |z| < k` (k in the check, default 2, `convention:`); `sd: unknown` → ratio score.
- `ceiling:` per check (real-fly pass rate or repeat-trial reliability); report `score/ceiling`.
- `--seeds` default 20 for leaderboard rows; IQM + stratified bootstrap 95% CI per task and suite;
  clustered SE by task; all-seeds strict flag retained as `strict_pass`.
- `flybench compare` computes paired per-check differences and probability of improvement; BH-FDR
  q=0.10 on "A beats B on task X" claims.
- Performance profile (pass fraction vs margin threshold) emitted as JSON and drawn on /bench.
- Raw per-seed, per-check JSON is the canonical result; summary derived from it.

**Edge cases**
- z undefined when sd = 0 or observed n = 1 → fall back to ratio score and warn in lint.
- Ceiling < model score (model "better than the fly") → cap score/ceiling at 1 and flag; a
  probabilistic behaviour (looming escape) passing 100 % is not a better fly.
- Bootstrap with 3 seeds → CI is honest but wide; do not hide it; leaderboard sorts by lower CI bound.
- NaN measurements (readout absent on one seed) → excluded with a count, never treated as 0.
- Old results without per-seed data → re-scored with `legacy: true`, shown but not ranked.

**Tests**
- `test_scoring.py`: z/sigmoid monotonic, symmetric, pass flag matches |z|<k; sd unknown path;
  ceiling capping; hand-computed IQM and CI on a fixed synthetic array; clustered SE > naive SE on a
  correlated fixture; BH-FDR on a known p-value set; paired diff equals mean of per-check diffs.
- Property test (hypothesis): score ∈ [0,1] for any finite input; seed order invariance.
- Snapshot test: re-scoring every file in `results/` produces numbers within tolerance of the
  published legacy scores where the check was pass/fail-only.

**QA**: `make reproduce` regenerates LEADERBOARD.md; every row shows CI; explorer bench page renders
CI bars and the profile; `bench.test.ts` updated to the new snapshot schema.

---

## Phase 2 — Recording-match tasks (items 10–18)

Tasks 16–24 in the numbering. Each needs a measured mean and, ideally, spread; each needs a toy
circuit; each needs a shuffle result.

**Deliverables (in order)**
1. `16_gf_single_spike.yaml` — one spike per loom; azimuth invariance (three loom positions;
   DSI < 0.5). Requires stimulus geometry in `stim.py`: loom at azimuth −45/0/+45 mapped to
   LPLC2/LC4 subsets by receptive field (approximate by hemisphere + dorsal/ventral; label INFERRED).
2. `17_pn_rate_ceiling.yaml` — uniglomerular PN peak ≤ 170 Hz; transfer-function fit against
   Olsen 2010 (σ, exponent) as a graded check.
3. `18_da1_sparseness.yaml` — lifetime sparseness ≥ 0.90 across an odour panel of ≥ 8 glomeruli.
4. `19_da1_adaptation_by_type.yaml` — lvPN no adaptation, lPN adaptation over 10 s.
5. `20_gf_flicker.yaml` — response at 0.5 Hz with adaptation; none at 10 Hz.
6. `21_gf_to_muscle_latency.yaml` — TTM 0.93 ms / DLM 1.44 ms; requires adapter capability
   `min_dt ≤ 0.1 ms` (skip otherwise, via `requires_capabilities`).
7. `22_resting_state_fc.yaml` — region-level correlation vs Turner 2021 figshare data (downloaded
   and checksummed by `flybench fetch-observations`); r ≥ 0.74 graded with CC_norm.
8. `23_escape_timing.yaml` — takeoff latency envelope; MaleCNS only.
9. `24_silencing_phenotypes.yaml` — 10/11 MN9 activators and 5/6 water-pathway silencings from
   Shiu 2024; requires adapter capability `can_silence`.

**Edge cases**
- Sub-ms latency tasks on a 0.1 ms default dt: dt must be a task-level override, adapter must
  declare support; refractory (2 ms) and synaptic delay conventions must be explicit or latencies
  are meaningless — record `synaptic_delay_ms` as a convention with basis.
- Sparseness with silent PNs (0 Hz everywhere) is undefined → task fails with reason, not NaN pass.
- Resting-state task depends on an external dataset: checksum, licence note, offline cache, and a
  skip (not fail) when absent.
- Region mapping FlyWire neuropil ↔ hemibrain ROI is INFERRED; publish the mapping table.
- Odour panel: the model has no receptor model, so "odour" = a set of ORN types at 100 Hz; document
  as a convention and keep the panel fixed and versioned.
- Silencing = zeroing outgoing weights of a type, not removing the neuron; document.

**Tests**
- Toy circuits for each (a GF that fires once, a PN saturating, a two-glomerulus panel, a
  silence-able activator); each task passes on the intended toy and fails on a deliberately broken
  toy variant (`toy --broken gf_burst`).
- Metric unit tests: lifetime sparseness on known vectors (Willmore & Tolhurst formula), DSI on
  synthetic tuning, CC_norm on synthetic repeats, latency from spike trains with jitter.
- Integration: FlyWire 0.45 and MaleCNS 0.65 results recorded; expected: GF single-spike fails on
  plain LIF (129 spikes), passes on adaptive LIF? — record the prediction in the task RFC *before*
  running (item 46), then the result.

**QA**: each task page on /bench shows the observed value with citation next to the model value.

---

## Phase 3 — New behavioural tasks (items 19–30)

Order: 19 taste modality family → 20 LC→DN matrix → 21 courtship (MaleCNS-only) → 23 leg MN size
principle → 22 optic-flow → 24 grooming → 25 MB/APL → 26 CO2 → 27 steering → 28 ring attractor
(expected-fail) → 29 egg-laying (FlyWire-only) → 30 halt.

**Deliverables**: one YAML each, each first as an RFC issue with the pre-registered prediction; a
`matrix` task type for 20 (conditions × readouts with an expected sign grid); `dataset_only:` field
for 21 and 29 (task must be skipped on the other dataset and the skip shown as "not applicable").

**Edge cases**
- Type names verified against `flybench select` on both datasets before the YAML exists; a name
  that matches 0 neurons is a lint error, not a silent empty stimulus (already the case; extend to
  matrix cells).
- Courtship: P1 drive must not leak to leg MNs; laterality check needs a side field on MNs (MaleCNS
  has `somaSide`; FlyWire hemisphere from x coordinate — INFERRED).
- Size principle: MN "size" = total input synapses or soma volume? Use input synapse count
  (Azevedo used both); label convention; require ≥ 10 MNs per leg for a rank correlation.
- APL removal is a silencing operation → shares the `can_silence` capability.
- Ring attractor: the pass criterion (one bump, FWHM ~90°) needs a bump detector; test the detector
  on synthetic bumps; the task is shipped `expected_fail: true` with reason, and a pass would be
  flagged for review rather than celebrated.

**Tests**: as Phase 2 (toy circuit + broken toy per task; matrix task tests every cell sign).
Integration on both datasets, with the "dataset_only" tasks asserted skipped on the wrong one.

---

## Phase 4 — Reproducibility and packaging (items 37–44)

**Deliverables**: artefact manifest `(id, version, sha256)` in `connectome.py`, stamped into every
result; `CITATION.cff` + Zenodo DOI on the next tag; Dockerfile + `make reproduce`; adapter ABC with
capabilities and `flybench verify-adapter`; `flybench-adapter-template` repo with Brian2 and PyTorch
examples; parquet spike schema; provenance tags in lint; versioning policy in README; cost column
(wall-clock, peak RSS, sim-s per bio-s, n_free_parameters); flyvis adapter first.

**Edge cases**
- Codex re-exports change bytes without a version bump: mismatch is an error with a
  `--allow-unpinned` escape that marks the result `unpinned: true` and un-rankable.
- Windows: Docker optional; `make reproduce` must have a PowerShell equivalent (`reproduce.ps1`).
- Adapter that returns spikes for a subset of neurons: allowed if it declares `partial_readout`;
  tasks needing absent neurons skip.
- Peak-RSS measurement differs across OS; record method.
- Adapter timeouts: a run that exceeds N× the reference wall-clock is aborted and reported, not hung.

**Tests**: manifest mismatch test; `verify-adapter` against a deliberately non-conformant adapter
(wrong shapes, missing method, non-deterministic under a fixed seed) reports each defect by name;
reproduce script compared to committed README numbers in CI (tolerance for floating point); flyvis
adapter smoke on its toy config; Windows + Linux install matrix in CI.

---

## Phase 5 — Governance (items 45–50)

**Deliverables**: `flybench-reference-lif` split out and submitted as `reference_baseline`; task RFC
issue template; two-reviewer rule in CONTRIBUTING and a CODEOWNERS that prevents the maintainer
from merging own task PRs without a second approval; conflict-of-interest field; lifecycle policy;
"break flybench" round announced once ≥ 3 external models are on the board.

**Edge cases**: a task RFC with no shuffle result → bot comment asks for it; a task the reference
model already passes with margin > 10× and the shuffle also passes → auto-labelled non-diagnostic.

**Tests**: CI job that lints RFC issue bodies for the required fields; PR check that refuses task
YAMLs missing `prediction:` and `shuffle_result:`.

---

## Phase 6 — Explorer and adoption (items 52–60)

**Deliverables**: Colab notebooks (toy / FlyWire / MaleCNS) tested in CI with `nbconvert --execute`
on the toy one; permalinks (`?dataset&gain&stim&dur&seed&readouts`) with a "cite this" button;
trace/raster download (worker `dump` command → CSV/PNG); synonym table `synonyms.json` shipped
with the export (GF/DNp01/giant fiber, EPG/E-PG, TTM/TTMn, MN9/CB0701...); per-type links to
Codex/neuPrint/VFB/Neuroglancer; `compare` outputs (JSON/markdown/SVG, `--fail-on-regression`);
classroom bundle (three exercises + answer key); "what this model cannot do" page; task linter for
`basis:` DOI.

**Edge cases**
- Permalink with a type absent in the chosen dataset → banner "not in this dataset", no silent toy
  fallback (the malecns 404 bug is the precedent).
- Permalink length: cap stimulus list; encode readouts as ids, not names.
- Trace download on 139k neurons → limit to selected populations + top-N by rate, with a size warning.
- Neuroglancer links require segment ids: FlyWire root ids are in the export; MaleCNS body ids
  differ; generate per dataset and hide the link when unknown.
- Synonyms colliding across datasets (`GF` type exists only in MaleCNS; FlyWire's is `DNp01`) → alias
  resolves per dataset and search shows which name is native.
- Colab RAM: FlyWire full run needs > 12 GB; the FlyWire notebook uses the reduced (≥ 10 syn)
  matrix and says so.

**Tests**: Playwright: permalink round-trip (load → state → URL → reload → same state), absent-type
banner, download produces a non-empty CSV with expected columns, synonym search returns the native
name, external links have correct ids for two known neurons; vitest for URL codec and synonym
resolution; `nbconvert` on the toy notebook in CI.

---

## Phase 7 — Closed-loop track (item 51) — only after Phases 0–3

FlyGym/NeuroMechFly first (Gymnasium API, Apache-2.0). Score: loom → takeoff within the Card &
Dickinson envelope; sugar contact → proboscis extension; and *every* closed-loop task run with the
shuffled connectome in the same release. Edge cases: body controller doing the work (Eon's own
caveat) → report the shuffled score next to the real one; simulation dt mismatch between brain and
body → resample with a declared policy; non-determinism in the physics engine → seeds recorded,
pass fraction reported. Tests: sphinx control (a random RNN of matched size must score below the
real connectome or the task is non-diagnostic).

---

## Cross-cutting evals and Q/A

- **Golden results**: `results/golden/` holds FlyWire 0.45, Shiu 1.0, Adaptive 1.0, MaleCNS 0.65
  raw JSON; CI re-runs the toy suite on every push and the FlyWire core tier weekly, diffing
  against golden with tolerance; any drift opens an issue.
- **Mutation tests for tasks**: for each task, an automated "break the toy" variant (drop the key
  edge, flip a sign, double a weight) must make the task fail — a task that survives all mutations
  is non-diagnostic and lint says so.
- **Determinism**: same seed → bit-identical spikes on the same platform (test); cross-platform
  (Windows/Linux, numpy versions) → rate-level agreement within 1 % (nightly).
- **Docs tests**: every number in README that appears in a results JSON is generated by
  `make reproduce`, not typed; a doc-test greps for stale values.
- **Schema versioning**: result JSON carries `schema_version`; the explorer refuses newer schemas
  with a clear message rather than rendering garbage.
- **Security/abuse on the leaderboard**: PR-based submissions run in CI with no secrets; hold-out
  endpoint rate-limited per GitHub identity; result files size-capped; YAML loaded with `safe_load` only.
- **Accessibility/UX smoke**: explorer at 400 px width; keyboard access to fire/hold; guide text
  never overlaps controls (the popover complaint).
- **Release checklist** (`docs/RELEASE.md`): tests green on both OSes; reproduce diff clean;
  leaderboard regenerated; snapshot regenerated and `npm test` green; CHANGELOG entry with
  score-affecting changes listed; tag; Zenodo DOI minted; explorer deployed; smoke against production.

## Suggested cadence

Phase 0 this week (it fixes wrong things). Phase 1 next, because it changes what every later task
looks like. Phases 2 and 3 interleave one task at a time, each as an RFC first. Phase 4 alongside,
since the adapter ABC is what external submitters need. Phase 5 once there is a second external
model. Phase 6 continuously, driven by what the analytics show people doing. Phase 7 last.
