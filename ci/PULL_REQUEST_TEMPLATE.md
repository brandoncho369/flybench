<!-- Pick one section, delete the others. CI validates the files; a maintainer re-runs results before they are marked verified. -->

## Result submission
- Label (as in the JSON): 
- Connectome + Codex data version (e.g. FlyWire v783, Connections (Filtered), July 2025): 
- What you changed vs. the reference model, in one or two sentences: 
- Command used (e.g. `flybench run -c flywire783 --gain 0.42 --seeds 3 -o results/….json --label "…"`): 
- [ ] I did **not** tune any per-neuron parameter to pass a task.

## New task
- Behaviour and the paper(s) it comes from: 
- `flybench lint` passes and the task runs on the toy (`flybench run -t tasks/….yaml`): [ ]
- Tier (`core` if the reference LIF passes it, `hard` if not) and why: 

## Model / simulator
- Import path (`module:Class`) and how to install it: 
- What it adds over LIF: 
- Reference scores with `--seeds 3` attached under `results/`: [ ]
