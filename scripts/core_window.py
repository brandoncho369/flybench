"""Core window from a gain sweep (RFC D1): for each (connectome, model) series of result files, the
gains at which every core task passes on every seed, the longest consecutive run of them, and what
fails at the others.

    python scripts/core_window.py results/sweeps/d1_core_fine
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

CORE = ("stability", "sugar_to_proboscis", "bitter_suppression", "looming_to_giant_fiber", "taste_specificity")
NAME = re.compile(r"^(?P<series>.+)_(?P<gain>\d\.\d\d)\.json$")


def load(folder: Path) -> dict[str, dict[float, dict]]:
    series: dict[str, dict[float, dict]] = defaultdict(dict)
    for f in sorted(folder.glob("*.json")):
        m = NAME.match(f.name)
        if m:
            series[m["series"]][float(m["gain"])] = json.loads(f.read_text(encoding="utf-8"))
    return series


def failing(report: dict) -> list[str]:
    tasks = {t["task"]: t for t in report["tasks"]}
    return [c for c in CORE if c not in tasks or not tasks[c]["passed"]]


def windows(gains: list[float], ok: set[float], step: float = 0.01) -> list[tuple[float, float]]:
    runs, start, prev = [], None, None
    for g in gains:
        if g in ok and start is not None and abs(g - prev - step) < 1e-6:
            prev = g
        elif g in ok:
            if start is not None:
                runs.append((start, prev))
            start = prev = g
        elif start is not None:
            runs.append((start, prev)); start = None
    if start is not None:
        runs.append((start, prev))
    return runs


def main(folder: str) -> None:
    for name, by_gain in sorted(load(Path(folder)).items()):
        gains = sorted(by_gain)
        ok = {g for g in gains if not failing(by_gain[g])}
        runs = windows(gains, ok)
        best = max(runs, key=lambda r: r[1] - r[0], default=None)
        width = f"{best[0]:.2f}–{best[1]:.2f} ({round((best[1] - best[0]) / 0.01) + 1} points)" if best else "none"
        print(f"{name}: {len(gains)} gains {gains[0]:.2f}–{gains[-1]:.2f}; passing {len(ok)}; longest window {width}")
        if len(runs) > 1:
            print("   all windows: " + ", ".join(f"{a:.2f}–{b:.2f}" for a, b in runs))
        line = []
        for g in gains:
            f = failing(by_gain[g])
            line.append(f"{g:.2f}:" + ("ok" if not f else "+".join(c.split("_")[0] for c in f)))
        print("   " + " ".join(line))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/sweeps/d1_core_fine")
