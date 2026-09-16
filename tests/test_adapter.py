"""The adapter contract (flybench.adapter): the reference simulators conform; deliberately broken
adapters are reported by defect name."""
import numpy as np
import pytest

from flybench.adapter import CAPABILITIES, SimulatorAdapter, verify_adapter
from flybench.connectome import load_connectome
from flybench.models.adaptive_lif import AdaptiveLIFSimulator
from flybench.sim import LIFParams, LIFSimulator, SimResult


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    return load_connectome("toy", tmp_path_factory.mktemp("cache"))


def test_reference_simulators_conform(toy):
    for sim in (LIFSimulator, AdaptiveLIFSimulator):
        rep = verify_adapter(sim, toy)
        assert rep.ok, [d.name for d in rep.defects]
        assert rep.capabilities == ["can_silence"] and rep.spikes_per_second > 0
    assert isinstance(LIFSimulator(toy), SimulatorAdapter)      # registered as a virtual subclass
    assert set(CAPABILITIES) == {"can_silence"}


def _names(rep):
    return [d.name for d in rep.defects]


def test_broken_adapters_are_named(toy):
    # a duck-typed adapter with no `capabilities` attribute (a subclass would inherit the parent's)
    class Duck:
        def __init__(self, c, p=None):
            self.inner = LIFSimulator(c, p)
        def run(self, d, s=None):
            return self.inner.run(d, s)
    assert "capabilities_missing" in _names(verify_adapter(Duck, toy))

    class UnknownCap(LIFSimulator):
        capabilities = frozenset({"can_fly"})
    assert "capabilities_unknown" in _names(verify_adapter(UnknownCap, toy))

    class WrongType(LIFSimulator):
        def run(self, d, s=None, **k):
            r = super().run(d, s, **k)
            return (r.spike_times_ms, r.spike_neurons)
    assert "result_type" in _names(verify_adapter(WrongType, toy))

    class OutOfRange(LIFSimulator):
        def run(self, d, s=None, **k):
            r = super().run(d, s, **k)
            return SimResult(spike_times_ms=r.spike_times_ms + np.float32(d), spike_neurons=r.spike_neurons, duration_ms=d, n=r.n)
    assert "spike_times_range" in _names(verify_adapter(OutOfRange, toy))

    class SeedBlind(LIFSimulator):
        def __init__(self, c, p=None):
            p = LIFParams(**{**(p.__dict__ if p else {}), "seed": 0})
            super().__init__(c, p)
    assert "seed_ignored" in _names(verify_adapter(SeedBlind, toy))

    class Deaf(LIFSimulator):
        def run(self, d, s=None, **k):
            return super().run(d, [], **k)
    assert "stimulus_ignored" in _names(verify_adapter(Deaf, toy))

    class NoRamp(LIFSimulator):
        def run(self, d, s=None, **k):
            from flybench.sim import Stimulus
            flat = [Stimulus(neurons=x.neurons, rate_hz=x.rate_hz, t_start_ms=x.t_start_ms, t_end_ms=x.t_end_ms) for x in (s or [])]
            return super().run(d, flat, **k)
    assert "ramp_ignored" in _names(verify_adapter(NoRamp, toy))

    class Leaky(LIFSimulator):
        def run(self, d, s=None, **k):
            return super().run(d, s, reset=(self.t == 0.0))
    assert "state_leaks" in _names(verify_adapter(Leaky, toy))

    class Hoarder(LIFSimulator):
        """reads weights from a private copy of the original connectome, so silencing does nothing"""
        capabilities = frozenset({"can_silence"})
        def __init__(self, c, p=None):
            super().__init__(toy, p)
    assert "can_silence_false" in _names(verify_adapter(Hoarder, toy))
