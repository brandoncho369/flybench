"""Figure 3: the core window per build and neuron model, from the RFC D1 fine sweep (gain 0.40-0.70 in steps of 0.01,
5 seeds, core tasks only; flybench/results/sweeps/d1_core_fine). A cell is filled in the build's colour where all five
core reflexes pass on every seed; otherwise it is grey and lettered with what fails (S sugar -> proboscis,
B bitter suppression, L loom -> giant fibre, T taste specificity, R stability/rest)."""
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from common import BUILDS, FLYBENCH, GRID, INK, INK2, MUTED, save

sys.path.insert(0, str(FLYBENCH / "scripts"))
from core_window import failing, load, windows  # noqa: E402

SERIES = [("flywire783_lif", "flywire783", "LIF"), ("flywire783_adaptive", "flywire783", "adaptive LIF"),
          ("flywire783_ntfix_lif", "flywire783_ntfix", "LIF"), ("flywire783_ntfix_adaptive", "flywire783_ntfix", "adaptive LIF")]
CODE = {"sugar_to_proboscis": "S", "bitter_suppression": "B", "looming_to_giant_fiber": "L",
        "taste_specificity": "T", "stability": "R"}

data = load(FLYBENCH / "results" / "sweeps" / "d1_core_fine")
rows = [s for s in SERIES if s[0] in data]
gains = sorted({g for s, _, _ in rows for g in data[s]})
fig, ax = plt.subplots(figsize=(7.2, 0.7 + 0.55 * len(rows)))
ax.grid(False)
numbers = {}
for i, (s, build, model) in enumerate(rows):
    by_gain = data[s]
    ok = {g for g in by_gain if not failing(by_gain[g])}
    runs = windows(sorted(by_gain), ok)
    best = max(runs, key=lambda r: r[1] - r[0], default=None)
    numbers[s] = {"gains": [min(by_gain), max(by_gain)], "n_gains": len(by_gain), "n_passing": len(ok),
                  "window": [best[0], best[1]] if best else None,
                  "window_points": round((best[1] - best[0]) / 0.01) + 1 if best else 0,
                  "window_text": f"{best[0]:.2f}–{best[1]:.2f}" if best else "none",
                  "fails": {f"{g:.2f}": [CODE[c] for c in failing(by_gain[g])] for g in sorted(by_gain)}}
    y = len(rows) - 1 - i
    for g in sorted(by_gain):
        f = failing(by_gain[g])
        x = round((g - gains[0]) / 0.01)
        ax.add_patch(Rectangle((x + 0.06, y + 0.08), 0.88, 0.84, color=BUILDS[build][1] if not f else GRID, lw=0))
        if f:
            ax.text(x + 0.5, y + 0.5, "".join(CODE[c] for c in f), ha="center", va="center", fontsize=5.6, color=INK2, fontweight="bold")
    label = numbers[s]["window_text"] if best else "no window" if len(by_gain) == len(gains) else "(running)"
    ax.text(len(gains) + 0.4, y + 0.5, label, va="center", fontsize=7, color=INK if best else MUTED)
ax.set_xlim(0, len(gains)); ax.set_ylim(0, len(rows))
ticks = [k for k, g in enumerate(gains) if round(g * 100) % 5 == 0]
ax.set_xticks([k + 0.5 for k in ticks], [f"{gains[k]:.2f}" for k in ticks])
ax.set_yticks([len(rows) - 0.5 - i for i in range(len(rows))],
              [f"{BUILDS[b][0].split(' (')[0]}, {m}" for _, b, m in rows])
ax.set_xlabel("synaptic gain (×0.275 mV per synapse)")
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_title("Gains at which all five core reflexes pass on every seed\n", loc="left")
ax.text(0, len(rows) + 0.15, "grey = a core reflex fails: S sugar→proboscis, B bitter suppression, L loom→giant fibre, "
        "T taste specificity, R rest", fontsize=6.5, color=MUTED)
save(fig, "fig3_gain_windows", numbers)
