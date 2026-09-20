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
@click.option("--allow-unpinned", is_flag=True, help="run on a connectome whose fingerprint differs from flybench/manifests.json; the result is marked unpinned and ranked last")
@click.option("--dump-spikes", "dump_dir", default=None, type=click.Path(file_okay=False), help="write every spike of every condition and seed (real wiring only) as <dir>/<task>/<condition>_seed<k>.parquet (or .csv.gz): time_ms, trial, neuron_index, root_id")
@click.option("-v", "--verbose", is_flag=True)
def run(connectome, config, gain, task_paths, out, label, cache, simulator, tier, seeds, controls, jobs, allow_unpinned, dump_dir, verbose):
    """Run the benchmark suite."""
    from .manifest import check_pinned
    c = load_connectome(connectome, cache)
    pin = check_pinned(c)
    if pin["status"] == "mismatch" and not allow_unpinned:
        console.print(f"[red]connectome {c.name!r} does not match its pin[/] (flybench/manifests.json, version {pin['version']!r}):")
        console.print(f"  expected {pin['expected']}")
        console.print(f"  got      {pin['sha256']}")
        console.print("A rebuilt or re-exported dataset is a different graph; results would not be comparable. "
                      "Pass --allow-unpinned to run anyway (the result is marked unpinned), or re-pin with `flybench fingerprint`.")
        raise SystemExit(2)
    if pin["status"] != "pinned":
        console.print(f"[yellow]{pin['status']}:[/] connectome {c.name!r} is not the pinned artefact; the result will be marked unpinned")
    overrides = yaml.safe_load(Path(config).read_text(encoding="utf-8")) if config else {}
    if gain is not None:
        overrides["gain"] = gain
    params = LIFParams.from_dict(overrides or {})
    console.print(f"[bold]{c.name}[/]: {c.n:,} neurons, {c.n_edges:,} edges · gain={params.gain} w_syn={params.w_syn_mv} mV")
    tasks = load_tasks([Path(p) for p in task_paths]) if task_paths else load_tasks(tier=tier)
    from .controls import parse_controls
    report = run_suite(c, params, tasks, verbose=verbose, simulator=resolve_simulator(simulator), seeds=seeds,
                       controls=parse_controls(controls), jobs=int(jobs), connectome_ref=connectome, cache=cache, simulator_spec=simulator, dump_dir=dump_dir)
    if dump_dir:
        report["spike_dump"] = str(Path(dump_dir))
    report["label"] = label or (Path(config).stem if config else f"gain{params.gain}")
    report["connectome_meta"]["sha256"] = pin["sha256"]
    report["connectome_meta"]["pinned_version"] = pin["version"]
    report["unpinned"] = pin["status"] != "pinned"
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
@click.option("--fail-on-regression", is_flag=True, help="exit 1 if any check that passed in B fails in A, or any task score drops by more than --tolerance (for a lab's CI: A = the new run, B = the committed baseline)")
@click.option("--tolerance", default=0.0, show_default=True, help="allowed drop in a task's score before it counts as a regression")
@click.option("--format", "fmt", default="table", type=click.Choice(["table", "json", "markdown"]), show_default=True)
def diff(a, b, fail_on_regression, tolerance, fmt):
    """Paired comparison of two result files: per-check graded differences (A − B), the probability
    that A is better on a random check, and a bootstrap CI over seeds when both runs have them.
    With --fail-on-regression the exit code says whether A lost anything B had (ROADMAP item 57)."""
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
    # regressions: a check B passed that A fails; a task whose score dropped by more than the tolerance
    ta = {t["task"]: t for t in ra["tasks"]}; tb = {t["task"]: t for t in rb["tasks"]}
    lost_checks = [k for k in keys if cb[k]["passed"] and not ca[k]["passed"]]
    dropped_tasks = [(n, tb[n]["score"], ta[n]["score"]) for n in tb if n in ta and ta[n]["score"] < tb[n]["score"] - tolerance - 1e-9]
    missing_tasks = [n for n in tb if n not in ta]
    regressed = bool(lost_checks or dropped_tasks or missing_tasks)
    if fmt == "json":
        out = {"a": ra.get("label", a), "b": rb.get("label", b), "shared_checks": d["n"], "mean_graded_difference": d["mean"], "p_improve": d["p_improve"],
               "lost_checks": [{"task": k[0], "check": k[1]} for k in lost_checks],
               "dropped_tasks": [{"task": n, "before": s0, "after": s1} for n, s0, s1 in dropped_tasks],
               "missing_tasks": missing_tasks, "regressed": regressed,
               "per_check": [{"task": k[0], "check": k[1], "a": ca[k]["graded"], "b": cb[k]["graded"], "delta": ca[k]["graded"] - cb[k]["graded"]} for k in keys]}
        print(json.dumps(out, indent=2))
        if fail_on_regression and regressed:
            raise SystemExit(1)
        return
    if fmt == "markdown":
        print(f"### {ra.get('label', a)} vs {rb.get('label', b)}\n")
        print(f"{d['n']} shared checks · mean graded difference A − B {d['mean']:+.3f} · P(A better) {d['p_improve']:.0%}\n")
        print("| task | check | A | B | Δ |\n|---|---|---|---|---|")
        for k in sorted(keys, key=lambda k: -abs(ca[k]["graded"] - cb[k]["graded"]))[:20]:
            print(f"| {k[0]} | {k[1]} | {ca[k]['graded']:.2f} | {cb[k]['graded']:.2f} | {ca[k]['graded'] - cb[k]['graded']:+.2f} |")
        if regressed:
            print("\n**Regressions:** " + "; ".join([f"{k[0]}: {k[1]}" for k in lost_checks] + [f"{n} {s0:.2f} → {s1:.2f}" for n, s0, s1 in dropped_tasks] + [f"{n} missing" for n in missing_tasks]))
        if fail_on_regression and regressed:
            raise SystemExit(1)
        return
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
    if regressed:
        for k in lost_checks:
            console.print(f"[red]regression[/] {k[0]}: {escape(k[1])} passed in B, fails in A")
        for n, s0, s1 in dropped_tasks:
            console.print(f"[red]regression[/] {n}: score {s0:.2f} → {s1:.2f}")
        for n in missing_tasks:
            console.print(f"[red]regression[/] {n}: in B, missing from A")
    elif fail_on_regression:
        console.print("[green]no regressions[/]: every check B passed, A passes; no task score dropped")
    if fail_on_regression and regressed:
        raise SystemExit(1)


@main.command()
@click.argument("connectome")
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
def fingerprint(connectome, cache):
    """Print a connectome's fingerprint (SHA-256 over ids, sparse matrix and annotations) and whether
    it matches flybench/manifests.json. Paste it into the manifest after a deliberate rebuild."""
    from .manifest import check_pinned
    c = load_connectome(connectome, cache)
    pin = check_pinned(c)
    from rich.markup import escape as _esc
    console.print(_esc(f"{c.name}: {pin['sha256']}  [{pin['status']}]" + (f"  pinned: {pin['expected']}" if pin["status"] == "mismatch" else "")))


@main.command()
@click.argument("frontend", type=click.Choice(["flyvis"]))
@click.argument("action", type=click.Choice(["render", "status"]))
@click.option("--stimulus", "-s", multiple=True, help="which named stimuli to render (default: all)")
def frontend(frontend, action, stimulus):
    """Sensory front ends (flybench.frontends). `flyvis render` runs the named stimuli through the
    pretrained flyvis network and writes data/frontends/flyvis/<name>.npz (committed, so runs and CI
    need neither torch nor flyvis); `flyvis status` says what is cached and whether flyvis is installed."""
    from .frontends.flyvis_frontend import STIMULI, available, cache_path, cached, render_to_cache
    names = list(stimulus) or list(STIMULI)
    if action == "status":
        console.print(f"flyvis installed: {available()}")
        for n in STIMULI:
            console.print(f"  {n:10} {'cached ' + str(cache_path(n)) if cached(n) else 'not cached'}")
        return
    if not available():
        raise SystemExit("flyvis is not installed: pip install flyvis && flyvis download-pretrained (set FLYVIS_ROOT_DIR)")
    for n in names:
        console.print(f"rendering {n} …")
        console.print(f"  → {render_to_cache(n)}")


@main.command()
@click.argument("task_paths", nargs=-1, type=click.Path(exists=True, dir_okay=False))
@click.option("--connectome", "-c", default="flywire783", show_default=True)
@click.option("--gain", default=0.45, show_default=True, type=float, help="reference LIF gain (0.45 on FlyWire, 0.65 on MaleCNS)")
@click.option("--seeds", default=3, show_default=True, type=int)
@click.option("--jobs", "-j", default=1, show_default=True, type=int)
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
@click.option("--comment", default=None, help="write the markdown verdict here (CI posts it on the PR)")
@click.option("--json", "json_out", default=None, help="write the audit records here")
@click.option("--strict", is_flag=True, help="exit 1 on warnings too (tier mismatch, trivial hard task)")
def audit(task_paths, connectome, gain, seeds, jobs, cache, comment, json_out, strict):
    """Is a proposed task worth having? Runs it on the reference LIF with the rewired control and
    rejects non-diagnostic tasks (passes on shuffled wiring), flags trivial ones and tier mismatches.
    CI runs this on every task a pull request adds or changes."""
    from .audit import audit_paths, markdown, to_dict
    from .evaluate import ensure_cache

    if not task_paths:
        raise SystemExit("give one or more task YAML files")
    ensure_cache(connectome, Path(cache))
    c = load_connectome(connectome, cache)
    audits = audit_paths([Path(p) for p in task_paths], c, LIFParams(gain=gain), seeds=seeds, jobs=jobs, connectome_ref=connectome, cache=cache)
    md = markdown(audits, c.name, gain, seeds)
    console.print(md)
    if comment:
        Path(comment).write_text(md, encoding="utf-8")
    if json_out:
        Path(json_out).write_text(json.dumps([to_dict(a) for a in audits], indent=2), encoding="utf-8")
    worst = max((a.verdict for a in audits), key=["ok", "warn", "reject"].index)
    if worst == "reject" or (strict and worst == "warn"):
        raise SystemExit(1)


@main.command()
@click.argument("results", nargs=-1, type=click.Path(exists=True))
@click.option("--out", "-o", default=None, help="write markdown here (default: stdout)")
def lifecycle(results, out):
    """Which tasks still discriminate? Per task and connectome: rows run, rows passed, and whether the
    passing rows are indistinguishable (saturated → candidate for retirement, docs/GOVERNANCE.md)."""
    from .lifecycle import load_reports, markdown, states

    md = markdown(states(load_reports([Path(r) for r in results] or [Path("results")])))
    if out:
        Path(out).write_text(md + chr(10), encoding="utf-8")
        console.print(f"lifecycle → {out}")
    else:
        console.print(md)


@main.command("fetch-terminals")
@click.option("--connectome", "-c", default="flywire783", show_default=True, type=click.Choice(["flywire783", "malecns"]))
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
@click.option("--connections", default="data/connections.csv.gz", show_default=True, help="FlyWire: the Codex per-neuropil connection table")
@click.option("--table", default=None, help="MaleCNS: cached per-connection ROI counts (fetched from neuPrint if missing)")
def fetch_terminals(connectome, cache, connections, table):
    """Build <cache>/<connectome>/terminal.npz — each edge's axo-axonic (terminal) synapses by neuropil polarity
    (docs/rfcs/M1b): an input in a neuropil where the postsynaptic neuron is >= 80 % presynaptic sits on its axon.
    FlyWire from the Codex table in data/; MaleCNS from neuPrint's per-neuron and per-connection ROI counts."""
    import pandas as pd
    import scipy.sparse as sp
    from .terminal import THETA, flywire_per_neuropil, malecns_per_neuropil, polarity, terminal_counts, to_matrix
    c = load_connectome(connectome, cache)
    if connectome == "flywire783":
        per = flywire_per_neuropil(connections); pol = polarity(per)
    else:
        from .fetch_neuprint import NeuPrint
        t = Path(table or "data/terminal/malecns_per_neuropil.csv.gz")
        if not t.exists():
            console.print(f"fetching per-connection ROI counts from neuPrint → {t}")
            per = malecns_per_neuropil(NeuPrint(), log=lambda m: console.print(escape(str(m))))
            t.parent.mkdir(parents=True, exist_ok=True); per.to_csv(t, index=False)
        per = pd.read_csv(t); pol = polarity(per)
    tab = terminal_counts(per, pol)
    T = to_matrix(c, tab)
    if connectome == "malecns":
        # union with RFC M1's neck rule: an ascending neuron's brain arbor is axon whatever its local polarity
        # (its dendrites are in the cord), and the same for a descending neuron's cord arbor. Recorded in M1b.
        neck = pd.read_csv("data/terminal/malecns_terminal_synapses.csv.gz"); neck = neck[neck["terminal"] > 0]
        Tn = to_matrix(c, neck[["pre", "post", "terminal"]])
        T = abs(T).maximum(abs(Tn)).multiply(c.W.tocsr().sign()).tocsr(); T.eliminate_zeros()
    out = Path(cache) / connectome / "terminal.npz"
    sp.save_npz(out, T)
    n_neurons = int((abs(T).sum(axis=0) > 0).sum())
    console.print(f"[green]terminal[/] θ={THETA}: {T.nnz:,} edges carry {int(abs(T).sum()):,} terminal synapses "
                  f"({int(abs(T).sum()) / max(int(abs(c.W).sum()), 1):.2%} of all) onto {n_neurons:,} neurons → {out}")


@main.command("verify-adapter")
@click.argument("simulator")
@click.option("--connectome", "-c", default="toy", show_default=True, help="the contract is checked on this connectome (the toy is enough)")
@click.option("--gain", default=1.0, show_default=True)
@click.option("--cache", default=str(DEFAULT_CACHE), show_default=True)
def verify_adapter_cmd(simulator, connectome, gain, cache):
    """Check a simulator against the adapter contract (flybench.adapter): 'module:Class'. Names every
    defect — wrong result types, spikes out of range, ignored seeds or stimuli, an unhonoured ramp, a
    declared capability that does not hold — and exits 1 if there is one. Run before submitting."""
    from .adapter import verify_adapter
    c = load_connectome(connectome, cache)
    rep = verify_adapter(resolve_simulator(simulator), c, gain=gain)
    console.print(f"[bold]{rep.simulator}[/] · capabilities {rep.capabilities or '[]'} · toy run {rep.seconds:.1f} s ({rep.spikes_per_second:,.0f} spikes/s)")
    if rep.ok:
        console.print("[green]conforms[/]: no defects")
        return
    for d in rep.defects:
        console.print(f"  [red]{d.name}[/]: {d.detail}")
    console.print(f"[red]{len(rep.defects)} defect(s)[/]")
    raise SystemExit(1)


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
@click.option("--strict", is_flag=True, help="every cited basis must carry a DOI or bioRxiv id (in the basis or the task citation); conventions are exempt")
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def lint(paths, strict):
    """Validate task YAML files (defaults to tasks/)."""
    from .bench import TASK_DIR
    from .lint import lint_files

    files = [Path(p) for p in paths] or sorted(TASK_DIR.glob("*.yaml"))
    problems = lint_files(files, strict=strict)
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
@click.option("--jobs", "-j", default=1, show_default=True, type=int, help="worker processes (bit-identical to serial)")
def verify(report, cache, tolerance, mark, jobs):
    """Re-run a submitted report's parameters and compare scores. Maintainers run this before marking a result verified."""
    from .validate import validate_report

    r = json.loads(Path(report).read_text(encoding="utf-8"))
    errs = validate_report(r)
    if errs:
        console.print("[red]report is not valid:[/]"); [console.print("  " + escape(e)) for e in errs]; raise SystemExit(1)
    from .evaluate import ALLOWED_SIMULATORS
    sim_name = r.get("simulator", "flybench.sim.LIFSimulator")
    spec = next((s for s in ALLOWED_SIMULATORS if s.replace(":", ".") == sim_name), None)
    if spec is None:
        console.print(f"[yellow]custom simulator {sim_name} — install it, then re-run with --simulator to verify manually[/]"); raise SystemExit(2)
    c = load_connectome(r["connectome"], cache)
    params = LIFParams.from_dict(r["params"])
    names = {t["task"] for t in r["tasks"]}
    tasks = [t for t in load_tasks() if t["name"] in names]
    fresh = run_suite(c, params, tasks, seeds=int(r.get("seeds", 1)), simulator=resolve_simulator(spec), jobs=int(jobs),
                      connectome_ref=r["connectome"], cache=cache, simulator_spec=spec)
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
@click.option("--jobs", "-j", default=1, show_default=True, type=int, help="worker processes (bit-identical to serial)")
def evaluate(config, out, comment, seeds, cache, jobs):
    """Evaluate a submission config (configs/submissions/*.yaml) on the real connectome. This is what CI runs."""
    from .evaluate import evaluate as _evaluate

    _evaluate(Path(config), Path(out) if out else None, Path(comment) if comment else None, Path(cache), seeds, jobs=jobs)


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
