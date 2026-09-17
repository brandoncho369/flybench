"""Sensory front ends: published models that turn a stimulus into the rates of the cell types it
would drive, replacing the "100 Hz on the cells a stimulus would drive" convention.

A task's stimulus may say `frontend: flyvis` (docs/ROADMAP.md item 44); the run then needs either
the front end's cached output (`data/frontends/<name>/*.npz`, committed) or the front end itself.
`task_unavailable` skips a task whose front end is neither cached nor importable.
"""

from __future__ import annotations

FRONTENDS = ("flyvis",)
