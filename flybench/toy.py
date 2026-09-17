"""A synthetic ~3.6k-neuron 'connectome' that exhibits the benchmark reflexes.

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
    # task 22 (courtship song chain): P1 -> pIP10 -> TN1 -> song wing MNs, plus a leg-MN pool that must stay quiet
    ("p1",          40, "central", "",          "pC1_toy",    "",           "ACH",  "P1 pMP-e",         (30, 230, 30)),
    ("pip10",        2, "descending", "",       "pIP10",      "pIP10",      "ACH",  "song descending",  (80, 190, -25)),   # x = 80: the mirrored half lands on the left, so the pair is one per side
    ("tn1",         40, "vnc_intrinsic", "",    "TN1a_toy",   "",           "ACH",  "song premotor",    (0, 100, -60)),
    ("mn_hg1",       2, "vnc_motor", "",        "hg1 MN",     "",           "ACH",  "song wing MN",     (80, 80, -70)),
    ("mn_ps1",       2, "vnc_motor", "",        "ps1 MN",     "",           "ACH",  "song wing MN",     (80, 80, -70)),
    ("mn_i1",        2, "vnc_motor", "",        "i1 MN",      "",           "ACH",  "song wing MN",     (80, 70, -70)),
    ("mn_b1",        2, "vnc_motor", "",        "b1 MN",      "",           "ACH",  "song wing MN",     (80, 70, -70)),
    ("mn_leg",      20, "vnc_motor", "",        "Ti flexor MN", "",         "ACH",  "leg MN",           (0, 40, -80)),
    # task 23 (leg MN size principle): a front-leg (sub_class "fl") motor pool of graded size, its excitatory
    # central premotor pool, and the afferents that give the big MNs their extra input synapses
    ("leg_premotor", 60, "vnc_intrinsic", "",   "leg_premotor_toy", "",     "ACH",  "leg premotor",     (40, 60, -60)),
    ("leg_afferent", 60, "vnc_sensory", "",     "leg_afferent_toy", "",     "ACH",  "leg proprioceptor", (60, 30, -90)),
    ("mn_t1",       24, "vnc_motor", "",        "Ti extensor MN", "",       "ACH",  "T1 leg MN",        (120, 40, -80)),   # x = 120: the mirrored half lands cleanly on the left
    # task 24 (optic-flow rotation vs translation): the H2-HS network of Nat Neurosci 2025 — three HS cells and
    # one H2 per side, the bilateral GABAergic bIPS, and DNp15; x = 100 so the first half mirrors cleanly left
    ("hsn",          2, "visual_projection", "", "HSN",       "HSN",        "ACH",  "horizontal system", (100, 160, 20)),
    ("hse",          2, "visual_projection", "", "HSE",       "HSE",        "ACH",  "horizontal system", (100, 160, 10)),
    ("hss",          2, "visual_projection", "", "HSS",       "HSS",        "ACH",  "horizontal system", (100, 160, 0)),
    ("h2",           2, "visual_projection", "", "H2",        "H2",         "ACH",  "H2 heterolateral", (100, 150, 10)),
    ("bips",         2, "central", "",          "bIPS_toy",  "",           "GABA", "bIPS",             (100, 200, -10)),
    ("dnp15",        2, "descending", "",       "DNp15",     "DNp15",      "ACH",  "DNp15 / DNHS1",    (100, 195, -25)),
    # task 25 (antennal grooming vs backward walking): two Johnston's-organ populations, the aBN1 relay and
    # the antennal-grooming descending pair; JO-F also reaches the toy's MDN, JO-C/E does not
    ("jo_ce",       60, "sensory", "mechanosensory", "JO-CE_toy", "",       "ACH",  "JO-C/E",           (30, 300, -40)),
    ("jo_f",        30, "sensory", "mechanosensory", "JO-F_toy",  "",       "ACH",  "JO-F",             (30, 290, -50)),
    ("abn1",        10, "central", "",          "aBN1_toy",  "",           "ACH",  "antennal grooming BN", (20, 240, -30)),
    ("adn",          2, "descending", "",       "DNg62",     "DNg62",      "ACH",  "aDN1",             (100, 190, -40)),
    # task 26 (mushroom body sparseness with APL): Kenyon cells sampling the eight toy glomeruli, and the
    # GABAergic APL that reads the whole KC population and inhibits all of it
    ("kc",         400, "central", "",          "KC_toy",    "",           "ACH",  "Kenyon cell",      (60, 230, 70)),
    ("apl",          2, "central", "",          "APL",       "APL",        "GABA", "APL",              (60, 235, 60)),
    # task 27 (CO2 pathway): the V glomerulus's ORNs, its bilateral PN, the extraglomerular LN23 -> PNm1
    # channel of bioRxiv 2026.01.05.697655, and PNvbi's lateral-horn target
    ("orn_v",       40, "sensory", "olfactory", "ORN_V",     "ORN_V",      "ACH",  "CO2 ORN",          (0, 425, 5)),
    ("pnv_bi",       2, "central", "",          "V_ilPN",    "V_ilPN",     "ACH",  "CO2 bilateral PN", (0, 255, 45)),
    ("ln23",         4, "central", "",          "l2LN23",    "l2LN23",     "ACH",  "CO2 local neuron", (0, 265, 40)),
    ("pnm1",         2, "central", "",          "M_smPNm1",  "M_smPNm1",   "GABA", "PNm1",             (10, 250, 50)),
    ("lhpd5c1",      2, "central", "",          "LHPD5c1",   "LHPD5c1",    "GLUT", "LH CO2 target",    (120, 215, 65)),
    # task 28 (steering gain): DNa02 contacts the front-leg MNs directly, DNa01 only through a premotor pool
    ("dna02",        2, "descending", "",       "DNa02",     "DNa02",      "ACH",  "steering DN (high gain)", (100, 185, -20)),
    ("dna01",        2, "descending", "",       "DNa01",     "DNa01",      "ACH",  "steering DN (low gain)",  (100, 180, -20)),
    ("steer_in",    40, "vnc_intrinsic", "",    "steer_in_toy", "",        "ACH",  "steering premotor",       (100, 70, -60)),
    # task 29 (ring attractor): eight EPG wedges labelled like FlyWire's community labels (EPG_R{k}), their PEN
    # partners, and the glutamatergic Delta7 that inhibits the whole ring (GLUT is inhibitory, as in the datasets)
    *[(f"epg_g{k}", 6, "central", "", "EPG", "EPG", "ACH", f"EPG_R{k};EPG | EPG_L{k}", (int(60 * __import__("math").cos(k * 0.7854)), 240 + int(60 * __import__("math").sin(k * 0.7854)), 30)) for k in range(1, 9)],
    *[(f"pen_g{k}", 3, "central", "", "PEN_a/PEN1", "PEN_a", "ACH", f"PEN_R{k}", (int(45 * __import__("math").cos(k * 0.7854)), 240 + int(45 * __import__("math").sin(k * 0.7854)), 20)) for k in range(1, 9)],
    ("delta7",       8, "central", "",          "Delta7",    "Delta7",     "GLUT", "Delta7",           (0, 240, 40)),
    # task 30 (egg laying, the female twin of task 22): female pC1 -> the GABAergic oviIN -> oviDN and oviEN; oviEN -> oviDN
    ("pc1_female",  10, "central", "",          "pC1a",      "pC1a",       "ACH",  "female pC1",       (30, 225, 30)),
    ("oviin",        2, "central", "",          "oviIN",     "",           "GABA", "oviIN",            (20, 215, 20)),
    ("ovien",        2, "central", "",          "SMP550",    "SMP550",     "ACH",  "oviEN",            (25, 220, 25)),
    ("ovidn",        6, "descending", "",       "oviDNa_a",  "",           "ACH",  "oviDN",            (15, 200, -20)),
    # task 31 (halting, Sapkal 2024's walk-OFF): the GABAergic Foxglove and Bluebell, the walking DNs they inhibit,
    # and a walking-command input population; typed like FlyWire's community labels
    ("foxglove",     2, "central", "",          "CB0890",    "",           "GABA", "Foxglove",         (10, 330, -30)),
    ("bluebell",     2, "descending", "",       "DNg60",     "",           "GABA", "Bluebell",         (20, 330, -35)),
    ("odn1",         2, "descending", "",       "DNg97",     "",           "ACH",  "oDN1",             (30, 190, -30)),
    ("bdn2",         2, "descending", "",       "DNg100",    "",           "ACH",  "BDN2",             (40, 190, -30)),
    ("walk_in",     10, "central", "",          "PVLP137",   "PVLP137",    "ACH",  "walking command input", (60, 210, 0)),
    # task 32 (flyvis front end): the optic-lobe output types the front end drives. T5 (OFF-edge motion) feeds the
    # loom detectors; T4 (ON-edge motion) projects nowhere in the toy, so a flash is a null by construction.
    # Somata on a disc (spread 60) so the front end's PCA column mapping has something to work with.
    *[(f"t5{k}", 24, "visual_projection", "", f"T5{k}", f"T5{k}", "ACH", "T5", (-230, 150, 0)) for k in "abcd"],
    *[(f"t4{k}", 24, "visual_projection", "", f"T4{k}", f"T4{k}", "ACH", "T4", (-230, 130, 0)) for k in "abcd"],
    ("lpi",         20, "central", "",          "LPi_toy",   "",           "GABA", "lobula plate intrinsic", (-200, 140, 0)),
]

SUB_CLASS = {"mn_t1": "fl"}   # Codex-style `sub_class` (fl/ml/hl = front/mid/hind leg); "" elsewhere


# ring-attractor contact sizes (synapses per edge); see the task-29 block in build_toy_connectome
RING = {"epg_pen": 40, "pen_epg_self": 30, "pen_epg_side": 20, "epg_d7": 10, "d7_epg": 12}

# Bump when POPS or the wiring change: load_connectome("toy") rebuilds a cache whose version differs.
TOY_VERSION = "2026-09-17-flyvis3"


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
    # --- added 2026-09-14 for task 22 (MODELED): P1 -> pIP10 -> TN1 -> the four song MN pairs, both sides;
    #     the leg MN pool gets nothing, so the "not the legs" null passes trivially
    connect("p1", "pip10", 0.5, 4, 10)
    connect("pip10", "tn1", 1.0, 150, 250)   # one descending cell must drive TN1 alone: a big contact, like the real pIP10 -> dPR1 (~280 per pair)
    for mn in ("mn_hg1", "mn_ps1", "mn_i1", "mn_b1"):
        connect("tn1", mn, 0.8, 8, 16)      # ~300 synapses per MN from 40 premotor cells, the toy's loom -> GF scale
    # --- added 2026-09-15 for task 23 (MODELED, and explicitly not the fly's route to a pass): 12 MNs per side
    #     ranked by "size" k = 0..11. The premotor pool's contact on MN k falls with k (12 - k synapses per
    #     edge) while the afferents' contact rises steeply (2 + 4k), so total input (size) grows with k
    #     and a ramp on the premotor pool recruits the smallest MN first. The real fly gets that order from
    #     MN intrinsic properties on top of size-proportional wiring (Lesser et al. 2024); a uniform LIF
    #     cannot, so the toy buys it with wiring. It proves the checks are computable and passable, no more.
    t1 = idx["mn_t1"]
    for side in (t1[: t1.size // 2], t1[t1.size // 2:]):   # the first half is mirrored to the left in the position step below
        for k, mn in enumerate(side):
            for pre_pop, per_edge, p_conn in (("leg_premotor", 12 - k, 0.5), ("leg_afferent", 2 + 4 * k, 0.5)):
                a = idx[pre_pop]
                m = rng.random(a.size) < p_conn
                rows.append(a[m]); cols.append(np.full(m.sum(), mn)); vals.append(np.full(m.sum(), per_edge))
    # --- added 2026-09-15 for task 24 (MODELED: the FlyWire v783 motif, HS_L and H2_R converge on DNp15_L and on
    #     bIPS_L, and bIPS_L inhibits the *other* DNp15; contact sizes set so DNp15 sits well below its ceiling
    #     and the contralateral bIPS can pull it under threshold). Sides by index half: the first cell of each pair
    #     is mirrored to the left in the position step below.
    def edge(pre_cells, post_cell, syn):
        for p in np.atleast_1d(pre_cells):
            rows.append(np.array([p])); cols.append(np.array([post_cell])); vals.append(np.array([syn]))
    L, R = 0, 1
    for me, other in ((L, R), (R, L)):
        hs_me = np.array([idx["hsn"][me], idx["hse"][me], idx["hss"][me]])
        edge(hs_me, idx["dnp15"][me], 26)        # 3 × 26 synapses: a few tens of Hz at gain 1, well under the ceiling
        edge(hs_me, idx["bips"][me], 22)
        edge(idx["h2"][other], idx["dnp15"][me], 40)   # the contralateral H2 (right-eye back-to-front) joins HS_L on DNp15_L
        edge(idx["h2"][other], idx["bips"][me], 10)
        edge(idx["bips"][me], idx["dnp15"][other], 60)  # GABA: bIPS_L → DNp15_R, enough to halve it
    # --- added 2026-09-15 for task 25 (MODELED): JO-C/E and JO-F both reach aDN through aBN1 (Hampel 2015's
    #     circuit); JO-F alone also contacts the moonwalker DN, so the JO-C/E -> MDN null passes trivially
    connect("jo_ce", "abn1", 0.5, 4, 10)
    connect("jo_f", "abn1", 0.5, 4, 10)
    connect("abn1", "adn", 0.8, 8, 16)
    connect("jo_f", "mdn", 0.5, 6, 12)
    # --- added 2026-09-15 for task 26 (MODELED): each KC samples four random PNs from the eight named glomeruli
    #     (two to eight of them) with contacts of graded strength; a single strong contact is about at threshold. Every KC drives APL and APL inhibits every KC (~28 synapses each way, the FlyWire v783
    #     mean per KC), so population activity feeds back on itself.
    pn_all = np.concatenate([idx[f"pn_{g}"] for g in ("da1", "dm1", "dm4", "dl5", "dm2", "dl1", "va1v", "dc1")])
    for k in idx["kc"]:
        n_in = int(rng.integers(2, 9))       # 2-8 PN inputs: the well-connected KCs are the generalists APL has to hold down
        src = rng.choice(pn_all, size=n_in, replace=False)
        rows.append(src); cols.append(np.full(n_in, k)); vals.append(rng.integers(10, 21, size=n_in))
    connect("kc", "apl", 1.0, 26, 30)
    connect("apl", "kc", 1.0, 26, 30)
    # --- added 2026-09-15 for task 27 (MODELED): ORN_V -> V_ilPN and -> LN23; LN23 -> PNm1 (the extraglomerular
    #     channel); V_ilPN -> LHPD5c1. The other glomeruli do not touch any of it, so the nulls pass trivially.
    connect("orn_v", "pnv_bi", 0.8, 8, 16)
    connect("orn_v", "ln23", 0.5, 4, 10)
    connect("ln23", "pnm1", 1.0, 30, 50)
    connect("pnv_bi", "lhpd5c1", 1.0, 60, 100)
    # --- added 2026-09-15 for task 28 (MODELED, the MaleCNS pattern: DNa02 -> leg MNs 509 direct synapses on
    #     15 ipsilateral MNs, DNa01 98 on 7 and a much larger two-hop route): DNa02 drives its side's T1 MNs
    #     directly, DNa01 drives them through the steer_in pool; nothing crosses the midline
    #     Wired on the right side only: the left T1 pool is task 23's readout and its premotor pool is
    #     selected from the graph, so nothing new may contact it.
    t1 = idx["mn_t1"]; right_mns = t1[t1.size // 2:]; si = idx["steer_in"]; right_in = si[si.size // 2:]
    for mn in right_mns:
        edge(idx["dna02"][1], mn, 90)
    for s_ in right_in:
        edge(idx["dna01"][1], s_, 70)
        for mn in right_mns:
            if rng.random() < 0.5:
                edge(s_, mn, 14)
    # --- added 2026-09-15 for task 29 (MODELED): a hand-wired ring attractor. Each wedge's EPGs drive their PENs,
    #     each PEN feeds its own wedge and both neighbours (local recurrent excitation); every EPG drives Delta7 and
    #     Delta7 inhibits every EPG (global inhibition). Numbers chosen so that a cued bump outlives its cue.
    for k in range(1, 9):
        left, right = (k - 2) % 8 + 1, k % 8 + 1
        connect(f"epg_g{k}", f"pen_g{k}", 1.0, RING["epg_pen"], RING["epg_pen"])
        for tgt, w in ((k, RING["pen_epg_self"]), (left, RING["pen_epg_side"]), (right, RING["pen_epg_side"])):
            connect(f"pen_g{k}", f"epg_g{tgt}", 1.0, w, w)
        connect(f"epg_g{k}", "delta7", 1.0, RING["epg_d7"], RING["epg_d7"])
        connect("delta7", f"epg_g{k}", 1.0, RING["d7_epg"], RING["d7_epg"])
    # --- added 2026-09-15 for task 30 (MODELED, Wang 2020's diagram): pC1 -> oviIN; oviIN -> oviDN and -> oviEN
    #     (feed-forward inhibition); oviEN -> oviDN
    connect("pc1_female", "oviin", 0.8, 10, 20)
    connect("oviin", "ovidn", 1.0, 40, 60)
    connect("oviin", "ovien", 1.0, 40, 60)
    connect("ovien", "ovidn", 1.0, 40, 60)
    # --- added 2026-09-15 for task 31 (MODELED): the sugar pathway's second-order cells drive Foxglove; the walking
    #     input drives oDN1 and BDN2; Foxglove inhibits both, Bluebell inhibits oDN1 (Sapkal 2024's walk-OFF)
    connect("taste_in", "foxglove", 0.6, 6, 12)
    for dn in ("odn1", "bdn2"):
        connect("walk_in", dn, 0.8, 8, 14)
    connect("foxglove", "odn1", 1.0, 60, 90)
    connect("foxglove", "bdn2", 1.0, 60, 90)
    connect("bluebell", "odn1", 1.0, 60, 90)
    # --- added 2026-09-17 for task 32 (MODELED): a dark-loom detector. Every T5 subtype (OFF-edge motion) excites the
    #     loom detectors, strongly, because the front end's loom is a brief edge passing each column; every T4 subtype
    #     (ON-edge motion, what a brightening flash drives) reaches them through a GABAergic LPi-like layer. The real
    #     LPLC2 gets expansion selectivity from the layer-specific radial arrangement of T4/T5 inputs (Klapoetke 2017),
    #     which the toy cannot have without retinotopy; ON-inhibition is the toy's stand-in for "not a flash".
    for k in "abcd":
        connect(f"t5{k}", "lplc2", 0.6, 24, 34); connect(f"t5{k}", "lc4", 0.6, 24, 34)
        connect(f"t4{k}", "lpi", 0.8, 14, 20)
    connect("lpi", "lplc2", 0.9, 34, 44); connect("lpi", "lc4", 0.9, 34, 44)
    pre = np.concatenate(rows); post = np.concatenate(cols); syn = np.concatenate(vals).astype(np.float32)
    keep = pre != post
    pre, post, syn = pre[keep], post[keep], syn[keep]

    nt = np.empty(n, dtype=object)
    for p in POPS:
        nt[idx[p[0]]] = p[6]
    sign = np.where(np.isin(nt[pre], ("GABA", "GLUT")), -1.0, 1.0).astype(np.float32)   # the datasets' NT_SIGN: GABA and glutamate inhibit
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
    sub_class = np.full(n, "", dtype=object)
    for name, sc in SUB_CLASS.items():
        sub_class[idx[name]] = sc
    ann["sub_class"] = sub_class
    ann["population"] = np.concatenate([[name] * size for name, size in zip(names, sizes)])

    return Connectome(
        root_ids=root_ids, W=W, positions=positions, annotations=ann, name="toy",
        meta={"source": "synthetic", "toy_version": TOY_VERSION, "n": n, "n_edges": int(W.nnz), "note": "hand-wired; proves nothing about biology"},
    )
