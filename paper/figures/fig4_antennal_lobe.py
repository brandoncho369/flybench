"""Figure 4: DA1 projection neurons and their own channel, before and after signing the blank transmitters.

Task 18 (da1_sparseness): each condition drives one glomerulus's ORNs at 100 Hz; the readout is the DA1 PNs.
cVA (DA1's own ligand) should win; lifetime sparseness should reach the measured 0.90 (Schlief & Wilson 2007).
Both builds at the reference gain 0.45, 3 seeds: bars are seed means, dots the three seeds. Per-seed rates are
reconstructed from the per-seed check values (the own-channel rate check and each own/other ratio check)."""
import matplotlib.pyplot as plt
import numpy as np

from common import BUILDS, INK, INK2, MUTED, result, save

ROWS = {"flywire783": "flywire783_gain0.45", "flywire783_ntfix": "flywire783_ntfix_gain0.45"}
COND = ["cva", "dm1", "dm2", "dm4", "dl1", "dl5", "va1v", "dc1"]
LABEL = {"cva": "DA1\n(cVA, own)", "dm1": "DM1", "dm2": "DM2", "dm4": "DM4", "dl1": "DL1", "dl5": "DL5", "va1v": "VA1v", "dc1": "DC1"}

data = {}
for b, f in ROWS.items():
    t = next(t for t in result(f)["tasks"] if t["task"] == "da1_sparseness")
    s = next(c for c in t["checks"] if c["description"].startswith("lifetime"))
    own = next(c for c in t["checks"] if c["description"].startswith("rate[cva, da1_pn] >="))["per_seed"]
    per = {"cva": own}
    for c in COND[1:]:
        ratio = next(k for k in t["checks"] if k["description"].startswith(f"rate[cva, da1_pn] / rate[{c}]"))["per_seed"]
        per[c] = [o / r for o, r in zip(own, ratio)]
    data[b] = {"rates": {c: t["measurements"][c]["rate"] for c in COND}, "sparseness": s["value"],
               "sparseness_per_seed": s["per_seed"], "rates_per_seed": per}

fig, ax = plt.subplots(figsize=(7.2, 3.0))
x, w = np.arange(len(COND)), 0.38
for j, b in enumerate(ROWS):
    vals = [data[b]["rates"][c] for c in COND]
    ax.bar(x + (j - 0.5) * (w + 0.02), vals, w, color=BUILDS[b][1], zorder=2,
           label=f"{BUILDS[b][0]}: lifetime sparseness {data[b]['sparseness']:.3f}")
    for xi, v, c in zip(x + (j - 0.5) * (w + 0.02), vals, COND):
        ax.plot([xi - 0.08, xi, xi + 0.08], data[b]["rates_per_seed"][c], "o", ms=2.2, color=INK, zorder=3)
        ax.text(xi, max(v, *data[b]["rates_per_seed"][c]) + 8, f"{v:.0f}", ha="center", va="bottom", fontsize=6, color=INK)
ax.set_xticks(x, [LABEL[c] for c in COND]); ax.set_ylabel("DA1 PN rate (Hz)"); ax.set_ylim(0, 560)
ax.set_title("DA1 projection neurons: their own glomerulus vs seven others (gain 0.45)", loc="left")
ax.plot([], [], " ", label="real fly: lifetime sparseness 0.90 (Schlief & Wilson 2007)")
ax.legend(loc="upper right", fontsize=6.5, handlelength=1)

# for the text, not plotted: does adaptation alone, or Shiu's graph, give the channel back?
for k, f in {"adaptive_reference_0.45": "adaptive-lif-b-2-mv-tau-200-ms", "shiu_graph_0.7": "flywire783_shiu_gain0.7",
             "flywire783_ntfix_0.65": "flywire783_ntfix_gain0.65"}.items():
    t = next(t for t in result(f)["tasks"] if t["task"] == "da1_sparseness")
    data[k] = {"sparseness": next(c for c in t["checks"] if c["description"].startswith("lifetime"))["value"],
               "rates": {c: t["measurements"][c]["rate"] for c in COND}}
save(fig, "fig4_antennal_lobe", data)
