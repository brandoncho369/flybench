"""ROADMAP items 45 and 49: the reference model is a tagged submission; every row may declare a conflict of interest."""
import json
from pathlib import Path

import pytest
import yaml

from flybench.bench import leaderboard, load_tasks, run_suite
from flybench.connectome import load_connectome
from flybench.evaluate import ALLOWED_SIMULATORS, result_for, validate_submission
from flybench.models.reference_lif import MODEL_CARD, ReferenceLIFSimulator
from flybench.sim import LIFParams, LIFSimulator
from flybench.validate import validate_report

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


def test_reference_model_card_is_the_engine_with_provenance_on_every_constant():
    assert issubclass(ReferenceLIFSimulator, LIFSimulator)
    assert ReferenceLIFSimulator.reference_baseline is True
    defaults = LIFParams()
    for name, c in MODEL_CARD["constants"].items():
        assert c["provenance"] in {"MEASURED", "INFERRED", "MODELED", "CONVENTION"}, name
        assert c["basis"]
        assert getattr(defaults, name) == c["value"], f"model card disagrees with LIFParams on {name}"
    assert MODEL_CARD["n_free_parameters"] == 1 and set(MODEL_CARD["free_parameters"]) == {"gain"}
    assert MODEL_CARD["conflict_of_interest"]


def test_report_carries_reference_baseline_and_model_card(toy):
    task = next(t for t in load_tasks() if t["name"] == "stability")
    ref = run_suite(toy, LIFParams(gain=0.8), [task], simulator=ReferenceLIFSimulator)
    plain = run_suite(toy, LIFParams(gain=0.8), [task])
    assert ref["reference_baseline"] is True and ref["model_card"]["n_free_parameters"] == 1
    assert plain["reference_baseline"] is False and plain["model_card"] is None
    assert ref["tasks"][0]["score"] == plain["tasks"][0]["score"]     # the same engine, the same numbers
    for r in (ref, plain):
        r["label"] = "t"
        assert validate_report(r) == []


def test_leaderboard_has_role_and_conflict_columns(toy):
    task = next(t for t in load_tasks() if t["name"] == "stability")
    r = run_suite(toy, LIFParams(gain=0.8), [task], simulator=ReferenceLIFSimulator)
    r["label"] = "ref"; r["conflict_of_interest"] = "maintainers wrote it"
    md = leaderboard([r])
    head, _, row = md.split("\n")[:3]
    assert "| role |" in head and "| conflict of interest |" in head
    assert "| reference baseline |" in row and "| maintainers wrote it |" in row


def test_submission_configs_validate_and_declare_conflicts():
    for f in sorted((ROOT / "configs" / "submissions").glob("*.yaml")):
        cfg = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert validate_submission(cfg) == [], f.name
        assert cfg.get("conflict_of_interest"), f"{f.name}: the maintainers' own submissions must declare a conflict of interest"
        assert cfg["simulator"] in ALLOWED_SIMULATORS
    ref = yaml.safe_load((ROOT / "configs" / "submissions" / "reference-lif-0.45.yaml").read_text(encoding="utf-8"))
    assert ref["simulator"] == "flybench.models.reference_lif:ReferenceLIFSimulator" and ref["division"] == "closed"


def test_conflict_of_interest_is_validated():
    base = {"label": "x", "params": {"gain": 0.45}, "simulator": "flybench.sim:LIFSimulator"}
    assert validate_submission({**base, "conflict_of_interest": "none"}) == []
    assert any("conflict_of_interest" in e for e in validate_submission({**base, "conflict_of_interest": ""}))
    assert any("conflict_of_interest" in e for e in validate_submission({**base, "conflict_of_interest": "x" * 301}))


def test_one_result_file_per_label_and_the_reference_is_tagged_on_disk():
    labels = {}
    for f in sorted((ROOT / "results").glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        assert r["label"] not in labels, f"{f.name} repeats the label of {labels[r['label']]}"
        labels[r["label"]] = f.name
    ref = yaml.safe_load((ROOT / "configs" / "submissions" / "reference-lif-0.45.yaml").read_text(encoding="utf-8"))
    f = result_for(ref["label"], ROOT / "results")
    assert f is not None, "the reference submission has no result file"
    r = json.loads(f.read_text(encoding="utf-8"))
    assert r.get("reference_baseline") is True and r.get("verified") is True and r.get("division") == "closed"
    assert r.get("conflict_of_interest")
    assert r.get("simulator") == "flybench.models.reference_lif.ReferenceLIFSimulator"
