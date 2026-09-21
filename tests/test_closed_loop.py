"""Phase 7b: the closed loop's pieces (eye -> flyvis mapping, object path) and, with the stack installed, one loop on the toy."""
import numpy as np
import pytest

from flybench.embodied.closed_loop import LoopSpec, _object_xyz
from flybench.embodied.vision import available


def test_object_path_geometry():
    s = LoopSpec(world="approach", radius_mm=2.0, speed_mm_s=50.0, start_mm=60.0, t_start_ms=200)
    head = np.array([0.5, 0.0, 1.2])
    assert np.allclose(_object_xyz(s, head, 0.0), head + [60, 0, 0])           # parked ahead before it moves
    assert np.allclose(_object_xyz(s, head, 1200.0), head + [10, 0, 0])        # 50 mm in one second
    assert s.collision_ms() == pytest.approx(200 + 1000 * 58 / 50)             # contact when the surface reaches the eyes
    miss = LoopSpec(world="pass_by", lateral_mm=10.0)
    assert np.allclose(_object_xyz(miss, head, 1360.0)[1], 10.0)               # the miss path is 10 mm to the side
    assert np.allclose(_object_xyz(LoopSpec(world="static"), head, 1400.0), head + [60, 0, 0])


@pytest.mark.skipif(not available(), reason="closed loop needs flygym, flyvis and torch")
def test_eye_maps_one_to_one_onto_flyvis():
    from flyvis.datasets.rendering import BoxEye
    from flygym.vision.retina import Retina
    from flybench.embodied.vision import ommatidia_to_receptors
    rc = BoxEye(extent=15).receptor_centers
    rc = rc.numpy() if hasattr(rc, "numpy") else np.asarray(rc)
    left, right = ommatidia_to_receptors(Retina(), rc)
    assert left.shape == right.shape == (721,)
    assert len(set(right.tolist())) == 721 and len(set(left.tolist())) == 721   # a bijection, both eyes


@pytest.mark.skipif(not available(), reason="closed loop needs flygym, flyvis and torch")
def test_toy_loop_runs_and_the_object_is_seen():
    from flybench.bench import load_tasks, run_task
    from flybench.connectome import load_connectome
    from flybench.sim import LIFParams
    toy = load_connectome("toy")
    task = next(t for t in load_tasks() if t["name"] == "closed_loop_escape")
    task = {**task, "conditions": {"approach": task["conditions"]["approach"]}, "checks": task["checks"][:2]}
    r = run_task(task, toy, LIFParams(gain=1.0, seed=0))
    m = r.measurements["approach"]
    assert r.stimulus_sizes["eyes[approach]"] == 192 and m["min_distance_mm"] < 1.0 and m["collision_ms"] == pytest.approx(1160.0)
    assert m["rate[lplc2]"] > 0            # the toy's detectors saw the object
