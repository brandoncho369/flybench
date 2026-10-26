"""Rerun one task on existing result rows and splice it in, instead of rerunning every task.

    python scripts/rerun_task.py tasks/06_dose_response.yaml results/flywire783_gain0.45.json [...] --jobs 3

Each row is rerun with its own connectome, params (gain, adaptive constants), simulator, seeds and
controls, read from the file. The task's entry is replaced and the run-level statistics are recomputed
the way `run_suite` computes them; label, cost and everything else stay. As a determinism check, every
check whose description (condition and threshold) is unchanged must reproduce its old value exactly,
or the row is left alone."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flybench.bench import load_tasks, resolve_simulator, run_suite  # noqa: E402
from flybench.connectome import load_connectome  # noqa: E402
from flybench.scoring import performance_profile, run_score, stratified_bootstrap_ci  # noqa: E402
from flybench.sim import LIFParams  # noqa: E402


def summarize(rep: dict, tasks: dict) -> None:
    """Run-level fields from rep["tasks"], as in bench.run_suite."""
    rs = rep["tasks"]
    tier = lambda r: tasks[r["task"]].get("tier", "core")
    circuit = lambda r: tasks[r["task"]].get("circuit", r["task"])
    rep["score"] = float(np.mean([r["score"] for r in rs]))
    rep["passed"] = sum(bool(r["passed"]) for r in rs)
    rep["graded"] = run_score([r["graded_per_seed"] for r in rs])
    ci = stratified_bootstrap_ci([r["graded_per_seed"] for r in rs], seed=int(rep["params"].get("seed", 0)))
    rep["graded_ci95"] = list(ci) if ci else None
    rep["profile"] = performance_profile([ch["margin"] for r in rs for ch in r["checks"]])
    for t in ("core", "hard"):
        sel = [r for r in rs if tier(r) == t]
        rep[f"{t}_score"] = float(np.mean([r["score"] for r in sel])) if sel else None
        rep[f"{t}_graded"] = float(np.mean([r["graded"] for r in sel])) if sel else None
        by_c = {}
        for r in sel:
            by_c.setdefault(circuit(r), []).append(r["score"])
        rep[f"{t}_by_circuit"] = float(np.mean([np.mean(v) for v in by_c.values()])) if by_c else None
    if rep.get("controls"):
        rep["specificity"] = float(np.mean([r["specificity"] for r in rs]))
    rep["non_diagnostic"] = [r["task"] for r in rs if r.get("non_diagnostic")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("rows", nargs="+")
    ap.add_argument("--changed", default="", help="conditions whose stimulus changed (comma-separated): their checks may move")
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    task = load_tasks([Path(a.task)])[0]
    all_tasks = {t["name"]: t for t in load_tasks()}
    changed = [f"[{x}]" for x in a.changed.split(",") if x]
    bad = 0
    for row in a.rows:
        f = Path(row)
        rep = json.loads(f.read_text(encoding="utf-8"))
        old = next((t for t in rep["tasks"] if t["task"] == task["name"]), None)
        if old is None:
            print(f"{f.name}: {task['name']} not in this row (skipped there); left alone")
            continue
        check = json.loads(json.dumps(rep))
        summarize(check, all_tasks)
        stale = [k for k in ("score", "graded", "core_graded", "hard_graded", "specificity", "passed")
                 if rep.get(k) is not None and not np.isclose(rep[k], check[k], rtol=0, atol=1e-9)]
        if stale:
            print(f"{f.name}: stored statistics do not match a recomputation ({stale}); row left alone")
            bad += 1
            continue
        params = LIFParams(**rep["params"])
        mod, _, cls = rep["simulator"].rpartition(".")
        spec = f"{mod}:{cls}"
        c = load_connectome(rep["connectome"])
        new = run_suite(c, params, tasks=[task], simulator=resolve_simulator(spec), seeds=rep["seeds"],
                        controls=rep.get("controls") or [], jobs=a.jobs, connectome_ref=rep["connectome"],
                        simulator_spec=spec)["tasks"][0]
        before = {ch["description"].split("  [")[0]: ch["value"] for ch in old["checks"]}
        drift = [(d, before[d], ch["value"]) for ch in new["checks"]
                 if (d := ch["description"].split("  [")[0]) in before and not any(x in d for x in changed)
                 and before[d] != ch["value"]]
        if drift:
            print(f"{f.name}: unchanged checks did not reproduce, row left alone: {drift}")
            bad += 1
            continue
        rep["tasks"] = [new if t["task"] == task["name"] else t for t in rep["tasks"]]
        summarize(rep, all_tasks)
        f.write_text(json.dumps(rep, indent=2), encoding="utf-8")
        ms = [ch for ch in new["checks"] if ch["description"].startswith("rate[measured]")]
        print(f"{f.name}: passed {old['passed']} -> {new['passed']}, graded {old['graded']:.3f} -> {new['graded']:.3f}, "
              f"measured {[round(ch['value'], 1) for ch in ms]}; run graded -> {rep['graded']:.3f}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
