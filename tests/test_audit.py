"""ROADMAP item 47: the audit rejects tasks the shuffle also passes and flags tier claims a run contradicts."""
import copy

import pytest

from flybench.audit import audit_task, markdown
from flybench.bench import load_tasks
from flybench.connectome import load_connectome
from flybench.sim import LIFParams

GAIN = 0.8


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


@pytest.fixture(scope="module")
def sugar():
    return next(t for t in load_tasks() if t["name"] == "sugar_to_proboscis")


def test_a_real_reflex_task_is_ok(toy, sugar):
    a = audit_task(sugar, toy, LIFParams(gain=GAIN), seeds=2)
    assert a.ran and a.passed and a.verdict == "ok" and a.control_scores["rewired"] < 1.0
    assert "| sugar_to_proboscis | core |" in markdown([a], "toy", GAIN, 2)


def test_reading_out_the_stimulated_cells_is_rejected_as_non_diagnostic(toy, sugar):
    # "the cells I drive fire" passes on any wiring at all: the shuffle passes it, the audit refuses it
    t = copy.deepcopy(sugar)
    t["name"] = "grns_fire"; t["tier"] = "hard"
    t["readout"] = {"select": t["conditions"]["sugar"]["stimuli"][0]["select"]}
    t["checks"] = [{"type": "rate", "cond": "sugar", "op": ">", "value": 5, "basis": "convention: response"}]
    a = audit_task(t, toy, LIFParams(gain=GAIN), seeds=2)
    assert a.non_diagnostic and a.verdict == "reject"
    assert any("non-diagnostic" in p for p in a.problems)
    assert "❌ reject" in markdown([a], "toy", GAIN, 2)


def test_tier_claims_are_checked_against_the_run(toy, sugar):
    hard = copy.deepcopy(sugar); hard["tier"] = "hard"
    a = audit_task(hard, toy, LIFParams(gain=GAIN), seeds=2)
    assert a.verdict == "warn" and "tier: hard but the reference passes" in a.tier_mismatch
    core_fail = copy.deepcopy(sugar)
    core_fail["checks"] = [{"type": "rate", "cond": "sugar", "op": ">", "value": 1e6, "basis": "convention: impossible"}]
    a = audit_task(core_fail, toy, LIFParams(gain=GAIN), seeds=2)
    assert a.verdict == "warn" and "tier: core but the reference scores 0.00" in a.tier_mismatch


def test_trivial_hard_task_is_flagged(toy, sugar):
    t = copy.deepcopy(sugar); t["tier"] = "hard"
    t["checks"] = [{"type": "rate", "cond": "sugar", "op": ">", "value": 0.01, "basis": "convention: any spike at all"}]
    a = audit_task(t, toy, LIFParams(gain=GAIN), seeds=2)
    assert a.trivial and a.min_margin >= 1.0 and any("trivial" in p for p in a.problems)


def test_null_only_task_cannot_be_non_diagnostic(toy):
    t = next(t for t in load_tasks() if t["name"] == "taste_specificity")
    a = audit_task(t, toy, LIFParams(gain=GAIN), seeds=2)
    assert a.passed and not a.non_diagnostic and a.verdict == "ok"
    assert any("null task" in n for n in a.notes)


def test_task_this_dataset_cannot_run_is_a_warning_not_a_verdict(toy):
    t = next(t for t in load_tasks() if t["name"] == "steering_dna02_vs_dna01")   # MaleCNS-only
    t = copy.deepcopy(t); t["dataset_only"] = ["malecns"]
    a = audit_task(t, toy, LIFParams(gain=GAIN), seeds=1)
    assert not a.ran and a.verdict == "warn" and a.reason
