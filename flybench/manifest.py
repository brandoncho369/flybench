"""Pinned connectome artefacts (docs/ROADMAP.md item 37).

A result is only comparable to another if both ran on the same wiring. Codex re-exports change
bytes without a version bump, and a `flybench build` with a different `min_synapses` is a
different graph under the same name. So every named connectome is pinned here by a fingerprint —
the SHA-256 of its neuron ids, its sparse matrix (indptr, indices, signed synapse counts) and its
annotation table — and every result records the fingerprint it ran on.

`flybench run` refuses a named connectome whose fingerprint differs from the pin unless
`--allow-unpinned`, which marks the result `unpinned: true` (shown on the leaderboard, ranked
last). A connectome not in the manifest (a private build, a directory path) is `unpinned` too.
The toy is pinned by its `toy_version` (the code that builds it), not by bytes.

Pins live in `manifests.json` next to this file; `flybench fingerprint <name>` prints the value
to put there after a deliberate rebuild.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .connectome import Connectome

MANIFEST_PATH = Path(__file__).with_name("manifests.json")


def fingerprint(c: Connectome) -> str:
    """SHA-256 over the arrays that define the graph and its labels, independent of file format."""
    h = hashlib.sha256()
    W = c.W.tocsr()
    W.sort_indices()
    h.update(np.ascontiguousarray(c.root_ids, dtype=np.int64).tobytes())
    h.update(np.ascontiguousarray(W.indptr, dtype=np.int64).tobytes())
    h.update(np.ascontiguousarray(W.indices, dtype=np.int64).tobytes())
    h.update(np.ascontiguousarray(W.data, dtype=np.float32).tobytes())
    ann = c.annotations
    h.update(",".join(map(str, ann.columns)).encode())
    h.update(ann.astype(str).to_csv(index=False).encode("utf-8"))
    return h.hexdigest()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def check_pinned(c: Connectome) -> dict:
    """{'status': 'pinned' | 'mismatch' | 'unpinned', 'sha256': actual, 'expected': pinned or None,
    'version': the manifest's version string or None}. The toy is checked by toy_version."""
    man = load_manifest().get(c.name)
    if c.name == "toy":
        from .toy import TOY_VERSION
        actual = str(c.meta.get("toy_version", ""))
        if man is None:
            return {"status": "unpinned", "sha256": actual, "expected": None, "version": None}
        return {"status": "pinned" if actual == man.get("version") == TOY_VERSION else "mismatch", "sha256": actual, "expected": man.get("version"), "version": man.get("version")}
    actual = fingerprint(c)
    if man is None:
        return {"status": "unpinned", "sha256": actual, "expected": None, "version": None}
    return {"status": "pinned" if actual == man.get("sha256") else "mismatch", "sha256": actual, "expected": man.get("sha256"), "version": man.get("version")}
