# RFC M1: terminal-aware LIF — an input on the axon does not fire the cell

Status: pre-registered 2026-09-20, before the scored run. A **mechanism** RFC, admitted under the
"task before mechanism" rule by task 35's failed check 2 (docs/rfcs/35): the reference point-neuron
LIF lets brain-side axo-axonic inputs fire ascending neurons backwards into the nerve cord.
**Disclosure:** the mechanism was checked on the one condition it was built for before this RFC
was written — with every DN silenced, ascending neurons 0 Hz and TTMn 0.0 (reference: 3.4 Hz,
2.5 spikes/neuron), and with only the GF silenced TTMn 1.5 spikes/neuron (reference 4.5), single
seed. Everything else below is predicted blind.

## The mechanism

`flybench/models/terminal_lif.py`. Per connection onto a neck-spanning neuron (ascending,
descending, sensory-ascending/descending, efferent), neuPrint records how many synapses fall in
each ROI; the post-synapses on the neuron's axon side are its terminal (axo-axonic) inputs —
MEASURED, `flybench fetch-terminals`, 555,960 synapses on MaleCNS v1.0 (11.6 % of the ascending
classes' input, 4.9 % of the descending classes'; 0.62 % of all synapses). Those synapses are
removed from the somatic input and instead modulate the receiving neuron's release: inhibitory
terminal drive scales release linearly to a floor of 0.3 over one threshold distance (Olsen &
Wilson 2008, Nature 452:956, ~70 % reduction under GABA-B presynaptic inhibition — a different
synapse, so CONVENTION here); excitatory terminal drive is ignored rather than invented. Without
terminal data (FlyWire, the toy, every shuffled control) the model is the reference LIF bit for
bit. Open division, no free parameters.

## Predictions (MaleCNS v1.0, gain 0.65, 3 seeds, `rewired` control; row "Terminal LIF 0.65 (MaleCNS)")

- **Task 35** (the target): check 2 (`gf_all_dn_off` abolished) **passes**; the other nine
  unchanged — with the caveat that the GF-free route is weaker without antidromic AN drive
  (1.5 vs 4.5 spikes/neuron at seed 0), so a "survives" check may fail on a low seed. Prediction:
  **10/10**, the first model to pass the task; if a survives-check fails, 9/10 with check 2 now
  the one that passes.
- **Tasks 33 and 34**: unchanged pass/fail (33: 3/4, 34: 6/6). The loom convention's route to
  TTMn is DN → dendrite; the flash's GF route is unaffected; the eye loom's GF-free route is
  weaker but present.
- **Every other MaleCNS task (1–31 as applicable)**: identical pass/fail. The only change to a
  brain-side readout comes through ascending neurons' brain terminals, and ANs now fire less
  (AN rate halves under the eye loom); the brain-only reflexes do not run through ANs. Graded
  score within ±0.01 of the reference's 0.660; specificity within ±0.02.
- **The shuffled control** carries no terminal matrix, so on it this model *is* the reference:
  control scores identical to the reference row's.
- **FlyWire**: bit-identical to the reference (no terminal data). Not run; the reference row
  stands for it, and this RFC says so rather than adding a duplicate row.

## What would make this wrong

- **Excitatory axo-axonic contacts are ignored.** If DN → AN brain-side contacts are mostly
  cholinergic and facilitate release, ANs should fire *more* in the cord under brain drive,
  not the same; the model errs toward silence.
- **The floor and slope** come from one olfactory synapse; presynaptic inhibition at neck
  terminals is not measured. Different constants change how much the ANs are damped, not whether
  brain input can fire them (it cannot, under any constants).
- **Only neck-spanning neurons are treated.** Within-brain and within-cord axo-axonic contacts
  (a large fraction of all inhibitory synapses) still sum into the soma; a synapse-position
  table would extend the same rule to every neuron. That is the next data step, not this one.
- **Toy**: no sides, no terminal matrix; the toy runs the reference dynamics. A unit test builds
  a three-neuron connectome with one terminal synapse and checks that the terminal input does not
  fire the cell and does scale its release.

## Outcome (2026-09-20, MaleCNS v1.0, gain 0.65, 3 seeds, `rewired` control; row "Terminal LIF 0.65 (MaleCNS)")

| | reference LIF | terminal-aware LIF | predicted |
|---|---|---|---|
| task 35 | 9/10 (check 2 fails) | **10/10** — check 2 passes (all DNs silenced → TTMn 0.0); every "survives" check holds at 1.0–1.8 spikes/neuron | 10/10 ✓ (thin margins, as warned) |
| task 34 | 6/6 | 6/6 (eye loom: TTMn 1.5, takeoff 499 ms; convention loom: 14.8) | unchanged ✓ |
| task 33 | 3/4 | 3/4 (the flash jump now on 1 of 3 seeds, still a fail under the every-seed rule) | unchanged ✓ |
| tasks 1–31 as applicable | | **three tasks improved, none worsened**; 27 identical | "identical pass/fail" ✗ |
| core · hard · graded · specificity | 0.567 · 0.574 · 0.660 · +0.218 | 0.567 · **0.613** · **0.669** · **+0.252** | graded ±0.01 ✓, spec ±0.02 ✗ |
| control scores | | identical on 33 of 33 tasks (no terminal data on the shuffle) | ✓ |
| wall-clock (3 workers) | 4,930 s | 1,985 s | – |

The target held: with axo-axonic inputs kept off the soma, silencing every descending neuron
silences the nerve cord, and the terminal-aware LIF is the first model to pass task 35. The
GF-free loom route is thinner without antidromic AN drive (1.5 spikes/neuron at the low seed)
but present on every seed, as predicted.

**The wrong prediction is the informative one.** Three older MaleCNS tasks changed, all for the
better, with identical control scores:

- **task 20 `taste_modalities`, 2/4 → 4/4.** High salt → MN9 went from 183 Hz (the seed-bistable
  ignition of 2026-09-14: 273 / 0.9 / 275 Hz) to **0 Hz on every seed**, and sugar + high salt now
  halves the sugar response (ratio 1.04 → 0.00). Ascending neurons terminate in the
  gnathal/subesophageal region, where the labellar taste circuit lives; in the point-neuron model
  the high-salt drive reached those terminals, fired the ANs, and their SEZ outputs helped ignite
  MN9. The "MaleCNS's taste circuit is a hair-trigger at 0.65" finding of docs/MALECNS.md is in
  part this artefact: with the ANs' brain-side inputs where they belong, the null holds.
- **task 24 `optic_flow_rotation`, 3/6 → 4/6.** DNp15_L's response to rightward yaw rose from 14
  to 81 Hz and now exceeds its forward-translation response (ratio 0.37 → 2.23).
- **task 23 `leg_mn_size_principle`, 0/3 → 1/3.** Recruitment spread 114 → 121 ms across the
  50 ms line; the rank order is still inverted (−0.78).

Not tuned to any of these: the mechanism has no free parameters, was built for task 35, and the
RFC predicted no change elsewhere. That three unrelated tasks moved toward the fly when 0.6 % of
synapses were moved off the soma says how much of a whole-CNS point-neuron model's behaviour was
ascending neurons firing backwards. The controls did not move at all, so none of the gain is
"more activity": the network has *fewer* spikes (1.26 M vs 1.34 M per condition) and the same
peak active fraction (23 %).

Open: within-brain and within-cord axo-axonic contacts still sum into the soma. A synapse-position
table would extend the rule to every neuron; the datasets have the positions and the cache does
not yet carry them.
