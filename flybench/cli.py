from __future__ import annotations

import json
from pathlib import Path

import click
import numpy as np
import yaml
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from . import __version__
from .bench import leaderboard, load_tasks, resolve_simulator, run_suite, save_report
from .connectome import DEFAULT_CACHE, build_from_codex, load_connectome
from .sim import LIFParams

console = Console()


@click.group()
@click.version_option(__version__)
def main():
    """flybench — reflex benchmark for whole-brain fly connectome simulations."""


@main.command()
@click.argument("codex_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--name", default="flywire783", show_default=True)
@click.option("--min-synapses", default=5, show_default=True)
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
def build(codex_dir, name, min_synapses, cache):
    """Build + cache a connectome from FlyWire Codex CSV downloads."""
    console.print(f"reading {codex_dir} …")
    c = build_from_codex(codex_dir, min_synapses=min_synapses, name=name)
    p = c.save(Path(cache) / name)
    console.print(f"[green]saved[/] {c.n:,} neurons / {c.n_edges:,} edges → {p}")
    # sanity report: the things that silently break task selectors when a file is missing
    a = c.annotations
    import numpy as np
    def filled(col):
        return int((a[col].astype(str) != "").sum()) if col in a else 0
    console.print(f"  positions: {int(np.isfinite(c.positions).all(axis=1).sum()):,} / {c.n:,}   "
                  f"cell_type: {filled('cell_type'):,}   labels: {filled('labels'):,}   "
                  f"super_class: {filled('super_class'):,}")
    for col, note in (("cell_type", "Cell Types file"), ("labels", "Community Labels file")):
        if filled(col) == 0:
            console.print(f"  [yellow]warning:[/] no {col} annotations — did you include the {note}? Most tasks will match 0 neurons.")


@main.command("fetch-neuprint")
@click.argument("out_dir", type=click.Path(file_okay=False))
@click.option("--dataset", default="male-cns:v1.0", show_default=True, help="neuPrint dataset (the Minecraft demo used male-cns:v1.0)")
@click.option("--server", default="https://neuprint.janelia.org", show_default=True)
@click.option("--min-synapses", default=5, show_default=True)
@click.option("--token", default=None, help="neuPrint token (optional; anonymous works). Also read from NEUPRINT_APPLICATION_CREDENTIALS")
def fetch_neuprint(out_dir, dataset, server, min_synapses, token):
    """Download a connectome from neuPrint into a folder `flybench build` can read (resumable)."""
    from .fetch_neuprint import fetch
    fetch(out_dir, dataset=dataset, server=server, min_synapses=min_synapses, token=token, log=lambda m: console.print(escape(str(m))))


@main.command()
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
def toy(cache):
    """Build + cache the bundled synthetic toy connectome."""
    c = load_connectome("toy", cache)
    console.print(f"[green]toy[/] {c.n:,} neurons / {c.n_edges:,} edges → {Path(cache) / 'toy'}")


@main.command()
@click.option("--connectome", "-c", default="toy", show_default=True, help="cached name or directory")
@click.option("--config", type=click.Path(exists=True, dir_okay=False), help="YAML of LIFParams overrides")
@click.option("--gain", type=float, help="override gain")
@click.option("--task", "-t", "task_paths", multiple=True, type=click.Path(exists=True), help="run only these task files")
@click.option("--out", "-o", default=None, help="write JSON report here")
@click.option("--label", default="", help="label for the leaderboard")
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
@click.option("--simulator", default=None, help="custom simulator as 'module:Class' (see CONTRIBUTING.md)")
@click.option("--tier", default="all", type=click.Choice(["core", "hard", "all"]), show_default=True)
@click.option("--seeds", default=1, show_default=True, help="run every condition this many times with different seeds; checks must hold on the mean")
@click.option("--controls", default=None, help="also score each task on shuffled wiring: 'rewired', 'random', 'signflip', comma-separated, or 'all' (see docs/CONTROLS.md)")
@click.option("--jobs", "-j", default=1, show_default=True, help="worker processes: each (task, wiring) unit is an independent simulation, so N jobs ≈ N× faster on N cores; results are bit-identical")
@click.option("-v", "--verbose", is_flag=True)
def run(connectome, config, gain, task_paths, out, label, cache, simulator, tier, seeds, controls, jobs, verbose):
    """Run the benchmark suite."""
    c = load_connectome(connectome, cache)
    overrides = yaml.safe_load(Path(config).read_text(encoding="utf-8")) if config else {}
    if gain is not None:
        overrides["gain"] = gain
    params = LIFParams.from_dict(overrides or {})
    console.print(f"[bold]{c.name}[/]: {c.n:,} neurons, {c.n_edges:,} edges · gain={params.gain} w_syn={params.w_syn_mv} mV")
    tasks = load_tasks([Path(p) for p in task_paths]) if task_paths else load_tasks(tier=tier)
    from .controls import parse_controls
    report = run_suite(c, params, tasks, verbose=verbose, simulator=resolve_simulator(simulator), seeds=seeds,
                       controls=parse_controls(controls), jobs=int(jobs), connectome_ref=connectome, cache=cache, simulator_spec=simulator)
    report["label"] = label or (Path(config).stem if config else f"gain{params.gain}")
    saved = save_report(report, out) if out else None  # save before rendering: a console encoding error must not lose a 40-minute run

    ci = report.get("graded_ci95")
    ci_s = f" [{ci[0]:.2f}, {ci[1]:.2f}]" if ci else ""
    table = Table(title=f"flybench · score {report['score']:.2f} · graded {report['graded']:.2f}{ci_s} · {report['passed']}/{report['n_tasks']} tasks")
    table.add_column("task"); table.add_column("result"); table.add_column("checks"); table.add_column("notes", style="dim")
    for t in report["tasks"]:
        def marg(ch):  # effect size: how far from the line, as a multiplier on the passing (+) or failing (-) side
            m = ch.get("margin")
            if m is None or m != m or ch.get("saturated") or ch.get("floored"):
                return ""
            return f" [dim]{'+' if m >= 0 else '-'}{10 ** abs(m):.1f}x[/]"
        checks = "\n".join(("✓ " if ch["passed"] else "✗ ") + escape(f"{ch['description']}  [{ch['value']:.3g}]") + marg(ch) for ch in t["checks"])
        notes = list(t["notes"])
        n_sat = sum(1 for ch in t["checks"] if ch.get("saturated"))
        if n_sat:
            notes.append(f"[yellow]{n_sat} comparison check(s) saturated: every compared condition at the refractory ceiling → counted as failed (RFC S1)[/]")
        ef = next((tk.get("expected_fail") for tk in tasks if tk["name"] == t["task"]), None)
        if ef:
            notes.append(f"[dim]expected-fail tier: {ef}[/]")
        n_flo = sum(1 for ch in t["checks"] if ch.get("floored"))
        if n_flo:
            notes.append(f"[yellow]{n_flo} comparison check(s) floored: every compared condition silent → counted as failed (RFC S2)[/]")
        if t.get("controls"):
            ctrl = ", ".join(f"{k} {v['score']:.0%}" for k, v in t["controls"].items())
            notes.append(f"controls: {ctrl} · specificity {t['specificity']:+.2f}" + ("  [red]NON-DIAGNOSTIC[/]" if t.get("non_diagnostic") else ""))
        res = ("[green]PASS[/]" if t["passed"] else f"[red]FAIL[/] ({t['score']:.0%})") + f"\n[dim]graded {t['graded']:.2f}[/]"
        table.add_row(t["title"], res, checks, "\n".join(notes))
    console.print(table)
    for name, why in report.get("skipped", {}).items():
        console.print(f"[dim]skipped {name}: {why}[/]")
    prof = report.get("profile") or {}
    if prof and report.get("n_tasks"):
        console.print("profile (checks with margin ≥ τ): " + "  ".join(f"τ={k}: {v:.0%}" for k, v in prof.items()))
    if report.get("controls") and report.get("specificity") is not None:
        nd = report.get("non_diagnostic") or []
        console.print(f"specificity (mean over tasks, real − best shuffled): {report['specificity']:+.2f}"
                      + (f" · non-diagnostic: {', '.join(nd)}" if nd else " · every passing task fails on shuffled wiring"))
    if out:
        console.print(f"report → {saved}")


@main.command()
@click.argument("a", type=click.Path(exists=True, dir_okay=False))
@click.argument("b", type=click.Path(exists=True, dir_okay=False))
def diff(a, b):
    """Paired comparison of two result files: per-check graded differences (A − B), the probability
    that A is better on a random check, and a bootstrap CI over seeds when both runs have them."""
    from .scoring import paired_difference
    ra, rb = json.loads(Path(a).read_text(encoding="utf-8")), json.loads(Path(b).read_text(encoding="utf-8"))
    key = lambda t, ch: (t["task"], ch["description"].split("  [")[0])  # noqa: E731
    ca = {key(t, ch): ch for t in ra["tasks"] for ch in t["checks"]}
    cb = {key(t, ch): ch for t in rb["tasks"] for ch in t["checks"]}
    keys = [k for k in ca if k in cb]
    if not keys:
        raise SystemExit("the two runs share no checks")
    if any("graded" not in ca[k] or "graded" not in cb[k] for k in keys):
        raise SystemExit("one of the runs predates graded scoring; re-run it")
    d = paired_difference([ca[k]["graded"] for k in keys], [cb[k]["graded"] for k in keys])
    console.print(f"[bold]{ra.get('label', a)}[/] vs [bold]{rb.get('label', b)}[/] · {d['n']} shared checks "
                  f"({len(ca) - d['n']} only in A, {len(cb) - d['n']} only in B)")
    se = f" ± {2 * d['se']:.3f} (95%)" if d["se"] == d["se"] else ""
    console.print(f"mean graded difference A − B: {d['mean']:+.3f}{se} · P(A better on a random check): {d['p_improve']:.0%}")
    # bootstrap over seeds: resample each check's per-seed values in both runs, re-grade, recompute the mean paired difference
    if all(ca[k].get("per_seed") and cb[k].get("per_seed") and ca[k].get("op") for k in keys):
        from .bench import margin_of
        from .scoring import graded_from_margin
        rng = np.random.default_rng(0)
        boots = []
        for _ in range(500):
            diffs = []
            for k in keys:
                pa, pb = ca[k]["per_seed"], cb[k]["per_seed"]
                va = float(np.mean(rng.choice(pa, size=len(pa)))); vb = float(np.mean(rng.choice(pb, size=len(pb))))
                diffs.append(graded_from_margin(margin_of(va, ca[k]["op"], ca[k]["target"])) - graded_from_margin(margin_of(vb, cb[k]["op"], cb[k]["target"])))
            boots.append(float(np.mean(diffs)))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        console.print(f"seed-bootstrap 95% CI on the mean difference: [{lo:+.3f}, {hi:+.3f}]")
    table = Table(title="largest per-check changes (graded, A − B)")
    table.add_column("task"); table.add_column("check"); table.add_column("A"); table.add_column("B"); table.add_column("Δ")
    for k in sorted(keys, key=lambda k: -abs(ca[k]["graded"] - cb[k]["graded"]))[:12]:
        table.add_row(k[0], escape(k[1]), f"{ca[k]['graded']:.2f} ({ca[k]['value']:.3g})", f"{cb[k]['graded']:.2f} ({cb[k]['value']:.3g})", f"{ca[k]['graded'] - cb[k]['graded']:+.2f}")
    console.print(table)


@main.command()
@click.argument("results", nargs=-1, type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="recompute run-level graded, CI and tier scores from stored per-seed data even if present")
def rescore(results, force):
    """Fill in graded scores (and the profile) on result files written before graded scoring existed,
    from the stored values and margins; nothing is re-simulated. Files that already have them are left
    alone unless --force, which recomputes the run-level statistics from the stored per-seed task scores."""
    import re
    from .bench import margin_of
    from .scoring import graded_from_margin, iqm, performance_profile, run_score, stratified_bootstrap_ci
    tiers = {t["name"]: t.get("tier", "core") for t in load_tasks()}
    op_re = re.compile(r"\s(>=|<=|>|<|==)\s([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")
    files = []
    for r in results:
        pth = Path(r)
        files += sorted(pth.glob("*.json")) if pth.is_dir() else [pth]
    n = 0
    for f in files:
        rep = json.loads(f.read_text(encoding="utf-8"))
        if "graded" in rep and not force:
            continue
        if "graded" in rep and force:
            per = [t.get("graded_per_seed") or [t["graded"]] for t in rep["tasks"]]
            for t, ps in zip(rep["tasks"], per):
                t["graded"] = float(np.mean(ps))
            rep["graded"] = run_score(per) if per else 0.0
            ci = stratified_bootstrap_ci(per, seed=int(rep.get("params", {}).get("seed", 0)))
            rep["graded_ci95"] = list(ci) if ci else None
            for tier in ("core", "hard"):
                v = [t["graded"] for t in rep["tasks"] if tiers.get(t["task"]) == tier]
                rep[f"{tier}_graded"] = float(np.mean(v)) if v else None
            f.write_text(json.dumps(rep, indent=2), encoding="utf-8")
            n += 1
            continue
        complete = True
        for t in rep["tasks"]:
            for ch in t["checks"]:
                m = ch.get("margin")
                if not isinstance(m, (int, float)) or m != m:
                    # results older than margins: recover op and target from the description ("rate[sugar] > 5.0 Hz")
                    mo = op_re.search(ch["description"].split("  [")[0])
                    if mo and isinstance(ch.get("value"), (int, float)):
                        ch["op"], ch["target"] = mo.group(1), float(mo.group(2))
                        m = margin_of(float(ch["value"]), ch["op"], ch["target"])
                        ch["margin"] = m
                    else:
                        complete = False
                ch.setdefault("graded", graded_from_margin(m if isinstance(m, (int, float)) else float("nan")))
            t["graded"] = float(np.mean([ch["graded"] for ch in t["checks"]])) if t["checks"] else 0.0
            t.setdefault("graded_per_seed", [t["graded"]])
        rep["graded"] = (iqm([t["graded"] for t in rep["tasks"]]) if rep["tasks"] else 0.0) if complete else None
        rep["graded_ci95"] = None
        for tier in ("core", "hard"):
            v = [t["graded"] for t in rep["tasks"] if tiers.get(t["task"]) == tier]
            rep[f"{tier}_graded"] = float(np.mean(v)) if v and complete else None
        rep["profile"] = performance_profile([ch.get("margin", float("nan")) for t in rep["tasks"] for ch in t["checks"] if isinstance(ch.get("margin"), (int, float))])
        rep["rescored"] = True
        f.write_text(json.dumps(rep, indent=2), encoding="utf-8")
        n += 1
    console.print(f"rescored {n} of {len(files)} result files")


@main.command()
@click.argument("results", nargs=-1, type=click.Path(exists=True))
@click.option("--out", "-o", default=None, help="write markdown here (default: stdout)")
def compare(results, out):
    """Build a markdown leaderboard from JSON reports."""
    files = []
    for r in results:
        p = Path(r)
        files += sorted(p.glob("*.json")) if p.is_dir() else [p]
    reports = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    md = leaderboard(reports)
    if out:
        Path(out).write_text(md + "\n", encoding="utf-8")
        console.print(f"leaderboard → {out}")
    else:
        console.print(md)


@main.command()
@click.option("--connectome", "-c", default="toy", show_default=True)
@click.option("--out", "-o", required=True, help="output directory (e.g. ../fly-explorer/public/data/toy)")
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
def export(connectome, out, cache):
    """Export a connectome for the fly-explorer web app."""
    from .export import export_web

    c = load_connectome(connectome, cache)
    p = export_web(c, out)
    total = sum(f.stat().st_size for f in p.iterdir())
    console.print(f"[green]exported[/] {c.name} ({c.n:,} neurons) → {p}  ({total / 1e6:.1f} MB)")


@main.command()
@click.option("--connectome", "-c", default="toy", show_default=True)
@click.argument("spec")
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
def select(connectome, spec, cache):
    """Test a selector: flybench select '{labels_regex: sugar}'"""
    c = load_connectome(connectome, cache)
    idx = c.select(yaml.safe_load(spec))
    console.print(f"{idx.size} neurons")
    if idx.size:
        cols = [col for col in ("root_id", "cell_type", "hemibrain_type", "super_class", "nt_type", "labels") if col in c.annotations]
        console.print(c.annotations.iloc[idx[:15]][cols].to_string(index=False))


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def lint(paths):
    """Validate task YAML files (defaults to tasks/)."""
    from .bench import TASK_DIR
    from .lint import lint_files

    files = [Path(p) for p in paths] or sorted(TASK_DIR.glob("*.yaml"))
    problems = lint_files(files)
    for f in files:
        errs = problems.get(str(f))
        console.print(("[red]✗[/] " if errs else "[green]✓[/] ") + f.name)
        for e in errs or []:
            console.print(f"    {e}")
    if problems:
        raise SystemExit(1)


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def validate(paths):
    """Validate result JSON reports (defaults to results/). This is what CI runs on every pull request."""
    from .validate import validate_files

    files = []
    for p in paths or ["results"]:
        pp = Path(p)
        files += sorted(pp.glob("*.json")) if pp.is_dir() else [pp]
    if not files:
        console.print("no result files found"); raise SystemExit(1)
    problems = validate_files(files)
    for f in files:
        errs = problems.get(str(f))
        console.print(("[red]✗[/] " if errs else "[green]✓[/] ") + escape(str(f)))
        for e in errs or []:
            console.print("    " + escape(e))
    if problems:
        raise SystemExit(1)


@main.command()
@click.argument("report", type=click.Path(exists=True, dir_okay=False))
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
@click.option("--tolerance", default=0.05, show_default=True, help="max allowed difference in any task score")
@click.option("--mark", is_flag=True, help="on success, write verified: true into the report")
def verify(report, cache, tolerance, mark):
    """Re-run a submitted report's parameters and compare scores. Maintainers run this before marking a result verified."""
    from .validate import validate_report

    r = json.loads(Path(report).read_text(encoding="utf-8"))
    errs = validate_report(r)
    if errs:
        console.print("[red]report is not valid:[/]"); [console.print("  " + escape(e)) for e in errs]; raise SystemExit(1)
    if r.get("simulator", "flybench.sim.LIFSimulator") != "flybench.sim.LIFSimulator":
        console.print(f"[yellow]custom simulator {r['simulator']} — install it, then re-run with --simulator to verify manually[/]"); raise SystemExit(2)
    c = load_connectome(r["connectome"], cache)
    params = LIFParams.from_dict(r["params"])
    names = {t["task"] for t in r["tasks"]}
    tasks = [t for t in load_tasks() if t["name"] in names]
    fresh = run_suite(c, params, tasks, seeds=int(r.get("seeds", 1)))
    worst = 0.0
    for a in r["tasks"]:
        b = next((t for t in fresh["tasks"] if t["task"] == a["task"]), None)
        d = abs(a["score"] - b["score"]) if b else 1.0
        worst = max(worst, d)
        console.print(("[green]✓[/] " if d <= tolerance else "[red]✗[/] ") + f"{a['task']}: submitted {a['score']:.2f}, re-run {b['score'] if b else float('nan'):.2f}")
    if worst > tolerance:
        console.print(f"[red]not reproduced[/] (max diff {worst:.2f} > {tolerance})"); raise SystemExit(1)
    console.print(f"[green]reproduced[/] within {tolerance}")
    if mark:
        r["verified"] = True
        Path(report).write_text(json.dumps(r, indent=2), encoding="utf-8")
        console.print(f"marked verified → {report}")


@main.command()
@click.argument("report", type=click.Path(exists=True, dir_okay=False))
@click.option("--note", default="", help="one line: what you changed vs. the reference model")
@click.option("--dry-run", is_flag=True, help="show the PR that would be opened, change nothing")
def submit(report, note, dry_run):
    """Validate a result and open the pull request for it (needs the GitHub CLI, `gh`)."""
    from .submit import submit as _submit

    raise SystemExit(_submit(Path(report), note=note, dry_run=dry_run))


@main.command()
@click.argument("config", type=click.Path(exists=True, dir_okay=False))
@click.option("--out", "-o", default=None, help="result JSON (default results/<slug>.json)")
@click.option("--comment", default=None, help="write the markdown summary here (CI posts it on the PR)")
@click.option("--seeds", default=None, type=int, help="override the config's seed count")
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
def evaluate(config, out, comment, seeds, cache):
    """Evaluate a submission config (configs/submissions/*.yaml) on the real connectome. This is what CI runs."""
    from .evaluate import evaluate as _evaluate

    _evaluate(Path(config), Path(out) if out else None, Path(comment) if comment else None, Path(cache), seeds)


@main.command()
@click.argument("label")
@click.option("--gain", type=float, required=True)
@click.option("--note", default="", help="one line: what you changed")
@click.option("--seeds", default=3, show_default=True)
@click.option("--simulator", default="flybench.sim:LIFSimulator", show_default=True)
@click.option("--open-pr", is_flag=True, help="also branch, commit and open the pull request (needs gh)")
def propose(label, gain, note, seeds, simulator, open_pr):
    """Write a submission config for CI to evaluate. Nothing runs locally."""
    from .evaluate import slug, validate_submission

    cfg = {"label": label, "note": note, "connectome": "flywire783", "seeds": seeds, "params": {"gain": gain}, "simulator": simulator}
    errs = validate_submission(cfg)
    if errs:
        console.print("[red]invalid:[/]"); [console.print("  " + e) for e in errs]; raise SystemExit(1)
    path = Path("configs/submissions") / f"{slug(label)}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    console.print(f"[green]wrote[/] {path}")
    if open_pr:
        import subprocess
        branch = f"submit/{slug(label)}"
        subprocess.run(["git", "checkout", "-B", branch], check=True)
        subprocess.run(["git", "add", str(path)], check=True)
        subprocess.run(["git", "commit", "-m", f"Submission: {label}"], check=True)
        subprocess.run(["gh", "pr", "create", "--repo", "brandoncho369/flybench", "--title", f"Submission: {label}", "--body", f"{note}\n\n_CI will evaluate this config and comment the scores._", "--head", branch], check=False)
    else:
        console.print("next: commit it on a branch and open a PR (or rerun with --open-pr). CI does the rest.")


if __name__ == "__main__":
    main()
