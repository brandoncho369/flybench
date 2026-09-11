"""fetch-neuprint end to end against a fake server: fetch -> build -> simulate."""
import re

import numpy as np
import pandas as pd

from flybench import fetch_neuprint as fnp
from flybench.connectome import build_from_codex
from flybench.sim import LIFParams, LIFSimulator, Stimulus

# a 6-neuron fake male-cns: 2 sugar GRNs -> 1 interneuron -> MN9, one GABA neuron, one isolated
BODIES = [
    dict(bodyId=10, type="GRN_sugar", instance="sugar_L", superclass="sensory", subclass="gustatory", predictedNt="acetylcholine", somaSide="L", somaLocation={"coordinates": [1, 2, 3]}),
    dict(bodyId=11, type="GRN_sugar", instance="sugar_R", superclass="sensory", subclass="gustatory", predictedNt="acetylcholine", somaSide="R", somaLocation=[4, 5, 6]),
    dict(bodyId=20, type="IN1", instance="IN1_L", superclass="intrinsic", subclass=None, predictedNt="acetylcholine", somaSide="L", somaLocation=None),
    dict(bodyId=30, type="MN9", instance="MN9_L", superclass="motor", subclass=None, predictedNt="acetylcholine", somaSide="L", somaLocation=None),
    dict(bodyId=40, type="GABA_x", instance=None, superclass="intrinsic", subclass=None, predictedNt="gaba", somaSide=None, somaLocation=None),
    dict(bodyId=50, type=None, instance=None, superclass=None, subclass=None, predictedNt=None, somaSide=None, somaLocation=None),
]
EDGES = [(10, 20, 60), (11, 20, 50), (20, 30, 80), (40, 30, 7), (10, 11, 2)]  # last one is below threshold


class FakeNeuPrint:
    def __init__(self, *a, **k):
        self.calls = []

    def query(self, cypher):
        self.calls.append(cypher)
        rng = re.search(r"bodyId >= (\d+) AND \w+\.bodyId <= (\d+)", cypher)
        lo, hi = (int(rng.group(1)), int(rng.group(2))) if rng else (0, 10**9)
        if "ConnectsTo" in cypher:
            w = int(re.search(r"c\.weight >= (\d+)", cypher).group(1))
            rows = [(a, b, s) for a, b, s in EDGES if lo <= a <= hi and s >= w]
            return pd.DataFrame(rows, columns=["pre_root_id", "post_root_id", "syn_count"])
        if "RETURN n.bodyId AS id" in cypher:
            return pd.DataFrame({"id": [b["bodyId"] for b in BODIES]})
        cols = [c for c in fnp.NEURON_FIELDS.values()]
        rows = [[b.get(k) for k in fnp.NEURON_FIELDS] for b in BODIES if lo <= b["bodyId"] <= hi]
        return pd.DataFrame(rows, columns=cols)


def test_fetch_then_build_then_simulate(tmp_path, monkeypatch):
    monkeypatch.setattr(fnp, "NeuPrint", FakeNeuPrint)
    out = fnp.fetch(tmp_path / "raw", dataset="male-cns:v1.0", chunk=2, log=lambda *_: None)
    for f in ("connections.csv.gz", "neurons.csv.gz", "classification.csv.gz", "coordinates.csv.gz", "labels.csv.gz", "fetch_meta.json"):
        assert (out / f).exists(), f

    c = build_from_codex(out, min_synapses=5, name="malecns")
    assert c.n == 6 and c.n_edges == 4                     # the 2-synapse edge is dropped
    ann = c.annotations
    assert set(ann["root_id"]) == {10, 11, 20, 30, 40, 50}
    assert ann.loc[ann.root_id == 30, "cell_type"].item() == "MN9"        # type -> cell_type
    assert ann.loc[ann.root_id == 10, "sub_class"].item() == "gustatory"  # subclass -> sub_class
    assert ann.loc[ann.root_id == 10, "nt_type"].item() == "ACH"
    assert ann.loc[ann.root_id == 40, "nt_type"].item() == "GABA"
    assert ann.loc[ann.root_id == 10, "labels"].item() == "sugar_L"       # instance -> labels
    # GABA neuron's outgoing edge is negative; the rest positive
    i40, i30 = c.index_of([40]).item(), c.index_of([30]).item()
    assert c.W[i40, i30] < 0 and c.W[c.index_of([20]).item(), i30] > 0
    # soma positions in nm (8 nm voxels), both dict and list forms parsed
    assert np.allclose(c.positions[c.index_of([10]).item()], [8, 16, 24])
    assert np.allclose(c.positions[c.index_of([11]).item()], [32, 40, 48])
    assert np.isnan(c.positions[i30]).all()

    # selectors work on the mapped columns, and the fake reflex runs
    sugar = c.select({"cell_type": "GRN_sugar"})
    mn9 = c.select("MN9")
    assert len(sugar) == 2 and len(mn9) == 1
    sim = LIFSimulator(c, LIFParams(gain=0.65, seed=0))
    r = sim.run(300, [Stimulus(sugar, 200.0, 0, 300)])
    assert r.rate_hz(mn9) > 0

    # resumable: a second call re-uses the edge chunks
    fake = FakeNeuPrint()
    monkeypatch.setattr(fnp, "NeuPrint", lambda *a, **k: fake)
    fnp.fetch(tmp_path / "raw", chunk=2, log=lambda *_: None)
    assert not any("ConnectsTo" in q for q in fake.calls)
