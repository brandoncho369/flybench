"""Edge cases across the whole pipeline: loader, selectors, simulator, bench, export, CLI."""
import json

import numpy as np
import pandas as pd
import pytest
import yaml
from click.testing import CliRunner

from flybench import LIFParams, LIFSimulator, Stimulus, select
from flybench.bench import TASK_DIR, leaderboard, load_tasks, resolve_simulator, run_suite, run_task, save_report
from flybench.cli import main
from flybench.connectome import Connectome, build_from_codex
from flybench.export import export_web
from flybench.lint import lint_files, lint_task
from flybench.toy import build_toy_connectome


@pytest.fixture(scope="module")
def toy():
    return build_toy_connectome()


# ---------------------------------------------------------------- codex loader

def _codex_dir(tmp_path, *, coords=True, cell_types=True, labels=True, extra_conn_rows=()):
    ids = [100, 200, 300, 400, 500]
    conn = [(100, 200, "A", 3, "ACH"), (100, 200, "B", 4, "ACH"),   # 3+4=7 across neuropils -> kept
            (200, 300, "A", 4, "GABA"),                            # 4 < 5 -> dropped
            (300, 400, "A", 20, "ACH"), (400, 500, "A", 9, "GLUT"), (500, 100, "A", 6, "DA"),
            (999, 100, "A", 50, "ACH"),                           # pre not in neurons.csv -> still a neuron
            *extra_conn_rows]
    pd.DataFrame(conn, columns=["pre_root_id", "post_root_id", "neuropil", "syn_count", "nt_type"]).to_csv(tmp_path / "connections.csv.gz", index=False)
    pd.DataFrame({"root_id": ids, "nt_type": ["ACH", "GABA", "ACH", "GLUT", "DA"], "group": ["g"] * 5}).to_csv(tmp_path / "neurons.csv.gz", index=False)
    pd.DataFrame({"root_id": ids, "super_class": ["sensory", "central", "central", "motor", "descending"],
                  "class": ["gustatory", "", "", "", ""], "sub_class": ["sugar/water", "", "", "", ""], "side": ["left"] * 5}).to_csv(tmp_path / "classification.csv.gz", index=False)
    if labels:
        pd.DataFrame({"root_id": [100, 100, 400], "label": ["sugar GRN", "Gr64f", "Motor neuron 9; MN9"]}).to_csv(tmp_path / "labels.csv.gz", index=False)
    if coords:
        pd.DataFrame({"root_id": [100, 100, 200, 300, 400], "position": ["[1 2 3]", "[9 9 9]", "[4 5 6]", "garbage", "[10 11 12]"]}).to_csv(tmp_path / "coordinates.csv.gz", index=False)
    if cell_types:
        pd.DataFrame({"root_id": [200, 400, 500], "primary_type": ["G2N", "CB0701", "DNp01"]}).to_csv(tmp_path / "consolidated_cell_types.csv.gz", index=False)
    return tmp_path


def test_codex_build_full(tmp_path):
    c = build_from_codex(_codex_dir(tmp_path))
    assert c.n == 6                                   # 5 listed + 999 seen only in connections
    W = c.W.toarray()
    i = {r: k for k, r in enumerate(c.root_ids)}
    assert W[i[100], i[200]] == 7                     # summed across neuropils
    assert W[i[200], i[300]] == 0                     # below min_synapses
    assert W[i[400], i[500]] == -9                    # GLUT presyn -> inhibitory
    assert W[i[500], i[100]] == 6                     # DA -> excitatory
    assert W[i[999], i[100]] == 50                    # unknown nt -> excitatory
    assert np.allclose(c.positions[i[100]], [1, 2, 3])  # first coordinate wins on duplicates
    assert np.isnan(c.positions[i[300]]).all()        # garbage position -> NaN
    assert np.isnan(c.positions[i[999]]).all()
    assert list(c.select("CB0701")) == [i[400]]
    assert list(c.select({"labels_regex": r"\bMN9\b", "super_class": "motor"})) == [i[400]]
    assert len(c.select({"sub_class": "sugar/water"})) == 1
    assert c.meta["min_synapses"] == 5


def test_codex_build_without_optional_files(tmp_path):
    c = build_from_codex(_codex_dir(tmp_path, coords=False, cell_types=False, labels=False))
    assert c.n == 6
    assert np.isnan(c.positions).all()
    assert "labels" not in c.annotations.columns
    assert len(c.select("CB0701")) == 0                # no cell types -> selector returns empty, does not crash


def test_codex_build_min_synapses_override(tmp_path):
    c = build_from_codex(_codex_dir(tmp_path), min_synapses=1)
    assert c.n_edges == 6


def test_codex_missing_required_file(tmp_path):
    (tmp_path / "neurons.csv.gz").write_bytes(b"")
    with pytest.raises(FileNotFoundError):
        build_from_codex(tmp_path)


def test_save_load_roundtrip(tmp_path, toy):
    p = toy.save(tmp_path / "c")
    c2 = Connectome.load(p)
    assert c2.n == toy.n and c2.n_edges == toy.n_edges
    assert (c2.W != toy.W).nnz == 0
    assert np.allclose(c2.positions, toy.positions)
    assert len(c2.select("MN9")) == 2


# ---------------------------------------------------------------- selectors

def test_selector_edge_cases(toy):
    ann = toy.annotations
    assert len(select(ann, {})) == 0
    assert len(select(ann, {"all": False})) == 0
    assert len(select(ann, {"any": []})) == 0
    assert len(select(ann, {"all_of": []})) == toy.n
    assert len(select(ann, {"not": {"all": True}})) == 0
    assert len(select(ann, ["MN9", "GF"])) == 4                     # list shorthand = any
    assert len(select(ann, {"cell_type": ["MN9", "GF"]})) == 4       # isin
    assert len(select(ann, {"cell_type": "mn9"})) == 0               # exact match is case-sensitive
    assert len(select(ann, {"cell_type_regex": "^mn9$"})) == 2       # regex is not
    assert len(select(ann, {"cell_type_regex": "^(MN9|GF)$"})) == 4  # regex groups are fine
    assert len(select(ann, {"root_ids": [int(toy.root_ids[0]), 12345]})) == 1
    assert len(select(ann, {"nonexistent_column_regex": "x"})) == 0


# ---------------------------------------------------------------- simulator

def test_sim_determinism(toy):
    grn = toy.select({"labels_regex": "sugar"})
    a = LIFSimulator(toy, LIFParams(seed=7)).run(300, [Stimulus(grn, 100)])
    b = LIFSimulator(toy, LIFParams(seed=7)).run(300, [Stimulus(grn, 100)])
    assert np.array_equal(a.spike_times_ms, b.spike_times_ms) and np.array_equal(a.spike_neurons, b.spike_neurons)
    c = LIFSimulator(toy, LIFParams(seed=8)).run(300, [Stimulus(grn, 100)])
    assert not np.array_equal(a.spike_neurons, c.spike_neurons)


def test_sim_reset_gives_identical_conditions(toy):
    """Each run() must start from the same RNG state so conditions in a task are comparable."""
    sim = LIFSimulator(toy, LIFParams(seed=1))
    grn = toy.select({"labels_regex": "sugar"})
    r1 = sim.run(200, [Stimulus(grn, 100)])
    r2 = sim.run(200, [Stimulus(grn, 100)])
    assert np.array_equal(r1.spike_neurons, r2.spike_neurons)


def test_sim_degenerate_inputs(toy):
    sim = LIFSimulator(toy, LIFParams())
    assert len(sim.run(0).spike_times_ms) == 0
    assert len(sim.run(50, [Stimulus(np.empty(0, dtype=int), 100)]).spike_times_ms) == 0
    # stimulus entirely outside the run -> nothing
    grn = toy.select({"labels_regex": "sugar"})
    assert len(sim.run(50, [Stimulus(grn, 100, t_start_ms=500, t_end_ms=600)]).spike_times_ms) == 0
    # zero-rate stimulus -> nothing
    assert len(sim.run(50, [Stimulus(grn, 0.0)]).spike_times_ms) == 0


def test_sim_delay_and_dt_edge(toy):
    p = LIFParams(delay_ms=0.05, dt_ms=0.1)   # delay < dt -> clamps to 1 step, must not crash
    sim = LIFSimulator(toy, p)
    assert sim.delay_steps == 1
    grn = toy.select({"labels_regex": "sugar"})
    res = sim.run(100, [Stimulus(grn, 100)])
    assert len(res.spike_times_ms) > 0


def test_sim_gain_zero_only_forced_spikes(toy):
    grn = toy.select({"labels_regex": "sugar"})
    res = LIFSimulator(toy, LIFParams(gain=0.0)).run(200, [Stimulus(grn, 100)])
    assert set(np.unique(res.spike_neurons)) <= set(grn)


def test_simresult_metrics(toy):
    grn = toy.select({"labels_regex": "sugar"})
    res = LIFSimulator(toy, LIFParams()).run(200, [Stimulus(grn, 100)])
    assert np.isnan(res.rate_hz(np.empty(0, dtype=int)))
    assert res.rate_hz(grn, 0, 200) == pytest.approx(100, rel=0.35)
    assert 0 < res.active_fraction() <= 1
    assert res.counts().sum() == len(res.spike_times_ms)
    assert res.rate_hz(grn, 150, 100) >= 0      # inverted window degenerates to 0, not crash


# ---------------------------------------------------------------- bench

def _task(**over):
    t = {
        "name": "t", "title": "t", "citation": "x", "duration_ms": 300, "window": [100, 300],
        "readout": {"select": "MN9"},
        "conditions": {"baseline": {"stimuli": []},
                       "sugar": {"stimuli": [{"select": {"labels_regex": "sugar", "super_class": "sensory"}, "rate_hz": 100, "t_start_ms": 50, "t_end_ms": 300}]}},
        "checks": [{"type": "rate", "cond": "sugar", "op": ">", "value": 5}],
    }
    t.update(over)
    return t


def test_task_empty_readout_fails_not_crashes(toy):
    r = run_task(_task(readout={"select": {"cell_type": "NOPE"}}), toy, LIFParams())
    assert not r.passed and np.isnan(r.checks[0].value)
    assert any("matched 0" in n for n in r.notes)


def test_task_empty_stimulus_noted(toy):
    t = _task(conditions={"sugar": {"stimuli": [{"select": {"cell_type": "NOPE"}, "rate_hz": 100}]}})
    r = run_task(t, toy, LIFParams())
    assert any("stimulus" in n and "matched 0" in n for n in r.notes)
    assert r.checks[0].value == 0.0


def test_task_ratio_against_silent_baseline(toy):
    t = _task(checks=[{"type": "ratio", "cond": "sugar", "over": "baseline", "op": ">", "value": 5}])
    r = run_task(t, toy, LIFParams())
    assert r.passed and np.isfinite(r.checks[0].value)


def test_task_windows_and_multi_readouts(toy):
    t = _task(
        readouts={"mn9": {"select": "MN9"}, "gf": {"select": "GF"}},
        checks=[
            {"type": "rate", "cond": "sugar", "readout": "mn9", "op": ">", "value": 5, "window": [150, 300]},
            {"type": "rate", "cond": "sugar", "readout": "gf", "op": "<", "value": 1},
            {"type": "rate", "cond": "sugar", "readout": "mn9", "op": "<", "value": 1, "window": [0, 40]},   # before stimulus
            {"type": "readout_active_fraction", "cond": "sugar", "readout": "mn9", "op": ">", "value": 0.5},
            {"type": "ratio", "cond": "sugar", "over": "sugar", "readout": "mn9", "op": ">", "value": 0.5, "window": [200, 300], "over_window": [150, 300]},
        ])
    del t["readout"]
    r = run_task(t, toy, LIFParams())
    assert r.passed, [c.description for c in r.checks if not c.passed]
    assert r.readout_size == 2


def test_task_unknown_check_type_raises(toy):
    with pytest.raises(ValueError):
        run_task(_task(checks=[{"type": "vibes", "cond": "sugar", "op": ">", "value": 1}]), toy, LIFParams())


def test_suite_tiers_and_scores(toy):
    core = load_tasks(tier="core"); hard = load_tasks(tier="hard"); everything = load_tasks(tier="all")
    assert len(core) == 5 and len(hard) == 9 and len(everything) == 14
    assert {t["tier"] for t in hard} == {"hard"} and all(t.get("tier", "core") == "core" for t in core)
    report = run_suite(toy, LIFParams(), core)
    assert report["core_score"] == 1.0 and report["hard_score"] is None
    assert report["simulator"].endswith("LIFSimulator")


def test_report_roundtrip_and_leaderboard(toy, tmp_path):
    r1 = run_suite(toy, LIFParams(gain=1.0), load_tasks(tier="core")); r1["label"] = "a"
    r2 = run_suite(toy, LIFParams(gain=0.2), load_tasks(tier="core")[:3]); r2["label"] = "b"   # fewer tasks
    p = save_report(r1, tmp_path / "r" / "a.json")
    assert json.loads(p.read_text())["label"] == "a"
    md = leaderboard([r2, r1])
    lines = md.splitlines()
    assert lines[2].startswith("| a |")           # ranked by core score, not input order
    assert "–" in lines[3]                        # missing tasks shown as dash
    assert leaderboard([]) == "_no results_"


def test_resolve_simulator():
    assert resolve_simulator(None) is LIFSimulator
    assert resolve_simulator("flybench.sim:LIFSimulator") is LIFSimulator
    with pytest.raises((ImportError, AttributeError)):
        resolve_simulator("flybench.sim:Nope")


class _ConstantSim:
    """A 'model' that fires MN9 constantly no matter what — must fail negative controls."""
    def __init__(self, c, params):
        self.c, self.n = c, c.n
        self.mn9 = c.select("MN9")
    def run(self, duration_ms, stimuli):
        from flybench.sim import SimResult
        t = np.arange(0, duration_ms, 3.0, dtype=np.float32)
        return SimResult(np.repeat(t, len(self.mn9)), np.tile(self.mn9, len(t)).astype(np.int32), duration_ms, self.n)


def test_custom_simulator_cannot_game_negative_controls(toy):
    report = run_suite(toy, LIFParams(), load_tasks(tier="core"), simulator=_ConstantSim)
    by = {t["task"]: t for t in report["tasks"]}
    assert by["sugar_to_proboscis"]["passed"] is False      # ratio over baseline fails (baseline also fires)
    assert by["taste_specificity"]["passed"] is False
    assert by["bitter_suppression"]["passed"] is False
    # note: `stability` alone does NOT catch this (2 neurons firing is a tiny network rate) — the
    # negative-control tasks are what make a constant-output model lose. Keep them.
    assert report["core_score"] <= 0.6


# ---------------------------------------------------------------- lint

def test_lint_shipped_tasks_clean():
    assert lint_files(sorted(TASK_DIR.glob("*.yaml"))) == {}


def test_lint_catches_problems():
    bad = _task(checks=[{"type": "rate", "cond": "nope", "op": "≈", "value": 1},
                        {"type": "ratio", "cond": "sugar", "over": "baseline", "op": ">", "value": 1, "readout": "ghost"},
                        {"type": "rate", "cond": "sugar", "op": ">", "value": 1, "window": [200, 900]}])
    bad["tier"] = "medium"; del bad["citation"]
    errs = lint_task(bad)
    joined = "\n".join(errs)
    for needle in ("cond 'nope'", "unknown op", "readout 'ghost'", "window", "tier", "citation"):
        assert needle in joined, needle


def test_lint_duplicate_names(tmp_path):
    for i in range(2):
        (tmp_path / f"t{i}.yaml").write_text(yaml.safe_dump(_task()))
    problems = lint_files(sorted(tmp_path.glob("*.yaml")))
    assert any("duplicate" in e for errs in problems.values() for e in errs)


# ---------------------------------------------------------------- export

def test_export_handles_nan_positions_and_empty_populations(toy, tmp_path):
    c = Connectome(toy.root_ids, toy.W, toy.positions.copy(), toy.annotations.copy(), name="t")
    c.positions[:10] = np.nan
    out = export_web(c, tmp_path / "w", sets={"MN9": "MN9", "ghost": {"cell_type": "NOPE"}})
    pos = np.frombuffer((out / "positions.bin").read_bytes(), dtype=np.float32).reshape(-1, 3)
    assert np.isfinite(pos).all()
    meta = json.loads((out / "meta.json").read_text())
    assert "MN9" in meta["populations"] and "ghost" not in meta["populations"]
    cls = np.frombuffer((out / "classes.bin").read_bytes(), dtype=np.uint8)
    assert cls.max() < len(meta["classes"])
    indptr = np.frombuffer((out / "indptr.bin").read_bytes(), dtype=np.int32)
    assert len(indptr) == c.n + 1 and indptr[-1] == c.n_edges


# ---------------------------------------------------------------- CLI

def test_cli_end_to_end(tmp_path):
    cache = tmp_path / "cache"
    r = CliRunner()
    assert r.invoke(main, ["toy", "--cache", str(cache)]).exit_code == 0
    res = r.invoke(main, ["run", "--cache", str(cache), "--tier", "core", "--gain", "1.0", "-o", str(tmp_path / "res" / "a.json"), "--label", "a"])
    assert res.exit_code == 0, res.output
    assert "5/5" in res.output
    res = r.invoke(main, ["compare", str(tmp_path / "res"), "-o", str(tmp_path / "L.md")])
    assert res.exit_code == 0 and "| a |" in (tmp_path / "L.md").read_text()
    res = r.invoke(main, ["select", "--cache", str(cache), "{cell_type: MN9}"])
    assert res.exit_code == 0 and "2 neurons" in res.output
    res = r.invoke(main, ["export", "--cache", str(cache), "-o", str(tmp_path / "web")])
    assert res.exit_code == 0 and (tmp_path / "web" / "meta.json").exists()
    assert r.invoke(main, ["lint"]).exit_code == 0
    res = r.invoke(main, ["run", "--cache", str(cache), "-c", "does-not-exist"])
    assert res.exit_code != 0


# ---------------------------------------------------------------- submissions: validate / verify / seeds

def test_run_suite_report_validates(toy):
    from flybench.validate import validate_report
    report = run_suite(toy, LIFParams(), load_tasks(tier="core")); report["label"] = "t"
    assert validate_report(report) == []
    assert report["schema"] == 1 and report["seeds"] == 1 and report["verified"] is False


def test_validate_rejects_tampering(toy, tmp_path):
    from flybench.validate import validate_files, validate_report
    report = run_suite(toy, LIFParams(), load_tasks(tier="core")); report["label"] = "t"
    bad = json.loads(json.dumps(report)); bad["tasks"][0]["score"] = 1.0; bad["tasks"][0]["checks"][0]["passed"] = False
    assert any("fraction of checks" in e for e in validate_report(bad))
    bad = json.loads(json.dumps(report)); bad["core_score"] = 0.99
    assert any("core_score" in e for e in validate_report(bad))
    bad = json.loads(json.dumps(report)); bad["tasks"][1]["task"] = "made_up_task"
    assert any("not a task" in e for e in validate_report(bad))
    bad = json.loads(json.dumps(report)); bad["label"] = "<script>"
    assert any("schema" in e for e in validate_report(bad))
    bad = json.loads(json.dumps(report)); del bad["params"]
    assert validate_report(bad)
    # duplicate labels across files
    for i in range(2):
        (tmp_path / f"r{i}.json").write_text(json.dumps(report))
    problems = validate_files(sorted(tmp_path.glob("*.json")))
    assert any("duplicate label" in e for errs in problems.values() for e in errs)
    (tmp_path / "junk.json").write_text("{not json")
    assert any("unreadable" in e for e in validate_files([tmp_path / "junk.json"])[str(tmp_path / "junk.json")])


def test_multiseed_reports_seed_sensitivity(toy):
    r = run_task(_task(), toy, LIFParams(seed=1), seeds=3)
    assert "3/3 seeds" in r.checks[0].description
    assert r.passed
    # a check on the knife edge: threshold set at the observed mean so some seeds fall either side
    single = [run_task(_task(), toy, LIFParams(seed=1 + k)).checks[0].value for k in range(3)]
    edge = _task(checks=[{"type": "rate", "cond": "sugar", "op": ">", "value": sorted(single)[1] - 1e-9}])
    r = run_task(edge, toy, LIFParams(seed=1), seeds=3)
    assert any("seed-sensitive" in n for n in r.notes) or "3/3" in r.checks[0].description


def test_cli_validate_and_verify(tmp_path):
    cache = tmp_path / "cache"
    r = CliRunner()
    assert r.invoke(main, ["toy", "--cache", str(cache)]).exit_code == 0
    out = tmp_path / "res" / "a.json"
    assert r.invoke(main, ["run", "--cache", str(cache), "--tier", "core", "--seeds", "2", "-o", str(out), "--label", "a"]).exit_code == 0
    assert r.invoke(main, ["validate", str(out)]).exit_code == 0
    res = r.invoke(main, ["verify", str(out), "--cache", str(cache), "--mark"])
    assert res.exit_code == 0, res.output
    assert json.loads(out.read_text())["verified"] is True
    # tamper -> validate fails
    d = json.loads(out.read_text()); d["score"] = 0.123; out.write_text(json.dumps(d))
    assert r.invoke(main, ["validate", str(out)]).exit_code == 1


def test_submit_dry_run_and_body(tmp_path):
    from flybench.submit import pr_body, submit
    cache = tmp_path / "cache"
    r = CliRunner()
    assert r.invoke(main, ["toy", "--cache", str(cache)]).exit_code == 0
    out = tmp_path / "a.json"
    assert r.invoke(main, ["run", "--cache", str(cache), "--tier", "core", "-o", str(out), "--label", "My Run (v2)"]).exit_code == 0
    res = r.invoke(main, ["submit", str(out), "--dry-run", "--note", "tested a thing"])
    assert res.exit_code == 0, res.output
    assert "submit/my-run-v2" in res.output and "tested a thing" in res.output
    body = pr_body(json.loads(out.read_text()), "")
    assert "| stability |" in body and "please fill in" in body
    bad = tmp_path / "bad.json"; bad.write_text('{"schema": 1}')
    assert submit(bad, dry_run=True) == 1


# ---------------------------------------------------------------- submissions configs + adaptive model

def test_validate_submission():
    from flybench.evaluate import validate_submission, slug
    good = {"label": "Me, LIF gain 0.42", "note": "x", "connectome": "flywire783", "seeds": 3, "params": {"gain": 0.42}, "simulator": "flybench.sim:LIFSimulator"}
    assert validate_submission(good) == []
    assert slug(good["label"]) == "me-lif-gain-0-42"
    bad = dict(good, label="<script>"); assert any("label" in e for e in validate_submission(bad))
    bad = dict(good, simulator="os:system"); assert any("simulator" in e for e in validate_submission(bad))
    bad = dict(good, params={"gain": 0.42, "hack": 1}); assert any("hack" in e for e in validate_submission(bad))
    bad = dict(good, params={"gain": 50}); assert any("gain" in e for e in validate_submission(bad))
    bad = dict(good, seeds=99); assert any("seeds" in e for e in validate_submission(bad))
    bad = dict(good, connectome="secret"); assert any("connectome" in e for e in validate_submission(bad))
    ok = dict(good, params={"gain": 0.45, "extra": {"b_mv": 2, "tau_a_ms": 200}}, simulator="flybench.models.adaptive_lif:AdaptiveLIFSimulator")
    assert validate_submission(ok) == []
    assert validate_submission("nope") == ["config must be a mapping"]


def test_evaluate_on_toy(tmp_path):
    from flybench.evaluate import evaluate
    cfg = tmp_path / "s.yaml"
    cfg.write_text("label: toy eval\nnote: n\nconnectome: toy\nseeds: 1\nparams:\n  gain: 1.0\nsimulator: flybench.sim:LIFSimulator\n")
    r = evaluate(cfg, out=tmp_path / "r.json", comment=tmp_path / "c.md", cache=tmp_path / "cache")
    assert r["verified"] is True and r["label"] == "toy eval" and (tmp_path / "c.md").read_text(encoding="utf-8").startswith("### flybench evaluation")
    from flybench.validate import validate_report
    assert validate_report(json.loads((tmp_path / "r.json").read_text())) == []


def test_adaptive_lif_silences_and_keeps_reflexes(toy):
    from flybench.models.adaptive_lif import AdaptiveLIFSimulator, AdaptiveParams
    sugar = toy.select({"labels_regex": "sugar"}); mn9 = toy.select("MN9")
    ref = LIFSimulator(toy, LIFParams(seed=1)).run(600, [Stimulus(sugar, 100, 100, 400)])
    ada = AdaptiveLIFSimulator(toy, LIFParams(seed=1), AdaptiveParams(b_mv=2, tau_a_ms=200)).run(600, [Stimulus(sugar, 100, 100, 400)])
    assert ada.rate_hz(mn9, 150, 400) > 1                          # still responds (the toy is weakly wired; the real brain gives ~50 Hz)
    assert ada.rate_hz(mn9, 150, 400) < ref.rate_hz(mn9, 150, 400)  # but less than the un-adapting reference
    assert ada.rate_hz(None, 500, 600) <= ref.rate_hz(None, 500, 600)
    # extra params flow through LIFParams.extra
    sim = AdaptiveLIFSimulator(toy, LIFParams(extra={"b_mv": 3.5, "tau_a_ms": 100}))
    assert sim.ap.b_mv == 3.5 and sim.ap.tau_a_ms == 100
