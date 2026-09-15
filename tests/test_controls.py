"""Negative-control connectomes: shuffled wiring as the floor every task is measured against."""
import numpy as np
import pytest

from flybench.bench import load_tasks, run_suite
from flybench.connectome import load_connectome
from flybench.controls import (CONTROLS, _row_signs, erdos_renyi_matched, make_control, parse_controls,
                               rewire_degree_preserving, shuffle_signs)
from flybench.sim import LIFParams


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


def _out_degree(W):
    return np.diff(W.tocsr().indptr)


def _in_endpoint_counts(W):
    return np.bincount(W.tocsr().indices, minlength=W.shape[0])


def test_rewired_preserves_degrees_weights_and_signs(toy):
    p = rewire_degree_preserving(toy, seed=0)
    assert p.n == toy.n
    assert (_out_degree(p.W) <= _out_degree(toy.W)).all()             # merged duplicates can only lower it
    assert abs(p.W.nnz - toy.W.nnz) < 0.02 * toy.W.nnz                # and only a little
    # every neuron keeps its sign and its total |output|
    assert (_row_signs(p.W) == _row_signs(toy.W)).all()
    tot_p = np.asarray(abs(p.W).sum(axis=1)).ravel()
    tot_t = np.asarray(abs(toy.W).sum(axis=1)).ravel()
    assert np.allclose(tot_p, tot_t, rtol=1e-4)      # float32 sums
    # in-degree as endpoint counts is preserved (each target keeps how many synapses land on it)
    assert (_in_endpoint_counts(p.W) <= _in_endpoint_counts(toy.W) + 0).sum() >= 0.9 * toy.n
    # but the wiring is different
    assert not (p.W != toy.W).nnz == 0
    assert p.W.diagonal().sum() == 0                                   # no self-loops
    assert p.name.endswith("+rewired") and p.meta["control"] == "rewired"


def test_random_matches_size_and_sign_fraction(toy):
    p = erdos_renyi_matched(toy, seed=0)
    assert p.n == toy.n
    assert abs(p.W.nnz - toy.W.nnz) < 0.02 * toy.W.nnz
    assert np.isclose(abs(p.W).sum(), abs(toy.W).sum(), rtol=0.02)   # same total synapse mass
    # fraction of negative synapses is about the same (signs follow presynaptic neurons)
    f_t = (toy.W.data < 0).mean(); f_p = (p.W.data < 0).mean()
    assert abs(f_t - f_p) < 0.1
    assert p.W.diagonal().sum() == 0


def test_signflip_keeps_edges_and_permutes_signs(toy):
    p = shuffle_signs(toy, seed=0)
    assert (p.W.indices == toy.W.tocsr().indices).all() and (p.W.indptr == toy.W.tocsr().indptr).all()
    assert np.allclose(abs(p.W.data), abs(toy.W.tocsr().data))
    s_t, s_p = _row_signs(toy.W), _row_signs(p.W)
    assert (s_t == -1).sum() == (s_p == -1).sum()                     # same number of inhibitory neurons
    assert (s_t != s_p).any()


def test_controls_are_seeded_and_distinct(toy):
    for name in CONTROLS:
        a, b, c = make_control(toy, name, 0), make_control(toy, name, 0), make_control(toy, name, 1)
        assert (a.W != b.W).nnz == 0
        assert (a.W != c.W).nnz > 0


def test_parse_controls():
    assert parse_controls(None) == [] and parse_controls("") == []
    assert parse_controls("all") == list(CONTROLS)
    assert parse_controls("rewired, random") == ["rewired", "random"]
    with pytest.raises(ValueError):
        parse_controls("shuffled")
    with pytest.raises(ValueError):
        make_control(None, "nope")


def test_specificity_in_report_and_positive_task_fails_on_shuffled_wiring(toy):
    tasks = [t for t in load_tasks() if t["name"] in ("sugar_to_proboscis", "taste_specificity")]
    rep = run_suite(toy, LIFParams(gain=1.0, seed=0), tasks, controls=["rewired", "random"])
    assert rep["controls"] == ["rewired", "random"]
    by = {t["task"]: t for t in rep["tasks"]}
    sugar = by["sugar_to_proboscis"]
    assert set(sugar["controls"]) == {"rewired", "random"}
    assert sugar["passed"] and not sugar["controls"]["rewired"]["passed"] and not sugar["controls"]["random"]["passed"]
    assert sugar["specificity"] > 0 and not sugar["non_diagnostic"]
    # a null task ("bitter must NOT drive MN9") is passed by a dead network too; it is noted, not flagged
    null = by["taste_specificity"]
    assert not null["non_diagnostic"]
    assert any("null task" in n for n in null["notes"])
    assert rep["specificity"] == pytest.approx(np.mean([t["specificity"] for t in rep["tasks"]]))
    assert isinstance(rep["non_diagnostic"], list)


def test_no_controls_leaves_fields_empty(toy):
    tasks = [t for t in load_tasks() if t["name"] == "sugar_to_proboscis"]
    rep = run_suite(toy, LIFParams(gain=1.0, seed=0), tasks)
    t = rep["tasks"][0]
    assert t["controls"] == {} and t["specificity"] is None and t["non_diagnostic"] is False
    assert rep["controls"] == [] and rep["specificity"] is None


def test_jobs_gives_a_bit_identical_report(toy):
    """--jobs runs (task, wiring) units in worker processes that load the toy themselves; every
    number must match the serial run (only wall-clock differs)."""
    from flybench.bench import load_tasks, run_suite
    from flybench.sim import LIFParams
    tasks = [t for t in load_tasks() if t["name"] in ("stability", "sugar_to_proboscis", "taste_specificity")]
    p = LIFParams(seed=2)
    serial = run_suite(toy, p, tasks, seeds=2, controls=["rewired"])
    par = run_suite(toy, p, tasks, seeds=2, controls=["rewired"], jobs=2, connectome_ref="toy")
    import json
    for rep in (serial, par):
        for t in rep["tasks"]:
            t.pop("seconds")
    assert json.dumps(serial, sort_keys=True) == json.dumps(par, sort_keys=True)   # via JSON: NaN z-scores compare equal
    assert par["n_tasks"] == 3 and all(t["controls"]["rewired"] is not None for t in par["tasks"])
