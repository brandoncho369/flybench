"""ROADMAP item 50: task lifecycle — retired tasks are skipped, saturation is reported from result files."""
import copy
from pathlib import Path

import yaml

from flybench.bench import TASK_DIR, load_tasks
from flybench.lifecycle import MIN_ROWS, markdown, states
from flybench.lint import lint_task


def _report(connectome, verified, tasks):
    return {"connectome": connectome, "verified": verified,
            "tasks": [{"task": n, "passed": p, "checks": [{"margin": m}]} for n, p, m in tasks]}


def test_states_from_reports():
    reps = [_report("flywire783", i == 0, [("sugar_to_proboscis", True, 1.0 + 0.05 * i), ("dose_response", False, -1.0),
                                          ("stability", True, 1.8), ("adaptation", i == 0, 0.2)]) for i in range(MIN_ROWS)]
    by = {(s.task, s.connectome): s for s in states(reps)}
    assert by[("sugar_to_proboscis", "flywire783")].state == "saturated"
    assert by[("dose_response", "flywire783")].state == "target"          # hard tier, nobody passes
    assert by[("stability", "flywire783")].state == "guard"               # null task: never retired
    assert by[("adaptation", "flywire783")].state == "active" and by[("adaptation", "flywire783")].passed == 1
    thin = states(reps[:1])
    assert all(s.state == "thin" for s in thin)
    md = markdown(states(reps))
    assert "| sugar_to_proboscis | flywire783 | 3 (1) | 3 | **saturated** |" in md and "1 saturated" in md


def test_retired_tasks_need_a_reason_and_are_skipped_by_default(tmp_path):
    t = yaml.safe_load((TASK_DIR / "01_stability.yaml").read_text(encoding="utf-8"))
    t["status"] = "retired"
    assert any("retired" in e for e in lint_task(t))
    t["retired"] = {"date": "2026-09-17", "reason": "test"}
    assert lint_task(t) == []
    p = tmp_path / "99_retired.yaml"; p.write_text(yaml.safe_dump(t), encoding="utf-8")
    keep = tmp_path / "01_keep.yaml"; keep.write_text((TASK_DIR / "02_sugar_to_proboscis.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    # asked for by path: loaded; loaded as a directory scan: only with include_retired
    assert [x["name"] for x in load_tasks([p])] == ["stability"]
    import flybench.bench as b
    old = b.TASK_DIR
    try:
        b.TASK_DIR = tmp_path
        assert [x["name"] for x in load_tasks()] == ["sugar_to_proboscis"]
        assert len(load_tasks(include_retired=True)) == 2
    finally:
        b.TASK_DIR = old


def test_no_task_is_retired_without_the_repo_saying_so():
    for f in sorted(TASK_DIR.glob("*.yaml")):
        t = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert t.get("status", "active") in ("active", "retired"), f.name
        if t.get("status") == "retired":
            assert t["retired"]["date"] and t["retired"]["reason"], f.name
