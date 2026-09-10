"""A synthetic ~2k-neuron 'connectome' that exhibits the benchmark reflexes.

This is scaffolding, not science. It lets the tests, the CLI and the web
explorer run without the real FlyWire download, and it doubles as a sanity
check: if a benchmark task can't pass on a network hand-wired to pass it,
the task definition is broken.

Population layout mirrors the Codex annotation columns so the same selector
specs work on both.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from .connectome import Connectome

# name, size, super_class, class, cell_type, hemibrain_type, nt, label, centre(x,y,z in um)
POPS = [
    ("grn_sugar",   40, "sensory", "gustatory", "GRN_sugar",  "",           "ACH",  "sugar GRN",        (0, 380, 80)),
    ("grn_bitter",  30, "sensory", "gustatory", "GRN_bitter", "",           "ACH",  "bitter GRN",       (40, 380, 80)),
    ("grn_water",   20, "sensory", "gustatory", "GRN_water",  "",           "ACH",  "water GRN",        (-40, 380, 80)),
    ("taste_in",    30, "central", "",          "G2N-like",   "",           "ACH",  "taste 2nd order",  (0, 300, 60)),
    ("bitter_in",   30, "central", "",          "bitter_ln",  "",           "GABA", "bitter local",     (40, 300, 60)),
    ("mn9",          2, "motor",   "",          "MN9",        "MN9",        "ACH",  "proboscis motor",  (0, 330, -40)),
    ("lplc2",       60, "visual_projection", "", "LPLC2",     "LPLC2",      "ACH",  "looming",          (-200, 150, 0)),
    ("lc4",         50, "visual_projection", "", "LC4",       "LC4",        "ACH",  "looming",          (200, 150, 0)),
    ("gf",           2, "descending", "",       "GF",         "Giant Fiber","ACH",  "giant fiber",      (0, 200, -20)),
    ("orn",        120, "sensory", "olfactory", "ORN",        "",           "ACH",  "olfactory",        (0, 420, 0)),
    ("pn",          60, "central", "",          "PN",         "",           "ACH",  "projection neuron",(0, 250, 40)),
    ("lhn",         60, "central", "",          "LHN",        "",           "ACH",  "lateral horn",     (120, 220, 60)),
    ("bg_exc",    1000, "central", "",          "",           "",           "ACH",  "",                 (0, 200, 0)),
    ("bg_inh",     500, "central", "",          "",           "",           "GABA", "",                 (0, 200, 0)),
]


def build_toy_connectome(seed: int = 1) -> Connectome:
    rng = np.random.default_rng(seed)
    names, sizes = [p[0] for p in POPS], [p[1] for p in POPS]
    offsets = np.cumsum([0, *sizes])
    n = int(offsets[-1])
    idx = {name: np.arange(offsets[i], offsets[i + 1]) for i, name in enumerate(names)}

    rows, cols, vals = [], [], []

    def connect(pre: str, post: str, p_conn: float, syn_lo: int, syn_hi: int):
        a, b = idx[pre], idx[post]
        m = rng.random((a.size, b.size)) < p_conn
        r, c = np.nonzero(m)
        rows.append(a[r]); cols.append(b[c])
        vals.append(rng.integers(syn_lo, syn_hi + 1, size=r.size))

    # --- feeding circuit: sugar -> interneurons -> MN9, bitter inhibits interneurons
    connect("grn_sugar", "taste_in", 0.4, 4, 10)
    connect("grn_water", "taste_in", 0.3, 4, 10)
    connect("taste_in", "mn9", 0.7, 4, 10)
    connect("grn_bitter", "bitter_in", 0.5, 4, 10)
    connect("bitter_in", "taste_in", 0.6, 5, 12)
    connect("bitter_in", "mn9", 0.4, 4, 8)
    # --- escape: looming detectors -> giant fiber
    connect("lplc2", "gf", 0.6, 3, 8)
    connect("lc4", "gf", 0.6, 3, 8)
    # --- olfaction (present, just not benchmarked)
    connect("orn", "pn", 0.15, 5, 15)
    connect("pn", "lhn", 0.2, 5, 15)
    # --- sparse random background, balanced so it does not run away
    connect("bg_exc", "bg_exc", 0.004, 5, 8)
    connect("bg_exc", "bg_inh", 0.008, 5, 8)
    connect("bg_inh", "bg_exc", 0.010, 5, 12)
    connect("bg_inh", "bg_inh", 0.004, 5, 8)
    connect("lhn", "bg_exc", 0.05, 5, 8)
    connect("taste_in", "bg_exc", 0.03, 5, 8)

    pre = np.concatenate(rows); post = np.concatenate(cols); syn = np.concatenate(vals).astype(np.float32)
    keep = pre != post
    pre, post, syn = pre[keep], post[keep], syn[keep]

    nt = np.empty(n, dtype=object)
    for p in POPS:
        nt[idx[p[0]]] = p[6]
    sign = np.where(nt[pre] == "GABA", -1.0, 1.0).astype(np.float32)
    W = sp.csr_matrix((syn * sign, (pre, post)), shape=(n, n), dtype=np.float32)
    W.sum_duplicates()

    # positions: gaussian blob per population, in nm like FlyWire
    positions = np.empty((n, 3), dtype=np.float32)
    for p in POPS:
        cx, cy, cz = p[8]
        spread = 60 if p[1] > 200 else 25
        positions[idx[p[0]]] = (np.array([cx, cy, cz]) + rng.normal(0, spread, (p[1], 3))) * 1000.0
    # mirror half of each population to the other hemisphere for looks
    for p in POPS:
        ii = idx[p[0]]
        half = ii[: ii.size // 2]
        positions[half, 0] = -positions[half, 0] - 0  # symmetric about x=0

    root_ids = np.arange(720_000_000_000_000_000, 720_000_000_000_000_000 + n, dtype=np.int64)
    ann = pd.DataFrame({"root_id": root_ids})
    for col, k in (("super_class", 2), ("class", 3), ("cell_type", 4), ("hemibrain_type", 5), ("nt_type", 6), ("labels", 7)):
        arr = np.empty(n, dtype=object)
        for p in POPS:
            arr[idx[p[0]]] = p[k]
        ann[col] = arr
    side = np.where(positions[:, 0] < 0, "left", "right")
    ann["side"] = side
    ann["population"] = np.concatenate([[name] * size for name, size in zip(names, sizes)])

    return Connectome(
        root_ids=root_ids, W=W, positions=positions, annotations=ann, name="toy",
        meta={"source": "synthetic", "n": n, "n_edges": int(W.nnz), "note": "hand-wired; proves nothing about biology"},
    )
