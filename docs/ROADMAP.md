# flybench roadmap

What would make the ruler better, in priority order. Compiled September 2026 from a survey of
how comparable benchmarks (Brain-Score, NeuroBench, SciUnit/NeuronUnit, Neural Latents,
Sensorium, BIG-bench, MLPerf) are built, of how connectome-constrained fly models validated
themselves 2024–2026, and of the physiology literature for the cells our tasks read out.
Sources are cited per item; "convention" marks a choice that is ours.

The rule that governs everything below has not changed: a task is written before any model
mechanism, every threshold carries a citation or is labelled a convention, every mechanism is a
documented one with literature constants applied uniformly, and nothing is tuned to the tasks.

---

## 0. Fixes owed now (wrong or unsupported things currently in the repo)

1. **Drop LB3d from the male sugar set.** The MaleCNS gustatory paper (Cell 2026, bioRxiv
   10.1101/2025.08.25.671814) classifies LB3d as high-salt, aversive (Ir7c/ppk23), not sugar.
   LB3a is water (ppk28), LB3b sweet (Gr64f), LB3c sweet + low salt (Ir56b). Sugar set → `^LB3[bc]$`;
   LB3a becomes the water set. Re-run MaleCNS after.
2. **LB1e is not bitter.** It is glutamatergic, mediates mild aversion to amino acids. Bitter stays
   `^LB1[a-d]$`. Update docs/MALECNS.md (the "to verify" paragraph) accordingly.
3. **State that no MN9 electrophysiology exists.** Every MN9 rate in circulation (Shiu 2024's
   ">80 Hz", our "<150 Hz" ceiling) is a model number. Mark the task-13 MN9 check `convention:`
   and say so in README; anchor MN9 checks to behaviour (PER) rather than a rate wherever possible.
4. **Sugar GRN input rate.** Recorded: ~40 spikes/500 ms ≈ 80 Hz at 100 mM sucrose (Zhang, Guo &
   Montell 2016 Neuron 91:863). Shiu drives at 100 Hz. Make the stimulus rate cite this and sweep
   80/100 Hz in the dose-response task rather than treating 100 Hz as given.
5. **Giant fiber: one spike per loom**, not "1–4" (Ache et al. 2019 Curr Biol; von Reyn 2014 Nat
   Neurosci: "a single spike in the GF determines short vs long takeoff"). Tighten task 13's
   ceiling to 1 with the citation; keep the 1–4 band only as a labelled tolerance.
6. **Bitter suppression is partly peripheral.** Bitter inhibits sugar transduction inside the
   sensillum, in addition to the central pathway (French et al. 2015 J Neurosci 35:3990). A
   connectome-only model cannot reproduce that component; say so in task 3's description so a
   partial pass is interpreted correctly.

## 1. Hold-out gap and negative controls (the two numbers that make scores believable)

7. **Report `public_score`, `holdout_score`, `gap`** as leaderboard columns. A searched-parameter
   model (the kind now being built) is only trustworthy if the gap is small. Neural Latents keeps
   test labels server-side "to prevent hyperparameter hacking" (NeurIPS D&B 2021). Move hold-out
   scoring off a CI secret (readable on forks) to a rate-limited endpoint, and cap hold-out
   evaluations per model lineage (Algonauts 2025: max 10 in the final phase).
8. **Shuffled-connectome floor on every run.** Degree-preserving rewiring, Erdős–Rényi with matched
   node/edge counts, and sign-shuffled transmitters. Report `specificity = score(real) − score(shuffled)`
   per task and demote any task the shuffle also passes. Reason: a *C. elegans* connectome wired to
   a fly body produced realistic walking ("digital sphinx", bioRxiv 2026.03.20.713233), so
   behavioural success without a wiring control proves nothing. FlyGM (arXiv 2602.17997) already
   runs exactly these baselines.
9. **Declare `n_free_parameters` and `fit_data`** on every submission, and split the leaderboard into a
   *closed* division (reference LIF dynamics, only the global gain may be fitted) and an *open*
   division (any dynamics, any fitting, disclosed). Ranking a one-parameter model against a
   400-parameter fit in one column is a category error (MLPerf closed/open; Beiran & Litwin-Kumar
   2025 Nat Neurosci on identifiability).

## 2. Recording-match tasks (the biggest scientific hole)

Every current task is behavioural. These compare the model to a measured neuron. Rule: no
recording task without a published number and, for graded tasks, a reported spread.

10. **GF spike count and azimuth invariance**: exactly one GF spike per loom at r/v ∈ {14, 40, 70 ms};
    no directional selectivity across −45°/0°/+45° (DSI < 0.5). Ache 2019; J Exp Biol 2023 226:jeb244790.
11. **GF → TTMn / DLMn latency**: TTM 0.93 ms, DLM 1.44 ms in young flies; DLM lags TTM by ~0.5 ms;
    a ≥3.0 ms DLM response is the non-GF path (Augustin et al. 2019 eNeuro, code on ModelDB 245415;
    Engel & Wu 1996). Requires a sub-ms timestep option in the simulator adapter.
12. **Antennal-lobe PN rate ceiling and transfer**: uniglomerular PN peak ≤ 163–170 spikes/s;
    ORN→PN follows PN = Rmax·ORN^1.5/(ORN^1.5 + σ^1.5), σ = 11.8–16.3 spikes/s (Olsen, Bhandawat &
    Wilson 2010 Neuron 66:287). Replaces our convention-based olfactory ceiling with a measured one.
13. **DA1 lifetime sparseness ≥ 0.90** across an odour panel (Schlief & Wilson 2007 Nat Neurosci
    10:623). A measured number for the sparse-coding task we already have.
14. **DA1 adaptation is cell-type specific**: over a 10 s odour, DA1 lvPN output must not adapt,
    DA1 lPN output must (Taisz et al. 2023 Cell 186:2556). Rewrites task 7 with a sign.
    **Blocked (2026-09-14):** FlyWire v783 types DA1 PNs as `DA1_lPN` / `DA1_vPN` only; no `lvPN`
    type to contrast. Check MaleCNS typing; otherwise needs a root-id list from the paper.
15. **GF flicker ceiling**: adapts after the first cycle at 0.5 Hz, no detectable response at 10 Hz
    (Mu et al. 2014 J Exp Biol 217:2121). A habituation task with a measured constant.
16. **Whole-brain resting-state agreement**: region-level correlation matrix from the simulation vs
    measured resting-state functional connectivity, r ≥ 0.74 across 37 regions (Turner, Mann &
    Clandinin 2021 Curr Biol; data public, figshare 10.6084/m9.figshare.13349282). Wang et al. 2026
    Nat Commun already scores a FlyWire SNN against this dataset, so the metric exists off the shelf.
17. **Escape motor timing envelope**: takeoff ~191 ms after loom onset when the object subtends
    30–40°; GF-mode wing→leg interval ~1 ms vs ~35 ms voluntary (Card & Dickinson 2008 J Exp Biol).
    Needs task 15's VNC readouts plus timing.
18. **Knockout-phenotype family**: silence cell type X in silico and compare to published silencing
    phenotypes. Shiu 2024 validated 10/11 predicted MN9 activators and 5/6 water-pathway
    silencings; those are ready-made, cited, and hard to pass with a global gain.

Missing numbers to chase offline (both behind PMC captchas): Bhandawat et al. 2007 (PN spontaneous
rates, latencies) and Weiss et al. 2011 (500 ms spike-count atlas for all 31 labellar sensilla).
Not found anywhere: sugar-GRN within-stimulus adaptation constant; LC4/LPLC2 tuning curves as
numbers (figure-only in Ache 2019 / Klapoetke 2017).

## 3. New behavioural tasks (ranked by feasibility × value)

19. **Taste modality family on MN9**: water (LB3a) → PER; amino-acid (LB1e) and high-salt (LB3d)
    → MN9 suppressed. Same machinery as tasks 2–3, three new modalities, names from the Cell 2026
    gustatory paper (Cameron 2010 for ppk28/water). **Started 2026-09-14: task 20 covers water and
    high salt (docs/rfcs/20); amino acids (LB1e) wait for a behavioural citation with a number.**
20. **LC → DN action matrix**: LC4/LC6/LPLC1/LPLC2 → takeoff DNs; LC16 → MDN (backward walking),
    never TTMn; LC10 → not escape (Wu et al. 2016 eLife 5:e21022; Sen 2017; Dombrovski 2023; Morimoto et al. 2020 eLife 9:e57685). One matrix
    task; off-diagonal leaks are the signal. **Started 2026-09-14: task 21 (docs/rfcs/21), `matrix`
    check type in bench.py; LC6/LPLC1 → DN cells unscored until a DN target is published.**
21. **Courtship command chain, MaleCNS-only**: P1/pC1 → pIP10 → wing MNs (hg1–4, ps1, b1, i1)
    within ≤5 synapses, unilateral, no leg MNs; the same drive must fail on FlyWire because the
    dimorphic types are absent (Cell 2026 sexual-dimorphism paper; von Philipsborn 2011). Score
    reachability, laterality and MN class, never song rhythm. This is the first task that can pass
    on one dataset and must fail on the other. **Started 2026-09-14: task 22 (docs/rfcs/22), `dataset_only:`
    field; P1 = pC1 ∩ pMP-e lineage (86 cells); scores reachability, MN class, either-wing symmetry, and a
    leg-MN null — never rhythm.**
22. **Optic-flow rotation vs translation**: HS/H2/VS → DNp15/bIPS; DNp15 discriminates rotation from
    translation better than HS (Nat Neurosci 2025, s41593-025-01948-9).
23. **Leg MN recruitment order** (size principle): premotor → MN weight scales with MN size; ramping
    drive recruits in size order; wing steering MNs show no such order (Azevedo et al. 2024 Nature).
    Pure VNC graph + LIF; MaleCNS only. **Started 2026-09-15: task 23 (docs/rfcs/23), `rank_order` and
    `recruitment_spread` checks, `rate_end_hz` ramp stimuli, `upstream_of` graph selector; front-left leg
    (57 MNs), excitatory central premotor pool (664 cells). Wing not scored: pooled drive scales with size
    in the wing too (per-preMN it does not — a finding, docs/FINDINGS.md). Pre-registered as an
    expected fail for any uniform point model, per Lesser 2024's own inference.**
24. **Grooming somatotopy**: bristle MNs (BM-Ant, BM-InOm, …) → hemilineage 23b / aBN1/2 / aDN;
    eye-bristle drive must not produce antennal-grooming output (Eichler/Seeds 2025 eLife 108044;
    Hampel 2015, 2020).
25. **Mushroom body sparseness with APL**: KC responses sparse and decorrelated; removing APL
    lowers sparseness and raises inter-odour correlation (Lin et al. 2014 Nat Neurosci). Threshold
    as a relative change; the absolute KC fraction is figure-only.
26. **CO2 pathway specificity**: ORNv → PNv_bi → LH^PD5c1^; PNm1 is CO2-only, so DA1/DM1 drive must
    not activate it (bioRxiv 2026.01.05.697655; Suh 2004; Lin 2013). Names are hemibrain-style;
    needs a FlyWire mapping pass.
27. **Steering gain DNa02 vs DNa01**: DNa02 has more direct MN connections; equal drive should give
    shorter MN latency and steeper MN-rate slope (Rayshubskiy et al. 2025 eLife 102230).
28. **EPG ring attractor — expected-fail tier**: one bump, FWHM ≈ 90°, persists in darkness; two
    drives → one winner (Kim et al. 2017 Science; Turner-Evans 2017 eLife). A uniform-parameter LIF
    should fail; ship it labelled as such. Eon Systems concede they never validated this.
29. **Egg-laying oviDN pathway, FlyWire-only** (Wang et al. 2020 Nature) — the female twin of 21.
30. **Descending halt (Foxglove/Bluebell inhibit oDN1/P9)** (Sapkal et al. 2024 Nature) — types
    were found by screen, VNC targets unnamed; medium-high difficulty.

Blocked on annotation (do not build yet): thermosensory input types, ocellar types, adult MDN
premotor names. Out of scope with reasons documented: sleep (dFB role contested, minutes-scale,
neuromodulatory), circadian (24 h), song rhythm (needs dynamics a static LIF lacks).

## 4. Scoring statistics

31. **Graded scores**: per check, z = (model − observed mean)/observed SD mapped through a sigmoid
    to [0, 1], `pass = |z| < k` kept as a derived flag; checks whose observation has no SD declare
    `sd: unknown` and get a ratio score (SciUnit/NeuronUnit). Kills the threshold cliff.
32. **Ceilings**: every check gets one (the real fly's own trial-to-trial pass rate, or repeat-trial
    reliability for recordings, CC_norm per Schoppe et al. 2016); report score/ceiling. "A
    benchmark without a ceiling is not interpretable" (Brain-Score).
33. **Seeds**: default 20 for leaderboard rows; report IQM with stratified bootstrap 95% CI and
    task-clustered SEs; compare two models by paired per-check differences and probability of
    improvement (rliable, NeurIPS 2021; Colas et al. 2018; Anthropic eval-statistics 2024 found
    clustered SEs up to 3× naive). Keep the all-seeds strict flag.
34. **Performance profile**: fraction of checks passing as a function of the margin threshold,
    published per run, so the whole curve is visible rather than one cut.
35. **Multiple comparisons**: Benjamini–Hochberg at q = 0.10 across tasks for any "A beats B on X"
    claim; say so in README.
36. **Ship raw per-seed, per-check JSON** with every leaderboard entry.

## 5. Reproducibility and packaging

37. Pin every connectome artefact by `(id, version, sha256)`, fail loudly on mismatch, stamp it into
    every result JSON (the v783 synapse re-prediction halving the working gain is the argument).
38. `CITATION.cff` + Zenodo DOI per release; JOSS paper once the task set is v1.0 and six months public.
39. Docker image + `make reproduce` that regenerates every number in README and LEADERBOARD.
40. Adapter as a documented ABC with capability declarations (`can_silence`, `can_report_spike_times`,
    `is_closed_loop`, `min_dt`) and `flybench verify-adapter` conformance test; template repo with
    ~40-line stub; worked Brian2 and PyTorch adapters. Adopt the `time_ms, trial, neuron_index,
    flywire_id` parquet spike schema from eonsystemspbc/fly-brain (six backends share it).
41. Provenance vocabulary on every YAML constant: MEASURED / INFERRED / MODELED / CONVENTION
    (after JayceeB1/flybox). Our male taste labels are INFERRED-then-CONFIRMED; say which.
42. Versioning policy in the README: task set v1.0 frozen; additions in minor versions;
    score-changing edits force a major bump and re-score every archived submission.
43. Cost column on the leaderboard: wall-clock, peak RAM, sim-seconds per bio-second,
    n_free_parameters (NeuroBench pairs correctness with complexity).
44. Integrations, in order of tractability: flyvis as an adapter and as an observation source (its
    24-study tuning table), eonsystemspbc/fly-brain backends, chaobrain's fitted whole-brain SNN as
    the high-parameter counterpoint, FlyGym/flybody for a future closed-loop track.

## 6. Governance (not grading our own model)

45. Move the reference LIF into its own package and submit it like any third party, marked
    `reference_baseline`.
46. Task RFC template: cited experiment with mean ± SD ± n, readouts and margins, pre-registered
    prediction of whether the reference model passes, shuffled-connectome control result,
    provenance tags on every constant. Two public reviews + maintainer meta-review; accepted task
    authors join the reviewer pool and get co-authorship (BIG-bench's credit model).
47. Reject tasks the reference model trivially passes and tasks the shuffle also passes.
48. A "break flybench" round: solicit tasks that current passing models fail, score submissions by
    how far they drive mean scores down (Brain-Score 2024 inverted its competition this way).
49. Conflict-of-interest field per leaderboard row; task authors recuse from reviewing models that
    target their tasks.
50. Lifecycle policy: retire or rotate tasks once passing models are statistically indistinguishable;
    named maintainer; scope the README claim to "these cited manipulations", never "biological realism".

## 7. Closed-loop track (later, and only with the control)

51. A v2 embodied track on FlyGym/NeuroMechFly or flybody with its own hold-out. Not before item 8
    exists: a closed-loop success metric without a shuffled-connectome control is exactly the
    "digital sphinx" failure. Score behaviour against videography (flybody: 0.25 mm / <5° in flight).

## 8. Explorer and adoption

52. One-click Colab per tier (toy in seconds; FlyWire; MaleCNS), each ending with the leaderboard
    row you would submit.
53. Permalinks for every explorer experiment (dataset, populations, gain, duration, seed, readouts)
    in Codex's URL style; every task page links to the live experiment; "cite this experiment".
54. Downloadable traces and spike rasters (CSV/Parquet/PNG) from both CLI (`--dump-traces`) and explorer.
55. Cell-type search synonyms and cross-dataset aliases (GF = DNp01 = giant fiber; EPG = E-PG;
    TTM = TTMn), and an explicit "this type does not exist in this dataset" answer.
56. Cross-links per cell type: Codex, neuPrint, Virtual Fly Brain, Neuroglancer (CAVE state links).
57. `flybench compare` with JSON, markdown, per-check margin diff, and `--fail-on-regression` for labs' CI.
58. Classroom bundle for FlyWire Academy's open Python slot: trace a reflex; break the model (vary
    gain and min-synapse, explain which assumption you violated); write a task from a paper.
59. A "what this model cannot do" page quoting the field's own critiques (Marder on gap junctions,
    Currier on connectivity ≠ function, Otopalik on static snapshots, Beiran on degeneracy) and
    mapping each to the tasks it predicts should fail.
60. Task-authoring linter: `basis:` must carry a DOI or `convention:`; GitHub Discussions template
    with the Part-3 table columns.

## Agreed research thread (model side, task first)

Dopamine-gated KC→MBON plasticity with an `olfactory_conditioning` task written and pre-registered
before the rule. Now sits behind item 25 (MB sparseness), which it depends on.
