# RFC: task 31 — Foxglove and Bluebell switch the walking commands off; sugar switches Foxglove on

Status: pre-registered 2026-09-15, before the first run on any dataset. Synapse counts from the
wiring; no simulation was run.

## The behaviour

Sapkal et al. 2024 (Nature 634:191) screened for neurons whose activation halts a walking fly
and found two mechanisms. "Walk-OFF": the GABAergic brain neurons Bluebell (BB) and Foxglove
(FG) "inhibit specific descending walking commands in the brain" — "comparable to taking one's
foot off the gas pedal" — with "oDN1 and BDN2 [standing] apart as important nodes to mediate
differences in BB and FG effects on the walking pathways" (BDN2's activity is "strongly
correlated to forward velocity", oDN1 "mainly relevant for driving forward velocity"). Both
halt neurons are "downstream to the sugar sensory pathway"; FG "showed stronger responses in
starved flies", the halt-to-feed context. "Brake": six cholinergic ascending neurons in the
nerve cord that arrest stepping actively — not scored here (its targets are leg premotor
circuits in the VNC, and the mechanism is a muscle resistance state).

## What the task measures

FlyWire v783 carries the paper's neurons under community labels: Foxglove = CB0890 (2, GABA),
Bluebell = DNg60 (2, GABA), oDN1 = DNg97 (2), BDN2 = DNg100 (2). MaleCNS has DNg60, DNg97 and
DNg100 but no Foxglove under any name, so the task is skipped there ("readout fg matches no
neurons"), not marked not-applicable: the circuit may well exist in the male, unlabelled.

Wiring (v783, synapses): FG → BDN2 **−1,137**, FG → oDN1 −136, BB → oDN1 −206, BB → BDN2 −18;
neither touches P9 (DNp09), which is why P9 is not scored despite the paper's mention. The sugar
GRNs reach FG by two hops (86,751 synapse products; no direct contact) and BB (101,540).

The model has no walking fly. The walking command is stood in for by the two DNs' shared
excitatory inputs, PVLP137 and CB0529 (four cells; → BDN2 1,660, → oDN1 1,117), at 100 Hz —
CONVENTION, declared as such: they are chosen because they are the DNs' largest common inputs,
which is selecting a stimulus by the wiring. The suppression checks compare the same drive with
and without a halt neuron, so the convention cancels in the ratio; the two "walk drives the DN"
checks exist so that a floored ratio (S2) is not mistaken for suppression.

Conditions (100 Hz, 500 ms): sugar; walk; walk + Foxglove; walk + Bluebell. Checks: (1) sugar →
FG > 5 Hz; (2) walk → BDN2 > 5 Hz; (3) walk → oDN1 > 5 Hz; (4) BDN2 with FG / without < 0.5;
(5) oDN1 with FG / without < 0.5; (6) oDN1 with BB / without < 0.5 (task-03 convention).

## Pre-registered predictions

Steady state at 0.45 (0.124 mV per synapse): BDN2 gets 830 synapses per cell from the walk
drive → 51 mV → ceiling (~360 Hz); oDN1 560 → 35 mV → ceiling. FG at 100 Hz removes 570 per
BDN2 cell → −35 mV, and 68 per oDN1 cell → −4 mV; BB removes 103 per oDN1 → −6 mV.

- **FlyWire v783, LIF 0.45, 3 seeds.** (1) sugar → FG: sugar ignites the brain at 0.45 (task
  02 works there) and FG has an 87k two-hop route: **pass**. (2), (3) **pass**, both at ceiling.
  (4) BDN2: +51 − 35 = 16 mV → ~70 Hz against ~360 → ratio ≈ 0.2: **pass**, and not saturated
  (one side under the gate). (5) oDN1: −4 mV against +35 → ratio ≈ 0.95: **fail**. (6) oDN1
  with BB: −6 → ratio ≈ 0.9: **fail**. **4/6 = 0.67.** The four walk cells carry 14,600 output
  synapses — an H2's worth each (RFC 24) — so the walk drive likely lights the brain; that adds
  network excitation to both DNs and does not change the ordering above. If FG's own targets
  through the network (4,729 output synapses) suppress more broadly than its direct contacts,
  5 and 6 could pass: 6/6, one in five.
- **MaleCNS**: skipped (no Foxglove label).
- **Adaptive LIF (FlyWire 1.0)**: the same 4/6; at gain 1.0 BDN2's residual 16 mV becomes 36
  and the ratio rises toward the saturation gate — 3/6 if both sides reach ceiling.
- **Rewired control.** Four cells through random wiring: at 0.45 nothing → 2, 3 fail, 4–6
  floored; sugar through random wiring → FG silent → 1 fails. **0/6**, specificity +0.67.

The interesting outcome is 5 or 6 passing: a 136- or 206-synapse inhibitory contact doing the
job of 1,137, which would mean Foxglove and Bluebell act through the network rather than at
the DN — which is what the paper's whole-brain model suggests for BB.

## What would make this task wrong

- **The walking stand-in is chosen by the wiring.** If PVLP137/CB0529 are not part of any
  walking command in the fly, checks 2–3 are a wiring exercise; 4–6 still measure whether the
  halt neurons can turn *their* targets off, which is the mechanism the paper reports.
- **P9 dropped.** The paper names P9 among BB's effects; v783 has no BB → DNp09 contact. Either
  the effect is polysynaptic or the label maps differently. A task that scored it would fail
  for wiring the dataset does not have.
- **FG's context (starvation) is not modelled**; sugar → FG at 100 Hz is the fed and starved
  fly alike.
- **Toy**: sugar's second-order cells → Foxglove; a walking input → oDN1 and BDN2; Foxglove →
  both, Bluebell → oDN1 (MODELED). The broken-toy test cuts Foxglove → DN and must fail exactly
  the two Foxglove ratios.

## Outcome (recorded 2026-09-15, first run after pre-registration; `--jobs 6`)

**MaleCNS:** skipped — no Foxglove label (recorded as "readout fg matches no neurons").

**FlyWire v783, LIF 0.45, 3 seeds, `--controls rewired`:**

| check | value (3 seeds) | result | predicted |
|---|---|---|---|
| 1. sugar → Foxglove > 5 Hz | 66 Hz | pass | pass |
| 2. walk → BDN2 > 5 Hz | 105 Hz (102 / 89 / 125) | pass | pass (ceiling) |
| 3. walk → oDN1 > 5 Hz | 15 Hz | pass | pass (ceiling) |
| 4. BDN2 with FG / without < 0.5 | **0.69** (0.53 / 1.00 / 0.53) | fail | pass (≈ 0.2) |
| 5. oDN1 with FG / without < 0.5 | 1.06 | fail | fail |
| 6. oDN1 with BB / without < 0.5 | 0.91 | fail | fail |
| score | **3/6** | | 4/6 |
| rewired | 0/6, specificity **+0.50** | | 0/6, +0.67 |

Three things the steady-state arithmetic missed:

- **The walking stand-in ignites the brain (9 %) and recruits Foxglove itself**: under `walk`
  alone Foxglove already fires at 48 Hz. Forcing it to 100 Hz on top adds ~60 Hz of inhibition,
  not 100, and BDN2 goes 105 → 70 Hz (0.69) rather than 360 → 70. The DNs are not at ceiling
  either (BDN2 105 Hz, oDN1 15 Hz): the ignition's inhibitory recruits already hold them well
  below the 51 mV / 35 mV the direct inputs alone would give.
- **The BDN2 suppression is real but seed-sensitive**: 0.53 / 1.00 / 0.53 — on one seed the
  ignition's noise cancels Foxglove's contribution entirely. The every-seed rule fails it.
- **oDN1 is untouched by either halt neuron** (1.06, 0.91), as predicted from −136 and −206
  synapses against a network-driven 15 Hz. Sapkal 2024's oDN1 effect, if it is in the wiring,
  is polysynaptic.

Sugar → Foxglove is the clean result: 66 Hz through the two-hop route, with Bluebell at 1 Hz —
the paper's "FG responds to sugar; BB only weakly" reproduced by the wiring. Rewired 0/6:
random wiring carries none of it, specificity +0.50.
