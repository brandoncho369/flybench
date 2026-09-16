"""Pinned connectome artefacts (flybench.manifest): fingerprints are stable, sensitive to any edge
or label, and the toy pin tracks TOY_VERSION."""
import numpy as np
import pytest
import scipy.sparse as sp

from flybench.connectome import Connectome, load_connectome
from flybench.manifest import check_pinned, fingerprint, load_manifest
from flybench.toy import TOY_VERSION


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


def test_fingerprint_is_stable_and_sensitive(toy):
    a = fingerprint(toy)
    assert a == fingerprint(toy) and len(a) == 64
    # the same graph loaded through a different sparse layout fingerprints the same
    csc = Connectome(root_ids=toy.root_ids, W=toy.W.tocsc(), positions=toy.positions, annotations=toy.annotations, name="toy", meta=dict(toy.meta))
    assert fingerprint(csc) == a
    # one synapse more anywhere, or one label changed, is a different artefact
    W = toy.W.tolil(); W[0, 1] = W[0, 1] + 1
    assert fingerprint(Connectome(root_ids=toy.root_ids, W=sp.csr_matrix(W, dtype=np.float32), positions=toy.positions, annotations=toy.annotations, name="toy", meta=dict(toy.meta))) != a
    ann = toy.annotations.copy(); ann.loc[0, "cell_type"] = "renamed"
    assert fingerprint(Connectome(root_ids=toy.root_ids, W=toy.W, positions=toy.positions, annotations=ann, name="toy", meta=dict(toy.meta))) != a


def test_manifest_pins_the_toy_by_version_and_flags_mismatch(toy):
    man = load_manifest()
    assert set(man) >= {"toy", "flywire783", "malecns"}
    assert man["toy"]["version"] == TOY_VERSION, "toy.py changed: bump the toy entry in flybench/manifests.json (a rebuilt artefact is a new pin)"
    assert check_pinned(toy)["status"] == "pinned"
    old = Connectome(root_ids=toy.root_ids, W=toy.W, positions=toy.positions, annotations=toy.annotations, name="toy", meta={**toy.meta, "toy_version": "1999"})
    assert check_pinned(old)["status"] == "mismatch"
    private = Connectome(root_ids=toy.root_ids, W=toy.W, positions=toy.positions, annotations=toy.annotations, name="my-build", meta=dict(toy.meta))
    p = check_pinned(private)
    assert p["status"] == "unpinned" and p["expected"] is None and len(p["sha256"]) == 64
    for name in ("flywire783", "malecns"):
        assert len(man[name]["sha256"]) == 64 and man[name]["n_edges"] > 1_000_000


def test_run_refuses_a_mismatched_pin_unless_allowed(tmp_path, monkeypatch):
    """`flybench run` on a connectome whose fingerprint differs from its pin exits 2; with
    --allow-unpinned it runs and the result says unpinned."""
    import json
    from click.testing import CliRunner
    import flybench.connectome as fc
    from flybench.cli import main
    toy = load_connectome("toy")
    stale = Connectome(root_ids=toy.root_ids, W=toy.W, positions=toy.positions, annotations=toy.annotations, name="toy", meta={**toy.meta, "toy_version": "1999"})
    monkeypatch.setattr("flybench.cli.load_connectome", lambda name, cache=None: stale)
    runner = CliRunner()
    task = "tasks/01_stability.yaml"
    r = runner.invoke(main, ["run", "-c", "toy", "-t", task, "-o", str(tmp_path / "a.json")])
    assert r.exit_code == 2 and "does not match its pin" in r.output
    r = runner.invoke(main, ["run", "-c", "toy", "-t", task, "-o", str(tmp_path / "b.json"), "--allow-unpinned"])
    assert r.exit_code == 0, r.output
    rep = json.loads((tmp_path / "b.json").read_text())
    assert rep["unpinned"] is True and rep["connectome_meta"]["sha256"] == "1999"
