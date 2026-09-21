"""The closed loop (Phase 7b, docs/rfcs/36): the body's eyes → flyvis → connectome → TTMn → the body.

Every 0.1 ms the brain and the body step together. Every 10 ms the body's two retinas are
rendered, run through flyvis (stateful, one frame), and the resulting rates of the connectome's own
optic-lobe cells set their spike probabilities for the next 10 ms. A spike of the command readout
(TTMn, or the GF plus the measured GF → TTM delay) starts the jump program on the body, which
changes what the eyes see next. An object in the world moves on a kinematic path the task
declares; contact with the fly is disabled, so the object passes through a fly that did not move.

What closes here: vision → brain → legs → vision. What does not: proprioception, wind, the
halteres; the brain's other senses see nothing. The object is a black sphere; the sky is white
and the ground dark, as FlyGym renders them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..connectome import Connectome
from ..sim import LIFParams, SimResult
from .flygym_body import DT_S, PROGRAM_MS, TAKEOFF_WINDOW_MS, live_body
from .vision import FRAME_S, LiveEye, available

WORLDS = ("approach", "pass_by", "static")


@dataclass
class LoopSpec:
    world: str = "approach"           # approach | pass_by | static
    radius_mm: float = 2.0            # object radius
    speed_mm_s: float = 50.0          # approach speed (r/v = radius / speed; 2 mm at 50 mm/s = 40 ms, task 4's geometry)
    start_mm: float = 60.0            # starting distance ahead of the head
    lateral_mm: float = 10.0          # pass_by: lateral offset of the path (misses the fly)
    t_start_ms: float = 200.0         # the object appears (approach/static) or starts moving

    @classmethod
    def from_dict(cls, d: dict) -> "LoopSpec":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def collision_ms(self) -> float:
        return self.t_start_ms + 1000.0 * (self.start_mm - self.radius_mm) / self.speed_mm_s


@dataclass
class LoopTrace:
    takeoff: bool
    takeoff_ms: float
    n_commands: int
    thorax_rise_mm: float
    collision_ms: float
    min_distance_mm: float
    frames: int
    driven: int
    commands_ms: list[float] = field(default_factory=list)


def _object_xyz(spec: LoopSpec, head: np.ndarray, t_ms: float) -> np.ndarray:
    """The object's position at time t: ahead of the eyes along +x (the fly faces +x in FlyGym; the eye
    cameras look forward-left and forward-right), at eye height."""
    ahead = np.array([1.0, 0.0, 0.0])
    if spec.world == "static" or t_ms < spec.t_start_ms:
        d = spec.start_mm
    else:
        d = max(spec.start_mm - spec.speed_mm_s * (t_ms - spec.t_start_ms) / 1000.0, -spec.start_mm)
    pos = head + ahead * d
    if spec.world == "pass_by":
        pos = pos + np.array([0.0, spec.lateral_mm, 0.0])
    return pos


def run_closed_loop(c: Connectome, params: LIFParams, simulator_cls, spec: LoopSpec, duration_ms: float,
                    command_neurons: np.ndarray, command_delay_ms: float = 0.0, seed: int = 0) -> tuple[SimResult, LoopTrace]:
    if not available():
        raise RuntimeError("closed loop needs flygym, flyvis and torch (pip install -e .[embodied,flyvis])")
    body = live_body(spec.radius_mm)
    body.reset()
    head = body.head_xyz()
    body.set_ball(_object_xyz(spec, head, 0.0) if spec.world != "static" else _object_xyz(spec, head, 0.0))
    body.step(None)
    eye = LiveEye(c, body.retina, seed=seed)
    eye.settle(body.eyes())
    sim = simulator_cls(c, params)
    sim.reset()
    dt = params.dt_ms
    per_ms = dt / 1000.0
    steps_per_frame = int(round(FRAME_S * 1000.0 / dt))
    n_steps = int(round(duration_ms / dt))
    cmd_mask = np.zeros(c.n, dtype=bool); cmd_mask[command_neurons] = True
    pending: list[float] = []            # command times (ms) after the delay
    cmds: list[float] = []
    program_t0: float | None = None
    takeoff_ms = float("nan"); rise = 0.0; min_d = float("inf")
    times: list[np.ndarray] = []; ids: list[np.ndarray] = []
    neurons = np.empty(0, dtype=int); prob = np.empty(0, dtype=np.float32)
    frames = 0
    for k in range(n_steps):
        t = k * dt
        if k % steps_per_frame == 0:
            neurons, rates = eye.frame(body.eyes())
            prob = rates * per_ms
            frames += 1
        forced = neurons[sim.rng.random(neurons.size) < prob] if neurons.size else None
        fired = sim.step(forced)
        if fired.size:
            times.append(np.full(fired.size, sim.t, dtype=np.float32)); ids.append(fired.astype(np.int32))
            if cmd_mask[fired].any():
                pending.append(sim.t + command_delay_ms)
        # commands whose delay has elapsed start the program (one per program)
        while pending and pending[0] <= sim.t:
            tc = pending.pop(0)
            if program_t0 is None or tc >= program_t0 + PROGRAM_MS:
                program_t0 = tc; cmds.append(tc)
        phase = None if program_t0 is None or sim.t - program_t0 >= PROGRAM_MS else sim.t - program_t0
        obj = _object_xyz(spec, head, sim.t)
        body.set_ball(obj)
        body.step(phase)
        min_d = min(min_d, float(np.linalg.norm(obj - body.head_xyz())))
        rise = max(rise, body.thorax_z() - body.z0)
        if np.isnan(takeoff_ms) and program_t0 is not None and sim.t - program_t0 <= TAKEOFF_WINDOW_MS and not body.on_ground():
            takeoff_ms = sim.t
    st = np.concatenate(times) if times else np.empty(0, dtype=np.float32)
    si = np.concatenate(ids) if ids else np.empty(0, dtype=np.int32)
    res = SimResult(spike_times_ms=st, spike_neurons=si, duration_ms=duration_ms, n=c.n)
    return res, LoopTrace(bool(np.isfinite(takeoff_ms)), takeoff_ms, len(cmds), float(rise), spec.collision_ms(), float(min_d), frames, eye.n_driven, cmds)
