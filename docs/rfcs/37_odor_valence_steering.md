# RFC: task 37 — one antenna's attractive channel steers toward, an aversive one away

Status: pre-registered 2026-10-20, before the first run on any dataset. Prompted by Daniel Culotta
(email, 2026-10-19): in his recalibrated Shiu model, DNa02 steering across Knaden et al.'s 110
odours tracked total receptor activation (ρ = 0.69), not measured attraction (ρ = −0.04).
flybench has taste valence (tasks 3, 5, 20) and the CO2 pathway (27), but no test that odour
*sign* reaches a motor command.

## The behaviour

- **Single ORN types carry a sign.** Optogenetic activation of one ORN type in walking flies with
  wind: DM1, DM2 and VA2 (among eight types) each attract; DM1 unusually strongly (Bell & Wilson
  2016, Neuron 91:425; threshold at mean ORN rates of 10–20 Hz; free-walking chambers, n = 32–72
  per genotype). DM1 and VA2 are required for attraction to vinegar (Semmelhack & Wang 2009,
  Nature 459:218).
- **Two dedicated aversive channels.** V (Gr21a/Gr63a, CO2): activating these ORNs alone is
  sufficient for avoidance (Suh et al. 2004, Nature 431:854; weak repulsion in Bell & Wilson).
  DA2 (Or56a, geosmin): a single dedicated channel whose activation alone causes aversion
  (Stensmyr et al. 2012, Cell 151:1345).
- **Lateralisation.** ORN axons project to both antennal lobes but release more transmitter
  ipsilaterally, and flies turn toward the antenna with the stronger attractive input (Gaudry et
  al. 2013, Nature 493:424).
- **Readout.** DNa02 activity predicts ipsilateral turning, and unilateral DNa02 activation gives
  an ipsilateral steering bias (Rayshubskiy et al. 2025, eLife 13:RP102230; task 28).

## What the task measures

Five conditions, each the **left-antenna** ORNs of one glomerulus (`cell_type: ORN_X`, `side:
left`) at 100 Hz for 500 ms. Readouts: DNa02 left and right.

| choice | tag |
|---|---|
| channels and their signs: DM1, DM2, VA2 attractive; V, DA2 aversive | MEASURED (papers above) |
| one antenna stands for a lateral odour source | INFERRED (Gaudry 2013: ipsilateral release bias) |
| DNa02 L/R asymmetry as the turn readout | MEASURED for DNa02 → turn (Rayshubskiy 2025); INFERRED that odour turns go through it |
| "aversive → turn away" for one-antenna input | INFERRED: the aversion papers measured approach/avoid, not lateral turns |
| 100 Hz drive | CONVENTION (tasks 8, 17, 18); Bell & Wilson's behavioural threshold is 10–20 Hz |
| > 1 / < 1 on the L/R ratio | CONVENTION (task-18 direction convention) |

Checks: for each attractive channel, DNa02_left / DNa02_right > 1; for each aversive channel, < 1.
RFC S2 applies: if both DNa02 are below 2 Hz the check fails (`floored`), so a silent DN cannot
pass the aversive "< 1". There are no null checks.

The trap this is built to catch: a model whose turns follow how hard the antenna is driven, not
the channel, turns toward on all five and scores 3/5. Valence is needed for 5/5.

## Pre-registered predictions

| row | prediction | why |
|---|---|---|
| reference LIF, FlyWire 0.45 | **3/5**: all three attractive pass, both aversive fail (ipsilateral bias everywhere) | FINDINGS 2026-09-14: at the window gain any glomerulus drives every PN to ceiling; whatever reaches DNa02 is the broadcast, lateralised only by the ipsilateral ORN bias. Second likeliest: 0/5, DNa02 silent (floored) |
| adaptive LIF 0.45 | 3/5, same pattern | adaptation lowers rates, not channel identity |
| MaleCNS 0.65 | 3/5 | same broadcast (task 8: 91 % of PNs) |
| Shiu graph, 1.0 / 0.7 / 0.45 | 3/5 / 3/5 / 0–3/5 | Daniel's ρ(activation) = 0.69 on this graph |
| `rewired` | about 2.5/5 (random asymmetry), or 0/5 floored | degree-preserving shuffle destroys the ipsilateral route |
| toy | 5/5 | MODELED: left attractive ORNs → left DNa02, left aversive ORNs → right DNa02 |

## What would make this task wrong

- **ORN count asymmetry.** Left counts per type on FlyWire: DM1 35, DM2 29, VA2 34, V 34, DA2 16
  (see `flybench select`). Equal rate is not equal drive; a fails-on-DA2-only result may be the
  16 cells, not the sign.
- **The readout may be wrong for aversion.** If aversive odours cause slowing or backing up
  (MDN) rather than turning away, the "< 1" checks test an INFERRED behaviour. A pass on the
  attractive half with DNa02 symmetric under V and DA2 would be consistent with that.
- **The odour-level version** (Knaden 2012's 110 odours driven by Hallem & Carlson 2006 rates,
  rank correlation with attraction) is the stronger test. It is not this task because no copy
  of the per-odour attraction indices is reachable without the paper's supplement; it is the
  follow-up.
- **Rates.** At 100 Hz the antennal lobe is saturated (task 17). A 20 Hz variant would sit at
  Bell & Wilson's threshold; recorded as a follow-up, not run here.

## Outcome (first rows; FlyWire Codex, adaptive and MaleCNS pending)

| row | measured | predicted |
|---|---|---|
| toy | 5/5 every seed; rewired toy fails | 5/5 ✓ |
| LIF 0.7, Shiu graph (3 seeds) | **3/5**: the three attractive pass, V and DA2 fail, every seed; rewired 0/5 | 3/5 ✓ (that row was not predicted separately; the 1.0 row's 3/5 was) |

**Steering follows the stimulated side, not the channel.** Every one of the five channels drives
the left DNa02 at 17–30 Hz and leaves the right one at 0 Hz; one glomerulus on one antenna lights
8 % of the brain. A model with valence would split the five; this one turns toward all of them.
Same conclusion as Daniel's 110-odour analysis (ρ = 0.69 with activation, −0.04 with attraction),
now as a task any row can be scored on.
