"""The embodied track (ROADMAP item 51, task 33): the body is a fixed transducer, the toy jumps to a loom and not at rest."""
import numpy as np
import pytest

from flybench.bench import load_tasks, run_task, task_unavailable
from flybench.connectome import load_connectome
from flybench.embodied.flygym_body import PROGRAM_MS, accepted_commands, available, run_body
from flybench.sim import LIFParams

pytestmark = pytest.mark.skipif(not available(), reason="flygym / mujoco not installed (pip install -e .[embodied])")


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


def test_commands_are_one_per_program():
    assert accepted_commands(np.array([300.0, 302.0, 305.0, 300.0 + PROGRAM_MS + 1, 900.0])) == [300.0, 300.0 + PROGRAM_MS + 1, 900.0]
    assert accepted_commands(np.array([])) == []


def test_body_takes_off_on_a_command_and_not_without_one():
    quiet = run_body([], 1000)
    assert not quiet.takeoff and quiet.n_commands == 0 and quiet.thorax_rise_mm == 0.0
    jump = run_body([250.0], 1000)
    assert jump.takeoff and 250.0 < jump.takeoff_ms < 250.0 + 30.0 and jump.thorax_rise_mm > 0.3
    again = run_body([250.0], 1000)                                  # deterministic physics, reset between runs
    assert again.takeoff_ms == jump.takeoff_ms


def test_toy_jumps_to_the_loom_and_not_at_rest(toy):
    task = next(t for t in load_tasks() if t["name"] == "embodied_loom_escape")
    assert task_unavailable(task, toy) is None
    r = run_task(task, toy, LIFParams(gain=0.8, seed=1))
    m = r.measurements
    assert m["loom"]["takeoff"] == 1.0 and 0 < m["loom"]["takeoff_latency_ms"] < 300
    assert m["baseline"]["takeoff"] == 0.0 and np.isnan(m["baseline"]["takeoff_latency_ms"])
    assert m["loom"]["n_commands"] >= 1 and m["loom"]["thorax_rise_mm"] > 0.3
    # the toy has TTMn, so the command readout is the muscle's motor neuron, not the GF stand-in
    assert not any("using 'gf'" in n for n in r.notes)


def test_gf_stand_in_when_there_is_no_nerve_cord(toy):
    task = next(t for t in load_tasks() if t["name"] == "embodied_loom_escape")
    task = {**task, "readouts": {**task["readouts"], "ttmn": {"select": {"cell_type": "NoSuchType"}}}}
    r = run_task(task, toy, LIFParams(gain=0.8, seed=1))
    assert any("using 'gf' + 0.93 ms" in n for n in r.notes)
    assert r.measurements["loom"]["takeoff"] == 1.0
