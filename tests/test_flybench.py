import numpy as np
import pytest

from flybench import LIFParams, LIFSimulator, Stimulus, select
from flybench.bench import load_tasks, run_suite, leaderboard
from flybench.toy import build_toy_connectome


@pytest.fixture(scope="module")
def toy():
    return build_toy_connectome()


def test_toy_shape(toy):
    assert toy.n == 2004
    assert toy.W.shape == (toy.n, toy.n)
    assert (toy.W.diagonal() == 0).all()
    # GABA rows are negative, ACh rows positive
    gaba = select(toy.annotations, {"nt_type": "GABA"})
    assert (toy.W[gaba].data <= 0).all()


def test_selectors(toy):
    ann = toy.annotations
    assert len(select(ann, {"cell_type": "MN9"})) == 2
    assert len(select(ann, "MN9")) == 2
    assert len(select(ann, {"labels_regex": "sugar"})) == 40
    assert len(select(ann, {"all_of": [{"labels_regex": "GRN"}, {"not": {"labels_regex": "bitter"}}]})) == 60
    assert len(select(ann, {"any": [{"cell_type": "LPLC2"}, {"cell_type": "LC4"}]})) == 110
    assert len(select(ann, {"all": True})) == toy.n
    assert len(select(ann, {"nonexistent_column": "x"})) == 0


def test_silent_without_input(toy):
    res = LIFSimulator(toy, LIFParams()).run(200)
    assert len(res.spike_times_ms) == 0


def test_forced_spikes_respect_refractory(toy):
    sim = LIFSimulator(toy, LIFParams(seed=3))
    grn = select(toy.annotations, {"labels_regex": "sugar"})
    res = sim.run(300, [Stimulus(grn, rate_hz=5000)])   # absurd rate -> capped by t_ref
    rate = res.rate_hz(grn)
    assert rate <= 1000 / 2.2 + 1


def test_sugar_drives_mn9_and_bitter_suppresses(toy):
    ann = toy.annotations
    sim = LIFSimulator(toy, LIFParams(seed=1))
    sugar = select(ann, {"labels_regex": "sugar"}); bitter = select(ann, {"labels_regex": "bitter"}); mn9 = select(ann, "MN9")
    r_sugar = sim.run(600, [Stimulus(sugar, 100, 100, 600)]).rate_hz(mn9, 150, 600)
    r_both = sim.run(600, [Stimulus(sugar, 100, 100, 600), Stimulus(bitter, 100, 100, 600)]).rate_hz(mn9, 150, 600)
    assert r_sugar > 20
    assert r_both < 0.5 * r_sugar


def test_suite_runs_and_scores(toy):
    report = run_suite(toy, LIFParams(), load_tasks())
    assert report["n_tasks"] == 5
    assert report["score"] == 1.0
    md = leaderboard([{**report, "label": "t"}])
    assert "sugar_to_proboscis" in md


def test_low_gain_fails_reflexes(toy):
    report = run_suite(toy, LIFParams(gain=0.2), load_tasks())
    assert report["score"] < 1.0


def test_export_roundtrip(toy, tmp_path):
    from flybench.export import export_web
    import json
    out = export_web(toy, tmp_path / "web")
    meta = json.loads((out / "meta.json").read_text())
    assert meta["n"] == toy.n
    indptr = np.frombuffer((out / "indptr.bin").read_bytes(), dtype=np.int32)
    assert indptr[-1] == toy.n_edges
    assert "MN9 (proboscis)" in meta["populations"]
