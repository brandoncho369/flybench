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
    report = run_suite(c, params, load_tasks(), simulator=sim, seeds=seeds)
    report["label"] = cfg["label"]
    report["note"] = str(cfg.get("note", ""))
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
    return f"""### flybench evaluation — `{r['label']}`

**core {r['core_score']:.2f} · hard {r['hard_score']:.2f}** · {r['seeds']} seeds · {r['connectome']} · `{r['simulator'].replace('flybench.', '')}` · gain {p['gain']}

| task | result | seed notes |
|---|---|---|
{rows}

_Evaluated by CI on the real connectome; merging this PR adds the result to the leaderboard as **verified**._
"""
