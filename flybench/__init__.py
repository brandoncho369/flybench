"""flybench — a reflex benchmark for whole-brain fruit fly connectome simulations.

The idea: a connectome is a wiring diagram, not a working brain. Everyone who
drops one into a leaky integrate-and-fire model has to make choices (weights,
gain, which neurotransmitters are inhibitory, ...). flybench asks the only
question that keeps those choices honest: *does the simulated fly still do the
things a real fly is known to do?*
"""

from .connectome import Connectome, load_connectome, select
from .sim import LIFParams, LIFSimulator, Stimulus

__all__ = [
    "Connectome",
    "load_connectome",
    "select",
    "LIFParams",
    "LIFSimulator",
    "Stimulus",
]

__version__ = "0.1.0"
