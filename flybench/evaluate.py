"""Evaluate a submission config on the real connectome — what CI runs on every pull request.

    flybench evaluate configs/submissions/x.yaml [--out results/x.json] [--comment comment.md]

Fetches the prebuilt connectome cache from the GitHub release if it is not present locally,
runs the suite with the requested seeds, writes a result report marked `verified: true`
(the benchmark itself produced it), and writes a markdown summary for the PR comment.
"""

from __future__ import annotations

import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

import yaml

from .bench import load_tasks, resolve_simulator, run_suite, save_report
from .connectome import DEFAULT_CACHE, load_connectome
from .sim import LIFParams

CACHE_URL = "https://github.com/brandoncho369/flybench/releases/download/cache-{name}/{name}-cache.zip"
ALLOWED_SIMULATORS = {"flybench.sim:LIFSimulator", "flybench.models.adaptive_lif:AdaptiveLIFSimulator"}
ALLOWED_CONNECTOMES = {"flywire783", "toy"}
DIVISIONS = {"closed", "open"}
# closed division = the reference LIF dynamics with only the global gain fitted (Shiu et al. 2024 as
# published). Anything else — other dynamics, other parameters, fitted constants — is the open
# division, where the submitter must say how many parameters were free and what they were fit on.
CLOSED_SIMULATOR = "flybench.sim:LIFSimulator"
CLOSED_FREE_PARAMS = {"gain", "seed"}


def _task_names() -> set[str]:
    try:
        return {t["name"] for t in load_tasks()}
    except Exception:  # pragma: no cover
        return set()


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:60] or "submission"


def validate_submission(cfg: dict) -> list[str]:
    errs = []
    if not isinstance(cfg, dict):
        return ["config must be a mapping"]
    label = cfg.get("label")
    if not label or not re.fullmatch(r"[A-Za-z0-9 ._,()+/-]{1,60}", str(label)):
        errs.append("label: required; letters, digits, spaces, ._,()+/- ; max 60 chars")
    if cfg.get("connectome", "flywire783") not in ALLOWED_CONNECTOMES:
        errs.append(f"connectome: must be one of {sorted(ALLOWED_CONNECTOMES)}")
    seeds = cfg.get("seeds", 3)
    if not isinstance(seeds, int) or not 1 <= seeds <= 10:
        errs.append("seeds: integer 1–10")
    sim = cfg.get("simulator", "flybench.sim:LIFSimulator")
    if sim not in ALLOWED_SIMULATORS:
        errs.append(f"simulator: CI only runs built-in simulators {sorted(ALLOWED_SIMULATORS)}; submit custom code as a PR under submissions/ for manual verification")
    params = cfg.get("params", {}) or {}
    if not isinstance(params, dict):
        errs.append("params: must be a mapping")
    else:
        for k, v in params.items():
            if k not in LIFParams.__dataclass_fields__:
                errs.append(f"params.{k}: not a model parameter (known: {sorted(LIFParams.__dataclass_fields__)})")
            elif k == "extra":
                if not isinstance(v, dict) or not all(isinstance(x, (int, float)) for x in v.values()):
                    errs.append("params.extra: mapping of name -> number")
            elif not isinstance(v, (int, float)):
                errs.append(f"params.{k}: must be a number")
        g = params.get("gain", 1.0)
        if not 0 < g <= 10:
            errs.append("params.gain: must be in (0, 10]")
        if not 0 < params.get("dt_ms", 0.1) <= 1:
            errs.append("params.dt_ms: must be in (0, 1]")
    if len(str(cfg.get("note", ""))) > 300:
        errs.append("note: max 300 characters")
    # division, free parameters, fit data (ROADMAP items 7 and 9)
    division = cfg.get("division", "closed")
    if division not in DIVISIONS:
        errs.append(f"division: must be one of {sorted(DIVISIONS)}")
    changed = {k for k in (params if isinstance(params, dict) else {}) if k not in CLOSED_FREE_PARAMS}
    if division == "closed":
        if sim != CLOSED_SIMULATOR or changed:
            errs.append("division: 'closed' means the reference LIF with only params.gain changed; "
                        f"this submission changes {sorted(changed) or 'the simulator'} → set division: open, "
                        "n_free_parameters and fit_data")
        cfg.setdefault("n_free_parameters", 1)
        cfg.setdefault("fit_data", "gain swept; not fitted to any task")
    nfp = cfg.get("n_free_parameters")
    if division == "open" and nfp is None:
        errs.append("n_free_parameters: required in the open division (how many constants were fitted, 0 if all are literature values)")
    if nfp is not None and (not isinstance(nfp, int) or isinstance(nfp, bool) or nfp < 0):
        errs.append("n_free_parameters: non-negative integer")
    fit = cfg.get("fit_data")
    if division == "open" and not fit:
        errs.append("fit_data: required in the open division (what the free parameters were fitted on; 'none' if literature values)")
    if fit is not None:
        fit_s = str(fit)
        if len(fit_s) > 300:
            errs.append("fit_data: max 300 characters")
        low = fit_s.lower()
        named = sorted(n for n in _task_names() if n in low)
        if named or "flybench" in low or "hold-out" in low or "holdout" in low:
            errs.append(f"fit_data: parameters fitted on benchmark tasks are not eligible ({', '.join(named) or 'names the benchmark'}); "
                        "fit on recordings or literature values, then evaluate")
    return errs


def ensure_cache(name: str, cache: Path = DEFAULT_CACHE) -> Path:
    target = Path(cache) / name
    if (target / "W.npz").exists():
        return target
    if name == "toy":
        load_connectome("toy", cache)
        return target
    url = CACHE_URL.format(name=name)
    print(f"downloading prebuilt connectome cache {url} …")
    data = urllib.request.urlopen(url, timeout=120).read()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(target)
    return target


def run_holdout(c, params, sim, seeds: int) -> dict | None:
    """Unpublished tasks, run only where FLYBENCH_HOLDOUT_URL is set (CI secret pointing at a private
    YAML bundle). Only pass/fail per task and the tier score are reported — no thresholds, no values —
    so nobody can tune to them. This is the benchmark's check on its own public tasks."""
    import os, tempfile, zipfile, io
    url = os.environ.get("FLYBENCH_HOLDOUT_URL")
    if not url:
        return None
    import requests
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        if url.endswith(".zip") or r.content[:2] == b"PK":
            zipfile.ZipFile(io.BytesIO(r.content)).extractall(d)
        else:
            (d / "holdout.yaml").write_bytes(r.content)
        paths = sorted(d.rglob("*.yaml"))
        if not paths:
            return {"n_tasks": 0, "score": None, "passed": {}}
        rep = run_suite(c, params, load_tasks(paths), simulator=sim, seeds=seeds)
    return {"n_tasks": rep["n_tasks"], "score": rep["score"], "passed": {t["task"]: t["passed"] for t in rep["tasks"]}}


def holdout_gap(public_score: float | None, holdout: dict | None) -> float | None:
    """public − hold-out suite score. Positive = the model does better on the tasks it could have
    seen than on the ones it could not; the number a searched-parameter model must keep small."""
    if holdout is None or holdout.get("score") is None or public_score is None:
        return None
    return float(public_score - holdout["score"])


def evaluate(config_path: Path, out: Path | None = None, comment: Path | None = None, cache: Path = DEFAULT_CACHE, seeds_override: int | None = None) -> dict:
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    errs = validate_submission(cfg)
    if errs:
        raise SystemExit("invalid submission:\n  " + "\n  ".join(errs))
    name = cfg.get("connectome", "flywire783")
    ensure_cache(name, cache)
    c = load_connectome(name, cache)
    params = LIFParams.from_dict(cfg.get("params", {}) or {})
    sim = resolve_simulator(cfg.get("simulator", "flybench.sim:LIFSimulator"))
    seeds = seeds_override or int(cfg.get("seeds", 3))
    from .controls import parse_controls
    controls = parse_controls(str(cfg.get("controls", "rewired")).replace("none", ""))
    report = run_suite(c, params, load_tasks(), simulator=sim, seeds=seeds, controls=controls)
    holdout = run_holdout(c, params, sim, seeds)
    report["public_score"] = report["score"]
    if holdout is not None:
        holdout["gap"] = holdout_gap(report["score"], holdout)
        report["holdout"] = holdout
    report["label"] = cfg["label"]
    report["note"] = str(cfg.get("note", ""))
    report["division"] = cfg.get("division", "closed")
    report["n_free_parameters"] = cfg.get("n_free_parameters")
    report["fit_data"] = str(cfg.get("fit_data", ""))
    report["verified"] = True            # produced by the benchmark's own CI, not self-reported
    report["submission"] = str(Path(config_path).as_posix())
    out = out or Path("results") / f"{slug(cfg['label'])}.json"
    save_report(report, out)
    md = summary_markdown(report)
    if comment:
        Path(comment).write_text(md, encoding="utf-8")
    print(md)
    return report


def summary_markdown(r: dict) -> str:
    rows = []
    for t in r["tasks"]:
        mark = "✅" if t["passed"] else f"{t['score']:.0%}"
        notes = "; ".join(n for n in t.get("notes", []) if "seed" in n)
        rows.append(f"| {t['task']} | {mark} | {notes} |")
    rows = "\n".join(rows)
    p = r["params"]
    h = r.get("holdout")
    hold = ""
    if h:
        hs = "n/a" if h.get("score") is None else f"{h['score']:.2f}"
        gap = "" if h.get("gap") is None else f", gap {h['gap']:+.2f}"
        hold = f" · hold-out {hs} on {h['n_tasks']} unpublished tasks{gap}"
    spec = "" if r.get("specificity") is None else f" · specificity {r['specificity']:+.2f} vs {'/'.join(r['controls'])} wiring"
    nd = r.get("non_diagnostic") or []
    ndl = f"\n\n⚠ non-diagnostic (a shuffled brain also passes): {', '.join(nd)}" if nd else ""
    div = f" · {r.get('division', 'closed')} division" + (f", {r['n_free_parameters']} free parameter(s)" if r.get("n_free_parameters") is not None else "")
    return f"""### flybench evaluation — `{r['label']}`

**core {r['core_score']:.2f} · hard {r['hard_score']:.2f}** (by circuit {r.get('core_by_circuit') or 0:.2f} / {r.get('hard_by_circuit') or 0:.2f}){hold}{spec}{div} · {r['seeds']} seeds · {r['connectome']} · `{r['simulator'].replace('flybench.', '')}` · gain {p['gain']}{ndl}

| task | result | seed notes |
|---|---|---|
{rows}

_Evaluated by CI on the real connectome; merging this PR adds the result to the leaderboard as **verified**._
"""
