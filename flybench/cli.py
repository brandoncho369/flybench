from __future__ import annotations

import json
from pathlib import Path

import click
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
@click.option("-v", "--verbose", is_flag=True)
def run(connectome, config, gain, task_paths, out, label, cache, simulator, tier, seeds, verbose):
    """Run the benchmark suite."""
    c = load_connectome(connectome, cache)
    overrides = yaml.safe_load(Path(config).read_text(encoding="utf-8")) if config else {}
    if gain is not None:
        overrides["gain"] = gain
    params = LIFParams.from_dict(overrides or {})
    console.print(f"[bold]{c.name}[/]: {c.n:,} neurons, {c.n_edges:,} edges · gain={params.gain} w_syn={params.w_syn_mv} mV")
    tasks = load_tasks([Path(p) for p in task_paths]) if task_paths else load_tasks(tier=tier)
    report = run_suite(c, params, tasks, verbose=verbose, simulator=resolve_simulator(simulator), seeds=seeds)
    report["label"] = label or (Path(config).stem if config else f"gain{params.gain}")

    table = Table(title=f"flybench · score {report['score']:.2f} · {report['passed']}/{report['n_tasks']} tasks")
    table.add_column("task"); table.add_column("result"); table.add_column("checks"); table.add_column("notes", style="dim")
    for t in report["tasks"]:
        checks = "\n".join(("✓ " if ch["passed"] else "✗ ") + escape(f"{ch['description']}  [{ch['value']:.3g}]") for ch in t["checks"])
        table.add_row(t["title"], "[green]PASS[/]" if t["passed"] else f"[red]FAIL[/] ({t['score']:.0%})", checks, "\n".join(t["notes"]))
    console.print(table)
    if out:
        p = save_report(report, out)
        console.print(f"report → {p}")


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
