"""Shared paths, loading and style for the preprint figures. Every number a figure shows comes from a
flybench v1.0.0 result file and is also written to <figure>.numbers.json for the numbers check."""
import json
from pathlib import Path

import matplotlib as mpl
import yaml

_UP = Path(__file__).resolve().parents[2]
FLYBENCH = _UP if (_UP / "tasks").is_dir() else _UP / "flybench"   # inside the flybench repo, or beside it
RESULTS = FLYBENCH / "results"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

# Three FlyWire v783 builds, in a fixed order; colours are the first three categorical slots of the
# validated reference palette (all-pairs CVD-safe; aqua is < 3:1 on white, so bars carry value labels).
BUILDS = {
    "flywire783": ("Codex ≥5 (reference)", "#2a78d6"),
    "flywire783_ntfix": ("Codex, blank transmitters signed", "#eb6834"),
    "flywire783_shiu": ("Shiu et al. 2024 graph", "#1baf7a"),
}
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"

mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"], "font.size": 8,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlesize": 9, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "legend.frameon": False, "savefig.dpi": 300, "pdf.fonttype": 42,
})


def result(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


def graded_by_task(report: dict) -> dict[str, float]:
    return {t["task"]: t["graded"] for t in report["tasks"] if t.get("graded") is not None}


def task_meta() -> dict[str, dict]:
    meta = {}
    for f in sorted((FLYBENCH / "tasks").glob("*.yaml")):
        y = yaml.safe_load(f.read_text(encoding="utf-8"))
        meta[y["name"]] = {"tier": y.get("tier", "hard"), "circuit": y.get("circuit", "")}
    return meta


def save(fig, name: str, numbers: dict) -> None:
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    (OUT / f"{name}.numbers.json").write_text(json.dumps(numbers, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT / name}.pdf/.png/.numbers.json")
