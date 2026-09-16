"""Static validation of task YAML files — catches typos before a 45 s run does."""

from __future__ import annotations

from pathlib import Path

import yaml

from .bench import BUMP_STATS, KNOWN_CAPABILITIES, KNOWN_DATASETS, MATRIX_SIGNS, MATRIX_UNSCORED, OPS, RANK_ATTRIBUTES, expand_checks

METRICS = {"rate", "network_rate", "active_fraction", "readout_active_fraction", "ratio", "spikes_per_neuron", "lifetime_sparseness", "latency",
           "rank_order", "recruitment_spread", "population_sparseness", "bump"}
RATIO_METRICS = {"rate", "readout_active_fraction", "spikes_per_neuron", "population_sparseness", "latency"}
CELL_METRICS = {"rate", "readout_active_fraction", "spikes_per_neuron"}   # what a matrix cell may measure
CIRCUITS = {"stability", "taste", "escape", "olfaction", "physiology", "robustness", "courtship", "locomotion", "optic_flow", "grooming", "navigation"}
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
    if "expected_fail" in task and not (isinstance(task["expected_fail"], str) and task["expected_fail"].strip()):
        errs.append("expected_fail must be a non-empty string saying why the reference model is expected to fail")
    if task.get("circuit") not in CIRCUITS:
        errs.append(f"needs `circuit` (one of {sorted(CIRCUITS)}) so the score can be weighted per pathway")
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
    needs_silence = any(isinstance(cond, dict) and cond.get("silence") is not None for cond in conds.values())
    caps = task.get("requires_capabilities", []) or []
    for cap in caps:
        if cap not in KNOWN_CAPABILITIES:
            errs.append(f"requires_capabilities: {cap!r} is not a known capability {KNOWN_CAPABILITIES}")
    if needs_silence and "can_silence" not in caps:
        errs.append("a condition silences neurons: add `requires_capabilities: [can_silence]` so simulators that cannot do it skip the task")
    for cname, cond in conds.items():
        if cond.get("silence") is not None and not isinstance(cond["silence"], (dict, str, list)):
            errs.append(f"{cname}: silence must be a selector")
        jit = cond.get("weight_jitter", 0)
        if not (isinstance(jit, (int, float)) and 0 <= jit <= 1):
            errs.append(f"{cname}: weight_jitter must be a number in [0, 1] (lognormal sigma)")
        for i, s in enumerate(cond.get("stimuli", []) or []):
            if "select" not in s:
                errs.append(f"{cname}: stimulus {i} has no `select`")
            t0, t1 = float(s.get("t_start_ms", 0)), float(s.get("t_end_ms", duration))
            if t0 >= t1 or t0 < 0 or t0 >= duration:
                errs.append(f"{cname}: stimulus {i} window [{t0}, {t1}] is empty or outside the run")
            rate, rate_end = float(s.get("rate_hz", 100)), s.get("rate_end_hz")
            if rate_end is None and rate <= 0:
                errs.append(f"{cname}: stimulus {i} rate_hz must be > 0")
            if rate_end is not None and (not isinstance(rate_end, (int, float)) or rate < 0 or rate_end < 0 or rate_end == rate):
                errs.append(f"{cname}: stimulus {i} rate_end_hz must be a rate >= 0 different from rate_hz (a ramp), with rate_hz >= 0")
    stim_names = {st.get("name") for cond in conds.values() for st in (cond.get("stimuli") or []) if isinstance(cond, dict)}
    for name in task.get("requires_stimuli", []) or []:
        if name not in stim_names:
            errs.append(f"requires_stimuli: {name!r} is not a stimulus name in any condition")
    for name in task.get("requires_readouts", []) or []:
        if name not in readouts:
            errs.append(f"requires_readouts: {name!r} is not a defined readout")
    only = task.get("dataset_only")
    if only is not None:
        if not isinstance(only, list) or not only or not all(isinstance(d, str) for d in only):
            errs.append("dataset_only must be a non-empty list of connectome names")
        else:
            for d in only:
                if d not in KNOWN_DATASETS:
                    errs.append(f"dataset_only: {d!r} is not a known connectome name {KNOWN_DATASETS}")
            if "toy" not in only:
                errs.append("dataset_only must include 'toy': every task has to pass on the network wired to pass it")
    if not task["checks"]:
        errs.append("needs at least one check")
    # a matrix check: every cell must name a condition and a readout, carry a legal sign, and end up
    # with a basis (its own or the matrix's); a grid that names nothing is a typo, not an empty task
    for i, chk in enumerate(task["checks"]):
        if chk.get("type") != "matrix":
            continue
        if chk.get("metric", "spikes_per_neuron") not in CELL_METRICS:
            errs.append(f"check {i}: matrix metric must be one of {sorted(CELL_METRICS)}")
        if "value" not in chk:
            errs.append(f"check {i}: matrix needs `value` (the threshold every cell is held to)")
        expect = chk.get("expect")
        if not isinstance(expect, dict) or not expect:
            errs.append(f"check {i}: matrix needs `expect`, a mapping condition -> {{readout: sign}}")
            continue
        scored = 0
        for cond, row in expect.items():
            if cond not in conds:
                errs.append(f"check {i}: matrix row {cond!r} is not a condition")
            if not isinstance(row, dict):
                errs.append(f"check {i}: matrix row {cond!r} must map readouts to signs")
                continue
            for rname, cell in row.items():
                if rname not in readouts:
                    errs.append(f"check {i}: matrix cell {cond}/{rname}: readout {rname!r} not defined")
                sign, basis = (cell.get("sign"), cell.get("basis")) if isinstance(cell, dict) else (cell, None)
                if sign in MATRIX_UNSCORED:
                    continue
                if sign not in MATRIX_SIGNS:
                    errs.append(f"check {i}: matrix cell {cond}/{rname}: sign {sign!r} must be '+', '-' or '?'")
                    continue
                scored += 1
                if not str(basis or chk.get("basis", "")).strip():
                    errs.append(f"check {i}: matrix cell {cond}/{rname}: needs `basis` (its own, or on the matrix)")
        if scored == 0:
            errs.append(f"check {i}: matrix scores no cell (every sign is '?')")
    if any("matrix" in e for e in errs):
        return errs
    task = expand_checks(task)
    for i, chk in enumerate(task["checks"]):
        typ = chk.get("type")
        if typ not in METRICS:
            errs.append(f"check {i}: unknown type {typ!r}")
        if chk.get("op") not in OPS:
            errs.append(f"check {i}: unknown op {chk.get('op')!r}")
        if "value" not in chk:
            errs.append(f"check {i}: missing value")
        if not str(chk.get("basis", "")).strip():
            errs.append(f"check {i}: needs `basis` — a citation for the threshold, or 'convention: <why this number>'")
        if typ == "lifetime_sparseness":
            panel = chk.get("conds")
            if not isinstance(panel, list) or len(panel) < 2:
                errs.append(f"check {i}: lifetime_sparseness needs `conds`, a list of at least 2 conditions")
            else:
                for cn in panel:
                    if cn not in conds:
                        errs.append(f"check {i}: conds entry {cn!r} is not a condition")
        elif chk.get("cond") not in conds:
            errs.append(f"check {i}: cond {chk.get('cond')!r} is not a condition")
        # recording-match checks: observed {mean, sd|'unknown', n, source}; ceiling in (0, 1]; k > 0
        obs = chk.get("observed")
        if obs is not None:
            if not isinstance(obs, dict) or "mean" not in obs or "source" not in obs:
                errs.append(f"check {i}: observed must be a mapping with mean, sd (number or 'unknown'), n, source")
            else:
                if not isinstance(obs["mean"], (int, float)):
                    errs.append(f"check {i}: observed.mean must be a number")
                sd = obs.get("sd", None)
                if sd is None:
                    errs.append(f"check {i}: observed.sd is required (a number, or 'unknown' when the paper gives none)")
                elif sd != "unknown" and (not isinstance(sd, (int, float)) or sd < 0):
                    errs.append(f"check {i}: observed.sd must be a non-negative number or 'unknown'")
                if "n" in obs and (not isinstance(obs["n"], int) or obs["n"] < 1):
                    errs.append(f"check {i}: observed.n must be a positive integer")
                if not str(obs.get("source", "")).strip():
                    errs.append(f"check {i}: observed.source must cite the recording")
        if "ceiling" in chk and (not isinstance(chk["ceiling"], (int, float)) or not 0 < chk["ceiling"] <= 1):
            errs.append(f"check {i}: ceiling must be a number in (0, 1]")
        if "k" in chk and (not isinstance(chk["k"], (int, float)) or chk["k"] <= 0):
            errs.append(f"check {i}: k (z-score pass width) must be a positive number")
        if typ == "ratio" and chk.get("over") not in conds:
            errs.append(f"check {i}: over {chk.get('over')!r} is not a condition")
        if typ == "ratio" and chk.get("metric", "rate") not in RATIO_METRICS:
            errs.append(f"check {i}: ratio metric must be one of {sorted(RATIO_METRICS)}")
        if typ == "ratio" and "over_readout" in chk and chk["over_readout"] not in readouts:
            errs.append(f"check {i}: over_readout {chk['over_readout']!r} not defined")
        # network-level metrics ignore readouts; readout metrics default to the task's first readout (runtime does the same)
        if typ == "latency" and "from" in chk and chk["from"] not in readouts:
            errs.append(f"check {i}: latency `from` {chk['from']!r} is not a defined readout")
        if typ in ("rate", "ratio", "readout_active_fraction", "lifetime_sparseness", "latency", "rank_order", "recruitment_spread", "population_sparseness", "bump") and "readout" in chk and chk["readout"] not in readouts:
            errs.append(f"check {i}: readout {chk['readout']!r} not defined")
        if typ == "rank_order" and chk.get("by", "input_synapses") not in RANK_ATTRIBUTES:
            errs.append(f"check {i}: rank_order `by` must be one of {RANK_ATTRIBUTES}")
        if typ == "bump":
            angles = chk.get("angles")
            if not isinstance(angles, dict) or len(angles) < 3:
                errs.append(f"check {i}: bump needs `angles`, a mapping of at least 3 readouts to degrees")
            else:
                for rn, deg in angles.items():
                    if rn not in readouts:
                        errs.append(f"check {i}: bump angles: readout {rn!r} not defined")
                    if not isinstance(deg, (int, float)):
                        errs.append(f"check {i}: bump angles: {rn!r} must map to degrees")
            if chk.get("stat", "resultant") not in BUMP_STATS:
                errs.append(f"check {i}: bump stat must be one of {BUMP_STATS}")
            if chk.get("stat") == "error_deg" and not isinstance(chk.get("cue_deg"), (int, float)):
                errs.append(f"check {i}: bump error_deg needs `cue_deg`")
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
