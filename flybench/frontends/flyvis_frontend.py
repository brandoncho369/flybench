"""flyvis as a visual front end (ROADMAP item 44).

flyvis (Lappalainen et al. 2024, Nature 634:1132) is a connectome-constrained model of the fly
optic lobe: 65 cell types on a 721-column hexagonal retina, trained on optic flow. Here it does
one job: a rendered stimulus — a looming disc, a flash, a contracting disc — goes through the
pretrained network and comes out as a *rate per cell type per column*, and those rates drive the
same cell types in the FlyWire / MaleCNS graph, one column to a set of neurons, so that the LIF's
own wiring from T4/T5/Tm to LPLC2, LC4 and the giant fiber does the rest. Compare the task-04
convention, "LPLC2 at 150 Hz": here nothing downstream of the medulla is driven directly.

Choices, all stated:

- **Which types are driven.** The output layer of the optic lobe that flyvis models and both
  connectomes name identically: T4a–d, T5a–d, and every Tm / TmY type present (CONVENTION —
  driving the medulla inputs L1–L5 as well would double-count them through the LIF's own L → Mi →
  Tm wiring).
- **Activity → rate.** flyvis activities are in arbitrary units with a resting offset (Tm3 sits at
  ~1.2 on a grey field). The rate is the activity *above its own resting value on the grey field*,
  rectified, at 1.0 unit = 100 Hz (CONVENTION: the task-02 rate at the network's flash-transient
  peak in T4; the "above rest" part is how responses are reported in the flyvis paper). Nothing
  is fitted.
- **Column → neuron.** A FlyWire type has ~700 cells per hemisphere, one per column, but no column
  annotation. The mapping here projects a type's somata (one hemisphere) onto their first two
  principal axes, normalises to the hexagonal disc and takes the nearest flyvis column — INFERRED
  retinotopy, right up to a rotation and a flip. Radially symmetric stimuli (loom, flash,
  contraction, centred on the eye) do not depend on the rotation; directional stimuli would, and
  are not offered until the orientation is pinned by an anatomical landmark.
- **Both eyes see the same movie.** A frontal stimulus, both hemispheres driven alike.

The heavy part runs once: `flybench frontend flyvis render` writes `data/frontends/flyvis/<stimulus>.npz`
(per-type, per-column rate time courses, 10 ms bins, float16), which is committed, so a run — and
CI — needs neither torch nor flyvis. The renderer needs `pip install flyvis` and
`flyvis download-pretrained` (FLYVIS_ROOT_DIR); on Windows it also patches a datamate file lock.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ..connectome import Connectome
from ..sim import Stimulus

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "frontends" / "flyvis"
OUTPUT_TYPES = ("T4a", "T4b", "T4c", "T4d", "T5a", "T5b", "T5c", "T5d", "T2", "T2a", "T3",
                "Tm1", "Tm2", "Tm3", "Tm4", "Tm9", "Tm16", "Tm20", "Tm5a", "Tm5b", "Tm5c",
                "TmY3", "TmY4", "TmY5a", "TmY10", "TmY14", "TmY15")
RATE_PER_UNIT_HZ = 100.0     # 1.0 flyvis activity unit above rest -> 100 Hz (convention, see module docstring)
REST_FRAMES = 10             # the first 100 ms of every stimulus is the grey field: the resting activity
BIN_MS = 10.0                # flyvis runs at 100 Hz
HEX_EXTENT = 15              # flyvis BoxEye default: radius 15 -> 721 columns

# The stimulus vocabulary a task may name. Each is radially symmetric and centred on the eye.
STIMULI: dict[str, dict] = {
    # a dark disc on a grey field expanding with r/v = 40 ms, collision at 1.0 s (task-04 / Ache 2019 geometry)
    "loom":     {"kind": "loom", "duration_s": 1.0, "rv_s": 0.04, "collision_s": 1.0, "contrast": "dark"},
    # the same disc played backwards: OFF edges moving inward — what LPLC2 must not answer (Klapoetke 2017)
    "recede":   {"kind": "recede", "duration_s": 1.0, "rv_s": 0.04, "collision_s": 1.0, "contrast": "dark"},
    # full-field brightening step at 0.2 s (task 11's flash through the eye instead of onto the photoreceptors)
    "flash":    {"kind": "flash", "duration_s": 1.0, "onset_s": 0.2, "level": 1.0},
    # full-field darkening step at 0.2 s
    "dimming":  {"kind": "flash", "duration_s": 1.0, "onset_s": 0.2, "level": 0.0},
}


def available() -> bool:
    try:
        import flyvis  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def cache_path(name: str) -> Path:
    return CACHE_DIR / f"{name}.npz"


def cached(name: str) -> bool:
    return cache_path(name).exists()


# ---------------------------------------------------------------------------------------------
# rendering + simulation (needs flyvis / torch)
# ---------------------------------------------------------------------------------------------

def _patch_datamate_windows() -> None:
    """datamate's h5 writer opens a file, fails, and unlinks it without closing — Windows refuses."""
    import sys
    if sys.platform != "win32":
        return
    import h5py as h5
    import datamate.io as dio
    import datamate.directory as dd

    def _write_h5(path: Path, val) -> None:
        val = np.asarray(val)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        with h5.File(path, libver="latest", mode="w") as f:
            f["data"] = val

    dio._write_h5 = _write_h5
    dd._write_h5 = _write_h5


def render_frames(spec: dict, frame_px: int) -> np.ndarray:
    """(T, 1, H, W) luminance frames in [0, 1] at 100 Hz for one STIMULI entry."""
    T = int(round(spec["duration_s"] * 100))
    fr = np.full((T, 1, frame_px, frame_px), 0.5, np.float32)
    yy, xx = np.mgrid[0:frame_px, 0:frame_px]
    cy = cx = frame_px / 2.0
    r2 = (yy - cy) ** 2 + (xx - cx) ** 2
    if spec["kind"] in ("loom", "recede"):
        level = 0.0 if spec["contrast"] == "dark" else 1.0
        lead = REST_FRAMES if spec["kind"] == "recede" else 0                          # the contracting disc appears after the grey lead-in
        for t in range(lead, T):
            tt = (t / 100.0) if spec["kind"] == "loom" else max(T - 1 - t, 0) / 100.0
            ang = np.arctan(spec["rv_s"] / max(spec["collision_s"] - tt, 0.02))     # half-angle subtended
            rad = min(ang / (np.pi / 2), 1.0) * (frame_px / 2.0)                      # 90 deg -> frame edge
            fr[t, 0][r2 < rad ** 2] = level
    elif spec["kind"] == "flash":
        fr[int(round(spec["onset_s"] * 100)):, 0] = spec["level"]
    else:
        raise ValueError(f"unknown stimulus kind {spec['kind']!r}")
    return fr


def render_to_cache(name: str, network: str = "flow/0000/000") -> Path:
    """Run one named stimulus through the pretrained flyvis network; write per-type per-column
    rates (Hz, 10 ms bins) to the cache. Returns the file written."""
    import torch
    from flyvis import NetworkView
    from flyvis.datasets.rendering import BoxEye
    _patch_datamate_windows()
    spec = STIMULI[name]
    eye = BoxEye(extent=HEX_EXTENT)
    px = int(eye.min_frame_size[0])
    frames = render_frames(spec, px)
    movie = eye(torch.tensor(frames)).squeeze(1).squeeze(1)[None, :, None, :]   # (1, T, 1, 721)
    net = NetworkView(network).init_network()
    act = net.simulate(movie, dt=1.0 / 100).detach().numpy()[0]                  # (T, nodes)
    nodes = net.connectome.nodes
    types = np.array([t.decode() for t in nodes.type[:]])
    u, v = nodes.u[:].astype(int), nodes.v[:].astype(int)
    out: dict[str, np.ndarray] = {}
    columns = None
    for tname in OUTPUT_TYPES:
        m = types == tname
        if not m.any():
            continue
        order = np.lexsort((v[m], u[m]))
        cols = np.stack([u[m][order], v[m][order]], axis=1)
        if columns is None:
            columns = cols
        a = act[:, m][:, order]
        rest = a[:REST_FRAMES].mean(axis=0, keepdims=True)                                # the grey field before the stimulus
        rates = np.maximum(a - rest, 0.0) * RATE_PER_UNIT_HZ                              # (T, columns), Hz above rest
        out[tname] = rates.astype(np.float16)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"stimulus": name, "spec": spec, "network": network, "rate_per_unit_hz": RATE_PER_UNIT_HZ, "bin_ms": BIN_MS,
            "flyvis": __import__("flyvis").__version__, "sha256_frames": hashlib.sha256(frames.tobytes()).hexdigest()}
    np.savez_compressed(cache_path(name), columns=columns, meta=json.dumps(meta), **out)
    return cache_path(name)


# ---------------------------------------------------------------------------------------------
# cache -> stimuli (numpy only)
# ---------------------------------------------------------------------------------------------

def load_cache(name: str) -> tuple[np.ndarray, dict[str, np.ndarray], dict]:
    z = np.load(cache_path(name), allow_pickle=False)
    columns = z["columns"]
    rates = {k: z[k].astype(np.float32) for k in z.files if k not in ("columns", "meta")}
    return columns, rates, json.loads(str(z["meta"]))


def hex_to_xy(columns: np.ndarray) -> np.ndarray:
    """Axial hex (u, v) -> 2-D positions in a unit disc."""
    u, v = columns[:, 0].astype(float), columns[:, 1].astype(float)
    x = u + v / 2.0
    y = v * np.sqrt(3) / 2.0
    xy = np.stack([x, y], axis=1)
    return xy / max(np.abs(xy).max(), 1e-9)


def map_neurons_to_columns(positions: np.ndarray, columns: np.ndarray, seed: int = 0) -> np.ndarray:
    """Assign each neuron (rows of `positions`, one hemisphere of one type) to a flyvis column:
    project the somata onto their first two principal axes, normalise to the unit disc, take the
    nearest column centre. INFERRED retinotopy, up to rotation and flip. Neurons with no position
    are spread over columns at random (seeded)."""
    n = positions.shape[0]
    hex_xy = hex_to_xy(columns)
    ok = np.isfinite(positions).all(axis=1)
    out = np.zeros(n, dtype=np.int64)
    rng = np.random.default_rng(seed)
    if ok.sum() >= 3:
        P = positions[ok] - positions[ok].mean(axis=0)
        _, _, vt = np.linalg.svd(P, full_matrices=False)
        proj = P @ vt[:2].T
        proj = proj / max(np.abs(proj).max(), 1e-9)
        d = ((proj[:, None, :] - hex_xy[None, :, :]) ** 2).sum(axis=2)
        out[ok] = d.argmin(axis=1)
    if (~ok).any():
        out[~ok] = rng.integers(0, len(columns), size=int((~ok).sum()))
    return out


def stimuli_from_cache(c: Connectome, name: str, t_start_ms: float, scale: float = 1.0, seed: int = 0) -> tuple[list[Stimulus], dict[str, int]]:
    """One Stimulus per driven cell type present in `c`, each with a per-neuron rate time course
    (Hz, 10 ms bins) taken from that neuron's column. Both hemispheres get the same movie.
    Returns the stimuli and {type: n_neurons} for the report."""
    columns, rates, _meta = load_cache(name)
    stims: list[Stimulus] = []
    sizes: dict[str, int] = {}
    ann = c.annotations
    side_col = ann["side"].astype(str).str.lower().str[:1] if "side" in ann.columns else None
    for tname, series in rates.items():                       # series: (T, columns)
        idx = c.select({"cell_type": tname})
        if idx.size == 0:
            continue
        sizes[tname] = int(idx.size)
        per_neuron = np.zeros((idx.size, series.shape[0]), dtype=np.float32)
        sides = side_col.iloc[idx].to_numpy() if side_col is not None else np.array([""] * idx.size)
        for s in np.unique(sides):
            sel = np.flatnonzero(sides == s)
            col_of = map_neurons_to_columns(c.positions[idx[sel]].astype(float), columns, seed=seed)
            per_neuron[sel] = series[:, col_of].T * scale
        stims.append(Stimulus(neurons=idx, rate_hz=float(per_neuron.mean()), t_start_ms=t_start_ms,
                              t_end_ms=t_start_ms + series.shape[0] * BIN_MS, name=f"{name}:{tname}",
                              rate_series_hz=per_neuron, series_bin_ms=BIN_MS))
    return stims, sizes
