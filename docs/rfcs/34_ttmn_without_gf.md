# RFC: task 34 — the jump without the giant fiber: a loom through the eye reaches TTMn with the GF silenced

Status: pre-registered 2026-09-18, before any scored run. Follows directly from task 33's
unasked-for MaleCNS finding (docs/rfcs/33: the flyvis loom made the body jump at 499 ms with
the GF at 0 Hz). **That observation is the reason this task exists and is disclosed as such**;
no other run on a real brain preceded this RFC. MaleCNS-only in practice (TTMn needs a nerve
cord; FlyWire is skipped by `requires_readouts`).

## The behaviour

Flies take off from a loom in two modes (Card & Dickinson 2008, Curr Biol 18:1300; von Reyn et
al. 2014, Nat Neurosci 17:962): the giant-fiber *short mode* — one GF spike near collision, legs
extend, no wing raising — and a *long mode* that does not require the GF at all: GF-silenced flies
still take off, with raised wings, earlier relative to collision and with a more variable latency
(von Reyn 2014, GF-silenced flies; Engel & Wu 1996 for the long-latency, non-GF muscle response).
Both modes end in the tergotrochanteral muscle firing. So the connectome should contain a route
from the loom detectors to TTMn that does not pass through the GF.

## What the task measures

Task 33's `loom_eye` on MaleCNS: GF 0 Hz, TTMn 3.3 Hz, the body jumps. Here the GF's outgoing
synapses are zeroed for the condition (`silence:`, the in-silico shibire of task 26, so the GF
cannot be the route even if it fires) and the question is asked directly, on the body:

Conditions (all with the GF silenced except the first):

- `loom_eye` — the flyvis loom, GF intact (task 33's measurement, reproduced here).
- `loom_eye_gf_off` — the flyvis loom, GF silenced.
- `loom_gf_off` — the task-4 convention (LPLC2 + LC4 at 150 Hz, 200–500 ms), GF silenced.
- `flash_eye_gf_off` — the flyvis flash, GF silenced.
- `rest_gf_off` — nothing, GF silenced.

Body: NeuroMechFly as in task 33, command readout TTMn (no fallback: a dataset without TTMn is
skipped). Checks:

1. `loom_eye_gf_off`: TTMn ≥ 1 spike per neuron over the window — the loom reaches the jump
   motor neuron without the giant fiber.
2. `loom_eye_gf_off`: takeoff ≥ 1 — and the body leaves the ground.
3. `loom_eye_gf_off`: takeoff latency < 1000 ms from loom onset — before the movie's collision
   (CONVENTION: a takeoff after the object has arrived is not an escape; Card & Dickinson 2008
   measure every takeoff before contact).
4. `loom_gf_off`: TTMn ≥ 1 spike per neuron — the convention loom also has a GF-free route
   (LC4 → DNp02 / DNp11 and onward, task 10's ensemble).
5. `flash_eye_gf_off`: takeoff < 0.5 — the flash's jump in task 33 should not survive the GF's
   silencing if it was GF-borne.
6. `rest_gf_off`: takeoff < 0.5.

`loom_eye` (GF intact) is measured, not scored: task 33 owns it.

## Pre-registered predictions

- **MaleCNS v1.0, LIF 0.65, 3 seeds.** Checks 1–3 **pass** (this is task 33's observation with
  the GF's synapses removed, and the GF was silent there anyway: TTMn ~3 Hz, takeoff ~500 ms).
  Check 4: **pass** — LC4 at 150 Hz drives DNp02/DNp11 strongly on MaleCNS (task 10) and the
  loom-through-the-eye result says the nerve cord carries loom drive to TTMn without the GF;
  a much stronger loom will too. Check 5: **fail** — the flash lights 23 % of the CNS (task 32),
  more than the loom's 15 %, and the loom reached TTMn without the GF; the flash will too, GF or
  no GF. Check 6: pass. **5/6.** Tier: `hard` pre-registered; if the reference passes 6/6 the
  outcome section says so and the tier becomes `core` per docs/GOVERNANCE.md (the audit rule).
- **FlyWire.** Skipped (no TTMn).
- **Adaptive LIF.** Not run on MaleCNS; no prediction.
- **Rewired.** The shuffle passed task 33's rest and flash nulls and failed its looms; here the
  same: checks 5 and 6 pass, 1–4 fail. **2/6**, specificity +0.50.

The interesting outcomes: check 5 passing (the flash's route to TTMn *is* the GF, and the loom's
is not — a real dissociation), or check 4 failing (the strong convention loom saturates the DNs
into something that does not reach TTMn, while the weak eye loom does).

## What would make this task wrong

- **Silencing is outgoing-synapse zeroing.** A GF that still spikes but transmits nothing: the
  right manipulation for "is the GF the route", not for "does the GF exist".
- **The eye loom on MaleCNS is a 15 %-of-CNS event** (task 32). TTMn firing inside that could be
  non-specific spread rather than a loom pathway. Check 5 (the flash, an even bigger event) is
  the control for exactly that; if both pass, the "route" is just spread and the task says so.
- **Latency.** The fly's long-mode takeoff comes *earlier* relative to collision than the GF
  mode for the same loom; the task only asks "before collision". A recording-matched latency
  would need the loom's r/v and the fly's threshold angle, which the flyvis movie fixes at
  r/v 40 ms — a later task.
- **Toy:** DNp02/DNp11 → TTMn added (MODELED, weaker than GF → TTMn), so with the GF silenced the
  toy's LC4 → DN → TTMn route carries the convention loom (check 4), and the flash and rest nulls
  hold. The toy does **not** make checks 1–3: its eye-driven detectors (task 32's dark-loom
  circuit) fire only in the loom's last ~100 ms, so TTMn's first spike lands at 990–1005 ms after
  onset, at the collision itself, and over the scored window there are none. Making the
  detectors fire earlier (stronger T5 → LC contacts) was tried and rejected: it makes the toy
  jump at the flash in task 33. The toy scores 3/6 by design; the checks it fails are exactly
  the ones the real brain is being asked about.

## Outcome (2026-09-18, MaleCNS v1.0, LIF 0.65, 3 seeds, `rewired` control)

| condition (GF silenced unless noted) | TTMn | takeoff | latency from onset | predicted |
|---|---|---|---|---|
| loom through the eye | 3.3 spikes/neuron (4.5, 4.0, 1.5) | yes, 3/3 | **499 ms** (527, 411, 558) | pass ✓ |
| convention loom (LPLC2/LC4 150 Hz) | 27 spikes/neuron | yes, 3/3 | **30 ms** | pass ✓ |
| flash through the eye | **0.0** (GF itself still 6 Hz) | **no**, 3/3 | – | **fail ✗** |
| rest | 0 | no | – | pass ✓ |
| loom through the eye, GF intact (unscored) | 3.3 | yes | 499 ms | – |

**6/6; predicted 5/6.** Rewired 1/6 (predicted 2/6), specificity **+0.83**, the highest of any
task in the suite.

The miss is the finding. With the giant fiber's synapses zeroed, the flash through the eye no
longer reaches TTMn at all — 0.0 spikes on every seed, while the GF itself still fires at 6 Hz
into nothing — but the loom through the eye reaches TTMn exactly as before (3.3 Hz, the same
seeds, the same 499 ms). So the two stimuli take different roads to the jump muscle: the flash's
road *is* the giant fiber (task 32/33's wrong-way escape is entirely GF-borne), and the loom's
road is GF-independent. That is a dissociation the RFC named as the interesting outcome and bet
against ("the flash lights more of the CNS than the loom; it will reach TTMn too"). It did not.
The 23 %-of-CNS flash event and the 15 %-of-CNS loom event are not the same kind of spread: one
of them contains a route to the jump motor neuron that does not need the GF and the other does
not. What that route is — which descending neurons, and whether they are the long-mode DNs of the
literature — is the next task's question (`upstream_of: TTMn` minus the GF, with each candidate
DN silenced in turn).

The convention loom's GF-free route is fast: 30 ms to takeoff against 23 ms with the GF (task
33). The eye loom's is slow and variable (411–558 ms), as the long mode's is in the fly.

The shuffle: 1/6 rather than 2/6 — on rewired wiring the flash *does* reach TTMn without the GF
(`checks: [✗ ✗ ✗ ✗ ✗ ✓]`), i.e. the flash null is passed by the real wiring and failed by its
degree-matched shuffle. Specificity +0.83.

**Tier stays `hard`.** The reference passes 6/6 on MaleCNS, and the pre-registration said that
would make it `core`. It does not, for a reason the RFC should have stated: the tiers are
defined against the reference *submission* (`configs/submissions/reference-lif-0.45.yaml`,
FlyWire), and that submission cannot run this task — FlyWire has no TTMn. A core task is a
regression test the reference submission must pass; a task it skips cannot be one.
docs/GOVERNANCE.md now says so. The audit's tier rule agrees (it reports "not run" on FlyWire).
