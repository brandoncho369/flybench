"""Negative-control connectomes: what a task scores when the wiring is destroyed.

A behavioural pass proves little on its own. A *C. elegans* connectome wired to a fly body produced
realistic walking (the "digital sphinx", bioRxiv 2026.03.20.713233), and FlyGM (arXiv 2602.17997)
showed that degree-preserving rewiring and Erdős–Rényi graphs are the right baselines for any
connectome-based claim. So every task can be scored on the real wiring and on a shuffled version
of it; the difference is the task's *specificity*. A task the shuffled brain also passes is not
measuring the connectome and is flagged `non_diagnostic`.

Three controls, all seeded and reproducible, all keeping the same neurons, annotations and
selectors so stimuli and readouts land on the same cells:

- ``rewired``   degree-preserving: every neuron keeps its exact out-degree, its synapse weights and
                its transmitter sign, and the multiset of postsynaptic endpoints is preserved (so
                in-degrees are preserved as endpoint counts); only *who* connects to *whom* changes.
- ``random``    Erdős–Rényi matched on neuron count, edge count and weight distribution, with each
                edge's sign taken from its (random) presynaptic neuron's transmitter.
- ``signflip``  same wiring, transmitter signs permuted across neurons (same fraction inhibitory).

W is CSR with W[pre, post] = signed synapse count and the sign is a property of the presynaptic
neuron (flybench.connectome), so every control derives signs per row.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from .connectome import Connectome

CONTROLS = ("rewired", "random", "signflip")


def _row_signs(W: sp.csr_matrix) -> np.ndarray:
    """Sign of each presynaptic neuron's output (+1 for neurons with no edges)."""
    W = W.tocsr()
    n = W.shape[0]
    signs = np.ones(n, dtype=np.int8)
    nnz_per_row = np.diff(W.indptr)
    has = nnz_per_row > 0
    first = W.indptr[:-1][has]
    signs[has] = np.where(W.data[first] < 0, -1, 1)
    return signs


def _rows_of(W: sp.csr_matrix) -> np.ndarray:
    return np.repeat(np.arange(W.shape[0], dtype=np.int64), np.diff(W.indptr))


def _build(c: Connectome, rows: np.ndarray, cols: np.ndarray, vals: np.ndarray, control: str) -> Connectome:
    n = c.n
    keep = rows != cols                                    # no self-loops
    W = sp.csr_matrix((vals[keep].astype(np.float32), (rows[keep], cols[keep])), shape=(n, n))
    W.sum_duplicates()
    W.sort_indices()
    return Connectome(root_ids=c.root_ids, W=W, positions=c.positions, annotations=c.annotations,
                      name=f"{c.name}+{control}", meta={**c.meta, "control": control})


def rewire_degree_preserving(c: Connectome, seed: int = 0) -> Connectome:
    """Permute the postsynaptic endpoints of all edges. Out-degree, per-row weights and signs are
    exactly preserved; the in-degree multiset is preserved up to merged duplicates."""
    rng = np.random.default_rng(20_000 + seed)
    W = c.W.tocsr()
    rows = _rows_of(W)
    cols = W.indices.astype(np.int64).copy()
    vals = W.data.copy()
    perm = rng.permutation(cols.size)
    cols = cols[perm]
    # re-draw the few self-loops the permutation creates instead of dropping them
    for _ in range(10):
        bad = np.flatnonzero(rows == cols)
        if bad.size == 0:
            break
        swap = rng.permutation(bad.size)
        cols[bad] = cols[bad][swap]
    return _build(c, rows, cols, vals, "rewired")


def erdos_renyi_matched(c: Connectome, seed: int = 0) -> Connectome:
    """Random graph with the same n, the same number of edges, the same |weight| multiset, and
    signs given by each edge's random presynaptic neuron (same fraction of inhibitory neurons)."""
    rng = np.random.default_rng(30_000 + seed)
    W = c.W.tocsr()
    n, m = c.n, W.nnz
    signs = _row_signs(W)
    rows = rng.integers(0, n, size=m, dtype=np.int64)
    cols = rng.integers(0, n, size=m, dtype=np.int64)
    vals = np.abs(W.data)[rng.permutation(m)] * signs[rows]
    return _build(c, rows, cols, vals, "random")


def shuffle_signs(c: Connectome, seed: int = 0) -> Connectome:
    """Same edges and magnitudes; the per-neuron transmitter signs are permuted across neurons."""
    rng = np.random.default_rng(40_000 + seed)
    W = c.W.tocsr()
    signs = _row_signs(W)
    # permute only among neurons that have outputs, so the inhibitory count is exactly preserved
    has = np.flatnonzero(np.diff(W.indptr) > 0)
    new_signs = signs.copy()
    new_signs[has] = signs[has][rng.permutation(has.size)]
    rows = _rows_of(W)
    vals = np.abs(W.data) * new_signs[rows]
    return _build(c, rows, W.indices.astype(np.int64), vals, "signflip")


def make_control(c: Connectome, control: str, seed: int = 0) -> Connectome:
    if control == "rewired":
        return rewire_degree_preserving(c, seed)
    if control == "random":
        return erdos_renyi_matched(c, seed)
    if control == "signflip":
        return shuffle_signs(c, seed)
    raise ValueError(f"unknown control {control!r}; choose from {CONTROLS}")


def parse_controls(spec: str | None) -> list[str]:
    """'all' -> every control; 'rewired,random' -> those; None/'' -> none."""
    if not spec:
        return []
    if spec == "all":
        return list(CONTROLS)
    names = [s.strip() for s in spec.split(",") if s.strip()]
    for s in names:
        if s not in CONTROLS:
            raise ValueError(f"unknown control {s!r}; choose from {CONTROLS} or 'all'")
    return names
