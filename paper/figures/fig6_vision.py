"""Figure 6: through a real eye (flyvis front end, task 32) the giant-fibre readout fires at a flash and not at a
loom, on every build and both datasets. Readout rate in the task window, mean of 3 seeds (the results keep per-seed
values only for checked quantities; the loom is 0 on every seed, the flash rate is not a check)."""
import matplotlib.pyplot as plt
import numpy as np

from common import BUILDS, INK, INK2, result, save

ROWS = [("Codex ≥5 (reference), 0.45", "flywire783_gain0.45", BUILDS["flywire783"][1]),
        ("adaptive LIF, Codex ≥5, 0.45", "adaptive-lif-b-2-mv-tau-200-ms", BUILDS["flywire783"][1]),
        ("Shiu constants, Codex ≥5, 1.0", "shiu2024", BUILDS["flywire783"][1]),
        ("Shiu et al. 2024 graph, 0.7", "flywire783_shiu_gain0.7", BUILDS["flywire783_shiu"][1]),
        ("Codex, blank transmitters signed, 0.65", "flywire783_ntfix_gain0.65", BUILDS["flywire783_ntfix"][1]),
        ("MaleCNS v1.0, 0.65", "malecns-gain-0.65", "#6250d6")]

numbers = {}
fig, ax = plt.subplots(figsize=(5.6, 3.2))
y = np.arange(len(ROWS))[::-1]
for yi, (name, f, color) in zip(y, ROWS):
    t = next(t for t in result(f)["tasks"] if t["task"] == "flyvis_loom_escape")
    loom, flash = t["measurements"]["loom"]["rate"], t["measurements"]["flash"]["rate"]
    numbers[f] = {"loom_hz": loom, "flash_hz": flash}
    ax.barh(yi + 0.19, flash, 0.34, color=color, zorder=2)
    ax.barh(yi - 0.19, max(loom, 0.4), 0.34, color="none", edgecolor=color, lw=1, zorder=2)
    ax.text(flash + 1, yi + 0.19, f"flash {flash:.0f} Hz", va="center", fontsize=6.5, color=INK)
    ax.text(max(loom, 0.4) + 1, yi - 0.19, f"loom {loom:.0f} Hz", va="center", fontsize=6.5, color=INK2)
ax.set_yticks(y, [n for n, _, _ in ROWS]); ax.set_xlabel("giant-fibre readout rate (Hz)"); ax.set_xlim(0, 60)
ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_title("Through the flyvis eye, a flash drives the escape readout and a loom does not", loc="left")
save(fig, "fig6_vision", numbers)
