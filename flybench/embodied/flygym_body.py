"""NeuroMechFly (FlyGym 2.x, Lobato-Rios et al. 2022; Wang-Chen et al. 2024) as the body.

The transducer: a jump command makes the body extend both middle legs — the tergotrochanteral
muscle's job (Trimarchi & Schneiderman 1995: the TTM extends the mesothoracic legs and the fly
leaves the substrate) — by a fixed program on the position actuators, then return to standing.
Nothing in the program depends on the brain except *when* it runs.

    JUMP_EXTENSION_RAD  +1.0 rad on the middle legs' trochanter–femur and femur–tibia pitch
    JUMP_RISE_MS        5 ms ramp to the extended pose        (CONVENTION: the MuJoCo actuators
    JUMP_HOLD_MS        20 ms held                              are force-limited; this program
    JUMP_RETURN_MS      50 ms ramp back to standing             lifts the thorax ~0.7 mm and
    TAKEOFF_WINDOW_MS   30 ms: all six feet off the ground      every foot leaves the ground
                        within this of the command = takeoff    ~6 ms after the command)

A command that arrives while a program is running is ignored (one jump per program; the GF fires
at hundreds of Hz in the reference model, the real fly jumps once). Takeoff is a *physics* event:
the ground-contact sensors of all six legs read zero. Latency is measured from the condition's
stimulus onset to that event.

Cost: the body is only stepped from the first command to the end of the last program plus the
takeoff window — a brain that never commands costs no body time — at MuJoCo's 0.1 ms step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

JUMP_EXTENSION_RAD = 1.0
JUMP_RISE_MS = 5.0
JUMP_HOLD_MS = 20.0
JUMP_RETURN_MS = 50.0
PROGRAM_MS = JUMP_RISE_MS + JUMP_HOLD_MS + JUMP_RETURN_MS
TAKEOFF_WINDOW_MS = 30.0
JUMP_DOFS = ("lm_trochanterfemur_pitch", "lm_tibia_pitch", "rm_trochanterfemur_pitch", "rm_tibia_pitch")
DT_S = 1e-4
SETTLE_MS = 200.0      # the fly is dropped 0.7 mm onto the ground and left to stand before anything else
FLY_NAME = "nmf"


def available() -> bool:
    try:
        import flygym  # noqa: F401
        import mujoco  # noqa: F401
    except Exception:
        return False
    return True


@dataclass
class BodyTrace:
    takeoff: bool
    takeoff_ms: float                 # absolute sim time of takeoff (ms), NaN if none
    n_commands: int                   # commands accepted (not during a running program)
    thorax_rise_mm: float
    commands_ms: list[float] = field(default_factory=list)


_BODY = None


def _build():
    """Compile the fly once per process; runs reset it."""
    global _BODY
    if _BODY is not None:
        return _BODY
    from flygym import Simulation
    from flygym.anatomy import ActuatedDOFPreset, AxisOrder, ContactBodiesPreset, JointPreset, Skeleton
    from flygym.compose import FlatGroundWorld, KinematicPosePreset, NeuroMechFly
    from flygym.compose.fly.base_fly import ActuatorType
    from flygym.utils.math import Rotation3D

    fly = NeuroMechFly(name=FLY_NAME)
    skeleton = Skeleton(joint_preset=JointPreset.LEGS_ACTIVE_ONLY, axis_order=AxisOrder.ROLL_PITCH_YAW)
    neutral = KinematicPosePreset.NEUTRAL
    fly.add_joints(skeleton, neutral_pose=neutral)
    dofs = skeleton.get_actuated_dofs_from_preset(ActuatedDOFPreset.LEGS_ACTIVE_ONLY)
    fly.add_actuators(dofs, actuator_type="position", neutral_input=neutral, kp=50)
    world = FlatGroundWorld()
    world.add_fly(fly, [0, 0, 0.7], Rotation3D(format="quat", values=[1, 0, 0, 0]),
                  bodysegs_with_ground_contact=ContactBodiesPreset.LEGS_THORAX_ABDOMEN_HEAD)
    sim = Simulation(world, timestep=DT_S)
    order = fly.get_actuated_jointdofs_order(ActuatorType.POSITION)
    names = [f"{d.child.name}_{d.axis.value}" for d in order]
    na = fly.jointdof_to_neutralaction_by_type[ActuatorType.POSITION]
    neutral_in = np.array([na[d] for d in order], dtype=float)
    jump_idx = np.array([names.index(n) for n in JUMP_DOFS])
    thorax = [s.name for s in fly.get_bodysegs_order()].index("c_thorax")
    _BODY = {"sim": sim, "neutral": neutral_in, "jump_idx": jump_idx, "thorax": thorax, "ActuatorType": ActuatorType}
    return _BODY


def _pose_at(dt_ms: float, neutral: np.ndarray, jump_idx: np.ndarray) -> np.ndarray:
    """Actuator targets `dt_ms` after a command: rise, hold, return."""
    if dt_ms < JUMP_RISE_MS:
        f = dt_ms / JUMP_RISE_MS
    elif dt_ms < JUMP_RISE_MS + JUMP_HOLD_MS:
        f = 1.0
    elif dt_ms < PROGRAM_MS:
        f = 1.0 - (dt_ms - JUMP_RISE_MS - JUMP_HOLD_MS) / JUMP_RETURN_MS
    else:
        f = 0.0
    out = neutral.copy()
    out[jump_idx] += f * JUMP_EXTENSION_RAD
    return out


def accepted_commands(spike_times_ms: np.ndarray, t_from_ms: float = 0.0) -> list[float]:
    """Command times the program accepts: the first spike, then the first spike after each program ends."""
    out: list[float] = []
    for t in np.sort(np.asarray(spike_times_ms, dtype=float)):
        if t < t_from_ms:
            continue
        if not out or t >= out[-1] + PROGRAM_MS:
            out.append(float(t))
    return out


def run_body(command_times_ms: list[float], duration_ms: float) -> BodyTrace:
    """Stand the fly, run the jump program at each accepted command, report takeoff."""
    cmds = accepted_commands(np.asarray(command_times_ms, dtype=float))
    if not cmds:
        return BodyTrace(False, float("nan"), 0, 0.0, [])
    b = _build()
    sim, neutral, jump_idx, ith, AT = b["sim"], b["neutral"], b["jump_idx"], b["thorax"], b["ActuatorType"]
    sim.reset()
    step_ms = DT_S * 1000.0
    for _ in range(int(SETTLE_MS / step_ms)):
        sim.set_actuator_inputs(FLY_NAME, AT.POSITION, neutral)
        sim.step()
    z0 = float(sim.get_body_positions(FLY_NAME)[ith, 2])
    # body time runs from the first command (the standing fly does nothing before it) to the end
    # of the last program plus the takeoff window, clipped to the brain's duration
    t_start = cmds[0]
    t_end = min(duration_ms, cmds[-1] + PROGRAM_MS + TAKEOFF_WINDOW_MS)
    n = int(np.ceil((t_end - t_start) / step_ms))
    takeoff_ms = float("nan")
    rise = 0.0
    ci = 0
    for k in range(n):
        t = t_start + k * step_ms
        while ci + 1 < len(cmds) and cmds[ci + 1] <= t:
            ci += 1
        sim.set_actuator_inputs(FLY_NAME, AT.POSITION, _pose_at(t - cmds[ci], neutral, jump_idx))
        sim.step()
        z = float(sim.get_body_positions(FLY_NAME)[ith, 2])
        rise = max(rise, z - z0)
        if np.isnan(takeoff_ms) and t - cmds[ci] <= TAKEOFF_WINDOW_MS:
            if not np.any(sim.get_ground_contact_info(FLY_NAME)[0]):
                takeoff_ms = t
    return BodyTrace(bool(np.isfinite(takeoff_ms)), takeoff_ms, len(cmds), rise, cmds)


# ---------------------------------------------------------------------------------------------
# A steppable body with eyes and a world object, for the closed loop (flybench.embodied.closed_loop)
# ---------------------------------------------------------------------------------------------

BALL_RGBA = (0.0, 0.0, 0.0, 1.0)     # a black object on FlyGym's white sky and dark ground


class Body:
    """NeuroMechFly with compound eyes and one kinematic ball in its world. `reset()` stands the fly
    up; `step(program_dt_ms)` advances 0.1 ms with the jump program at that phase (None = standing
    pose); `eyes()` renders both retinas; `set_ball(xyz)` moves the object. Built once per process
    with the ball present (a compiled MuJoCo model cannot gain bodies), parked far away when unused."""

    PARK = (1000.0, 1000.0, 1000.0)

    def __init__(self, ball_radius_mm: float = 2.0):
        import mujoco
        from flygym import Simulation
        from flygym.anatomy import ActuatedDOFPreset, AxisOrder, ContactBodiesPreset, JointPreset, Skeleton
        from flygym.compose import FlatGroundWorld, KinematicPosePreset, NeuroMechFly
        from flygym.compose.fly.base_fly import ActuatorType
        from flygym.utils.math import Rotation3D
        fly = NeuroMechFly(name=FLY_NAME)
        skeleton = Skeleton(joint_preset=JointPreset.LEGS_ACTIVE_ONLY, axis_order=AxisOrder.ROLL_PITCH_YAW)
        neutral = KinematicPosePreset.NEUTRAL
        fly.add_joints(skeleton, neutral_pose=neutral)
        fly.add_actuators(skeleton.get_actuated_dofs_from_preset(ActuatedDOFPreset.LEGS_ACTIVE_ONLY), actuator_type="position", neutral_input=neutral, kp=50)
        fly.add_vision()
        world = FlatGroundWorld()
        b = world.mjcf_root.worldbody.add_body(name="ball", pos=list(self.PARK), mocap=True)
        b.add_geom(name="ball_geom", type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[ball_radius_mm, 0, 0], rgba=list(BALL_RGBA), contype=0, conaffinity=0)
        world.add_fly(fly, [0, 0, 0.7], Rotation3D(format="quat", values=[1, 0, 0, 0]), bodysegs_with_ground_contact=ContactBodiesPreset.LEGS_THORAX_ABDOMEN_HEAD)
        self.sim = Simulation(world, timestep=DT_S)
        self.AT = ActuatorType
        order = fly.get_actuated_jointdofs_order(ActuatorType.POSITION)
        names = [f"{d.child.name}_{d.axis.value}" for d in order]
        na = fly.jointdof_to_neutralaction_by_type[ActuatorType.POSITION]
        self.neutral = np.array([na[d] for d in order], dtype=float)
        self.jump_idx = np.array([names.index(n) for n in JUMP_DOFS])
        segs = [s.name for s in fly.get_bodysegs_order()]
        self.thorax = segs.index("c_thorax"); self.head = segs.index("c_head")
        self.mocap_id = int(mujoco.mj_name2id(self.sim.mj_model, mujoco.mjtObj.mjOBJ_BODY, "ball"))
        self.mocap_index = int(self.sim.mj_model.body_mocapid[self.mocap_id])
        self.radius = ball_radius_mm
        self.z0 = None

    @property
    def retina(self):
        if self.sim.retina is None:
            self.sim.get_raw_vision(FLY_NAME)      # lazily builds the retina and the eye renderer
        return self.sim.retina

    def set_ball(self, xyz) -> None:
        self.sim.mj_data.mocap_pos[self.mocap_index] = np.asarray(xyz, dtype=float)

    def reset(self) -> None:
        self.sim.reset()
        self.set_ball(self.PARK)
        for _ in range(int(SETTLE_MS / (DT_S * 1000.0))):
            self.step(None)
        self.z0 = self.thorax_z()

    def step(self, program_dt_ms: float | None) -> None:
        pose = self.neutral if program_dt_ms is None else _pose_at(program_dt_ms, self.neutral, self.jump_idx)
        self.sim.set_actuator_inputs(FLY_NAME, self.AT.POSITION, pose)
        self.sim.step()

    def thorax_z(self) -> float:
        return float(self.sim.get_body_positions(FLY_NAME)[self.thorax, 2])

    def head_xyz(self) -> np.ndarray:
        """The point between the two eye cameras, in world coordinates (what the object approaches)."""
        import mujoco
        m, d = self.sim.mj_model, self.sim.mj_data
        cams = [i for i in range(m.ncam) if "eye" in (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_CAMERA, i) or "")]
        return np.asarray(d.cam_xpos[cams].mean(axis=0), dtype=float) if cams else np.asarray(self.sim.get_body_positions(FLY_NAME)[self.head], dtype=float)

    def on_ground(self) -> bool:
        return bool(np.any(self.sim.get_ground_contact_info(FLY_NAME)[0]))

    def eyes(self) -> np.ndarray:
        """(2, 721, 2) ommatidia readouts, left then right."""
        return self.sim.get_ommatidia_readouts(FLY_NAME)


_LIVE_BODY: Body | None = None


def live_body(ball_radius_mm: float = 2.0) -> Body:
    global _LIVE_BODY
    if _LIVE_BODY is None or _LIVE_BODY.radius != ball_radius_mm:
        _LIVE_BODY = Body(ball_radius_mm)
    return _LIVE_BODY
