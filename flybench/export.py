"""Export a connectome in the compact binary layout fly-explorer loads.

Files written to <out>/:
  meta.json       n, n_edges, populations {name: [indices]}, bounds, source note
  positions.bin   float32 (n, 3), nm, NaN replaced by the centroid
  indptr.bin      int32   (n+1)   CSR row pointers, rows = presynaptic
  indices.bin     int32   (nnz)   postsynaptic index
  weights.bin     float32 (nnz)   signed synapse counts
  classes.bin     uint8   (n)     colour class per neuron (see CLASS_ORDER)
  types.bin       uint16  (n)     cell-type id per neuron (0 = untyped)
  types.json      {names: [...], counts: [...], super_class: [...]}  id -> name, ordered by count desc
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .connectome import Connectome

CLASS_ORDER = ["other", "sensory", "visual_projection", "central", "descending", "motor", "optic", "ascending", "endocrine"]

# MaleCNS (neuPrint) super_class names -> the same colour classes FlyWire uses
CLASS_ALIASES = {
    "cb_intrinsic": "central", "vnc_intrinsic": "central", "ol_intrinsic": "optic", "ol_sensory": "sensory",
    "cb_sensory": "sensory", "vnc_sensory": "sensory", "sensory_ascending": "ascending", "sensory_descending": "descending",
    "descending_neuron": "descending", "ascending_neuron": "ascending", "cb_motor": "motor", "vnc_motor": "motor",
    "vnc_efferent": "motor", "cb_efferent": "motor", "efferent_ascending": "ascending", "efferent_descending": "descending",
    "visual_centrifugal": "visual_projection", "cb_endocrine": "endocrine", "vnc_endocrine": "endocrine",
}

# Named neuron sets the explorer exposes as buttons. Same selector grammar as tasks.
DEFAULT_SETS = {
    "sugar GRNs":     {"any": [{"sub_class": "sugar/water"}, {"all_of": [{"labels_regex": "sugar"}, {"super_class": "sensory"}, {"not": {"labels_regex": "bitter"}}]}, {"all_of": [{"sub_class": "labellar bristle"}, {"cell_type_regex": "^LB3[bc]$"}]}]},
    "bitter GRNs":    {"any": [{"sub_class": "bitter"}, {"all_of": [{"labels_regex": "bitter"}, {"super_class": "sensory"}]}, {"all_of": [{"sub_class": "labellar bristle"}, {"cell_type_regex": "^LB1[a-d]$"}]}]},
    "water GRNs":     {"any": [{"all_of": [{"labels_regex": "water"}, {"super_class": "sensory"}]}, {"all_of": [{"sub_class": "labellar bristle"}, {"cell_type": "LB3a"}]}]},
    # MaleCNS-only modalities, from the Cell 2026 gustatory connectome (receptor driver lines)
    "high-salt GRNs": {"all_of": [{"sub_class": "labellar bristle"}, {"cell_type": "LB3d"}]},
    "amino-acid GRNs (LB1e)": {"all_of": [{"sub_class": "labellar bristle"}, {"cell_type": "LB1e"}]},
    "looming (LPLC2/LC4)": {"any": [{"cell_type": "LPLC2"}, {"cell_type": "LC4"}, {"hemibrain_type": "LPLC2"}, {"hemibrain_type": "LC4"}]},
    "olfactory RNs":  {"any": [{"class": "olfactory"}, {"cell_type": "ORN"}, {"labels_regex": "ORN"}]},
    "MN9 (proboscis)": {"any": [{"cell_type": "MN9"}, {"cell_type": "CB0701"}, {"hemibrain_type": "MN9"}, {"all_of": [{"labels_regex": r"\bMN9\b"}, {"super_class": "motor"}]}]},
    "Giant Fiber":    {"any": [{"cell_type": "GF"}, {"cell_type": "DNp01"}, {"hemibrain_type": "Giant Fiber"}, {"all_of": [{"labels_regex": "giant fib"}, {"super_class": "descending"}]}]},
    "JO (antennal mechanosensory)": {"cell_type_regex": "^JO-"},
    "photoreceptors": {"any": [{"sub_class": "photo_receptor"}, {"cell_type_regex": "^R[1-8]"}]},
    "descending neurons": {"super_class_regex": "^descending"},
    # body side (MaleCNS only: the ventral nerve cord)
    "jump muscle MN (TTMn)": {"cell_type": "TTMn"},
    "flight power MNs (DLMn)": {"cell_type_regex": "^DLMn"},
    "leg motor neurons": {"all_of": [{"super_class": "vnc_motor"}, {"cell_type_regex": "(flexor|extensor|rotator|reductor|depressor|levator|promotor|remotor|Tergotr|Sternotrochanter|ltm|^Ta |^Ti |^Tr |^Fe ) ?MN$"}]},
    "wing motor neurons": {"all_of": [{"super_class": "vnc_motor"}, {"sub_class": "wm"}]},
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
    cls = np.array([CLASS_ORDER.index(CLASS_ALIASES.get(s, s)) if CLASS_ALIASES.get(s, s) in CLASS_ORDER else 0 for s in sc], dtype=np.uint8)

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
    # every annotated cell type, so the explorer can activate any of them by name
    ct = c.annotations["cell_type"].astype(str).to_numpy() if "cell_type" in c.annotations else np.full(c.n, "")
    ct = np.where(ct == "nan", "", ct)
    names, inv, counts = np.unique(ct, return_inverse=True, return_counts=True)
    order = np.argsort(-counts, kind="stable")
    order = np.concatenate([[int(np.flatnonzero(names == "")[0])] if "" in names else [], [i for i in order if names[i] != ""]]).astype(int)
    remap = np.empty(len(names), dtype=np.int64); remap[order] = np.arange(len(names))
    ids = remap[inv]
    if ids.max() > 65535:
        raise ValueError("more than 65535 cell types; widen types.bin")
    if "" not in names:   # keep id 0 reserved for "untyped"
        ids = ids + 1
    type_sc = []
    for i in order:
        rows = np.flatnonzero(inv == i)
        vals, cnt = np.unique(sc[rows], return_counts=True)
        type_sc.append(str(vals[np.argmax(cnt)]))
    tnames = [str(names[i]) for i in order]; tcounts = [int(counts[i]) for i in order]
    if "" not in names:
        tnames.insert(0, ""); tcounts.insert(0, 0); type_sc.insert(0, "other")
    (out / "types.bin").write_bytes(ids.astype(np.uint16).tobytes())
    (out / "types.json").write_text(json.dumps({"names": tnames, "counts": tcounts, "super_class": type_sc}), encoding="utf-8")
    meta = {
        "name": c.name,
        "n": int(c.n),
        "n_edges": int(W.nnz),
        "bounds": {"min": pos.min(axis=0).tolist(), "max": pos.max(axis=0).tolist()},
        "classes": CLASS_ORDER,
        "populations": populations,
        "source": c.meta,
    }
    (out / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return out
