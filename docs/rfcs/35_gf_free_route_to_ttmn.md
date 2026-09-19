# RFC: task 35 — which descending neurons carry the giant-fiber-free loom route to the jump muscle

Status: **stage 1 pre-registered 2026-09-19** (anatomy, procedure, and the predictions that need
no simulation) before any run; **stage 2** (candidate-specific predictions) is added below after
one disclosed development run and before the scored run. This RFC identifies a pathway from data,
so it cannot be blind; what is pre-registered is the *test*, and every step is written down in
the order it happened. MaleCNS in practice (TTMn needs a nerve cord).

## The question

Task 34: with the GF's synapses zeroed, a loom through the flyvis eye still fires TTMn (3.3
spikes/neuron) and the body takes off at 499 ms; a flash through the same eye no longer reaches
TTMn at all. So MaleCNS contains a GF-independent route from the medulla to the jump motor neuron
that the loom uses and the flash does not. Which descending neurons carry it?

The flyvis stimulus drives medulla cell types only (T4/T5, T2/T3, Tm/TmY — all in the brain). The
only way for it to reach the VNC is a descending neuron (or an ascending neuron's feedback loop,
which cannot be the *origin*). So the route has a DN in it by construction.

## Anatomy (a dataset query, not a simulation; run 2026-09-19 before anything else)

TTMn (2 cells) on MaleCNS v1.0 has 166 presynaptic partners: 1,869 excitatory synapses, 3,859
inhibitory (mostly IN21A / IN13A VNC intrinsics). Its excitatory inputs by type:

| type | class | synapses |
|---|---|---|
| GFC2 | VNC intrinsic (the giant-fiber-coupled interneurons) | 471 |
| IN20A.22A001 | VNC intrinsic | 241 |
| IN07B044 / IN07B055 | VNC intrinsic | 179 / 157 |
| IN04B036 | VNC intrinsic | 91 |
| **DNp01 (GF)** | DN | 90 |
| **DNp06** | DN | 53 |
| **DNp02** | DN | 26 |
| DNp10 | DN | 8 |
| (others, each < 60) | | |

Four descending neurons synapse on TTMn directly: DNp01 (the GF), DNp06, DNp02 and DNp10 — the
last three all members of the loom-DN ensemble (Dombrovski et al. 2023; Ache et al. 2019; task
10's DNp02). Everything else reaches TTMn through VNC interneurons; GFC2's own big excitatory
inputs are IN04B036, IN07B055, IN20A.22A001, GFC2 itself and IN07B044 — not DNs directly.

## Task design

Every condition is the flyvis loom (200 ms onset) on MaleCNS with the GF silenced (task 34's
`loom_eye_gf_off`) plus one more silenced set; readout TTMn; body as in tasks 33–34. Conditions
fixed at stage 1:

- `gf_off` — task 34's condition: the route exists (positive control).
- `gf_direct_dn_off` — GF + DNp02 + DNp06 + DNp10 silenced: the three direct loom-DN inputs.
- `gf_all_dn_off` — GF + every descending neuron silenced (`super_class: descending_neuron`).
- `gf_route_off` — GF + the stage-2 candidate set silenced (defined below, after the dump).
- One condition per stage-2 candidate alone (`gf_<type>_off`), to test redundancy.

Checks fixed at stage 1:

1. `gf_off`: TTMn ≥ 1 spike per neuron (task 34's result reproduces).
2. `gf_all_dn_off`: TTMn < 0.5 spikes per neuron — silencing every DN abolishes the response;
   the route descends from the brain. **Predicted: pass.** If it fails, the "route" is a VNC
   artefact (an ascending/VNC loop the stimulus should not reach) and the task is wrong.
3. `gf_direct_dn_off`: TTMn ≥ 1 spike per neuron — silencing the three direct loom DNs does
   **not** abolish it. **Predicted from anatomy alone: pass** (the response survives): task 32
   found LPLC2 and LC4 at 0 Hz to this loom on MaleCNS, and DNp02/DNp06/DNp10 are the LC4/LPLC2
   targets; the route is polysynaptic through VNC interneurons driven by other DNs. If this
   fails, the direct loom DNs carry it after all and the pathway story is simpler than predicted.
4. `gf_route_off`: TTMn < 0.5 spikes per neuron — silencing the identified candidate set
   abolishes it (stage 2 names the set).
5. Per-candidate conditions: stage 2 predicts, for each, whether the response survives.
6. `gf_route_off`: takeoff < 0.5 — and the body no longer jumps.

## Procedure for stage 2 (fixed now)

One development run of `loom_eye_gf_off` on MaleCNS, 1 seed, `--dump-spikes`. From the dump:
every descending neuron's spike count in 200–1200 ms. Candidates = DN *types* (by `cell_type`)
whose cells fire ≥ 5 spikes in the window **and** that reach TTMn within two synapses (direct, or
through one VNC interneuron with ≥ 10 synapses on TTMn), ranked by spikes × path strength.
The candidate set is the smallest prefix of that ranking whose members together account for
≥ 80 % of the summed (spikes × synapses onto TTMn's excitatory drivers). Stage 2 lists the
ranking, the set, and a prediction for each single-candidate silencing, then the scored run.

## What would make this task wrong

- **Silencing is outgoing-synapse zeroing**; a silenced DN still spikes. Fine for "is it the route".
- **Two synapses** is a convention for "reaches TTMn"; a three-synapse route would be missed by
  the candidate rule and show up as check 4 failing. That is a result, not a bug.
- **The eye loom on MaleCNS lights 15 % of the CNS.** The candidate DNs will be among hundreds
  that fire; the test is whether the *named* few are necessary, not whether they are the only
  ones active.
- **Toy:** no toy version of a MaleCNS-specific pathway question; the toy skips the task
  (`dataset_only: [malecns]`, since its DN types are the dataset's).

## Stage 2 (2026-09-19, after one disclosed development run, before the scored run)

The dump (`loom_eye_gf_off`, MaleCNS 0.65, seed 0, 200–1200 ms): **465 of 1,314 descending
neurons fire** (27,774 DN spikes — the 15 %-of-CNS event of task 32 seen from the neck). TTMn:
one cell 9 spikes (first at 716 ms), the other 0. The direct loom DNs **DNp02, DNp06 and DNp10
fire zero spikes** — stage 1's anatomical prediction (check 3) is already consistent. TTMn's
excitatory drivers that fired: GFC2 (6 and 9 spikes; 120 and 73 synapses onto TTMn),
IN20A.22A001 (8, 5), IN20A.22A003 (17), IN07B044 (1). So the route is DN → {GFC2, IN20A.22A}
→ TTMn — through the giant-fiber-coupled interneurons, without the giant fiber.

Ranking by the fixed rule (spikes × two-synapse reach, DN types with ≥ 5 spikes and reach > 0;
29 such types):

| rank | DN type | cells | spikes | reach (via IN) | share | cumulative |
|---|---|---|---|---|---|---|
| 1 | DNge048 | 2 | 228 | 53.2 | 0.29 | 0.29 |
| 2 | DNa02 | 1 | 161 | 16.8 | 0.13 | 0.42 |
| 3 | DNbe007 | 2 | 307 | 10.8 | 0.08 | 0.50 |
| 4 | DNge006 | 1 | 206 | 7.0 | 0.07 | 0.57 |
| 5 | DNg45 | 2 | 33 | 77.5 | 0.06 | 0.64 |
| 6 | DNpe002 | 2 | 167 | 15.3 | 0.06 | 0.69 |
| 7 | DNa11 | 1 | 217 | 4.8 | 0.05 | 0.74 |
| 8 | DNb05 | 2 | 373 | 5.4 | 0.05 | 0.79 |
| 9 | DNge053 | 2 | 222 | 7.8 | 0.04 | **0.83** |

Candidate set (smallest prefix ≥ 80 %): the nine types above, 15 cells. None of them is a
loom DN of the literature; DNa02 is task 28's steering DN. Whatever the outcome, that is the
finding: the GF-free loom route on MaleCNS is not the LC4/LPLC2 → loom-DN ensemble (silent) but
a diffuse set of medulla-driven DNs converging on the GF-coupled interneurons.

**Amendment to stage 1, for cost:** single-candidate conditions for the top five only (each
condition is a 1.3 s whole-CNS simulation × 3 seeds × 2 wirings; nine would double the task's
cost). Stated here before the scored run.

Stage-2 predictions (MaleCNS 0.65, 3 seeds):

- check 1 `gf_off` survives: pass. check 2 `gf_all_dn_off` abolished: pass.
- check 3 `gf_direct_dn_off` survives: **pass** (those DNs do not fire).
- check 4 `gf_route_off` (GF + the nine) abolished: **pass** — GFC2 received a marginal drive
  (6–9 spikes) with everything on; removing 83 % of the weighted drive should silence it. The
  interesting failure: TTMn survives on the remaining 17 % (the route is even more diffuse than
  the top nine).
- per-candidate alone (checks 5a–e, "survives"): DNge048 alone — **survives, but this is the
  one most likely to break it** (29 % of the drive, TTMn marginal at 1.5–4.5 spikes/neuron
  across task 34's seeds); DNa02, DNbe007, DNge006, DNg45 alone — survive.
- check 6 `gf_route_off` no takeoff: pass.
- **11/11** predicted for the reference; tier `hard` (the reference submission on FlyWire
  cannot run it, docs/GOVERNANCE.md).
- Rewired: the shuffle's TTMn does not respond to the eye loom (task 34), so every "abolished"
  check passes trivially and every "survives" check fails: 3/11, specificity ≈ +0.73.

## Outcome (2026-09-19, MaleCNS v1.0, LIF 0.65, 3 seeds, `rewired` control)

The task has **10 checks** (stage 2 said 11: a miscount). **9/10; rewired 3/10; specificity
+0.60.**

| condition (loom through the eye, GF silenced, plus …) | TTMn spikes/neuron | GFC2 Hz | takeoff | predicted | |
|---|---|---|---|---|---|
| nothing more | 3.33 (4.5, 4.0, 1.5) | 1.07 | 499 ms | survives | ✓ |
| **every descending neuron** | **3.17** (2.5, 5.0, 2.0) | 1.57 | 873 ms | **abolished** | **✗** |
| DNp02 + DNp06 + DNp10 | 3.33 | 1.07 | 499 ms | survives | ✓ |
| the nine candidate types | **0.00** (0, 0, 0) | 0.00 | none | abolished | ✓ |
| DNge048 alone | 2.33 (1.5, 4.0, 1.5) | 0.83 | 499 ms | survives | ✓ |
| DNa02 alone | 9.50 | 3.10 | 501 ms | survives | ✓ |
| DNbe007 alone | 2.00 | 0.63 | 499 ms | survives | ✓ |
| DNge006 alone | 1.67 | 0.50 | 500 ms | survives | ✓ |
| DNg45 alone | 2.67 | 0.93 | 499 ms | survives | ✓ |

**The route.** Nine descending-neuron types — DNge048, DNa02, DNbe007, DNge006, DNg45, DNpe002,
DNa11, DNb05, DNge053, named by the fixed procedure — converge on the giant-fiber-coupled
interneurons GFC2 and IN20A.22A, which drive TTMn. Silencing the nine together abolishes the
response and the jump on every seed (GFC2 0 Hz); silencing any one of the top five does not
(each alone leaves 1.7–9.5 spikes/neuron), so no single DN is necessary — redundancy across a
diffuse set, as predicted. The three direct loom-DN inputs to TTMn play no part (silencing them
changes nothing; they do not fire), as predicted from anatomy. None of the nine is a loom DN of
the literature. Silencing DNa02 alone *raises* TTMn to 9.5 (its VNC targets include inhibitors of
the route; unasked for, reported).

**The failed check is the finding.** Silencing *every* descending neuron — 1,314 cells, the nine
among them — does not abolish the response: TTMn 3.2 spikes/neuron, GFC2 1.6 Hz, a takeoff at
873 ms. A subset abolishes what the superset does not, so with all DNs silent something else
carries loom activity into the nerve cord. It is the **ascending neurons, running backwards.**
On MaleCNS 22 % of the ascending neurons' input synapses are in the brain (544,147 of ~2.5 M —
axo-axonic contacts on their terminals, many from DNs). A point neuron cannot tell a terminal
input from a dendritic one: the loom's 15 %-of-brain activity drives 437 ANs (20,538 spikes in
the development dump), and their VNC outputs (490,000 synapses) reach GFC2 and TTMn. Diagnostic
runs (single seed, disclosed): every DN silenced → TTMn 2.5; every DN **and every AN** silenced →
TTMn **0.0**, GFC2 0.0; GF + every AN silenced (DNs intact) → TTMn 6.5. So the DN route is real
within the model and does not need the ANs, and the residual route with all DNs silent is the
ANs driven antidromically — a route no fly has, because an axon terminal does not fire its
own cell back down its axon. Why it shows only when *all* DNs are silent: DNs synapse heavily
on the ANs' brain arbors, and removing all of them removes that (largely inhibitory) drive;
silencing twenty cells does not.

Check 2 stays as written. It was pre-registered as the task's own test of whether the route
descends, and it now measures a specific model defect: a point-neuron whole-CNS model lets
brain-side axo-axonic input drive ascending neurons' nerve-cord outputs. A compartmental model,
or one that places axo-axonic synapses on the terminal rather than the soma, would pass it.
That is a hard-tier target, not a bug in the task, and the check's `basis` now says so.

Rewired: the shuffle's TTMn does not respond (task 34), so its three "abolished" checks pass
and its seven "survives" checks fail: 3/10, specificity +0.60.
