"""RFC M1: a synapse on a neuron's axon terminal does not fire the neuron; it scales its release."""
import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp

from flybench.bench import load_tasks, run_suite, silence_neurons
from flybench.connectome import Connectome, load_connectome
from flybench.models.terminal_lif import RELEASE_FLOOR, TerminalLIFSimulator
from flybench.sim import LIFParams, LIFSimulator, Stimulus


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


def _three(terminal: bool):
    # 0 -> 1 with 60 synapses; 2 -> 1 with 60 inhibitory synapses; 1 -> 3 with 200 synapses
    W = sp.csr_matrix((np.array([60.0, -60.0, 200.0], dtype=np.float32), ([0, 2, 1], [1, 1, 3])), shape=(4, 4))
    T = None
    if terminal:
        # the inhibitory contact from 2 sits on 1's axon terminal, not its dendrite
        T = sp.csr_matrix((np.array([-60.0], dtype=np.float32), ([2], [1])), shape=(4, 4))
    ann = pd.DataFrame({"root_id": [0, 1, 2, 3], "cell_type": ["A", "B", "C", "D"], "super_class": [""] * 4})
    return Connectome(root_ids=np.arange(4), W=W, positions=np.zeros((4, 3)), annotations=ann, name="t3", terminal=T)


def _rates(c, Sim, drive_c: bool):
    stims = [Stimulus(np.array([0]), 200.0, 0, 500)] + ([Stimulus(np.array([2]), 200.0, 0, 500)] if drive_c else [])
    res = Sim(c, LIFParams(gain=1.0, seed=0)).run(500, stims)
    return {i: res.rate_hz(np.array([i]), 0, 500) for i in range(4)}


def test_terminal_input_does_not_fire_the_cell_but_damps_its_output():
    plain = _three(False); term = _three(True)
    # C alone (inhibitory) never fires B in either model; A drives B, B drives D
    a = _rates(plain, LIFSimulator, drive_c=False); assert a[1] > 50 and a[3] > 20
    # somatic inhibition from C silences B and hence D in the reference model
    b = _rates(plain, LIFSimulator, drive_c=True); assert b[1] < a[1] * 0.5
    # with the contact on the terminal, B still fires (its soma sees no inhibition; the small drop is the
    # shared Poisson stream shifting A's spikes when a second stimulus is drawn) …
    t = _rates(term, TerminalLIFSimulator, drive_c=True); assert t[1] > 0.8 * a[1] and t[1] > 5 * b[1]
    # … but its release is scaled down, so D fires less than without terminal inhibition, never below the floor
    t0 = _rates(term, TerminalLIFSimulator, drive_c=False)
    assert t0[3] == pytest.approx(a[3], rel=0.05) and t[3] < t0[3]
    sim = TerminalLIFSimulator(term, LIFParams()); sim.d[1] = -100.0
    assert sim.release(np.array([1]))[0] == pytest.approx(RELEASE_FLOOR)
    assert sim.release(np.array([0]))[0] == 1.0


def test_without_terminal_data_it_is_the_reference_bit_for_bit(toy):
    assert toy.terminal is None
    task = next(t for t in load_tasks() if t["name"] == "sugar_to_proboscis")
    a = run_suite(toy, LIFParams(gain=0.8), [task])["tasks"][0]
    b = run_suite(toy, LIFParams(gain=0.8), [task], simulator=TerminalLIFSimulator)["tasks"][0]
    assert a["measurements"] == b["measurements"] and b["score"] == a["score"]


def test_silencing_and_perturbing_keep_the_terminal_matrix():
    from flybench.bench import perturb_weights
    c = _three(True)
    s = silence_neurons(c, np.array([2]))
    assert s.terminal is not None and s.terminal.nnz == 0          # the silenced neuron's terminal contact goes with its output
    p = perturb_weights(c, 0.25, seed=0)
    assert p.terminal is not None and p.terminal.nnz == 1
