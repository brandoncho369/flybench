# RFC: task NN — <one-line behaviour>

Status: pre-registered <date>, before the first run on any dataset.

## The behaviour
What the real fly does, with the citations and the numbers (mean, sd, n where the paper gives them).

## What the task measures
Stimulus (which cell types, what drive, and the provenance tag of every choice: MEASURED /
INFERRED / MODELED / CONVENTION), readout, checks. Say which checks are null checks ("X must not
happen"): a dead network passes those.

## Pre-registered predictions
For the reference LIF at its window, the adaptive LIF, MaleCNS at 0.65, and the `rewired`
control. Written before running. A surprise here is the interesting outcome, not a mistake.

## What would make this task wrong
Annotation the dataset might lack (→ `requires_readouts` / `requires_stimuli`), a convention that
could be doing the work, a known confound.
