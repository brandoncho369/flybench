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
@click.option("-v", "--verbose", is_flag=True)
def run(connectome, config, gain, task_paths, out, label, cache, simulator, tier, verbose):
    """Run the benchmark suite."""
    c = load_connectome(connectome, cache)
    overrides = yaml.safe_load(Path(config).read_text()) if config else {}
    if gain is not None:
        overrides["gain"] = gain
    params = LIFParams.from_dict(overrides or {})
    console.print(f"[bold]{c.name}[/]: {c.n:,} neurons, {c.n_edges:,} edges · gain={params.gain} w_syn={params.w_syn_mv} mV")
    tasks = load_tasks([Path(p) for p in task_paths]) if task_paths else load_tasks(tier=tier)
    report = run_suite(c, params, tasks, verbose=verbose, simulator=resolve_simulator(simulator))
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
    reports = [json.loads(f.read_text()) for f in files]
    md = leaderboard(reports)
    if out:
        Path(out).write_text(md + "\n")
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


if __name__ == "__main__":
    main()
