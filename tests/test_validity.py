"""The benchmark-validity additions: effect sizes, thresholds with provenance, physiological
ceilings, circuit-weighted scores, and the 'different individual' perturbation."""
import copy

import numpy as np
import pytest
import yaml

from flybench.bench import TASK_DIR, load_tasks, margin_of, perturb_weights, run_suite, run_task
from flybench.connectome import load_connectome
from flybench.lint import lint_task
from flybench.sim import LIFParams


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


def test_margin_is_signed_decades():
    assert margin_of(50, ">", 5) == pytest.approx(1.0)      # 10x on the passing side
    assert margin_of(0.5, ">", 5) == pytest.approx(-1.0)    # 10x on the failing side
    assert margin_of(0.01, "<", 0.1) == pytest.approx(1.0)  # for '<', smaller is better
    assert margin_of(1.0, "<", 0.1) == pytest.approx(-1.0)
    assert margin_of(0.0, ">", 5) < -3                      # zero response is far on the failing side, finite
    assert margin_of(-0.9, ">", 0.5) < -2                   # a negative correlation against a positive threshold: far on the failing side, not +0.26
    assert margin_of(-0.9, "<", 0.5) > 2
    assert np.isnan(margin_of(float("nan"), ">", 5))


def test_every_published_threshold_has_a_basis_and_every_task_a_circuit():
    for t in load_tasks():
        assert t.get("circuit"), t["name"]
        for i, ch in enumerate(t["checks"]):
            assert str(ch.get("basis", "")).strip(), f"{t['name']} check {i} has no basis"
            # a basis is either a citation (has a year) or an explicit convention
            b = ch["basis"]
            assert "convention" in b.lower() or any(str(y) in b for y in range(1950, 2030)), f"{t['name']} check {i}: {b!r}"


def test_lint_rejects_missing_basis_and_circuit():
    t = yaml.safe_load((TASK_DIR / "01_stability.yaml").read_text(encoding="utf-8"))
    bad = copy.deepcopy(t); bad["checks"][0].pop("basis")
    assert any("basis" in e for e in lint_task(bad))
    bad = copy.deepcopy(t); bad.pop("circuit")
    assert any("circuit" in e for e in lint_task(bad))
    bad = copy.deepcopy(t); bad["conditions"]["baseline"]["weight_jitter"] = 3
    assert any("weight_jitter" in e for e in lint_task(bad))
    assert lint_task(t) == []


def test_spikes_per_neuron_and_physiology_task_on_toy(toy):
    task = next(t for t in load_tasks() if t["name"] == "physiological_rates")
    r = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    by = {c.description.split("  [")[0]: c for c in r.checks}
    gf_count = next(v for k, v in by.items() if k.startswith("spikes per neuron[loom, 200-500ms] >="))
    assert gf_count.value >= 1                               # the toy GF does fire
    assert all(np.isfinite(c.margin) for c in r.checks)
    for c in r.checks:
        assert c.basis                                       # provenance travels into the result


def test_perturb_weights_is_a_different_individual_with_the_same_wiring(toy):
    p = perturb_weights(toy, 0.25, seed=0)
    assert p.n == toy.n and p.W.nnz == toy.W.nnz
    assert (p.W.indices == toy.W.indices).all() and (p.W.indptr == toy.W.indptr).all()   # same edges
    ratio = p.W.data / toy.W.data
    assert (ratio > 0).all()                                 # signs preserved
    assert 0.15 < np.std(np.log(ratio)) < 0.35               # ~sigma 0.25 in log units
    assert abs(np.mean(np.log(ratio))) < 0.05                # unbiased
    q = perturb_weights(toy, 0.25, seed=0)
    assert np.allclose(p.W.data, q.W.data)                   # seeded: reproducible
    assert not np.allclose(perturb_weights(toy, 0.25, seed=1).W.data, p.W.data)


def test_wiring_robustness_task_runs_and_uses_jitter(toy):
    task = next(t for t in load_tasks() if t["name"] == "wiring_robustness")
    r = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    assert set(r.measurements) == {"baseline_other_fly", "sugar_other_fly", "loom_other_fly"}
    # the perturbed sugar response differs from the unperturbed one (it is a different brain)
    plain = next(t for t in load_tasks() if t["name"] == "sugar_to_proboscis")
    r0 = run_task(plain, toy, LIFParams(gain=1.0, seed=0))
    assert r.measurements["sugar_other_fly"]["rate[mn9]"] != r0.measurements["sugar"]["rate"]


def test_circuit_weighted_scores(toy):
    tasks = load_tasks()
    rep = run_suite(toy, LIFParams(gain=1.0, seed=0), tasks)
    assert set(rep["circuits"].values()) >= {"taste", "escape", "olfaction", "stability", "physiology", "robustness"}
    # by-circuit is a mean over circuits of per-circuit means; recompute by hand
    by_name = {t["name"]: t for t in tasks}
    for tier, key in (("core", "core_by_circuit"), ("hard", "hard_by_circuit")):
        by = {}
        for t in rep["tasks"]:                      # skipped tasks (e.g. 15 on the toy) are absent, so match by name
            task = by_name[t["task"]]
            if task.get("tier", "core") == tier:
                by.setdefault(task["circuit"], []).append(t["score"])
        assert rep[key] == pytest.approx(np.mean([np.mean(v) for v in by.values()]))
    # seven taste tasks count once: a suite where only taste passes scores 1/num_circuits by circuit, not 7/12
    fake = copy.deepcopy(rep)
    for t in fake["tasks"]:
        t["score"] = 1.0 if by_name[t["task"]]["circuit"] == "taste" else 0.0
    n_hard_circuits = len({task["circuit"] for task in tasks if task.get("tier") == "hard"})
    hard_scores = [t["score"] for t in fake["tasks"] if by_name[t["task"]].get("tier") == "hard"]
    assert np.mean(hard_scores) > 1 / n_hard_circuits         # task-weighted flatters the taste pathway


def test_tasks_needing_neurons_the_dataset_lacks_are_skipped_not_failed(toy):
    from flybench.bench import task_unavailable
    tasks = load_tasks()
    jump = next(t for t in tasks if t["name"] == "looming_to_jump_muscle")
    assert task_unavailable(jump, toy)                      # the toy has no ventral cord
    sugar = next(t for t in tasks if t["name"] == "sugar_to_proboscis")
    assert task_unavailable(sugar, toy) is None
    rep = run_suite(toy, LIFParams(gain=1.0, seed=0), tasks)
    assert "looming_to_jump_muscle" in rep["skipped"]
    assert all(t["task"] != "looming_to_jump_muscle" for t in rep["tasks"])
    assert rep["n_tasks"] == len(tasks) - len(rep["skipped"]) and len(rep["skipped"]) == 2   # 15 and 19 need the nerve cord
    # a required readout that is not defined is a lint error, not a silent skip
    bad = dict(jump, requires_readouts=["nope"])
    assert task_unavailable(bad, toy).startswith("requires readout")
    assert any("nope" in e for e in lint_task(bad))


def test_task16_gf_azimuth_invariance_runs_and_skips_without_side_labels(toy):
    from flybench.bench import task_unavailable
    from flybench.connectome import Connectome
    task = next(t for t in load_tasks() if t["name"] == "gf_azimuth_invariance")
    assert task_unavailable(task, toy) is None
    r = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    by = {c.description.split("  [")[0]: c for c in r.checks}
    assert len(r.checks) == 9
    # the unilateral looms drive half the detectors each; both are seen
    assert r.stimulus_sizes["loom_left"] > 0 and r.stimulus_sizes["loom_right"] > 0
    assert by["spikes per neuron[left] >= 1.0 spikes/neuron"].passed and by["spikes per neuron[right] >= 1.0 spikes/neuron"].passed
    # the recording-match checks carry their source and (sd unknown) score by the threshold rule
    one = by["spikes per neuron[left] <= 1.0 spikes/neuron"]
    assert np.isnan(one.z) and not one.passed          # the plain LIF fires a burst, as pre-registered
    assert one.graded < 0.1
    # invariance holds on the toy (symmetric wiring)
    assert by["rate[left, gf] / rate[right] < 3.0"].passed and by["rate[right, gf] / rate[left] < 3.0"].passed
    # a dataset without side labels cannot pose the question: skipped, not failed
    ann = toy.annotations.copy(); ann["side"] = ""
    nosides = Connectome(root_ids=toy.root_ids, W=toy.W, positions=toy.positions, annotations=ann, name="nosides", meta=toy.meta)
    why = task_unavailable(task, nosides)
    assert why and "loom_left" in why
    rep = run_suite(nosides, LIFParams(gain=1.0, seed=0), [task])
    assert rep["skipped"] == {"gf_azimuth_invariance": why} and rep["n_tasks"] == 0
    # lint: requires_stimuli must name a real stimulus
    bad = dict(task, requires_stimuli=["nope"])
    assert any("requires_stimuli" in e for e in lint_task(bad))


def test_task17_pn_transfer_function_on_toy(toy):
    task = next(t for t in load_tasks() if t["name"] == "pn_transfer_function")
    r = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    assert len(r.checks) == 7 and r.readout_size == 8 and r.stimulus_sizes["da1_orn"] == 40
    by = {c.description.split("  [")[0]: c for c in r.checks}
    rates = {k: r.measurements[k]["rate[da1_pn]"] for k in ("orn10", "orn30", "orn100")}
    assert rates["orn10"] < rates["orn30"] < rates["orn100"]            # monotonic on the toy
    assert by["rate[orn30, da1_pn] / rate[orn10] > 1.0"].passed and by["rate[orn100, da1_pn] / rate[orn30] > 1.0"].passed
    assert by["rate[orn10, da1_pn] >= 5.0 Hz"].passed                     # 10 Hz input is enough to respond
    ceiling = by["rate[orn100, da1_pn] <= 170.0 Hz"]
    assert ceiling.basis.startswith("Olsen") and np.isnan(ceiling.z)      # sd unknown → threshold rule, with its source
    # the toy is a plain LIF: threshold-linear, so it is expected to fail the compression checks
    assert not by["rate[orn30, da1_pn] / rate[orn10] < 3.0"].passed
    # task 8 now has real glomeruli to read: DA1 fires, the three bystanders stay quiet
    sparse = next(t for t in load_tasks() if t["name"] == "olfactory_sparse_coding")
    r8 = run_task(sparse, toy, LIFParams(gain=1.0, seed=0))
    assert r8.passed and r8.measurements["cva"]["readout_active_fraction[all_pn]"] == pytest.approx(0.125)   # DA1 of 8 glomeruli


def test_task17_dynamic_range_check_fails_a_saturated_model(toy):
    """The amendment: ratios of two ceilings must not pass 'compressive'."""
    task = copy.deepcopy(next(t for t in load_tasks() if t["name"] == "pn_transfer_function"))
    for cond in task["conditions"].values():                        # 30x the input: the toy PNs sit at their ceiling at every rate
        for st in cond["stimuli"]:
            st["rate_hz"] *= 30
    r = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    rates = {k: r.measurements[k]["rate[da1_pn]"] for k in ("orn10", "orn30", "orn100")}
    assert rates["orn10"] > 0.7 * rates["orn100"]                   # saturated at the weakest input
    by = {c.description.split("  [")[0]: c for c in r.checks}
    comp = by["rate[orn30, da1_pn] / rate[orn10] < 3.0"]
    assert comp.value < 3 and comp.saturated and not comp.passed      # the vacuous pass RFC 17 documents, now caught by RFC S1
    assert not by["rate[orn10, da1_pn] / rate[orn100] < 0.6"].passed  # and task 17's own dynamic-range check


def test_lifetime_sparseness_metric():
    from flybench.bench import lifetime_sparseness
    assert lifetime_sparseness([10, 0, 0, 0]) == pytest.approx(1.0)          # one stimulus only
    assert lifetime_sparseness([5, 5, 5, 5]) == pytest.approx(0.0)           # all equal
    assert 0.3 < lifetime_sparseness([10, 3, 2, 1, 0, 0, 0, 0]) < 0.9
    assert np.isnan(lifetime_sparseness([0, 0, 0]))                          # silent readout: undefined, not 1
    assert np.isnan(lifetime_sparseness([5]))
    assert lifetime_sparseness([10, float("nan"), 0, 0]) == pytest.approx(1.0)


def test_task18_da1_sparseness_on_toy(toy):
    from flybench.bench import task_unavailable
    task = next(t for t in load_tasks() if t["name"] == "da1_sparseness")
    assert task_unavailable(task, toy) is None
    r = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    assert len(r.checks) == 9 and len(r.stimulus_sizes) == 8
    by = {c.description.split("  [")[0]: c for c in r.checks}
    s = by["lifetime sparseness[da1_pn, 8 stimuli] >= 0.9"]
    assert s.passed and s.value > 0.95 and np.isnan(s.z) and "Schlief" in s.basis   # toy: wired only through inhibition
    assert r.passed
    # lint: a panel entry that is not a condition, or a panel of one, is rejected
    bad = copy.deepcopy(task); bad["checks"][0]["conds"] = ["cva", "nope"]
    assert any("nope" in e for e in lint_task(bad))
    bad = copy.deepcopy(task); bad["checks"][0]["conds"] = ["cva"]
    assert any("at least 2" in e for e in lint_task(bad))
    # a dataset missing one panel glomerulus skips rather than inflating S
    from flybench.connectome import Connectome
    ann = toy.annotations.copy(); ann.loc[ann["cell_type"] == "ORN_DC1", "cell_type"] = "ORN_gone"
    partial = Connectome(root_ids=toy.root_ids, W=toy.W, positions=toy.positions, annotations=ann, name="partial", meta=toy.meta)
    assert "orn_dc1" in (task_unavailable(task, partial) or "")


def test_rfc_s1_ceiling_gate_fails_saturated_comparisons(toy):
    """A ratio or sparseness check whose every compared condition sits at the refractory ceiling is
    marked saturated and counted as failed (docs/rfcs/S1_ceiling_gate.md)."""
    task = copy.deepcopy(next(t for t in load_tasks() if t["name"] == "pn_transfer_function"))
    for cond in task["conditions"].values():
        for st in cond["stimuli"]:
            st["rate_hz"] *= 30                                      # every input rate pins the toy PNs
    r = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    ratios = [c for c in r.checks if c.description.startswith("rate[orn")]
    sat = [c for c in ratios if c.saturated]
    assert sat and all((not c.passed) and c.graded == 0.0 and c.margin == -10.0 and "saturated" in c.description for c in sat)
    # the ceiling check itself is an absolute-rate check: untouched by the gate, and it fails on its own
    ceiling = next(c for c in r.checks if "<= 170.0 Hz" in c.description)
    assert not ceiling.saturated and not ceiling.passed
    # multi-seed: saturated on every seed → saturated; description carries both tags once
    r3 = run_task(task, toy, LIFParams(gain=1.0, seed=0), seeds=2)
    s3 = [c for c in r3.checks if c.saturated]
    assert s3 and all(c.description.count("saturated") == 1 and "2/2 seeds" in c.description or "0/2 seeds" in c.description or "1/2 seeds" in c.description for c in s3)
    # a comparison against a silent condition is never saturated (baseline is not at ceiling)
    sugar = next(t for t in load_tasks() if t["name"] == "sugar_to_proboscis")
    rs = run_task(sugar, toy, LIFParams(gain=1.0, seed=0))
    assert not any(c.saturated for c in rs.checks)
    # unsaturated inputs: the same task at its real rates has no saturated checks on the toy
    plain = next(t for t in load_tasks() if t["name"] == "pn_transfer_function")
    assert not any(c.saturated for c in run_task(plain, toy, LIFParams(gain=1.0, seed=0)).checks)


def test_latency_metric_and_task19_skips_without_a_nerve_cord(toy):
    from flybench.bench import first_spike_ms, task_unavailable
    from flybench.sim import LIFSimulator, Stimulus
    loom = toy.select({"any": [{"cell_type": "LPLC2"}, {"cell_type": "LC4"}]}); gf = toy.select("GF")
    res = LIFSimulator(toy, LIFParams(seed=0)).run(400, [Stimulus(loom, 150, 100, 300)])
    t_loom, t_gf = first_spike_ms(res, loom, 100, 400), first_spike_ms(res, gf, 100, 400)
    assert 100 <= t_loom < t_gf < 200                               # detectors first, GF after one synaptic delay
    assert t_gf - t_loom >= toy_delay(LIFParams()) - 1e-6           # never faster than the model's own delay
    assert np.isnan(first_spike_ms(res, gf, 0, 100))                # silent before the loom
    assert np.isnan(first_spike_ms(res, np.empty(0, dtype=int), 0, 400))
    # a latency check through the task machinery, on the toy's own loom → GF hop
    task = {"name": "t", "title": "t", "citation": "test", "duration_ms": 400, "window": [100, 300], "circuit": "escape",
            "readouts": {"gf": {"select": "GF"}, "det": {"select": {"any": [{"cell_type": "LPLC2"}, {"cell_type": "LC4"}]}}},
            "conditions": {"loom": {"stimuli": [{"name": "d", "select": {"any": [{"cell_type": "LPLC2"}, {"cell_type": "LC4"}]}, "rate_hz": 150, "t_start_ms": 100, "t_end_ms": 300}]}},
            "checks": [{"type": "latency", "cond": "loom", "readout": "gf", "op": "<", "value": 50, "basis": "convention: test"},
                       {"type": "latency", "cond": "loom", "readout": "gf", "from": "det", "op": ">=", "value": 1.8, "basis": "convention: one chemical delay"}]}
    assert lint_task(task) == []
    r = run_task(task, toy, LIFParams(seed=0))
    assert r.checks[0].passed and 0 < r.checks[0].value < 50 and r.checks[1].passed
    assert r.checks[1].description.startswith("latency[loom, det → gf]")
    bad = dict(task, checks=[dict(task["checks"][1], **{"from": "nope"})])
    assert any("from" in e for e in lint_task(bad))
    # task 19 needs the nerve cord: skipped on the toy, not failed
    t19 = next(t for t in load_tasks() if t["name"] == "gf_to_muscle_latency")
    assert task_unavailable(t19, toy) and "ttmn" in task_unavailable(t19, toy)


def toy_delay(p):
    return p.delay_ms


def test_task21_matrix_expands_lints_and_a_broken_toy_fails_the_leaking_cell(toy):
    import scipy.sparse as sp
    from flybench.bench import expand_checks, task_unavailable
    from flybench.connectome import Connectome
    t21 = next(t for t in load_tasks() if t["name"] == "lc_dn_matrix")
    raw = yaml.safe_load((TASK_DIR / "21_lc_dn_matrix.yaml").read_text(encoding="utf-8"))
    assert lint_task(raw) == [] and task_unavailable(t21, toy) is None
    # expansion: one check per scored cell, "+" -> ">=", "-" -> "<", "?" dropped, row-major order, cell tag kept
    grid = raw["checks"][0]["expect"]
    scored = [(c, r, v["sign"]) for c, row in grid.items() for r, v in row.items() if isinstance(v, dict)]
    assert len(t21["checks"]) == len(scored) == 16
    assert expand_checks(t21) is t21                                    # already expanded: returned as is
    for chk, (cond, rname, sign) in zip(t21["checks"], scored):
        assert (chk["cond"], chk["readout"], chk["op"]) == (cond, rname, ">=" if sign == "+" else "<")
        assert chk["type"] == "spikes_per_neuron" and chk["value"] == 1 and chk["cell"][:2] == [cond, rname]
        assert chk["basis"].strip()
    # lint: a cell that names a missing readout / condition, a bad sign, or a grid with nothing scored
    bad = copy.deepcopy(raw); bad["checks"][0]["expect"]["lc4"]["nope"] = "+"
    assert any("readout 'nope'" in e for e in lint_task(bad))
    bad = copy.deepcopy(raw); bad["checks"][0]["expect"]["lc99"] = {"gf": "+"}
    assert any("lc99" in e for e in lint_task(bad))
    bad = copy.deepcopy(raw); bad["checks"][0]["expect"]["lc4"]["gf"] = "x"
    assert any("sign" in e for e in lint_task(bad))
    bad = copy.deepcopy(raw); bad["checks"][0]["expect"] = {"lc4": {"gf": "?"}}
    assert any("scores no cell" in e for e in lint_task(bad))
    bad = copy.deepcopy(raw); bad["checks"][0].pop("basis"); bad["checks"][0]["expect"]["lc4"]["gf"] = "+"
    assert any("needs `basis`" in e for e in lint_task(bad))
    # the toy passes every cell; a toy with an LC16 -> GF edge fails exactly the LC16/GF cell
    r = run_task(t21, toy, LIFParams(seed=1))
    assert r.passed and r.score == 1.0
    assert r.checks[8].description.startswith("spikes per neuron[lc16, gf] <")
    W = toy.W.tolil(); lc16 = toy.select("LC16"); gf = toy.select("GF")
    for i in lc16:
        for j in gf:
            W[i, j] = 6.0
    broken = Connectome(root_ids=toy.root_ids, W=sp.csr_matrix(W, dtype=np.float32), positions=toy.positions,
                        annotations=toy.annotations, name="broken-toy", meta=dict(toy.meta))
    rb = run_task(t21, broken, LIFParams(seed=1))
    assert not rb.checks[8].passed and rb.checks[8].value >= 1
    assert sum(not ch.passed for ch in rb.checks) == 1
    # multi-seed keeps the per-cell alignment
    rm = run_task(t21, toy, LIFParams(seed=1), seeds=2)
    assert len(rm.checks) == 16 and rm.passed


def test_task22_dataset_only_skips_elsewhere_lints_and_a_broken_toy_fails_the_leg_null(toy):
    import scipy.sparse as sp
    from flybench.bench import task_unavailable
    from flybench.connectome import Connectome
    t22 = next(t for t in load_tasks() if t["name"] == "courtship_song_chain")
    raw = yaml.safe_load((TASK_DIR / "22_courtship_song_chain.yaml").read_text(encoding="utf-8"))
    assert lint_task(raw) == [] and t22["dataset_only"] == ["malecns", "toy"]
    assert task_unavailable(t22, toy) is None
    # the same network under another name is "not applicable" — before any selector is consulted
    female = Connectome(root_ids=toy.root_ids, W=toy.W, positions=toy.positions, annotations=toy.annotations, name="flywire783", meta=dict(toy.meta))
    why = task_unavailable(t22, female)
    assert why and why.startswith("not applicable") and "malecns/toy" in why and "flywire783" in why
    rep = run_suite(female, LIFParams(seed=1), [t22])
    assert rep["n_tasks"] == 0 and rep["skipped"]["courtship_song_chain"].startswith("not applicable")
    # lint: unknown dataset names, a list that leaves the toy out, a non-list
    bad = copy.deepcopy(raw); bad["dataset_only"] = ["malecns", "toy", "hemibrain"]
    assert any("hemibrain" in e for e in lint_task(bad))
    bad = copy.deepcopy(raw); bad["dataset_only"] = ["malecns"]
    assert any("must include 'toy'" in e for e in lint_task(bad))
    bad = copy.deepcopy(raw); bad["dataset_only"] = "malecns"
    assert any("non-empty list" in e for e in lint_task(bad))
    # the toy passes; a toy with a pIP10 -> leg MN contact fails exactly the leg-MN null
    r = run_task(t22, toy, LIFParams(seed=1))
    assert r.passed and r.score == 1.0
    assert r.checks[3].description.startswith("rate[pip10_left, leg_mn] <")
    W = toy.W.tolil(); pip10 = toy.select("pIP10"); leg = toy.select({"all_of": [{"super_class": "vnc_motor"}, {"cell_type_regex": "flexor MN$"}]})
    assert leg.size == 20
    for i in pip10:
        for j in leg:
            W[i, j] = 200.0
    broken = Connectome(root_ids=toy.root_ids, W=sp.csr_matrix(W, dtype=np.float32), positions=toy.positions,
                        annotations=toy.annotations, name="toy", meta=dict(toy.meta))
    rb = run_task(t22, broken, LIFParams(seed=1))
    assert not rb.checks[3].passed and rb.checks[3].value >= 2
    assert all(ch.passed for k, ch in enumerate(rb.checks) if k != 3)


def test_recruitment_metrics_on_known_vectors():
    from flybench.bench import MIN_RANK_N, first_spikes_per_neuron, recruitment_order, recruitment_spread
    from flybench.sim import SimResult
    # Henneman order: size ranks 0..11, the smallest fires first -> rho = +1; reversed -> -1
    size = np.arange(12, dtype=float) * 100 + 7
    t = 200 + np.arange(12) * 50.0
    assert recruitment_order(t, size) == pytest.approx(1.0)
    assert recruitment_order(t[::-1], size) == pytest.approx(-1.0)
    # unrecruited neurons rank last (tied): the biggest three never firing keeps the order positive
    t2 = t.copy(); t2[-3:] = np.nan
    assert recruitment_order(t2, size) > 0.9
    # undefined, not a fail with a number: too few neurons, fewer than two recruited, all sizes equal
    assert np.isnan(recruitment_order(t[:MIN_RANK_N - 1], size[:MIN_RANK_N - 1]))
    assert np.isnan(recruitment_order(np.where(np.arange(12) == 0, 300.0, np.nan), size))
    assert np.isnan(recruitment_order(t, np.ones(12)))
    # spread: IQR of the recruited first-spike times, NaN below four recruited
    assert recruitment_spread(t) == pytest.approx(np.percentile(t, 75) - np.percentile(t, 25))
    assert np.isnan(recruitment_spread(np.array([1.0, 2.0, 3.0, np.nan])))
    # first spikes per neuron, in readout order, from a spike train (neuron 5 fires twice, neuron 9 never)
    res = SimResult(spike_times_ms=np.array([300.0, 250.0, 260.0, 100.0], dtype=np.float32), spike_neurons=np.array([5, 7, 5, 9], dtype=np.int32), duration_ms=1000, n=20)
    fs = first_spikes_per_neuron(res, np.array([9, 5, 7]), 200, 1000)
    assert np.isnan(fs[0]) and fs[1] == 260.0 and fs[2] == 250.0


def test_ramp_stimulus_rises_linearly(toy):
    from flybench.sim import LIFSimulator, Stimulus
    s = Stimulus(neurons=np.arange(5), rate_hz=0.0, t_start_ms=200, t_end_ms=1200, rate_end_hz=100.0)
    assert s.rate_at(100) == 0.0 and s.rate_at(200) == 0.0 and s.rate_at(700) == pytest.approx(50.0) and s.rate_at(1200) == 100.0 and s.rate_at(5000) == 100.0
    assert Stimulus(neurons=np.arange(5), rate_hz=30.0).rate_at(999) == 30.0     # no ramp: constant
    # driven neurons fire more in the last fifth of the ramp than in the first fifth
    grn = toy.select("GRN_sugar")
    res = LIFSimulator(toy, LIFParams(seed=3, gain=0.01)).run(1200, [Stimulus(neurons=grn, rate_hz=0.0, t_start_ms=200, t_end_ms=1200, rate_end_hz=100.0)])
    early, late = res.rate_hz(grn, 200, 400), res.rate_hz(grn, 1000, 1200)
    assert early < 25 and late > 75 and late > 4 * early


def test_upstream_of_selector(toy):
    from flybench.connectome import select
    mn9 = toy.select("MN9")
    pre = toy.select({"upstream_of": "MN9"})
    W = abs(toy.W)[:, mn9]
    assert set(pre) == set(np.flatnonzero(np.asarray(W.sum(axis=1)).ravel() > 0))
    strong = toy.select({"upstream_of": "MN9", "min_synapses": 8})
    assert 0 < strong.size < pre.size and set(strong) <= set(pre)
    assert set(strong) == set(np.flatnonzero(W.max(axis=1).toarray().ravel() >= 8))
    assert toy.select({"all_of": [{"upstream_of": "MN9"}, {"nt_type": "GABA"}]}).size == toy.select({"all_of": [{"upstream_of": "MN9"}, "bitter_ln"]}).size
    assert toy.select({"upstream_of": {"cell_type": "no_such_type"}}).size == 0
    with pytest.raises(ValueError):
        select(toy.annotations, {"upstream_of": "MN9"})      # the graph is needed, annotations alone will not do


def test_task23_size_principle_passes_on_toy_and_fails_on_size_proportional_wiring(toy):
    import scipy.sparse as sp
    from flybench.bench import task_unavailable
    from flybench.connectome import Connectome
    t23 = next(t for t in load_tasks() if t["name"] == "leg_mn_size_principle")
    raw = yaml.safe_load((TASK_DIR / "23_leg_mn_size_principle.yaml").read_text(encoding="utf-8"))
    assert lint_task(raw) == [] and t23["dataset_only"] == ["malecns", "toy"]
    assert task_unavailable(t23, toy) is None
    leg = toy.select(t23["readouts"]["leg_t1l"]["select"])
    pool = toy.select(t23["conditions"]["ramp"]["stimuli"][0]["select"])
    assert leg.size == 12 and pool.size == 60                      # one front leg; the excitatory central premotor pool, no afferents
    assert set(toy.annotations.iloc[pool].cell_type) == {"leg_premotor_toy"}
    r = run_task(t23, toy, LIFParams(seed=1))
    assert r.passed and r.score == 1.0
    assert r.checks[0].description.startswith("rank order[ramp, leg_t1l]") and r.checks[0].value > 0.9
    assert r.checks[2].value > 50
    # lint: rank_order must name a known attribute; a ramp needs rate_end_hz != rate_hz
    bad = copy.deepcopy(raw); bad["checks"][0]["by"] = "soma_volume"
    assert any("rank_order `by`" in e for e in lint_task(bad))
    bad = copy.deepcopy(raw); bad["conditions"]["ramp"]["stimuli"][0]["rate_end_hz"] = 0
    assert any("rate_end_hz" in e for e in lint_task(bad))
    # the Lesser 2024 wiring: premotor contact proportional to MN size. Under a uniform LIF the largest
    # MN is recruited first (rho -> -1) and only the order check fails; the pool still recruits, graded
    W = toy.W.tolil()
    size = np.asarray(abs(toy.W).sum(axis=0)).ravel()[leg]
    for j, s in zip(leg, size):
        for i in pool:
            if W[i, j] != 0:
                W[i, j] = max(1.0, round(12.0 * s / size.max()))
    broken = Connectome(root_ids=toy.root_ids, W=sp.csr_matrix(W, dtype=np.float32), positions=toy.positions,
                        annotations=toy.annotations, name="toy", meta=dict(toy.meta))
    rb = run_task(t23, broken, LIFParams(seed=1))
    assert not rb.checks[0].passed and rb.checks[0].value < -0.5
    assert rb.checks[1].passed and rb.checks[2].passed


def test_task24_optic_flow_passes_on_toy_and_fails_without_bips(toy):
    import scipy.sparse as sp
    from flybench.bench import task_unavailable
    from flybench.connectome import Connectome
    t24 = next(t for t in load_tasks() if t["name"] == "optic_flow_rotation")
    raw = yaml.safe_load((TASK_DIR / "24_optic_flow_rotation.yaml").read_text(encoding="utf-8"))
    assert lint_task(raw) == [] and task_unavailable(t24, toy) is None
    assert toy.select(t24["readouts"]["bips"]["select"]).size == 2
    hs_l = toy.select(t24["conditions"]["ftb_left"]["stimuli"][0]["select"])
    assert hs_l.size == 3 and set(toy.annotations.iloc[hs_l].side) == {"left"}
    r = run_task(t24, toy, LIFParams(seed=1))
    assert r.passed and r.score == 1.0
    assert r.checks[2].description.startswith("rate[yaw_right, dnp15_right] <") and r.checks[2].value == 0.0
    assert r.checks[4].description.startswith("rate[forward, dnp15_left] / rate[ftb_left] <") and r.checks[4].value < 0.8
    # cut bIPS -> DNp15: the contralateral symmetric component no longer suppresses DNp15 (check 5 fails,
    # ratio ~ 1); the yaw responses, the null and the bIPS preference are untouched
    W = toy.W.tolil(); bips = toy.select("bIPS_toy"); dn = toy.select("DNp15")
    for i in bips:
        for j in dn:
            W[i, j] = 0.0
    broken = Connectome(root_ids=toy.root_ids, W=sp.csr_matrix(W, dtype=np.float32), positions=toy.positions,
                        annotations=toy.annotations, name="toy", meta=dict(toy.meta))
    rb = run_task(t24, broken, LIFParams(seed=1))
    assert not rb.checks[4].passed and rb.checks[4].value > 0.8
    assert all(ch.passed for k, ch in enumerate(rb.checks) if k not in (3, 4))


def test_task25_grooming_passes_on_toy_and_a_jo_ce_to_mdn_edge_fails_the_null(toy):
    import scipy.sparse as sp
    from flybench.bench import task_unavailable
    from flybench.connectome import Connectome
    t25 = next(t for t in load_tasks() if t["name"] == "antennal_grooming_vs_backward")
    raw = yaml.safe_load((TASK_DIR / "25_antennal_grooming_vs_backward.yaml").read_text(encoding="utf-8"))
    assert lint_task(raw) == [] and task_unavailable(t25, toy) is None
    jo_ce = toy.select(t25["conditions"]["jo_ce"]["stimuli"][0]["select"]); jo_f = toy.select(t25["conditions"]["jo_f"]["stimuli"][0]["select"])
    assert jo_ce.size == 60 and jo_f.size == 30 and not set(jo_ce) & set(jo_f)
    r = run_task(t25, toy, LIFParams(seed=1))
    assert r.passed and r.score == 1.0
    assert r.checks[3].description.startswith("rate[jo_ce, mdn] <") and r.checks[3].value == 0.0
    W = toy.W.tolil(); mdn = toy.select("MDN")
    for i in jo_ce[:20]:
        for j in mdn:
            W[i, j] = 8.0
    broken = Connectome(root_ids=toy.root_ids, W=sp.csr_matrix(W, dtype=np.float32), positions=toy.positions,
                        annotations=toy.annotations, name="toy", meta=dict(toy.meta))
    rb = run_task(t25, broken, LIFParams(seed=1))
    assert not rb.checks[3].passed and rb.checks[3].value >= 2
    assert all(ch.passed for k, ch in enumerate(rb.checks) if k != 3)
