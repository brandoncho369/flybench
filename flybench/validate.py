"""Validate result reports before they reach the leaderboard.

Two layers: a JSON schema (shape), then semantic checks that recompute every
score from its parts and confirm the task names exist in this checkout. A
report that fails here is rejected by CI on the pull request.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .bench import TASK_DIR, load_tasks

SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "result.schema.json"


def validate_report(report: dict, known_tasks: dict[str, str] | None = None) -> list[str]:
    errs: list[str] = []
    try:
        import jsonschema  # type: ignore

        v = jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
        errs += [f"schema: {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in v.iter_errors(report)]
    except ImportError:  # keep working without jsonschema; the semantic checks below still run
        for key in ("schema", "label", "connectome", "params", "simulator", "tasks", "score"):
            if key not in report:
                errs.append(f"missing key {key!r}")
    if errs:
        return errs

    known = known_tasks if known_tasks is not None else {t["name"]: t.get("tier", "core") for t in load_tasks()}
    seen = set()
    tier_scores: dict[str, list[float]] = {"core": [], "hard": []}
    for t in report["tasks"]:
        name = t["task"]
        if name in seen:
            errs.append(f"{name}: duplicated")
        seen.add(name)
        if name not in known:
            errs.append(f"{name}: not a task in this checkout (tasks/)")
        checks = t["checks"]
        if not checks:
            errs.append(f"{name}: no checks")
            continue
        frac = sum(bool(c["passed"]) for c in checks) / len(checks)
        if abs(frac - t["score"]) > 1e-6:
            errs.append(f"{name}: score {t['score']} != fraction of checks passed {frac:.4f}")
        if bool(t["passed"]) != all(bool(c["passed"]) for c in checks):
            errs.append(f"{name}: passed flag disagrees with checks")
        for c in checks:
            if c["value"] is not None and not (isinstance(c["value"], (int, float))):
                errs.append(f"{name}: check value is not numeric")
        if name in known:
            tier_scores[known[name]].append(float(t["score"]))
    if abs(float(np.mean([t["score"] for t in report["tasks"]])) - report["score"]) > 1e-6:
        errs.append("score != mean of task scores")
    if report.get("passed") != sum(bool(t["passed"]) for t in report["tasks"]):
        errs.append("passed != number of passed tasks")
    if report.get("n_tasks") != len(report["tasks"]):
        errs.append("n_tasks != len(tasks)")
    for tier in ("core", "hard"):
        got = report.get(f"{tier}_score")
        exp = float(np.mean(tier_scores[tier])) if tier_scores[tier] else None
        if got is not None and exp is not None and abs(got - exp) > 1e-6:
            errs.append(f"{tier}_score {got} != mean of {tier} task scores {exp:.4f}")
    return errs


def validate_files(paths: list[Path]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    labels: dict[str, str] = {}
    known = {t["name"]: t.get("tier", "core") for t in load_tasks()} if TASK_DIR.exists() else {}
    for p in paths:
        try:
            r = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            out[str(p)] = [f"unreadable JSON: {e}"]
            continue
        errs = validate_report(r, known)
        lab = r.get("label")
        if lab in labels:
            errs.append(f"duplicate label {lab!r} (also {labels[lab]})")
        elif lab:
            labels[lab] = str(p)
        if errs:
            out[str(p)] = errs
    return out
