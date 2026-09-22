"""The body's own eyes into the connectome, live (Phase 7b, docs/rfcs/36).

FlyGym renders each compound eye as a fisheye image and bins it into 721 ommatidia (the
NeuroMechFly retina); flyvis's BoxEye is a 721-hexal lattice of the same extent. So a rendered
eye maps onto flyvis's receptors one to one — a minimum-distance bijection between the two
721-point lattices after whitening each axis (CONVENTION; the left eye is mirrored so anterior sits on the same side of the lattice for
both eyes, since the one flyvis network is used for each eye in turn). flyvis then runs one frame
at a time with its state carried over (`Network.simulate(..., initial_state=state, as_states=True)`,
which is bit-identical to a batch simulation), and each frame's activity becomes the same
per-type, per-column rates the cached front end produces (RATE_PER_UNIT_HZ × activity above the
resting activity of the *actual* standing scene, held for the next 10 ms), delivered to the
connectome's own T4/T5/T2/T3/Tm/TmY cells through the same inferred column mapping.

Luminance per ommatidium = the max of FlyGym's yellow/pale channels (both in [0, 1]; the two
photoreceptor types see the same grey-scale scene here). No colour, no motion blur, no
photoreceptor adaptation beyond what flyvis's R1–R8 do.
"""

from __future__ import annotations

import numpy as np

from ..connectome import Connectome
from ..frontends.flyvis_frontend import (BIN_MS, HEX_EXTENT, OUTPUT_TYPES, RATE_PER_UNIT_HZ, _patch_datamate_windows,
                                         map_neurons_to_columns, network_view)

FLYVIS_NETWORK = "flow/0000/000"
FRAME_S = BIN_MS / 1000.0


def available() -> bool:
    """flygym, flyvis, torch and the pretrained flyvis network (flyvis_frontend.pretrained_available)."""
    from ..frontends.flyvis_frontend import pretrained_available
    try:
        import flygym  # noqa: F401
    except Exception:
        return False
    return pretrained_available(FLYVIS_NETWORK)


def _whiten(xy: np.ndarray) -> np.ndarray:
    xy = xy - xy.mean(axis=0, keepdims=True)
    return xy / np.maximum(xy.std(axis=0, keepdims=True), 1e-9)


def ommatidia_to_receptors(retina, receptor_centers: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For the left and right eye: index arrays such that receptors[k] = ommatidia[perm[k]] — a bijection
    between the two 721-point lattices by minimum total squared distance after whitening each axis
    (the two lattices have different aspect ratios in their own pixel frames)."""
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
    m = retina.ommatidia_id_map
    ids = np.arange(1, int(m.max()) + 1)
    rows, cols = np.indices(m.shape)
    cx = np.array([cols[m == i].mean() for i in ids]); cy = np.array([rows[m == i].mean() for i in ids])
    omm = _whiten(np.c_[cx, -cy])                            # image y down -> lattice y up
    rc = _whiten(np.asarray(receptor_centers, dtype=float))
    _, right = linear_sum_assignment(cdist(rc, omm, "sqeuclidean"))            # right eye as rendered
    _, left = linear_sum_assignment(cdist(rc, omm * np.array([-1.0, 1.0]), "sqeuclidean"))   # left eye mirrored
    return left.astype(int), right.astype(int)


class LiveEye:
    """The loop's sensory half: FlyGym ommatidia -> flyvis (stateful) -> per-neuron rates for `c`."""

    def __init__(self, c: Connectome, retina, seed: int = 0, network: str = FLYVIS_NETWORK):
        import torch
        from flyvis.datasets.rendering import BoxEye
        _patch_datamate_windows()
        self.torch = torch
        self.net = network_view(network).init_network()
        eye = BoxEye(extent=HEX_EXTENT)
        rc = eye.receptor_centers
        rc = rc.numpy() if hasattr(rc, "numpy") else np.asarray(rc)
        self.perm_left, self.perm_right = ommatidia_to_receptors(retina, rc)
        nodes = self.net.connectome.nodes
        types = np.array([t.decode() for t in nodes.type[:]])
        u, v = nodes.u[:].astype(int), nodes.v[:].astype(int)
        # per driven type: flyvis node indices in (u, v) order, and each hemisphere's connectome neurons with their column
        ann = c.annotations
        side = ann["side"].astype(str).str.lower().str[:1].to_numpy() if "side" in ann.columns else np.array([""] * c.n)
        columns = None
        self.plan = []
        for tname in OUTPUT_TYPES:
            m = types == tname
            idx = c.select({"cell_type": tname})
            if not m.any() or idx.size == 0:
                continue
            order = np.lexsort((v[m], u[m]))
            node_idx = np.flatnonzero(m)[order]
            cols = np.stack([u[m][order], v[m][order]], axis=1)
            columns = cols if columns is None else columns
            per_side = {}
            for s in np.unique(side[idx]):
                sel = idx[side[idx] == s]
                per_side[s] = (sel, map_neurons_to_columns(c.positions[sel].astype(float), cols, seed=seed))
            self.plan.append((tname, node_idx, per_side))
        self.n_driven = int(sum(len(sel) for _, _, ps in self.plan for sel, _ in ps.values()))
        self.state_L = self.state_R = None
        self.rest_L = self.rest_R = None

    def luminance(self, ommatidia: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """FlyGym readouts (2, 721, 2) -> receptor intensities for the left and right eye (721,) each."""
        lum = ommatidia.max(axis=2)
        return lum[0][self.perm_left], lum[1][self.perm_right]

    def settle(self, ommatidia: np.ndarray, t_pre_s: float = 1.0) -> None:
        """Steady state on the actual standing scene; its activity is the resting activity."""
        torch = self.torch
        L, R = self.luminance(ommatidia)
        n = int(round(t_pre_s / FRAME_S))
        self.state_L = self.net.steady_state(t_pre=0.5, dt=FRAME_S, batch_size=1, value=float(L.mean()))
        self.state_R = self.net.steady_state(t_pre=0.5, dt=FRAME_S, batch_size=1, value=float(R.mean()))
        xL = torch.tensor(np.tile(L, (1, n, 1, 1)), dtype=torch.float32)
        xR = torch.tensor(np.tile(R, (1, n, 1, 1)), dtype=torch.float32)
        self.state_L = self.net.simulate(xL, dt=FRAME_S, initial_state=self.state_L, as_states=True)[-1]
        self.state_R = self.net.simulate(xR, dt=FRAME_S, initial_state=self.state_R, as_states=True)[-1]
        self.rest_L = self.state_L.nodes.activity.detach().numpy()[0].copy()
        self.rest_R = self.state_R.nodes.activity.detach().numpy()[0].copy()

    def frame(self, ommatidia: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Advance flyvis by one 10 ms frame for each eye; return (neurons, rates_hz) for the connectome."""
        torch = self.torch
        L, R = self.luminance(ommatidia)
        self.state_L = self.net.simulate(torch.tensor(L, dtype=torch.float32)[None, None, None, :], dt=FRAME_S, initial_state=self.state_L, as_states=True)[-1]
        self.state_R = self.net.simulate(torch.tensor(R, dtype=torch.float32)[None, None, None, :], dt=FRAME_S, initial_state=self.state_R, as_states=True)[-1]
        aL = self.state_L.nodes.activity.detach().numpy()[0]; aR = self.state_R.nodes.activity.detach().numpy()[0]
        rL = np.maximum(aL - self.rest_L, 0.0) * RATE_PER_UNIT_HZ
        rR = np.maximum(aR - self.rest_R, 0.0) * RATE_PER_UNIT_HZ
        neurons, rates = [], []
        for tname, node_idx, per_side in self.plan:
            for s, (sel, col_of) in per_side.items():
                src = rL if s == "l" else rR         # unlabelled sides see the right eye
                neurons.append(sel); rates.append(src[node_idx][col_of])
        return np.concatenate(neurons), np.concatenate(rates).astype(np.float32)
