# Changelog

Score-affecting changes are listed with the RFC that introduced them; every archived result is rerun
when one lands, and the RFC records the before and after.

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
  hand-wired toy that proves every task can pass.
- Results: 14 runs on the full set, including the first cross-model comparison (adaptive LIF vs
  the reference; docs/FINDINGS.md 2026-09-16).
