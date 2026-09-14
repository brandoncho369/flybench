# RFC: task 19 — the giant fiber reaches the jump muscle in under a millisecond

Status: pre-registered 2026-09-14, before the first run on any dataset. (The DA1 adaptation task
planned as 19 is deferred: FlyWire v783 types DA1 projection neurons only as `DA1_lPN` and
`DA1_vPN`; the `lvPN` subtype Taisz et al. 2023 contrast against is not a separate type there,
so the task cannot pose its question. Recorded in ROADMAP item 14.)

## The behaviour

The giant fiber drives the tergotrochanteral (jump) motor neuron through a mixed electrical–
chemical synapse and the dorsal longitudinal (flight) motor neurons through the peripherally
synapsing interneuron. Augustin et al. (2019, eNeuro 6:ENEURO.0423-18.2019; model on ModelDB
245415) measured, in 5–7-day flies, **TTM 0.93 ms** and **DLM 1.44 ms** from brain stimulation
to muscle depolarisation, including a 0.35 ms neuromuscular delay; so GF → TTMn ≈ 0.6 ms and
GF → DLMn ≈ 1.1 ms, with DLM lagging TTM by ~0.5 ms. Engel & Wu (1996, J Neurosci 16:3486): a
DLM response ≥ 3.0 ms is the non-GF ("long-latency") pathway.

## What the task measures

MaleCNS only (needs the nerve cord; `requires_readouts: [ttmn, dlmn]`). Loom drives LPLC2/LC4
as in task 15; readouts GF, TTMn, DLMn. Latency = median over the readout's neurons of each
neuron's first spike, measured from the GF's first spike (`from: gf`).

Checks:

1. GF → TTMn latency ≤ 1.5 ms (`observed: mean 0.93 − 0.35 = 0.58, sd unknown`, Augustin 2019;
   1.5 ms is a lenient convention: the fastest chemical route the model could offer).
2. GF → DLMn latency ≤ 3.0 ms (Engel & Wu 1996: ≥ 3.0 ms is the non-GF path; the GF path is 1.1).
3. Ordering: DLMn after TTMn — latency(GF → DLMn) > latency(GF → TTMn) (Augustin 2019: DLM lags
   TTM by ~0.5 ms; ratio of the two > 1).
4. Sanity: TTMn fires at all (spikes per neuron ≥ 1 during the loom, as in task 15).

## Pre-registered predictions — and why the task will fail by construction

The reference model has one synaptic delay for every connection: 1.8 ms (Shiu 2024). The GF →
TTMn synapse in the fly is largely **electrical** (gap junction, no delay to speak of); the model
treats it as chemical. So check 1 fails on every model that keeps the uniform delay — predicted
GF → TTMn in the model: ≈ 1.8–2.5 ms. Check 2 passes (GF → PSI → DLMn is two chemical hops,
≈ 3.6 ms plus integration; borderline — guess: fails narrowly, 3.6–4.5 ms). Check 3 passes (two
hops are later than one). Rewired: TTMn does not fire → check 4 fails → diagnostic.

This is the first task written to fail for a *named missing mechanism* rather than a wrong
parameter: no global gain fixes it, only electrical synapses do. That is the point of having it:
it turns Marder's "you are missing the gap junctions" critique into a number on the board.

## What would make this task wrong

`first spike` latencies at dt = 0.1 ms are quantised to 0.1 ms; fine for a 0.6 vs 1.8 ms
question. If MaleCNS annotates the GF → TTMn edge with an electrical-synapse flag in a later
version, a model may legitimately use it; the task's threshold does not change.

## Outcome (recorded 2026-09-14, first run after pre-registration)

MaleCNS v1.0, gain 0.65, 3 seeds, `--controls rewired`:

| check | result |
|---|---|
| TTMn fires on the loom | 57.7 spikes per neuron — pass |
| GF → TTMn ≤ 1.5 ms | **11.8 ms** (sd 7 µs across seeds) — fail; predicted fail, but at 1.8–2.5 ms |
| GF → DLMn ≤ 3.0 ms | **10.6 ms** — fail; predicted borderline 3.6–4.5 |
| DLMn after TTMn | **−1.2 ms** (DLMn first) — fail; predicted pass |
| rewired control | 0 % — diagnostic |

Score 0.25, graded 0.52. Both magnitude predictions and the ordering prediction were wrong, and
the way they were wrong is more informative than the numbers I guessed:

1. TTMn does not follow the GF's first spike through one synaptic delay. It fires ~12 ms later,
   which at the GF's ~430 Hz is about five GF spikes. The GF → TTMn connection in the model is a
   chemical synapse whose weight is a synapse count, and one GF spike through it is not enough to
   bring TTMn to threshold; the motor neuron has to integrate a burst. In the fly the same
   contact is a giant electrical synapse that fires TTM on a single GF spike in ~0.6 ms. So the
   missing mechanism is not "the delay is 1.8 ms instead of 0": it is that a gap junction makes
   one spike sufficient, and a summed chemical synapse does not. The task now states this.
2. DLMn fires 1.2 ms *before* TTMn. The DLM path (GF → PSI → DLMn) has stronger summed input
   than the direct GF → TTMn contact in this wiring, so the two-hop route wins the race. That is
   the wrong order for an escape: the legs push ~1 ms before the wings open (Card & Dickinson
   2008), and it is TTM that starts the jump.
3. The near-zero seed sd (µs) says these latencies are set by the wiring, not by the Poisson
   input: a deterministic consequence of synapse counts and the fixed delay.

Prediction for the adaptive LIF: worse, not better (adaptation lowers the GF burst rate, so
TTMn needs longer to integrate the same number of spikes). Prediction for a model with the
GF → TTMn edge treated as electrical (weight applied as an instantaneous voltage step): TTMn
latency drops below the 1.5 ms line and the ordering flips to the correct one. That is the
first mechanism-level prediction this benchmark has made, and it is falsifiable with one
adapter change. It is *not* a licence to add that mechanism to the reference model: it goes in
as a separate, labelled open-division submission, if at all.
