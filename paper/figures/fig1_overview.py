"""Figure 1B: graded score of every task on the main rows (shuffled-wiring controls are reported as specificity in
the text: the controls record pass/fail per check, not a graded score). Tasks grouped by circuit, core first. Blank = the task cannot run on that dataset (MaleCNS
has a nerve cord, FlyWire does not; some selectors exist on one dataset only). Sequential blue, light = 0."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from common import INK, INK2, MUTED, result, save, task_meta

COLS = [("reference\nCodex 0.45", "flywire783_gain0.45", "real"),
        ("adaptive LIF\nCodex 0.45", "adaptive-lif-b-2-mv-tau-200-ms", "real"),
        ("Shiu constants\nCodex 1.0", "shiu2024", "real"),
        ("Shiu graph\n0.7", "flywire783_shiu_gain0.7", "real"),
        ("signed\nCodex 0.65", "flywire783_ntfix_gain0.65", "real"),
        ("MaleCNS\n0.65", "malecns-gain-0.65", "real")]
SEQ = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281"])

meta = task_meta()
CORE = ("stability", "sugar_to_proboscis", "bitter_suppression", "looming_to_giant_fiber", "taste_specificity")
order = sorted(meta, key=lambda t: (t not in CORE, meta[t]["circuit"], t))
grid = np.full((len(order), len(COLS)), np.nan)
for j, (_, f, kind) in enumerate(COLS):
    tasks = {t["task"]: t for t in result(f)["tasks"]}
    for i, name in enumerate(order):
        t = tasks.get(name)
        if t is None:
            continue
        if kind == "real":
            grid[i, j] = t.get("graded", np.nan)
        else:
            c = (t.get("controls") or {}).get("rewired") or {}
            grid[i, j] = c.get("graded", np.nan)

fig, ax = plt.subplots(figsize=(5.4, 8.6))
ax.grid(False)
im = ax.imshow(np.ma.masked_invalid(grid), cmap=SEQ, vmin=0, vmax=1, aspect="auto")
for i in range(len(order)):
    for j in range(len(COLS)):
        v = grid[i, j]
        if np.isnan(v):
            ax.text(j, i, "–", ha="center", va="center", fontsize=6, color=MUTED)
        else:
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=5.5, color="white" if v > 0.55 else INK)
ax.set_xticks(range(len(COLS)), [c for c, _, _ in COLS], fontsize=6.5)
ax.xaxis.tick_top()
ax.set_yticks(range(len(order)), [f"{n}  ({meta[n]['circuit']})" for n in order], fontsize=6)
n_core = sum(t in CORE for t in order)
ax.axhline(n_core - 0.5, color=INK, lw=1)
ax.text(len(COLS) - 0.45, n_core / 2 - 0.5, "core", rotation=-90, va="center", fontsize=6.5, color=INK2)
ax.text(len(COLS) - 0.45, (n_core + len(order)) / 2, "hard", rotation=-90, va="center", fontsize=6.5, color=INK2)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.08, orientation="horizontal")
cb.set_label("graded score (1 = every check met with margin)", fontsize=6.5, color=INK2); cb.outline.set_visible(False)
save(fig, "fig1b_overview", {"tasks": order, "columns": [c.replace("\n", " ") for c, _, _ in COLS],
                             "graded": [[None if np.isnan(v) else float(v) for v in row] for row in grid]})
