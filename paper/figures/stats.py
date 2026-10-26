"""Paired comparisons for the text: row A minus row B over the tasks both ran, with a 95 % CI from a hierarchical
bootstrap (tasks resampled with replacement, then each row's seeds resampled within each task; 10,000 draws).
Two summaries, because the order of the builds depends on it: the plain mean over tasks (what Fig. 2 plots) and
flybench's run-level `graded`, the interquartile mean (IQM) over tasks. -> out/stats.numbers.json"""
import numpy as np

from common import result, save

ROWS = {"ref045": "flywire783_gain0.45", "ref07": "flywire783_gain0.7",
        "ntfix045": "flywire783_ntfix_gain0.45", "ntfix07": "flywire783_ntfix_gain0.7",
        "shiu045": "flywire783_shiu_gain0.45", "shiu07": "flywire783_shiu_gain0.7",
        "adaptive045": "adaptive-lif-b-2-mv-tau-200-ms"}
PAIRS = [("ntfix07", "ref07"), ("shiu07", "ref07"), ("ntfix07", "shiu07"),
         ("ntfix045", "ref045"), ("shiu045", "ref045"), ("adaptive045", "ref045")]
N_BOOT, TIE = 10_000, 0.01


def iqm(v):
    v = np.sort(np.asarray(v, dtype=float))
    lo, hi = np.percentile(v, [25, 75])
    return float(v[(v >= lo) & (v <= hi)].mean())


per_seed = {k: {t["task"]: np.asarray(t["graded_per_seed"], dtype=float) for t in result(f)["tasks"]}
            for k, f in ROWS.items()}
shared = sorted(set.intersection(*(set(v) for v in per_seed.values())))
rng = np.random.default_rng(0)
out = {"n_tasks": len(shared), "n_boot": N_BOOT, "pairs": {}}
for a, b in PAIRS:
    A = [per_seed[a][t] for t in shared]; B = [per_seed[b][t] for t in shared]
    ma, mb = np.array([x.mean() for x in A]), np.array([x.mean() for x in B])
    d = ma - mb
    boot_mean, boot_iqm = np.empty(N_BOOT), np.empty(N_BOOT)
    for k in range(N_BOOT):
        idx = rng.integers(0, len(shared), len(shared))
        ra = np.array([rng.choice(A[i], A[i].size).mean() for i in idx])
        rb = np.array([rng.choice(B[i], B[i].size).mean() for i in idx])
        boot_mean[k], boot_iqm[k] = (ra - rb).mean(), iqm(ra) - iqm(rb)
    out["pairs"][f"{a}-{b}"] = {
        "mean_a": float(ma.mean()), "mean_b": float(mb.mean()), "diff": float(d.mean()),
        "ci": [float(x) for x in np.percentile(boot_mean, [2.5, 97.5])],
        "iqm_a": iqm(ma), "iqm_b": iqm(mb), "iqm_diff": iqm(ma) - iqm(mb),
        "iqm_ci": [float(x) for x in np.percentile(boot_iqm, [2.5, 97.5])],
        "better": int((d > TIE).sum()), "worse": int((d < -TIE).sum()), "tied": int((abs(d) <= TIE).sum())}
    p = out["pairs"][f"{a}-{b}"]
    print(f"{a}-{b}: mean {p['diff']:+.3f} [{p['ci'][0]:+.3f}, {p['ci'][1]:+.3f}]  IQM {p['iqm_diff']:+.3f} "
          f"[{p['iqm_ci'][0]:+.3f}, {p['iqm_ci'][1]:+.3f}]  better/worse/tied {p['better']}/{p['worse']}/{p['tied']}")
# headline: the build effect against the neuron-model effect, each with its CI
out["build_vs_model_mean"] = out["pairs"]["ntfix07-ref07"]["diff"] - out["pairs"]["adaptive045-ref045"]["diff"]
import matplotlib.pyplot as plt  # noqa: E402  (save() expects a figure; this script has none worth printing)
save(plt.figure(), "stats", out)
