"""Static validation of task YAML files — catches typos before a 45 s run does."""

from __future__ import annotations

from pathlib import Path

import yaml

from .bench import OPS

METRICS = {"rate", "network_rate", "active_fraction", "readout_active_fraction", "ratio"}
REQUIRED = {"name", "title", "conditions", "checks"}
TIERS = {"core", "hard"}


def lint_task(task: dict, source: str = "<task>") -> list[str]:
    errs: list[str] = []
    missing = REQUIRED - set(task)
    if missing:
        errs.append(f"missing keys: {sorted(missing)}")
        return errs
    if "readout" not in task and not task.get("readouts"):
        errs.append("needs `readout` or `readouts`")
    if task.get("tier", "core") not in TIERS:
        errs.append(f"tier must be one of {sorted(TIERS)}")
    if not task.get("citation"):
        errs.append("needs a `citation` (published fly behaviour)")
    duration = float(task.get("duration_ms", 1000))
    if duration <= 0:
        errs.append("duration_ms must be > 0")
    window = task.get("window", [0, duration])
    if not (0 <= window[0] < window[1] <= duration):
        errs.append(f"window {window} must lie within [0, {duration}]")
    readouts = set(task.get("readouts", {}).keys()) | ({"default"} if "readout" in task else set())
    for rname, r in task.get("readouts", {}).items():
        if "select" not in r:
            errs.append(f"readout {rname!r} has no `select`")
    conds = task["conditions"]
    if not isinstance(conds, dict) or not conds:
        errs.append("conditions must be a non-empty mapping")
        return errs
    for cname, cond in conds.items():
        for i, s in enumerate(cond.get("stimuli", []) or []):
            if "select" not in s:
                errs.append(f"{cname}: stimulus {i} has no `select`")
            t0, t1 = float(s.get("t_start_ms", 0)), float(s.get("t_end_ms", duration))
            if t0 >= t1 or t0 < 0 or t0 >= duration:
                errs.append(f"{cname}: stimulus {i} window [{t0}, {t1}] is empty or outside the run")
            if float(s.get("rate_hz", 100)) <= 0:
                errs.append(f"{cname}: stimulus {i} rate_hz must be > 0")
    if not task["checks"]:
        errs.append("needs at least one check")
    for i, chk in enumerate(task["checks"]):
        typ = chk.get("type")
        if typ not in METRICS:
            errs.append(f"check {i}: unknown type {typ!r}")
        if chk.get("op") not in OPS:
            errs.append(f"check {i}: unknown op {chk.get('op')!r}")
        if "value" not in chk:
            errs.append(f"check {i}: missing value")
        if chk.get("cond") not in conds:
            errs.append(f"check {i}: cond {chk.get('cond')!r} is not a condition")
        if typ == "ratio" and chk.get("over") not in conds:
            errs.append(f"check {i}: over {chk.get('over')!r} is not a condition")
        # network-level metrics ignore readouts; readout metrics default to the task's first readout (runtime does the same)
        if typ in ("rate", "ratio", "readout_active_fraction") and "readout" in chk and chk["readout"] not in readouts:
            errs.append(f"check {i}: readout {chk['readout']!r} not defined")
        for key in ("window", "over_window"):
            if key in chk:
                w = chk[key]
                if not (isinstance(w, list) and len(w) == 2 and 0 <= w[0] < w[1] <= duration):
                    errs.append(f"check {i}: {key} {w} must lie within [0, {duration}]")
    return errs


def lint_files(paths: list[Path]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    for p in paths:
        try:
            task = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            out[str(p)] = [f"YAML error: {e}"]
            continue
        errs = lint_task(task, str(p))
        name = task.get("name") if isinstance(task, dict) else None
        if name in names:
            errs.append(f"duplicate task name {name!r} (also in {names[name]})")
        elif name:
            names[name] = str(p)
        if errs:
            out[str(p)] = errs
    return out
