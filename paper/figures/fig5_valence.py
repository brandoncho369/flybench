"""Figure 5: odour valence (task 37). One antenna's ORNs of one glomerulus at 100 Hz; DNa02 left vs right.
Asymmetry index (L - R) / (L + R): +1 = only the stimulated (left) side, i.e. a turn toward; -1 = a turn away.
Attractive channels should be positive, aversive negative. Silent pairs (both DNa02 < 2 Hz, RFC S2) are drawn
hollow at 0. Reference and Shiu's graph at their working gains; the signed build, which has no gain passing every
core reflex, at 0.65 (its best core score). Large dots: from seed-mean rates; small dots: each seed, from the per-seed
L/R ratio check."""
import matplotlib.pyplot as plt
import numpy as np

from common import BUILDS, INK2, MUTED, result, save

ROWS = [("flywire783", "flywire783_gain0.45", "0.45"), ("flywire783_shiu", "flywire783_shiu_gain0.7", "0.7"),
        ("flywire783_ntfix", "flywire783_ntfix_gain0.65", "0.65")]
CH = [("dm1", "DM1\nvinegar"), ("dm2", "DM2"), ("va2", "VA2"), ("v", "V\nCO₂"), ("da2", "DA2\ngeosmin")]
ATTRACTIVE = 3

numbers = {}
fig, ax = plt.subplots(figsize=(5.6, 3.2))
ax.axvspan(-0.5, ATTRACTIVE - 0.5, color="#f0efec", zorder=0)
ax.text(1, 1.12, "attractive: should be > 0", ha="center", fontsize=6.5, color=MUTED)
ax.text(3.5, 1.12, "aversive: should be < 0", ha="center", fontsize=6.5, color=MUTED)
ax.axhline(0, color=INK2, lw=0.8)
for j, (b, f, g) in enumerate(ROWS):
    t = next(t for t in result(f)["tasks"] if t["task"] == "odor_valence_steering")
    numbers[f] = {}
    for i, (c, _) in enumerate(CH):
        L, R = t["measurements"][c]["rate[dna02_left]"], t["measurements"][c]["rate[dna02_right]"]
        silent = max(L, R) < 2
        idx = 0.0 if silent else (L - R) / (L + R)
        numbers[f][c] = {"left_hz": L, "right_hz": R, "asymmetry": idx, "silent": silent}
        x = i + (j - 1) * 0.22
        r = next(k for k in t["checks"] if k["description"].startswith(f"rate[{c}, dna02_left] / rate[{c}, dna02_right]"))["per_seed"]
        seeds = [(q - 1) / (q + 1) for q in r]
        numbers[f][c]["asymmetry_per_seed"] = seeds
        ax.plot([x + 0.07] * len(seeds), seeds, "o", ms=2.4, color=BUILDS[b][1], alpha=0.9, zorder=2)
        ax.plot([x], [idx], "o", ms=7, mfc="none" if silent else BUILDS[b][1], mec=BUILDS[b][1], mew=1.5, zorder=3,
                label=f"{BUILDS[b][0]}, gain {g}" if i == 0 else None)
ax.set_xticks(range(len(CH)), [n for _, n in CH]); ax.set_xlim(-0.5, len(CH) - 0.5); ax.set_ylim(-1.15, 1.25)
ax.set_ylabel("DNa02 asymmetry (L − R)/(L + R)\n+1 toward stimulated side")
ax.legend(loc="lower left", fontsize=6.5, handlelength=1)
ax.text(len(CH) - 0.55, -1.08, "hollow: both DNa02 silent", ha="right", fontsize=6, color=MUTED)
save(fig, "fig5_valence", numbers)
