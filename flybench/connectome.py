"""Connectome loading, caching and neuron selection.

A `Connectome` is:

* `root_ids`      – int64 array, one entry per neuron (row index == neuron index)
* `W`             – scipy CSR matrix, shape (N, N), **rows = presynaptic,
                    cols = postsynaptic**, value = signed synapse count
                    (+ excitatory, − inhibitory). Sign comes from the
                    presynaptic neuron's neurotransmitter.
* `positions`     – float32 (N, 3) soma / centroid positions in nm, or NaN
* `annotations`   – pandas DataFrame, one row per neuron, with whatever
                    columns the source provides (cell_type, super_class,
                    hemibrain_type, labels, nt_type, side, ...)

Two sources are supported:

1. **FlyWire Codex downloads** (v783, female adult brain). Download from
   https://codex.flywire.ai/api/download (free account) the files
   `connections.csv.gz`, `neurons.csv.gz`, `classification.csv.gz`,
   `labels.csv.gz` into a directory and run `flybench build <dir>`.
2. **The bundled toy connectome** (`flybench toy`) — a ~2k neuron synthetic
   network wired to exhibit the benchmark reflexes. It exists so the code,
   tests and the web explorer run without a 300 MB download. It proves
   nothing about biology.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import scipy.sparse as sp

# Shiu et al. 2024 (Nature): ACh excitatory, GABA and glutamate inhibitory,
# monoamines treated as excitatory. Unknown -> excitatory.
NT_SIGN = {
    "ACH": 1,
    "GABA": -1,
    "GLUT": -1,
    "DA": 1,
    "OCT": 1,
    "SER": 1,
}

DEFAULT_CACHE = Path.home() / ".cache" / "flybench"


@dataclass
class Connectome:
    root_ids: np.ndarray
    W: sp.csr_matrix
    positions: np.ndarray
    annotations: pd.DataFrame
    name: str = "unnamed"
    meta: dict[str, Any] = field(default_factory=dict)

    # ---- basic facts -------------------------------------------------
    @property
    def n(self) -> int:
        return int(self.W.shape[0])

    @property
    def n_edges(self) -> int:
        return int(self.W.nnz)

    def index_of(self, root_ids: Iterable[int]) -> np.ndarray:
        lookup = pd.Index(self.root_ids)
        idx = lookup.get_indexer(list(root_ids))
        return idx[idx >= 0]

    def select(self, spec: dict | str | list) -> np.ndarray:
        return select(self.annotations, spec)

    # ---- persistence -------------------------------------------------
    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        sp.save_npz(path / "W.npz", self.W)
        np.save(path / "root_ids.npy", self.root_ids)
        np.save(path / "positions.npy", self.positions)
        self.annotations.to_parquet(path / "annotations.parquet") if _has_parquet() \
            else self.annotations.to_csv(path / "annotations.csv", index=False)
        (path / "meta.json").write_text(json.dumps({"name": self.name, **self.meta}, indent=2))
        return path

    @classmethod
    def load(cls, path: Path | str) -> "Connectome":
        path = Path(path)
        W = sp.load_npz(path / "W.npz").tocsr()
        root_ids = np.load(path / "root_ids.npy")
        positions = np.load(path / "positions.npy")
        if (path / "annotations.parquet").exists():
            ann = pd.read_parquet(path / "annotations.parquet")
        else:
            ann = pd.read_csv(path / "annotations.csv", dtype=str, keep_default_na=False)
        meta = json.loads((path / "meta.json").read_text()) if (path / "meta.json").exists() else {}
        name = meta.pop("name", path.name)
        return cls(root_ids=root_ids, W=W, positions=positions, annotations=ann, name=name, meta=meta)


def _has_parquet() -> bool:
    try:
        import pyarrow  # noqa: F401

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def select(ann: pd.DataFrame, spec: dict | str | list) -> np.ndarray:
    """Return neuron indices matching a selector spec.

    Spec grammar (YAML-friendly):

        {all: true}                                 -> every neuron
        {root_ids: [7205..., 7205...]}              -> by id (needs `root_id` col)
        {cell_type: "MN9"}                          -> exact match on a column
        {hemibrain_type: ["LC4", "LPLC2"]}          -> isin
        {labels_regex: "sugar"}                     -> case-insensitive regex
        {any: [spec, spec]}  /  {all_of: [spec, ...]}  /  {not: spec}
        "MN9"                                       -> shorthand for cell_type
    """
    if isinstance(spec, str):
        spec = {"cell_type": spec}
    if isinstance(spec, list):
        spec = {"any": spec}
    mask = _mask(ann, spec)
    return np.flatnonzero(mask)


def _mask(ann: pd.DataFrame, spec: dict) -> np.ndarray:
    n = len(ann)
    if not spec:
        return np.zeros(n, dtype=bool)
    mask = np.ones(n, dtype=bool)
    for key, val in spec.items():
        if key == "all":
            m = np.ones(n, dtype=bool) if val else np.zeros(n, dtype=bool)
        elif key == "any":
            m = np.zeros(n, dtype=bool)
            for s in val:
                m |= _mask(ann, s)
        elif key == "all_of":
            m = np.ones(n, dtype=bool)
            for s in val:
                m &= _mask(ann, s)
        elif key == "not":
            m = ~_mask(ann, val)
        elif key == "root_ids":
            m = ann["root_id"].astype(np.int64).isin([int(v) for v in val]).to_numpy()
        elif key.endswith("_regex"):
            col = key[: -len("_regex")]
            if col not in ann.columns:
                m = np.zeros(n, dtype=bool)
            else:
                m = ann[col].astype(str).str.contains(val, case=False, regex=True, na=False).to_numpy()
        else:
            if key not in ann.columns:
                m = np.zeros(n, dtype=bool)
            elif isinstance(val, (list, tuple, set)):
                m = ann[key].astype(str).isin([str(v) for v in val]).to_numpy()
            else:
                m = (ann[key].astype(str) == str(val)).to_numpy()
        mask &= m
    return mask


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def load_connectome(name_or_path: str | Path = "toy", cache: Path | str = DEFAULT_CACHE) -> Connectome:
    """Load a cached connectome by name (`toy`, `flywire783`) or by directory path."""
    p = Path(name_or_path)
    if p.is_dir() and (p / "W.npz").exists():
        return Connectome.load(p)
    cached = Path(cache) / str(name_or_path)
    if (cached / "W.npz").exists():
        return Connectome.load(cached)
    if str(name_or_path) == "toy":
        from .toy import build_toy_connectome

        c = build_toy_connectome()
        c.save(cached)
        return c
    raise FileNotFoundError(
        f"No connectome named {name_or_path!r}. Run `flybench build <codex_dir>` for FlyWire, "
        f"or use `toy`."
    )


def build_from_codex(codex_dir: Path | str, min_synapses: int = 5, name: str = "flywire783") -> Connectome:
    """Build a Connectome from FlyWire Codex CSV downloads.

    Expects in `codex_dir`:
      connections.csv[.gz]     pre_root_id, post_root_id, neuropil, syn_count, nt_type
      neurons.csv[.gz]         root_id, ..., nt_type, ..., position (optional)
      classification.csv[.gz]  root_id, flow, super_class, class, sub_class, cell_type,
                               hemibrain_type, hemilineage, side, nerve
      labels.csv[.gz]          root_id, label, ...   (community labels; optional)
      coordinates.csv[.gz]     root_id, position     (marked neuron coordinates; optional, gives 3D positions)
      cell_types.csv[.gz]      root_id, primary_type (consolidated cell types; optional, fills cell_type gaps)
    """
    d = Path(codex_dir)
    conn = pd.read_csv(_find(d, "connections"), dtype={"pre_root_id": np.int64, "post_root_id": np.int64})
    neurons = pd.read_csv(_find(d, "neurons"), dtype={"root_id": np.int64})
    classification = pd.read_csv(_find(d, "classification"), dtype={"root_id": np.int64}, keep_default_na=False)
    labels_path = _find(d, "labels", required=False)

    # Aggregate synapses across neuropils, apply threshold.
    conn = conn.groupby(["pre_root_id", "post_root_id"], as_index=False)["syn_count"].sum()
    conn = conn[conn["syn_count"] >= min_synapses]

    root_ids = np.array(sorted(set(neurons["root_id"]) | set(conn["pre_root_id"]) | set(conn["post_root_id"])), dtype=np.int64)
    index = pd.Index(root_ids)
    n = len(root_ids)

    # Presynaptic transmitter -> sign.
    nt = neurons.set_index("root_id")["nt_type"].astype(str).str.upper() if "nt_type" in neurons else pd.Series(dtype=str)
    sign_per_neuron = np.ones(n, dtype=np.int8)
    if len(nt):
        s = nt.map(NT_SIGN).fillna(1).astype(np.int8)
        sign_per_neuron[index.get_indexer(s.index)] = s.to_numpy()

    pre = index.get_indexer(conn["pre_root_id"].to_numpy())
    post = index.get_indexer(conn["post_root_id"].to_numpy())
    vals = conn["syn_count"].to_numpy().astype(np.float32) * sign_per_neuron[pre]
    W = sp.csr_matrix((vals, (pre, post)), shape=(n, n), dtype=np.float32)

    # Positions: prefer coordinates.csv (Codex "Marked Neuron Coordinates"), else a position column in neurons.csv.
    positions = np.full((n, 3), np.nan, dtype=np.float32)
    coords_path = _find(d, "coordinates", required=False)
    pos_src = pd.read_csv(coords_path, dtype={"root_id": np.int64}) if coords_path is not None else neurons
    pos_src = pos_src.drop_duplicates("root_id")
    pos_col = next((c for c in pos_src.columns if c.lower() in ("position", "pos", "soma_position")), None)
    if pos_col is not None:
        parsed = pos_src[pos_col].astype(str).map(_parse_pos)
        ok = parsed.map(lambda v: v is not None).to_numpy()
        rows = index.get_indexer(pos_src.loc[ok, "root_id"])
        vals = np.stack(parsed[ok].to_list())
        positions[rows[rows >= 0]] = vals[rows >= 0]
    elif {"x", "y", "z"} <= set(pos_src.columns):
        rows = index.get_indexer(pos_src["root_id"])
        positions[rows[rows >= 0]] = pos_src[["x", "y", "z"]].to_numpy(np.float32)[rows >= 0]

    # Annotations.
    ann = pd.DataFrame({"root_id": root_ids})
    ann = ann.merge(classification, on="root_id", how="left")
    keep = [c for c in ("nt_type", "group") if c in neurons.columns]
    ann = ann.merge(neurons[["root_id", *keep]], on="root_id", how="left")
    # Consolidated cell types (Codex "Cell Types"): fill empty cell_type from primary_type.
    ct_path = _find(d, "cell_types", required=False)
    if ct_path is not None:
        ct = pd.read_csv(ct_path, dtype={"root_id": np.int64}, keep_default_na=False).drop_duplicates("root_id")
        pt_col = next((c for c in ct.columns if c in ("primary_type", "cell_type", "type")), None)
        if pt_col is not None:
            ann = ann.merge(ct[["root_id", pt_col]].rename(columns={pt_col: "primary_type"}), on="root_id", how="left")
            if "cell_type" in ann.columns:
                empty = ann["cell_type"].isna() | (ann["cell_type"].astype(str) == "")
                ann.loc[empty, "cell_type"] = ann.loc[empty, "primary_type"]
            else:
                ann["cell_type"] = ann["primary_type"]
    if labels_path is not None:
        labels = pd.read_csv(labels_path, dtype={"root_id": np.int64}, keep_default_na=False)
        lab_col = "label" if "label" in labels.columns else labels.columns[1]
        agg = labels.groupby("root_id")[lab_col].apply(lambda s: " | ".join(map(str, s)))
        ann["labels"] = ann["root_id"].map(agg)
    ann = ann.fillna("").astype({c: str for c in ann.columns if c != "root_id"})

    return Connectome(
        root_ids=root_ids,
        W=W,
        positions=positions,
        annotations=ann,
        name=name,
        meta={"source": "flywire-codex", "min_synapses": min_synapses, "n": n, "n_edges": int(W.nnz)},
    )


def _find(d: Path, stem: str, required: bool = True) -> Path | None:
    for cand in (d / f"{stem}.csv.gz", d / f"{stem}.csv"):
        if cand.exists():
            return cand
    for cand in d.glob(f"*{stem}*.csv*"):
        return cand
    if required:
        raise FileNotFoundError(f"{stem}.csv(.gz) not found in {d}")
    return None


_num = re.compile(r"-?\d+(?:\.\d+)?")


def _parse_pos(s: str):
    nums = _num.findall(s)
    if len(nums) < 3:
        return None
    return np.array(nums[:3], dtype=np.float32)
