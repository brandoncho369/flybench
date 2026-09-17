"""The flyvis front end (flybench.frontends.flyvis_frontend): the cached output drives the right cells
at the right times without torch; the mapping and the per-neuron rate series behave; tasks that need
the front end skip cleanly when it is neither cached nor installed."""
import copy

import numpy as np
import pytest
import yaml

from flybench.bench import TASK_DIR, load_tasks, run_task, task_unavailable
from flybench.connectome import load_connectome
from flybench.frontends import flyvis_frontend as fv
from flybench.lint import lint_task
from flybench.sim import LIFParams, LIFSimulator, Stimulus


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


def test_cache_is_committed_and_well_formed():
    for name in ("loom", "flash", "recede", "dimming"):
        assert fv.cached(name), f"data/frontends/flyvis/{name}.npz missing: run `flybench frontend flyvis render`"
        cols, rates, meta = fv.load_cache(name)
        assert cols.shape == (721, 2) and meta["stimulus"] == name and meta["bin_ms"] == fv.BIN_MS
        assert set(rates) >= {"T4a", "T5a", "Tm3"} and all(r.shape == (100, 721) and (r >= 0).all() for r in rates.values())
    _, loom, _ = fv.load_cache("loom"); _, flash, _ = fv.load_cache("flash")
    # the first 100 ms of every movie is the grey field: rates there are ~0 (activity relative to rest)
    assert loom["T5a"][:10].mean() < 2.0 and flash["T4a"][:10].mean() < 2.0
    # a dark loom drives T5 (OFF-edge motion) late; a brightening drives T4 (ON) at onset
    assert loom["T5a"][80:].mean() > loom["T5a"][10:40].mean()
    assert flash["T4a"][20:30].max() > 50 and flash["T4a"][20:30].max() > loom["T4a"].max()


def test_hex_mapping_is_a_bijection_on_the_lattice_and_spreads_somata():
    cols, _, _ = fv.load_cache("loom")
    xy = fv.hex_to_xy(cols)
    assert np.abs(xy).max() <= 1.0 + 1e-9
    # positions that are exactly the lattice (rotated, scaled) map onto nearly every column exactly once: the
    # mapping is retinotopic up to a rotation (a disc's principal axes are arbitrary), as the module says
    theta = 0.7; R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    pos3d = np.column_stack([xy @ R.T * 37.0, np.zeros(len(xy))])
    m = fv.map_neurons_to_columns(pos3d, cols)
    assert len(np.unique(m)) > 600
    # and neighbours stay neighbours: the columns two lattice-neighbours land on are close on the lattice
    d_in = np.linalg.norm(xy[0] - xy[1]); d_out = np.linalg.norm(xy[m[0]] - xy[m[1]])
    assert d_out < 4 * d_in
    # a random blob of somata is spread over many columns, and NaN positions get a column too
    rng = np.random.default_rng(0)
    blob = rng.normal(size=(700, 3)) * [30, 30, 3]
    m = fv.map_neurons_to_columns(blob, cols)
    assert len(np.unique(m)) > 200 and m.min() >= 0 and m.max() < 721
    blob[:5] = np.nan
    assert np.isfinite(fv.map_neurons_to_columns(blob, cols)).all()


def test_rate_series_stimulus_drives_neurons_per_bin(toy):
    grn = toy.select("GRN_sugar")
    series = np.zeros((grn.size, 50), dtype=np.float32)      # 500 ms in 10 ms bins
    series[: grn.size // 2, 10:20] = 200.0                     # half the neurons, 100 ms burst at 100-200 ms after onset
    st = Stimulus(neurons=grn, rate_hz=0.0, t_start_ms=200, t_end_ms=700, rate_series_hz=series, series_bin_ms=10.0)
    assert st.rates_at(250).sum() == 0 and st.rates_at(350)[0] == 200.0 and st.rates_at(350)[-1] == 0.0
    res = LIFSimulator(toy, LIFParams(gain=0.01, seed=0)).run(900, [st])
    first, second = grn[: grn.size // 2], grn[grn.size // 2:]
    assert res.rate_hz(first, 300, 400) > 120 and res.rate_hz(first, 500, 700) < 5 and res.rate_hz(second, 200, 700) < 5


def test_stimuli_from_cache_on_the_toy(toy):
    stims, sizes = fv.stimuli_from_cache(toy, "loom", t_start_ms=200.0)
    assert set(sizes) == {f"T{k}{s}" for k in "45" for s in "abcd"} and all(v == 24 for v in sizes.values())
    st = next(s for s in stims if s.name == "loom:T5a")
    assert st.rate_series_hz.shape == (24, 100) and st.t_end_ms == 1200.0 and st.series_bin_ms == 10.0


def test_task32_lints_runs_on_toy_and_skips_without_the_front_end(toy, monkeypatch):
    t32 = next(t for t in load_tasks() if t["name"] == "flyvis_loom_escape")
    raw = yaml.safe_load((TASK_DIR / "32_flyvis_loom_escape.yaml").read_text(encoding="utf-8"))
    assert lint_task(raw) == [] and raw["requires_frontends"] == ["flyvis"]
    bad = copy.deepcopy(raw); bad.pop("requires_frontends")
    assert any("requires_frontends" in e for e in lint_task(bad))
    bad = copy.deepcopy(raw); bad["conditions"]["loom"]["stimuli"][0]["stimulus"] = "explosion"
    assert any("flyvis stimulus" in e for e in lint_task(bad))
    assert task_unavailable(t32, toy) is None
    r = run_task(t32, toy, LIFParams(seed=0))
    assert r.passed and r.score == 1.0 and r.stimulus_sizes["loom"] == 192
    assert "rate[gf]" in r.measurements["flash"]          # the flash is measured, not scored
    # no cache and no flyvis -> skipped with a reason, never a fail
    monkeypatch.setattr(fv, "cached", lambda name: False)
    monkeypatch.setattr(fv, "available", lambda: False)
    why = task_unavailable(t32, toy)
    assert why and "not cached" in why and "not installed" in why
    # a dataset without the optic-lobe types skips too
    from flybench.connectome import Connectome
    monkeypatch.undo()
    ann = toy.annotations.copy(); ann.loc[ann["cell_type"].str.match(r"^T[45]"), "cell_type"] = "gone"
    blind = Connectome(root_ids=toy.root_ids, W=toy.W, positions=toy.positions, annotations=ann, name="toy", meta=dict(toy.meta))
    assert "none of its output cell types" in (task_unavailable(t32, blind) or "")
