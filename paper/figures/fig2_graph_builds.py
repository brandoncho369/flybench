"""Figure 2: three builds of the same FlyWire v783 neurons.

A  what differs between the builds (edges, excitatory / inhibitory synapse mass, E/I), from the pinned caches
B  mean graded score per build at gain 0.45 and 0.7 (dots) with 95 % CIs (bootstrap over tasks and seeds),
   against the adaptive LIF on the reference build at 0.45
C  per-task change, signed build minus reference build, at gain 0.7

Scores in B and C are means over the tasks every compared row ran, so all bars share one task set."""
import sys

import matplotlib.pyplot as plt
import numpy as np

from common import BUILDS, FLYBENCH, INK, INK2, MUTED, graded_by_task, result, save, task_meta

sys.path.insert(0, str(FLYBENCH))
from flybench.connectome import load_connectome  # noqa: E402

ROWS = {  # (build, gain) -> result file
    ("flywire783", 0.45): "flywire783_gain0.45", ("flywire783", 0.7): "flywire783_gain0.7",
    ("flywire783_ntfix", 0.45): "flywire783_ntfix_gain0.45", ("flywire783_ntfix", 0.7): "flywire783_ntfix_gain0.7",
    ("flywire783_shiu", 0.45): "flywire783_shiu_gain0.45", ("flywire783_shiu", 0.7): "flywire783_shiu_gain0.7",
}
ADAPTIVE = "adaptive-lif-b-2-mv-tau-200-ms"

graded = {k: graded_by_task(result(v)) for k, v in ROWS.items()}
adaptive = graded_by_task(result(ADAPTIVE))
common = sorted(set.intersection(*(set(g) for g in graded.values()), set(adaptive)))
mean = lambda g: float(np.mean([g[t] for t in common]))
seeds = {k: {t["task"]: np.asarray(t["graded_per_seed"], float) for t in result(v)["tasks"]} for k, v in ROWS.items()}
seeds["adaptive"] = {t["task"]: np.asarray(t["graded_per_seed"], float) for t in result(ADAPTIVE)["tasks"]}
rng = np.random.default_rng(0)


def ci(k, n=4000):
    """95 % CI of the mean over the shared tasks: tasks resampled with replacement, seeds within each task."""
    rows = [seeds[k][t] for t in common]
    draws = [np.mean([rng.choice(rows[i], rows[i].size).mean() for i in rng.integers(0, len(rows), len(rows))])
             for _ in range(n)]
    return [float(x) for x in np.percentile(draws, [2.5, 97.5])]

# A: graph statistics from the caches
stats = {}
for b in BUILDS:
    W = load_connectome(b).W
    exc, inh = float(W.data[W.data > 0].sum()), float(-W.data[W.data < 0].sum())
    stats[b] = {"edges": int(W.nnz), "exc_synapses": exc, "inh_synapses": inh, "e_over_i": exc / inh}

fig = plt.figure(figsize=(7.2, 6.8))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.35], width_ratios=[1, 1.25], hspace=0.45, wspace=0.35)

axA = fig.add_subplot(gs[0, 0]); axA.axis("off"); axA.set_title("A  Same neurons, three graphs", loc="left")
SHORT = {"flywire783": "Codex ≥5", "flywire783_ntfix": "Codex, signed", "flywire783_shiu": "Shiu 2024"}
cells = [[SHORT[b], f"{s['edges'] / 1e6:.2f} M", f"{s['exc_synapses'] / 1e6:.1f} M", f"{s['inh_synapses'] / 1e6:.1f} M",
          f"{s['e_over_i']:.2f}"] for b, s in stats.items()]
tab = axA.table(cellText=cells, colLabels=["build", "edges", "exc.", "inh.", "E/I"], loc="center", cellLoc="right", colLoc="right")
tab.auto_set_font_size(False); tab.set_fontsize(7); tab.scale(1, 1.5); tab.auto_set_column_width([0])
for (r, c), cell in tab.get_celld().items():
    cell.set_edgecolor("#e1e0d9"); cell.set_linewidth(0.5)
    if c == 0: cell.set_text_props(ha="left"); cell._loc = "left"
    if r == 0: cell.set_text_props(color=INK2, weight="bold")
for i, b in enumerate(BUILDS, start=1):
    tab[i, 0].get_text().set_color(BUILDS[b][1] if b != "flywire783_shiu" else "#0f7a54")  # darker aqua for text contrast

axB = fig.add_subplot(gs[0, 1]); axB.set_title("B  Graded score by build and gain", loc="left")
gains, step = (0.45, 0.7), 0.22
cis = {}
for j, b in enumerate(BUILDS):
    xs = np.arange(len(gains)) + (j - 1) * step
    for x, g in zip(xs, gains):
        v, (lo, hi) = mean(graded[(b, g)]), ci((b, g))
        cis[f"{b}@{g}"] = [lo, hi]
        axB.plot([x, x], [lo, hi], color=BUILDS[b][1], lw=1.6, zorder=2, solid_capstyle="round")
        axB.plot([x], [v], "o", ms=6.5, color=BUILDS[b][1], mec="white", mew=1, zorder=3,
                 label=BUILDS[b][0] if g == gains[0] else None)
        axB.text(x + 0.05, v, f"{v:.3f}", ha="left", va="center", fontsize=6, color=INK)
a = mean(adaptive)
cis["adaptive_reference_0.45"] = ci("adaptive")
axB.axhline(a, color=INK2, lw=1, ls=(0, (4, 3)), zorder=1, label=f"adaptive LIF, reference build, 0.45: {a:.3f}")
axB.set_xticks(range(len(gains)), [f"gain {g}" for g in gains]); axB.set_xlim(-0.5, 1.5); axB.set_ylim(0.3, 0.9)
axB.set_ylabel("mean graded score (95 % CI)")
axB.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=1, fontsize=6.5, handlelength=1)

axC = fig.add_subplot(gs[1, :]); axC.set_title("C  Per task at gain 0.7: signed build minus reference build", loc="left")
meta = task_meta()
d = sorted(((graded[("flywire783_ntfix", 0.7)][t] - graded[("flywire783", 0.7)][t], t) for t in common), reverse=True)
ys = np.arange(len(d))
colors = [BUILDS["flywire783_ntfix"][1] if v > 0 else BUILDS["flywire783"][1] for v, _ in d]
axC.bar(ys, [v for v, _ in d], 0.7, color=colors, zorder=2)
axC.axhline(0, color=INK2, lw=0.8)
axC.set_xticks(ys, [f"{t} ({meta.get(t, {}).get('circuit', '')})" for _, t in d], rotation=60, ha="right", fontsize=6)
axC.set_ylabel("Δ graded score"); axC.set_xlim(-0.6, len(d) - 0.4)
axC.text(len(d) - 1, max(v for v, _ in d) * 0.9, f"{len(common)} tasks shared by every row\norange: signed build higher · blue: reference build higher", ha="right", va="top", fontsize=6.5, color=MUTED)

save(fig, "fig2_graph_builds", {
    "tasks_compared": common,
    "graph_stats": stats,
    "mean_graded": {f"{b}@{g}": mean(graded[(b, g)]) for (b, g) in ROWS},
    "adaptive_reference_0.45": a,
    "ci95": cis,
    "delta_ntfix_minus_codex_0.7": {t: v for v, t in d},
})
