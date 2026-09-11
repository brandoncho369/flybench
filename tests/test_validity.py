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
    for tier, key in (("core", "core_by_circuit"), ("hard", "hard_by_circuit")):
        by = {}
        for t, task in zip(rep["tasks"], tasks):
            if task.get("tier", "core") == tier:
                by.setdefault(task["circuit"], []).append(t["score"])
        assert rep[key] == pytest.approx(np.mean([np.mean(v) for v in by.values()]))
    # seven taste tasks count once: a suite where only taste passes scores 1/num_circuits by circuit, not 7/12
    fake = copy.deepcopy(rep)
    for t, task in zip(fake["tasks"], tasks):
        t["score"] = 1.0 if task["circuit"] == "taste" else 0.0
    n_hard_circuits = len({task["circuit"] for task in tasks if task.get("tier") == "hard"})
    hard_scores = [t["score"] for t, task in zip(fake["tasks"], tasks) if task.get("tier") == "hard"]
    assert np.mean(hard_scores) > 1 / n_hard_circuits         # task-weighted flatters the taste pathway
