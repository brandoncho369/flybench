"""Export a connectome in the compact binary layout fly-explorer loads.

Files written to <out>/:
  meta.json       n, n_edges, populations {name: [indices]}, bounds, source note
  positions.bin   float32 (n, 3), nm, NaN replaced by the centroid
  indptr.bin      int32   (n+1)   CSR row pointers, rows = presynaptic
  indices.bin     int32   (nnz)   postsynaptic index
  weights.bin     float32 (nnz)   signed synapse counts
  classes.bin     uint8   (n)     colour class per neuron (see CLASS_ORDER)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .connectome import Connectome

CLASS_ORDER = ["other", "sensory", "visual_projection", "central", "descending", "motor", "optic", "ascending", "endocrine"]

# Named neuron sets the explorer exposes as buttons. Same selector grammar as tasks.
DEFAULT_SETS = {
    "sugar GRNs":     {"all_of": [{"labels_regex": "sugar"}, {"super_class": "sensory"}, {"not": {"labels_regex": "bitter"}}]},
    "bitter GRNs":    {"all_of": [{"labels_regex": "bitter"}, {"super_class": "sensory"}]},
    "water GRNs":     {"all_of": [{"labels_regex": "water"}, {"super_class": "sensory"}]},
    "looming (LPLC2/LC4)": {"any": [{"cell_type": "LPLC2"}, {"cell_type": "LC4"}, {"hemibrain_type": "LPLC2"}, {"hemibrain_type": "LC4"}]},
    "olfactory RNs":  {"any": [{"class": "olfactory"}, {"cell_type": "ORN"}, {"labels_regex": "ORN"}]},
    "MN9 (proboscis)": {"any": [{"cell_type": "MN9"}, {"hemibrain_type": "MN9"}]},
    "Giant Fiber":    {"any": [{"cell_type": "GF"}, {"hemibrain_type": "Giant Fiber"}, {"cell_type": "DNp01"}]},
    "descending neurons": {"super_class": "descending"},
}


def export_web(c: Connectome, out: Path | str, sets: dict | None = None, max_neurons: int | None = None) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    sets = sets or DEFAULT_SETS

    W = c.W.tocsr()
    W.sort_indices()
    pos = c.positions.astype(np.float32).copy()
    bad = ~np.isfinite(pos).all(axis=1)
    if bad.any():
        pos[bad] = np.nanmean(pos[~bad], axis=0) if (~bad).any() else 0.0

    sc = c.annotations["super_class"].astype(str).to_numpy() if "super_class" in c.annotations else np.full(c.n, "other")
    cls = np.array([CLASS_ORDER.index(s) if s in CLASS_ORDER else 0 for s in sc], dtype=np.uint8)

    populations = {}
    for name, spec in sets.items():
        idx = c.select(spec)
        if idx.size:
            populations[name] = idx.astype(int).tolist()

    (out / "positions.bin").write_bytes(pos.tobytes())
    (out / "indptr.bin").write_bytes(W.indptr.astype(np.int32).tobytes())
    (out / "indices.bin").write_bytes(W.indices.astype(np.int32).tobytes())
    (out / "weights.bin").write_bytes(W.data.astype(np.float32).tobytes())
    (out / "classes.bin").write_bytes(cls.tobytes())
    meta = {
        "name": c.name,
        "n": int(c.n),
        "n_edges": int(W.nnz),
        "bounds": {"min": pos.min(axis=0).tolist(), "max": pos.max(axis=0).tolist()},
        "classes": CLASS_ORDER,
        "populations": populations,
        "source": c.meta,
    }
    (out / "meta.json").write_text(json.dumps(meta))
    return out
