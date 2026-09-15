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
    # two named glomeruli with Codex-style names so the olfactory tasks (8, 17) have something to read:
    # DA1 (driven by the tasks) and DM1 (a bystander that lateral inhibition should keep quiet)
    ("orn_da1",     40, "sensory", "olfactory", "ORN_DA1",    "ORN_DA1",    "ACH",  "olfactory DA1",    (-30, 420, 10)),
    ("orn_dm1",     40, "sensory", "olfactory", "ORN_DM1",    "ORN_DM1",    "ACH",  "olfactory DM1",    (30, 420, 10)),
    ("pn_da1",       8, "central", "",          "DA1_lPN",    "DA1_lPN",    "ACH",  "DA1 projection",   (-30, 250, 50)),
    ("pn_dm1",       8, "central", "",          "DM1_lPN",    "DM1_lPN",    "ACH",  "DM1 projection",   (30, 250, 50)),
    ("orn_dm4",     40, "sensory", "olfactory", "ORN_DM4",    "ORN_DM4",    "ACH",  "olfactory DM4",    (60, 420, 10)),
    ("orn_dl5",     40, "sensory", "olfactory", "ORN_DL5",    "ORN_DL5",    "ACH",  "olfactory DL5",    (-60, 420, 10)),
    ("pn_dm4",       8, "central", "",          "DM4_lPN",    "DM4_lPN",    "ACH",  "DM4 projection",   (60, 250, 50)),
    ("pn_dl5",       8, "central", "",          "DL5_lPN",    "DL5_lPN",    "ACH",  "DL5 projection",   (-60, 250, 50)),
    ("orn_dm2",     40, "sensory", "olfactory", "ORN_DM2",    "ORN_DM2",    "ACH",  "olfactory DM2",    (90, 420, 10)),
    ("orn_dl1",     40, "sensory", "olfactory", "ORN_DL1",    "ORN_DL1",    "ACH",  "olfactory DL1",    (-90, 420, 10)),
    ("orn_va1v",    40, "sensory", "olfactory", "ORN_VA1v",   "ORN_VA1v",   "ACH",  "olfactory VA1v",   (120, 420, 10)),
    ("orn_dc1",     40, "sensory", "olfactory", "ORN_DC1",    "ORN_DC1",    "ACH",  "olfactory DC1",    (-120, 420, 10)),
    ("pn_dm2",       8, "central", "",          "DM2_lPN",    "DM2_lPN",    "ACH",  "DM2 projection",   (90, 250, 50)),
    ("pn_dl1",       8, "central", "",          "DL1_adPN",   "DL1_adPN",   "ACH",  "DL1 projection",   (-90, 250, 50)),
    ("pn_va1v",      8, "central", "",          "VA1v_adPN",  "VA1v_adPN",  "ACH",  "VA1v projection",  (120, 250, 50)),
    ("pn_dc1",       8, "central", "",          "DC1_adPN",   "DC1_adPN",   "ACH",  "DC1 projection",   (-120, 250, 50)),
    ("ln_al",       20, "central", "",          "LN_AL",      "",           "GABA", "antennal lobe LN", (0, 260, 45)),
    ("lhn",         60, "central", "",          "LHN",        "",           "ACH",  "lateral horn",     (120, 220, 60)),
    ("bg_exc",    1000, "central", "",          "",           "",           "ACH",  "",                 (0, 200, 0)),
    ("bg_inh",     500, "central", "",          "",           "",           "GABA", "",                 (0, 200, 0)),
    # appended last (and wired last) so the random draws of every older population are unchanged
    ("grn_salt",    20, "sensory", "gustatory", "GRN_salt",   "",           "ACH",  "high salt GRN",    (80, 380, 80)),
    # task 21 (LC -> DN matrix): four more LC types and three more descending readouts, appended after salt
    ("lc6",         40, "visual_projection", "", "LC6",       "LC6",        "ACH",  "looming",          (-200, 120, 0)),
    ("lplc1",       40, "visual_projection", "", "LPLC1",     "LPLC1",      "ACH",  "looming",          (200, 120, 0)),
    ("lc16",        40, "visual_projection", "", "LC16",      "LC16",       "ACH",  "retreat",          (-200, 90, 0)),
    ("lc10a",       40, "visual_projection", "", "LC10a",     "LC10a",      "ACH",  "courtship tracking", (200, 90, 0)),
    ("mdn",          4, "descending", "",       "MDN",        "MDN",        "ACH",  "moonwalker",       (0, 180, -30)),
    ("dnp02",        2, "descending", "",       "DNp02",      "DNp02",      "ACH",  "backward takeoff", (-20, 200, -20)),
    ("dnp11",        2, "descending", "",       "DNp11",      "DNp11",      "ACH",  "forward takeoff",  (20, 200, -20)),
]


# Bump when POPS or the wiring change: load_connectome("toy") rebuilds a cache whose version differs.
TOY_VERSION = "2026-09-14-lcdn1"


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
    # --- two glomeruli with lateral inhibition: each ORN set drives its own PNs; all ORNs drive the
    #     GABAergic local neurons, which inhibit every PN (the antennal-lobe normalisation motif)
    for g in ("da1", "dm1", "dm4", "dl5", "dm2", "dl1", "va1v", "dc1"):
        connect(f"orn_{g}", f"pn_{g}", 0.8, 8, 16)     # strong convergence: ~110 ORNs per glomerulus in the fly
        connect(f"orn_{g}", "ln_al", 0.3, 3, 6)
        connect("ln_al", f"pn_{g}", 0.5, 3, 6)
        connect(f"pn_{g}", "lhn", 0.2, 5, 15)
    # --- sparse random background, balanced so it does not run away
    connect("bg_exc", "bg_exc", 0.004, 5, 8)
    connect("bg_exc", "bg_inh", 0.008, 5, 8)
    connect("bg_inh", "bg_exc", 0.010, 5, 12)
    connect("bg_inh", "bg_inh", 0.004, 5, 8)
    connect("lhn", "bg_exc", 0.05, 5, 8)
    connect("taste_in", "bg_exc", 0.03, 5, 8)

    # --- added 2026-09-14 for task 20, after every older draw so the older populations are bit-identical:
    #     water gets a second helping of taste_in synapses (duplicates sum) so that 20 water cells carry
    #     about the drive of 40 sugar cells and water alone can reach MN9; high salt: INFERRED — the
    #     second-order salt circuit is not mapped; the toy sends it into the same inhibitory pool as bitter
    #     (Jaeger et al. 2018 put part of high-salt aversion in the bitter GRNs themselves)
    connect("grn_water", "taste_in", 0.4, 4, 10)
    connect("grn_salt", "bitter_in", 0.5, 4, 10)
    # --- added 2026-09-14 for task 21 (MODELED: the toy proves the matrix can pass, nothing more):
    #     LC16 -> MDN and LC4 -> DNp02 / DNp11 as direct contacts like the toy's loom -> GF;
    #     LC6, LPLC1 and LC10a project nowhere, so the negatives pass trivially
    connect("lc16", "mdn", 0.6, 3, 8)
    connect("lc4", "dnp02", 0.6, 3, 8)
    connect("lc4", "dnp11", 0.6, 3, 8)
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
        meta={"source": "synthetic", "toy_version": TOY_VERSION, "n": n, "n_edges": int(W.nnz), "note": "hand-wired; proves nothing about biology"},
    )
