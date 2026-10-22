# Changelog

Score-affecting changes are listed with the RFC that introduced them; every archived result is rerun
when one lands, and the RFC records the before and after.

## 1.0.0 — 2026-10-22

**The task set is frozen: 37 tasks** (5 core, 32 hard), every cited basis with a Crossref-verified
DOI. Three pinned builds of FlyWire v783 are scored side by side; the reference stays the Codex
build at gain 0.45 (the sign-fixed build has no gain at which all five core reflexes pass on every
seed; RFC D1). The graph findings were prompted by Daniel Culotta (2026-10-19).

Rows and the task set: on FlyWire, the reference, the adaptive LIF, both Shiu-constant rows and
every row on the two new builds run on all 37 tasks, and previously run checks are bit-identical (138/138 on
each rerun row). Left on the 36-task set, with "–" for task 37 (rerunning them costs 10+ hours each
for the closed-loop task, and they are exploratory): the terminal LIF 0.45 and the single-seed
Codex gain sweep (0.3, 0.35, 0.4, 0.4 × 3 seeds, 0.5, 0.7). Task 37 does not apply to MaleCNS
(its ORNs have no soma side), so the MaleCNS rows were not rerun.

- **Relabel, score-affecting for one row's name only:** "Shiu 2024 (gain 1.0)" ran Shiu's constants
  on flybench's Codex ≥ 5 graph, not on the published model's graph; it is now "Shiu constants,
  gain 1.0 (Codex ≥5 graph)". README's claim that the threshold "matched Shiu et al." is corrected.
- `flybench build-shiu` and the pinned connectome `flywire783_shiu`: Shiu et al. 2024's
  `Connectivity_783.parquet` (15.09 M edges, no threshold, its own signs) on the flywire783 neurons
  (RFC D1). On it the plain LIF at gain 0.7 passes every core reflex (graded 0.764).
- `flybench build --blank-nt-from-connections` and `flywire783_ntfix`: the Codex graph with the
  19,658 blank-transmitter neurons signed from their connection rows instead of as excitatory.
- Findings recorded with this release (RFC D1, RFC 37, FINDINGS): signing the blank transmitters
  recovers ~80 % of the gap to Shiu's graph (LIF 0.7 graded 0.695 → 0.749) and part of the antennal
  lobe's channel identity (retracting part of a 2026-09-14 finding), but leaves no core window;
  the sign-fixed build is the only one that turns away from CO2 (task 37, 4/5 at 0.5–0.65).
- `meta.dataset`: another graph of the same animal keeps `dataset_only` tasks (task 30 runs on both
  new graphs).
- Task 37 (RFC 37): odour valence steering — one antenna's attractive channel must steer toward,
  an aversive one away, read on DNa02. Every real-brain row turns toward every channel.
  Not applicable on MaleCNS (its ORNs carry no soma side). Toy version `2026-10-20-valence37`.
- Citations: every task passes `lint --strict`; each cited paper carries a Crossref-verified DOI.
  Four citations were wrong or unmatched and are corrected: Ribeiro et al. 2018 is Cell 174:607
  (not Curr Biol); Olsen & Wilson 2008 is Nature 452:956; "Chen & Dahanukar 2017 (Cell Rep 18:1140)"
  (task 20) and "Chen et al. 2018 (Nat Neurosci 21:1290)" (task 28) match no paper and are removed
  (Cameron et al. 2010 carries task 20's water claim; no task-28 check cited Chen). No threshold changed.
- CITATION.cff: v0.2.1's own version DOI (10.5281/zenodo.22930641).
- GOVERNANCE: submissions with fitted parameters are ranked only with held-out seeds, the same fit
  on shuffled wiring, and size-matched random additions.

## 0.2.1 — 2026-09-24

- **Packaging fix:** `pip install flybench` shipped no tasks and no sensory-front-end caches, so
  `flybench run -c toy` — the README's first command — scored zero tasks on a clean install. The
  wheel now carries both (`flybench/_bundled/`), and the paths prefer a checkout's copy. Verified
  in a fresh virtualenv: 30 tasks scored on the toy, 6 skipped with stated reasons.
- CI: the toy's skip test no longer assumed the optional closed-loop stack was installed.
- Colab notebook: task and neuron counts refreshed.

## 0.2.0 — 2026-09-21

**36 tasks** (5 core, 31 hard); 15 result rows all on this task set; the embodied track; two
mechanisms earned by the "task before mechanism" rule; governance.

- Sensory front end (RFC 32): `flybench.frontends.flyvis_frontend` renders a movie through the
  pretrained flyvis optic-lobe model and drives the connectome's own T4/T5/T2/T3/Tm/TmY cells
  column by column; outputs cached in `data/frontends/flyvis/` so runs need neither torch nor
  flyvis. Finding: through a real eye the reference giant fiber fires at a flash, not a loom.
- Embodied track (RFCs 33–36, ROADMAP item 51): a task's `body:` block hands a readout's spikes
  (TTMn, or the GF + 0.93 ms) to NeuroMechFly in FlyGym/MuJoCo; takeoff is a physics event.
  Task 36 closes the loop — the body's own retinas, through flyvis frame by frame, are the
  brain's input, and the jump moves the eyes. Findings: the loom's GF-free route to the jump
  muscle on MaleCNS (nine descending types onto the GF-coupled interneurons), the flash's route
  being the GF itself, and the closed-loop fly jumping before contact and at a near miss alike.
- Mechanism M1/M1b, the terminal-aware LIF: axo-axonic inputs kept off the soma (neuPrint ROI
  counts for the neck-spanning classes; neuropil polarity θ 0.8 for every neuron on both
  datasets; `flybench fetch-terminals`). No free parameters. FlyWire graded 0.655 → 0.711,
  MaleCNS core 0.57 → 0.90, the mushroom body sparse on both brains, shuffled controls unchanged;
  it thins the GF-free loom route (task 35 3/10 against M1's 10/10). Task 35's failed check is
  what earned it: ascending neurons firing backwards in a point-neuron CNS.
- Governance (items 45, 47, 49, 50): the reference LIF is a model card submitted through
  `flybench evaluate` and tagged `reference_baseline`; `flybench audit` rejects tasks the shuffle
  passes (CI on every task a PR touches); `conflict_of_interest` on every row; docs/GOVERNANCE.md
  with the scope claim ("these cited manipulations"), a named maintainer and the task lifecycle
  (`status: retired`, `flybench lifecycle`).
- Also: per-check control records (`controls.<name>.checks`), `flybench evaluate --jobs`,
  `flybench verify` for every built-in simulator, CI on Python 3.12 with the embodied extra.

## 0.1.0 — 2026-09-16

The first tagged task set: **31 tasks** (5 core, 26 hard), every one pre-registered as an RFC
(`docs/rfcs/`) with predictions written before its first run and its outcome recorded.

- Scoring: graded margins, seeds with stratified-bootstrap CIs, performance profiles, the S1
  ceiling gate and the S2 response floor on comparison checks, shuffled-wiring controls
  (`rewired`, `random`, `signflip`) and per-task specificity, circuit-weighted tier scores.
- Task machinery: named readouts, `matrix` checks, `dataset_only`, `requires_readouts` /
  `requires_stimuli` / `requires_capabilities`, condition-level `silence:` and `weight_jitter:`,
  ramp stimuli (`rate_end_hz`), the `upstream_of` graph selector, `rank_order`,
  `recruitment_spread`, `population_sparseness`, `latency` and `bump` metrics, `over_readout`
  ratios, `expected_fail` tasks, a provenance rule on every `basis`.
- Reproducibility: `--jobs N` (bit-identical), pinned connectome fingerprints
  (`flybench/manifests.json`, `flybench fingerprint`, `--allow-unpinned`), the adapter contract
  (`flybench.adapter`, `flybench verify-adapter`), the cost column, `reproduce.ps1` /
  `Makefile`, `Dockerfile`, `CITATION.cff`.
- Datasets: FlyWire v783 (female brain) and MaleCNS v1.0 (male brain + nerve cord), plus the
  hand-wired toy on which every circuit-level task can pass (the tasks that need dynamics a
  uniform LIF lacks — dose response, adaptation, one spike per loom — fail on it too, by design).
- Results: 14 runs on the full set, including the first cross-model comparison (adaptive LIF vs
  the reference; docs/FINDINGS.md 2026-09-16).
