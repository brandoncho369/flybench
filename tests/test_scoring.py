"""Graded scores, ceilings, z-scores and seed statistics (flybench.scoring)."""
import copy
import json

import numpy as np
import pytest

from flybench.bench import TASK_DIR, load_tasks, margin_of, run_suite, run_task
from flybench.connectome import load_connectome
from flybench.lint import lint_task
from flybench.scoring import (grade_check, graded_from_margin, graded_from_z, iqm, paired_difference,
                              performance_profile, stratified_bootstrap_ci, z_score)
from flybench.sim import LIFParams


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


def test_graded_from_margin_is_monotonic_bounded_and_centred():
    assert graded_from_margin(0.0) == pytest.approx(0.5)
    assert graded_from_margin(0.5) == pytest.approx(0.909, abs=1e-3)      # 3.2x on the passing side
    assert graded_from_margin(-0.5) == pytest.approx(0.091, abs=1e-3)
    assert graded_from_margin(float("nan")) == 0.0
    xs = np.linspace(-3, 3, 61)
    g = [graded_from_margin(x) for x in xs]
    assert all(0 <= v <= 1 for v in g) and all(b >= a for a, b in zip(g, g[1:]))
    assert graded_from_margin(50) == pytest.approx(1.0) and graded_from_margin(-50) == pytest.approx(0.0, abs=1e-9)   # clamped, no overflow


def test_z_and_graded_from_z():
    assert z_score(12, 10, 2) == pytest.approx(1.0)
    assert np.isnan(z_score(12, 10, 0)) and np.isnan(z_score(float("nan"), 10, 2))
    assert graded_from_z(0.0) > 0.97
    assert graded_from_z(2.0) == pytest.approx(0.5)              # |z| = k is the pass boundary
    assert graded_from_z(-2.0) == pytest.approx(0.5)             # symmetric
    assert graded_from_z(4.0) < 0.03
    assert graded_from_z(1e6) == pytest.approx(0.0, abs=1e-9) and graded_from_z(float("nan")) == 0.0


def test_grade_check_paths():
    # threshold-only: graded from the margin, z is nan, pass flag not overridden
    g, z, pz, ceil, capped = grade_check(50.0, margin_of(50, ">", 5))
    assert g > 0.99 and np.isnan(z) and pz is False and ceil is None and not capped
    # with a recording: z decides
    g, z, pz, _, _ = grade_check(11.0, 0.0, observed={"mean": 10, "sd": 1, "n": 5, "source": "x"})
    assert z == pytest.approx(1.0) and pz and 0.5 < g < 1
    g, z, pz, _, _ = grade_check(15.0, 0.0, observed={"mean": 10, "sd": 1, "n": 5, "source": "x"})
    assert z == pytest.approx(5.0) and not pz and g < 0.01
    # sd unknown / zero → threshold path
    for sd in ("unknown", 0, None):
        g, z, pz, _, _ = grade_check(50.0, 1.0, observed={"mean": 10, "sd": sd, "source": "x"})
        assert np.isnan(z) and g > 0.98
    # ceiling divides and caps
    g, _, _, ceil, capped = grade_check(50.0, 1.0, ceiling=0.5)
    assert g == 1.0 and capped and ceil == 0.5
    g, _, _, _, capped = grade_check(1.0, 0.0, ceiling=0.8)      # 0.5 / 0.8
    assert g == pytest.approx(0.625) and not capped


def test_iqm_and_bootstrap():
    assert np.isnan(iqm([]))
    assert iqm([1, 2, 3]) == pytest.approx(2.0)                    # < 4 values: plain mean
    assert iqm([0, 1, 1, 1, 1, 1, 1, 100]) == pytest.approx(1.0)  # outliers trimmed
    assert stratified_bootstrap_ci([[0.5], [0.7]]) is None         # nothing to resample with one seed
    ci = stratified_bootstrap_ci([[0.4, 0.5, 0.6], [0.9, 0.9, 0.9]], n_boot=300, seed=1)
    assert ci is not None and ci[0] <= 0.7 <= ci[1] and ci[1] - ci[0] < 0.2
    # the CI brackets the point estimate computed with the same statistic, also when tasks differ in spread
    from flybench.scoring import run_score
    rows = [[0.2, 0.9, 0.5], [0.95, 0.96, 0.97], [0.1, 0.1, 0.1], [0.6, 0.7, 0.8], [0.99, 0.99, 0.99]]
    pt = run_score(rows); lo, hi = stratified_bootstrap_ci(rows, n_boot=500, seed=2)
    assert lo <= pt <= hi
    a = stratified_bootstrap_ci([[0.4, 0.5, 0.6]], n_boot=100, seed=3)
    assert a == stratified_bootstrap_ci([[0.4, 0.5, 0.6]], n_boot=100, seed=3)   # seeded


def test_performance_profile_and_paired_difference():
    prof = performance_profile([-2, -0.3, 0.1, 0.4, 2])
    assert prof["0"] == pytest.approx(0.6) and prof["-1"] == pytest.approx(0.8) and prof["1"] == pytest.approx(0.2)
    assert all(np.isnan(v) for v in performance_profile([]).values())
    d = paired_difference([0.9, 0.8, 0.5], [0.8, 0.8, 0.7])
    assert d["n"] == 3 and d["mean"] == pytest.approx(-0.1 / 3) and d["p_improve"] == pytest.approx(0.5)  # 1 better, 1 tie, 1 worse
    assert paired_difference([float("nan")], [1.0])["n"] == 0


def test_lint_validates_observed_ceiling_k():
    import yaml
    t = yaml.safe_load((TASK_DIR / "02_sugar_to_proboscis.yaml").read_text(encoding="utf-8"))
    ok = copy.deepcopy(t); ok["checks"][0].update(observed={"mean": 80, "sd": 10, "n": 5, "source": "Zhang 2016"}, ceiling=0.95, k=2)
    assert lint_task(ok) == []
    ok2 = copy.deepcopy(t); ok2["checks"][0]["observed"] = {"mean": 80, "sd": "unknown", "source": "x"}
    assert lint_task(ok2) == []
    for bad_patch in ({"observed": {"mean": 80}}, {"observed": {"mean": "x", "sd": 1, "source": "s"}},
                      {"observed": {"mean": 80, "sd": -1, "source": "s"}}, {"observed": {"mean": 80, "sd": 1, "n": 0, "source": "s"}},
                      {"ceiling": 0}, {"ceiling": 1.5}, {"k": 0}):
        bad = copy.deepcopy(t); bad["checks"][0].update(bad_patch)
        assert lint_task(bad), bad_patch


def test_results_carry_graded_ci_profile_and_per_seed(toy):
    tasks = [x for x in load_tasks() if x["name"] in ("sugar_to_proboscis", "taste_specificity")]
    rep = run_suite(toy, LIFParams(gain=1.0, seed=0), tasks, seeds=3)
    assert 0 <= rep["graded"] <= 1 and rep["graded_ci95"] and rep["graded_ci95"][0] <= rep["graded"] <= rep["graded_ci95"][1] + 1e-9
    assert set(rep["profile"]) == {"-1", "-0.5", "-0.25", "0", "0.25", "0.5", "1"}
    assert rep["profile"]["0"] == pytest.approx(np.mean([ch["passed"] for t in rep["tasks"] for ch in t["checks"]]))  # τ=0 is the pass rate
    from flybench.scoring import run_score
    assert rep["graded"] == pytest.approx(run_score([t["graded_per_seed"] for t in rep["tasks"]]))
    for t in rep["tasks"]:
        assert t["graded"] == pytest.approx(np.mean(t["graded_per_seed"]))      # same statistic the CI resamples
        assert len(t["graded_per_seed"]) == 3
        for ch in t["checks"]:
            assert len(ch["per_seed"]) == 3 and ch["op"] and np.isfinite(ch["target"])
            assert (ch["graded"] > 0.5) == ch["passed"] or not np.isfinite(ch["margin"])   # threshold checks: graded and pass agree at the line
    single = run_suite(toy, LIFParams(gain=1.0, seed=0), tasks, seeds=1)
    assert single["graded_ci95"] is None and single["tasks"][0]["graded_per_seed"] and len(single["tasks"][0]["checks"][0]["per_seed"]) == 0
    json.dumps(rep)   # serialisable


def test_recording_check_changes_the_pass_flag(toy):
    task = copy.deepcopy(next(t for t in load_tasks() if t["name"] == "sugar_to_proboscis"))
    r0 = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    v = r0.checks[0].value                                   # the toy's MN9 rate under sugar
    task["checks"][0]["observed"] = {"mean": v, "sd": max(v * 0.1, 1e-3), "n": 5, "source": "pretend recording"}
    r1 = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    assert abs(r1.checks[0].z) < 1e-6 and r1.checks[0].passed and r1.checks[0].graded > 0.97
    task["checks"][0]["observed"] = {"mean": v * 10, "sd": max(v * 0.1, 1e-3), "n": 5, "source": "pretend recording"}
    r2 = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    assert not r2.checks[0].passed and r2.checks[0].graded < 0.01   # threshold would pass (v > 5 Hz), the recording says no
