"""Terminal (axo-axonic) input synapses by neuropil polarity (docs/rfcs/M1b_terminal_everywhere.md).

For neuron j and neuropil r: p_j(r) = out_j(r) / (out_j(r) + in_j(r)). An input synapse onto j in
r is terminal when p_j(r) >= THETA and j has at least MIN_TOTAL synapses there — j's arbor in that
neuropil is axon, so the synapse sits on its terminal, not its dendrite. CONVENTION, fixed in the
RFC before any run. Output: a signed (pre, post) count matrix aligned to a Connectome's W, the
`terminal` the terminal-aware LIF (flybench.models.terminal_lif) keeps off the soma.

FlyWire: the Codex connection table is already per neuropil (`data/connections.csv.gz`).
MaleCNS: neuPrint's per-connection `roiInfo` (post counts per ROI) fetched for every edge onto a
neuron that has an axonal ROI receiving input, plus per-neuron pre/post per ROI for the polarity.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

THETA = 0.8       # polarity above which a neuron's arbor in a neuropil is axon (RFC M1b table)
MIN_TOTAL = 20    # synapses a neuron needs in a neuropil before its polarity there means anything


def polarity(per_neuropil: pd.DataFrame) -> pd.DataFrame:
    """per_neuropil: columns pre, post, neuropil, syn -> one row per (root_id, neuropil) with out, in, p."""
    out = per_neuropil.groupby(["pre", "neuropil"])["syn"].sum().rename("out")
    inp = per_neuropil.groupby(["post", "neuropil"])["syn"].sum().rename("in")
    out.index.names = inp.index.names = ["root_id", "neuropil"]
    pol = pd.concat([out, inp], axis=1).fillna(0.0)
    pol["tot"] = pol["out"] + pol["in"]
    pol["p"] = pol["out"] / pol["tot"].where(pol["tot"] > 0, 1.0)
    return pol.reset_index()


def terminal_counts(per_neuropil: pd.DataFrame, pol: pd.DataFrame | None = None, theta: float = THETA, min_total: int = MIN_TOTAL) -> pd.DataFrame:
    """Rows (pre, post, terminal): the synapses of each edge that land in an axonal neuropil of `post`."""
    pol = polarity(per_neuropil) if pol is None else pol
    axonal = pol[(pol["p"] >= theta) & (pol["tot"] >= min_total)][["root_id", "neuropil"]]
    key = pd.MultiIndex.from_frame(axonal)
    m = pd.MultiIndex.from_arrays([per_neuropil["post"], per_neuropil["neuropil"]]).isin(key)
    t = per_neuropil[m].groupby(["pre", "post"], as_index=False)["syn"].sum().rename(columns={"syn": "terminal"})
    return t


def to_matrix(c, table: pd.DataFrame) -> sp.csr_matrix:
    """Signed like W, magnitude clipped to the edge, aligned to the connectome's indices."""
    idx = pd.Series(np.arange(c.n), index=c.root_ids.astype(np.int64))
    pre = idx.reindex(table["pre"].astype(np.int64)).to_numpy()
    post = idx.reindex(table["post"].astype(np.int64)).to_numpy()
    ok = ~(np.isnan(pre) | np.isnan(post)) & (table["terminal"].to_numpy() > 0)
    T = sp.csr_matrix((table["terminal"].to_numpy()[ok].astype(np.float32), (pre[ok].astype(int), post[ok].astype(int))), shape=(c.n, c.n))
    W = c.W.tocsr()
    T = T.minimum(abs(W)).multiply(W.sign()).tocsr()
    T.eliminate_zeros()
    return T


# ---- FlyWire: Codex per-neuropil connections -------------------------------------------------

def flywire_per_neuropil(connections_csv: Path | str) -> pd.DataFrame:
    df = pd.read_csv(connections_csv, dtype={"pre_root_id": np.int64, "post_root_id": np.int64, "neuropil": str, "syn_count": np.int32})
    return df.rename(columns={"pre_root_id": "pre", "post_root_id": "post", "syn_count": "syn"})[["pre", "post", "neuropil", "syn"]]


# ---- MaleCNS: neuPrint roiInfo -----------------------------------------------------------------

def malecns_per_neuropil(np_, min_synapses: int = 5, log=print) -> pd.DataFrame:
    """Per-connection post counts per primary ROI for every edge with weight >= min_synapses — the same
    (pre, post, neuropil, syn) table Codex publishes for FlyWire, in the same units (one count per
    pre-post pair per synapse, so a polyadic T-bar counts once per partner). neuPrint's per-neuron
    roiInfo counts sites (T-bars vs PSDs) and gives a different polarity scale; it is not used."""
    meta = np_.query("MATCH (m:Meta) RETURN m.primaryRois AS p").p[0]
    prim = set(json.loads(meta) if isinstance(meta, str) else meta)
    ids = np_.query("MATCH (n:Neuron) RETURN n.bodyId AS id ORDER BY id")["id"].astype(np.int64).to_numpy()
    log(f"neurons: {ids.size:,}")
    frames = []
    step = 400
    for k in range(0, ids.size, step):
        chunk = ids[k:k + step].tolist()
        df = np_.query(f"MATCH (a:Neuron)-[c:ConnectsTo]->(b:Neuron) WHERE b.bodyId IN {chunk} AND c.weight >= {min_synapses} "
                       "RETURN a.bodyId AS pre, b.bodyId AS post, c.roiInfo AS roi")
        recs = []
        for pre, post, roi in zip(df["pre"], df["post"], df["roi"]):
            r = json.loads(roi) if isinstance(roi, str) else (roi or {})
            for name, v in r.items():
                if name in prim and v.get("post", 0):
                    recs.append((int(pre), int(post), name, int(v["post"])))
        if recs:
            frames.append(pd.DataFrame(recs, columns=["pre", "post", "neuropil", "syn"]))
        if (k // step) % 50 == 0:
            log(f"  {k + len(chunk):,}/{ids.size:,} post neurons, {sum(len(f) for f in frames):,} rows")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["pre", "post", "neuropil", "syn"])
