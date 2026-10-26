"""Figure 1A: how one task is scored. Schematic: a pinned graph build (or a shuffled control of it) runs the same LIF;
a task drives a stimulus population and reads a readout population; each check compares the readout with a
threshold that carries its source; the run scores pass/graded per seed and specificity against the control.
The example is task 02 (sugar -> proboscis). No data; numbers.json records the labels only."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from common import BUILDS, GRID, INK, INK2, save

TOP, H, STEP = 33, 25, 2.75
fig, ax = plt.subplots(figsize=(7.2, 2.6))
ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")


def box(x, w, title, lines):
    ax.add_patch(FancyBboxPatch((x, TOP - H), w, H, boxstyle="round,pad=0.3,rounding_size=1.2", fc="white", ec=GRID, lw=1))
    ax.text(x + 1.2, TOP - 1.8, title, fontsize=7.5, fontweight="bold", color=INK, va="top")
    for k, t in enumerate(lines):
        ax.text(x + 1.2, TOP - 6.8 - STEP * k, t, fontsize=6.2, color=INK2, va="center")


def arrow(x0, x1):
    ax.add_patch(FancyArrowPatch((x0, TOP - H / 2), (x1, TOP - H / 2), arrowstyle="-|>", mutation_scale=9, color=INK2, lw=0.8))


box(1, 27, "1  Graph", ["FlyWire v783, one of three", "pinned builds:", "", "", "", "or a shuffled control of it", "(rewired, random, sign-flip)"])
for k, b in enumerate(BUILDS):
    y = TOP - 6.8 - STEP * (2 + k)
    ax.add_patch(FancyBboxPatch((2.4, y - 0.8), 1.5, 1.6, boxstyle="round,pad=0,rounding_size=0.3", fc=BUILDS[b][1], ec="none"))
    ax.text(4.8, y, BUILDS[b][0].replace(" (reference)", ", reference"), fontsize=6.2, color=INK2, va="center")
arrow(28.6, 30.6)
box(31, 21, "2  Model", ["the same LIF for every", "neuron (Shiu et al. 2024),", "one global gain", "", "or any submitted model", "through the adapter"])
arrow(52.6, 54.6)
box(55, 23, "3  Task (one YAML file)", ["stimulus: sugar GRNs, 100 Hz", "readout: MN9 (proboscis)", "check: MN9 rate > threshold",
                                        "basis: the cited experiment,", "  or \"convention\"", "conditions: drive, silence, mix"])
arrow(78.6, 80.6)
box(81, 18, "4  Score", ["pass: on every seed", "graded: sigmoid of the", "  log margin, 0.5 at", "  the threshold",
                         "specificity: real wiring", "  minus best control"])
ax.add_patch(FancyBboxPatch((1, 1.2), 98, 4, boxstyle="round,pad=0.2,rounding_size=1", fc="#f4f3ef", ec="none"))
ax.text(50, 3.2, "Pre-registration: an RFC commits predictions before the first run on real wiring; "
        "the outcome is recorded beside them, wrong ones included.", fontsize=6.2, color=INK2, ha="center", va="center")
ax.text(1, 39.5, "A  How a task is scored", fontsize=9, fontweight="bold", color=INK, va="top")
save(fig, "fig1a_pipeline", {"example_task": "sugar_to_proboscis", "builds": [v[0] for v in BUILDS.values()]})
