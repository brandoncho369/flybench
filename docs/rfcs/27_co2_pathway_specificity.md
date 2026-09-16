# RFC: task 27 — CO2 reaches its own projection neurons, its extraglomerular channel and the lateral horn; other odours do not

Status: pre-registered 2026-09-15, before the first run on any dataset. Synapse counts are from
the wiring; no simulation was run.

## The behaviour

CO2 is detected by the Gr21a/Gr63a neurons that innervate the V glomerulus (Suh et al. 2004,
Nature 431:854; Jones et al. 2007, Nature 445:86) and is innately aversive to walking flies.
Lin et al. 2013 (Nature 501:81) showed the V glomerulus is served by parallel projection
neurons with different sensitivities. The preprint "Structural basis of CO2 valence coding in
Drosophila" (bioRxiv 2026.01.05.697655) mapped the circuit in FlyWire: a bilateral cholinergic
PN (PNvbi, the type `V_ilPN`) to the lateral horn on both sides, a unilateral one (PNvuni,
`V_l2PN`), and an **extraglomerular** channel — the non-GABAergic (anti-GABA negative) local
neuron **LN23** (`l2LN23`), driven by ORN_V, relays to the multiglomerular **PNm1**
(`M_smPNm1`, GABAergic) and PNm17, which project to the PLP beside the lateral horn. "LN23
silencing fully abolished aversion behavior towards CO2"; optogenetic activation of PNm1
"induced strong aversion"; PNm1 "receives mostly input from the LN23 CO2 channel" (18 % of its
input from LN23). PNvbi's primary lateral-horn target is `LHPD5c1`, which "integrates CO2 +
food cues".

## What the task measures

Cell types (all MEASURED, the same names on both datasets):

| | FlyWire v783 | MaleCNS v1.0 |
|---|---|---|
| ORN_V | 67 | 55 |
| V_ilPN (PNvbi) | 2, ORN_V → 5,258; targets LHPD5c1 on both sides | 2, 5,487 |
| l2LN23 (LN23) | 4, ORN_V → 1,771, **nt unlabelled → excitatory in W** | 4, 3,145, **labelled GABA → inhibitory in W** |
| M_smPNm1 (PNm1) | 2, GABA; LN23 → 283 per cell | 2, GABA; LN23 → −195 per cell |
| LHPD5c1 | 2, GLUT; V_ilPN → 1,055, DM1_lPN 382, DM4 540, DP1m 665, VM7d 799 | 2; 894 / 392 / 386 / 711 / 514 |

Neither V_ilPN nor LN23 receives a synapse from ORN_DA1 or ORN_DM1 in either connectome.

Conditions: ORN_V, ORN_DA1, ORN_DM1, each at 100 Hz for 500 ms (task-02 / task-18 CONVENTION).
Checks: four positives on the CO2 drive (V_ilPN, LN23, PNm1, LHPD5c1 > 5 Hz) and three nulls
(DA1 → PNm1, DM1 → PNm1, DA1 → V_ilPN < 2 Hz). The nulls are the roadmap's point: the fly keeps
the CO2 channel private, and task 18 found this model's antennal lobe broadcasts one glomerulus
to 84 % of its PNs.

**The LN23 transmitter.** The preprint stains LN23 anti-GABA negative; FlyWire v783 leaves its
`nt_type` blank (which flybench treats as excitatory, matching the paper) and MaleCNS predicts
GABA (which does not). On MaleCNS the LN23 → PNm1 edge is therefore −195 per cell in W. This is
a dataset annotation, not a task choice; the task does not correct it (that would be tuning),
and the prediction below assumes it.

## Pre-registered predictions

Steady-state estimates at 0.45 (0.124 mV per synapse): V_ilPN gets ~2,600 ORN_V synapses per
cell → 160 mV → ceiling; LN23 ~440 per cell → 27 mV → ~120 Hz; PNm1 gets 283 × 120 Hz → 21 mV →
~100 Hz; LHPD5c1 527 × 360 Hz → far over threshold. V_ilPN alone has 26,000 output synapses —
five H2s (RFC 24) — so the CO2 drive will be a whole-brain event at 0.45.

- **FlyWire v783, LIF 0.45, 3 seeds.** Checks 1–4 **pass** (the direct chain is strong at
  every hop). Checks 5–7 **fail**: DA1 and DM1 at 100 Hz broadcast through the antennal lobe
  (task 18), V_ilPN is a PN and fires with the rest, and PNm1 gets the broadcast through its
  M_lPNm11A–D multiglomerular inputs. **4/7 = 0.57.** If the antennal lobe's broadcast does not
  reach the V channel — V_ilPN and LN23 have no ORN input but V, and the broadcast in task 18
  ran through PN → PN and LN routes whose reach into V is unmeasured — the nulls pass and it is
  7/7; I put that at one chance in five.
- **MaleCNS v1.0, LIF 0.65.** 1, 2, 4 pass. Check 3: LN23 is inhibitory here, so PNm1 gets
  −195 per cell from the CO2 channel; it fires only if the whole-CNS ignition drives it through
  M_lPNm13 (294) and M_lPNm11 — likely at 0.65: **pass, for the wrong reason**. Nulls fail
  (ignition). **4/7.**
- **Adaptive LIF (FlyWire 1.0).** 4/7.
- **Rewired control.** FlyWire 0.45: 67 ORNs through random wiring reach nothing; 1–4 fail,
  nulls pass → **3/7**, specificity +0.14. MaleCNS: random wiring conducts to single cells at
  0.65 (RFC 21): 1–4 pass, nulls fail → 4/7, specificity 0.

The interesting outcome would be the nulls passing on FlyWire with 1–4: the broadcast antennal
lobe sparing the one channel the fly keeps private. The other interesting outcome is check 3
failing on MaleCNS — the GABA label on LN23 doing what the paper's staining says it should not.

## What would make this task wrong

- **PNm1's "CO2-only" is 18 % of its input.** The rest is multiglomerular PNs (M_lPNm11A–D,
  M_lPNm13, DA4m_adPN) whose glomerular sources are not single. The nulls assume those do not
  carry DA1/DM1; in a broadcast antennal lobe they will. That is the point of the null, but a
  failing null here says "the antennal lobe broadcasts", not "PNm1 is not CO2-specific".
- **LN23's transmitter on MaleCNS** (above). A wrong-sign edge in the dataset makes check 3 a
  test of the ignition, not of the channel.
- **PNvbi = V_ilPN** is the preprint's own mapping (bilateral targets confirm it); PNvuni =
  V_l2PN is not scored.
- **The 100 Hz convention** on 67 ORNs is a strong CO2 pulse; Lin 2013's high-sensitivity PN
  responds at 0.1 %. Rates in 1–4 are not comparable to recordings; the nulls do not depend on it.
- **Toy:** ORN_V → V_ilPN and → LN23 → PNm1; V_ilPN → LHPD5c1; the other glomeruli do not touch
  the channel, so the nulls pass trivially (MODELED). The broken-toy test adds DA1_lPN → PNm1
  and must fail exactly the first null.

## Outcome (recorded 2026-09-15, first run after pre-registration; `--jobs 6`)

| check | FlyWire 0.45 (3 seeds) | MaleCNS 0.65 (3 seeds) | predicted |
|---|---|---|---|
| 1. CO2 → V_ilPN | 431 Hz, pass | 432 Hz, pass | pass |
| 2. CO2 → LN23 | 187 Hz, pass | 326 Hz, pass | pass |
| 3. CO2 → PNm1 | 392 Hz, pass | 374 Hz, pass | pass (MaleCNS: "for the wrong reason") |
| 4. CO2 → LHPD5c1 | 427 Hz, pass | 428 Hz, pass | pass |
| 5. DA1 ↛ PNm1 (null) | **234 Hz**, fail | 409 Hz, fail | fail |
| 6. DM1 ↛ PNm1 (null) | 236 Hz, fail | 410 Hz, fail | fail |
| 7. DA1 ↛ V_ilPN (null) | **417 Hz**, fail | 422 Hz, fail | fail |
| score | **4/7** | **4/7** | 4/7 / 4/7 |
| rewired | 3/7, specificity +0.14 | 3/7, +0.14 | 3/7 / 4/7 |

Both brains scored exactly as pre-registered, and the MaleCNS shuffle did slightly worse than
predicted (random wiring did not carry 67 ORNs to the four readouts). Every condition is a
whole-brain event (8 % of FlyWire, 12 % of the CNS) and every readout but one sits at its
ceiling (417–432 Hz) whether the drive is CO2, cVA or DM1: the model's antennal lobe hands the
private CO2 channel to any glomerulus, as task 18 said it would.

The one node that stays private is **LN23**: 187 Hz under CO2 against 20 Hz under either other
odour on FlyWire (9×), 326 vs 59–75 Hz on MaleCNS (5×). It is the only cell in the circuit whose
excitatory input is ORN_V alone with no PN-side route, so the broadcast reaches it only through
the residual network. That makes the extraglomerular channel's *entry* CO2-specific in the model
even when its exit (PNm1, fed also by the multiglomerular M_lPNm11/13) is not. On MaleCNS PNm1
fires at 374 Hz under CO2 despite its LN23 input being inhibitory there (−195 per cell, the
GABA label the paper's staining contradicts) — the ignition drives it, as predicted, so the
check passes without the pathway.

A future model with antennal-lobe lateral inhibition would be scored on 5–7 for the first
time; until then this task, like 26, measures task 18's broadcast on one more channel, and the
LN23 ratio is the number worth keeping.
