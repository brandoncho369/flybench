"""Fetch a connectome from a neuPrint server into the CSV layout `flybench build` reads.

This is how the viral "fly brain in Minecraft" demo got its data: dataset ``male-cns:v1.0``
on https://neuprint.janelia.org, anonymous access, edges with >= 5 synapses. We write the
same layout Codex downloads use (connections / neurons / classification / coordinates) so
the build step, the task selectors and the cache format are shared with FlyWire v783.

Column mapping (neuPrint -> flybench annotation columns):
    bodyId        -> root_id
    type          -> cell_type          superclass -> super_class
    subclass      -> sub_class          class      -> class
    predictedNt   -> nt_type            somaSide   -> side
    instance, systematicType, hemilineage, flow, status kept under their own names.
Anything the server does not have simply comes back empty; nothing here assumes a schema.
"""

from __future__ import annotations

import gzip
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SERVER = "https://neuprint.janelia.org"
DATASET = "male-cns:v1.0"

NEURON_FIELDS = {
    # neuPrint property -> flybench column
    "bodyId": "root_id", "type": "cell_type", "instance": "instance", "status": "status",
    "superclass": "super_class", "class": "class", "subclass": "sub_class", "flow": "flow",
    "predictedNt": "nt_type", "celltypePredictedNt": "celltype_nt", "consensusNt": "consensus_nt",
    "somaSide": "side", "rootSide": "root_side", "hemilineage": "hemilineage",
    "systematicType": "systematic_type", "synonyms": "synonyms", "somaLocation": "soma_location",
    "pre": "n_pre", "post": "n_post",
}


class NeuPrint:
    def __init__(self, server: str = SERVER, dataset: str = DATASET, token: str | None = None):
        self.server, self.dataset = server.rstrip("/"), dataset
        self.s = requests.Session()
        token = token or os.environ.get("NEUPRINT_APPLICATION_CREDENTIALS")
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"

    def query(self, cypher: str, retries: int = 5) -> pd.DataFrame:
        for attempt in range(retries):
            try:
                r = self.s.post(f"{self.server}/api/custom/custom", json={"cypher": cypher, "dataset": self.dataset}, timeout=300)
                if r.status_code >= 500 or r.status_code == 429:
                    raise requests.HTTPError(f"{r.status_code}: {r.text[:200]}")
                r.raise_for_status()
                j = r.json()
                return pd.DataFrame(j["data"], columns=j["columns"])
            except (requests.RequestException, ValueError, KeyError) as e:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("unreachable")


def fetch(out_dir: Path | str, dataset: str = DATASET, server: str = SERVER, min_synapses: int = 5,
          chunk: int = 1500, token: str | None = None, log=print) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    np_ = NeuPrint(server, dataset, token)

    # 1. neurons + annotations (one query; explicit fields so we never pull the huge roiInfo blobs)
    sel = ", ".join(f"n.{k} AS {v}" for k, v in NEURON_FIELDS.items())
    log(f"{dataset}: fetching neuron ids …")
    all_ids = np_.query("MATCH (n:Neuron) RETURN n.bodyId AS id ORDER BY n.bodyId")["id"].astype(np.int64).to_numpy()
    log(f"  {len(all_ids):,} neurons; fetching annotations …")
    parts = []
    step = 20000
    for i in range(0, len(all_ids), step):
        lo, hi = int(all_ids[i]), int(all_ids[min(i + step, len(all_ids)) - 1])
        parts.append(np_.query(f"MATCH (n:Neuron) WHERE n.bodyId >= {lo} AND n.bodyId <= {hi} RETURN {sel} ORDER BY n.bodyId"))
    neurons = pd.concat(parts, ignore_index=True)
    neurons["root_id"] = neurons["root_id"].astype(np.int64)

    # 2. edges, chunked by presynaptic body so no single query times out; resumable
    edge_dir = out / "edges"
    edge_dir.mkdir(exist_ok=True)
    ids = neurons["root_id"].to_numpy()
    n_chunks = int(np.ceil(len(ids) / chunk))
    log(f"  fetching edges (>= {min_synapses} synapses) in {n_chunks} chunks …")
    t0 = time.time()
    for i in range(n_chunks):
        part = edge_dir / f"chunk_{i:05d}.csv"
        if part.exists():
            continue
        lo, hi = int(ids[i * chunk]), int(ids[min((i + 1) * chunk, len(ids)) - 1])
        df = np_.query(
            f"MATCH (a:Neuron)-[c:ConnectsTo]->(b:Neuron) WHERE a.bodyId >= {lo} AND a.bodyId <= {hi} "
            f"AND c.weight >= {min_synapses} RETURN a.bodyId AS pre_root_id, b.bodyId AS post_root_id, c.weight AS syn_count"
        )
        df.to_csv(part, index=False)
        if (i + 1) % 10 == 0 or i == n_chunks - 1:
            el = time.time() - t0
            log(f"    {i + 1}/{n_chunks} chunks, {el / 60:.1f} min elapsed, ~{el / (i + 1) * (n_chunks - i - 1) / 60:.1f} min left")

    # 3. write the flybench/Codex layout
    edges = pd.concat([pd.read_csv(p) for p in sorted(edge_dir.glob("chunk_*.csv"))], ignore_index=True)
    edges["neuropil"] = "ALL"
    edges = edges[["pre_root_id", "post_root_id", "neuropil", "syn_count"]]
    edges.to_csv(out / "connections.csv.gz", index=False, compression="gzip")

    nt = neurons["nt_type"].fillna("").astype(str).str.upper().replace({"ACETYLCHOLINE": "ACH", "GLUTAMATE": "GLUT", "OCTOPAMINE": "OCT", "SEROTONIN": "SER", "DOPAMINE": "DA", "HISTAMINE": "HIST"})
    pd.DataFrame({"root_id": neurons["root_id"], "nt_type": nt}).to_csv(out / "neurons.csv.gz", index=False, compression="gzip")

    cls_cols = ["root_id", "flow", "super_class", "class", "sub_class", "cell_type", "side", "hemilineage", "instance", "systematic_type", "status", "root_side", "synonyms"]
    classification = neurons[[c for c in cls_cols if c in neurons.columns]].copy()
    classification["hemibrain_type"] = ""
    classification.fillna("").to_csv(out / "classification.csv.gz", index=False, compression="gzip")

    # somaLocation comes back as {"coordinates": [x, y, z]} or [x, y, z] (8 nm voxels); store nm like FlyWire
    def xyz(v):
        if isinstance(v, dict):
            v = v.get("coordinates")
        if isinstance(v, (list, tuple)) and len(v) == 3:
            return [float(x) * 8.0 for x in v]
        return None
    pos = neurons["soma_location"].map(xyz)
    ok = pos.map(lambda v: v is not None)
    coords = pd.DataFrame({"root_id": neurons.loc[ok, "root_id"]})
    coords[["x", "y", "z"]] = np.stack(pos[ok].to_list()) if ok.any() else np.empty((0, 3))
    coords.to_csv(out / "coordinates.csv.gz", index=False, compression="gzip")

    # instance strings are the closest thing neuPrint has to community labels
    lab = neurons[["root_id", "instance"]].dropna()
    lab = lab[lab["instance"].astype(str) != ""].rename(columns={"instance": "label"})
    lab.to_csv(out / "labels.csv.gz", index=False, compression="gzip")

    meta = {"source": "neuprint", "server": server, "dataset": dataset, "min_synapses": min_synapses,
            "n_neurons": int(len(neurons)), "n_edges": int(len(edges)), "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "positions": int(ok.sum())}
    (out / "fetch_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"  wrote {len(edges):,} edges, {int(ok.sum()):,} soma positions → {out}")
    log(f"  next: flybench build {out} --name {dataset.split(':')[0].replace('-', '')}")
    return out


# ---------------------------------------------------------------------------
# Terminal (axo-axonic) input synapses — the data behind flybench.models.terminal_lif
# ---------------------------------------------------------------------------
# A neuron that spans the neck has its dendrites on one side and its axon on the other:
# ascending neurons collect input in the nerve cord and terminate in the brain, descending
# neurons the reverse. An input synapse on the axon side is axo-axonic — it sits on the terminal,
# not the dendrite — and a point-neuron model that sums it into the soma lets a brain-side input
# fire an ascending neuron backwards into the cord (docs/rfcs/35). neuPrint records, per
# connection, how many of its synapses fall in each ROI; the super-level ROIs 'CentralBrain',
# 'Optic(L)', 'Optic(R)' and 'VNC' split them by side. MEASURED, per connection.
DENDRITIC_SIDE = {
    # superclass -> the side its dendrites are on; inputs on the other side are terminal
    "ascending_neuron": "vnc", "sensory_ascending": "vnc", "efferent_ascending": "vnc",
    "descending_neuron": "brain", "sensory_descending": "brain", "efferent_descending": "brain",
}
BRAIN_ROIS = ("CentralBrain", "Optic(L)", "Optic(R)")


def fetch_terminal_synapses(np_: "NeuPrint", min_synapses: int = 5, log=print) -> pd.DataFrame:
    """Per connection onto a neck-spanning neuron: total weight and the post-synapse count on the
    postsynaptic neuron's axon side (`terminal`). Columns: pre, post, weight, terminal, side."""
    frames = []
    for sc, side in DENDRITIC_SIDE.items():
        ids = np_.query(f"MATCH (b:Neuron) WHERE b.superclass = '{sc}' RETURN b.bodyId AS id ORDER BY id")
        ids = ids["id"].astype(np.int64).to_numpy()
        log(f"{sc}: {ids.size} neurons")
        for k in range(0, ids.size, 200):
            chunk = ids[k:k + 200].tolist()
            df = np_.query(
                f"MATCH (a:Neuron)-[c:ConnectsTo]->(b:Neuron) WHERE b.bodyId IN {chunk} AND c.weight >= {min_synapses} "
                "RETURN a.bodyId AS pre, b.bodyId AS post, c.weight AS weight, c.roiInfo AS roi")
            if df.empty:
                continue
            def terminal(roi: str) -> int:
                r = json.loads(roi) if isinstance(roi, str) else (roi or {})
                if side == "vnc":       # dendrites in the cord: brain-side posts are terminal
                    return int(sum(r.get(x, {}).get("post", 0) for x in BRAIN_ROIS))
                return int(r.get("VNC", {}).get("post", 0))
            df["terminal"] = df["roi"].map(terminal)
            df["side"] = side
            frames.append(df.drop(columns=["roi"]))
        log(f"  {sum(len(f) for f in frames):,} connections so far")
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["pre", "post", "weight", "terminal", "side"])
    return out


def build_terminal_matrix(c, table: pd.DataFrame):
    """Sparse (n, n) matrix of terminal post-synapse counts aligned to the connectome's W (pre rows,
    post columns), signed like W (an inhibitory terminal input is presynaptic inhibition)."""
    import scipy.sparse as sp
    idx = pd.Series(np.arange(c.n), index=c.root_ids.astype(np.int64))
    pre = idx.reindex(table["pre"].astype(np.int64)).to_numpy()
    post = idx.reindex(table["post"].astype(np.int64)).to_numpy()
    ok = ~(np.isnan(pre) | np.isnan(post)) & (table["terminal"].to_numpy() > 0)
    pre, post, cnt = pre[ok].astype(int), post[ok].astype(int), table["terminal"].to_numpy()[ok].astype(np.float32)
    T = sp.csr_matrix((cnt, (pre, post)), shape=(c.n, c.n), dtype=np.float32)
    # never more than the edge itself carries; sign from W
    W = c.W.tocsr()
    T = T.minimum(abs(W)).multiply(W.sign()).tocsr()
    T.eliminate_zeros()
    return T
