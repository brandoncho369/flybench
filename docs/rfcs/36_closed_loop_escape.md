# RFC: task 36 — the closed loop: the body's own eyes, an approaching object, and the jump

Status: pre-registered 2026-09-21, before any scored run. Phase 7b (ROADMAP item 51). Disclosure:
the loop's plumbing was checked on the toy before this RFC — the object is seen (dark ommatidia
rise from 308 to 424 per eye over the last 100 ms), flyvis rates reach 25–40 Hz in the last
50 ms, and the toy's TTMn issues no command — nothing was run on a real brain.

## What closes

Task 33 handed the brain a movie and the body a command. Here the brain's visual input *is* the
body's: every 10 ms NeuroMechFly's two compound eyes are rendered in MuJoCo (721 ommatidia each),
mapped one-to-one onto flyvis's 721-hexal retina, run through the pretrained flyvis network one
frame at a time with its state carried (bit-identical to a batch run), and the resulting rates
drive the connectome's own T4/T5/T2/T3/Tm/TmY cells for the next 10 ms — the task-32 front end,
live. A spike of TTMn (or the GF plus Augustin 2019's 0.93 ms where there is no cord) starts the
task-33 jump program on the body; the legs move; the eyes see the ground and the object from
wherever the body now is. Brain and body step together at 0.1 ms.

The object is a black sphere of radius 2 mm on FlyGym's white sky and dark ground, moving on a
kinematic path with contact disabled (it passes through a fly that did not move):

- `approach` — straight at the point between the eyes, 60 mm away, 50 mm/s: r/v = 40 ms, the
  geometry of every escape task in the suite; contact at 1,360 ms (object starts moving at 200 ms).
- `pass_by` — the same path shifted 10 mm to the fly's left: a fast near miss, expansion without
  collision.
- `static` — the object 60 mm ahead, motionless throughout (it is there during the settling
  period, so there is no onset).

Duration 1,500 ms; the standing scene's steady state is flyvis's resting activity.

## What the eye actually delivers (the toy's plumbing check)

With r/v = 40 ms the object's half-angle is atan(0.04/τ) at τ before contact: 14° at 160 ms,
34° at 60 ms, 45° at 40 ms. On a 721-ommatidia eye spanning the fly's field that is a handful of
ommatidia until the last 100 ms. flyvis's above-rest rates on the driven types reach 1 Hz at
τ = 160 ms, 13 Hz (3 cells > 5 Hz) at 60 ms, 39 Hz (9 cells) at 10 ms. The loom, seen by a real
eye at real resolution, is a late, small event — as it is for the fly, whose GF spikes when the
object subtends 20–40°, 55–110 ms before contact. Anything that needs the disc to fill the
field (the cached movie ended at 90° half-angle) gets ~50 ms of it here.

## Checks

1. `approach`: takeoff ≥ 1 — the body left the ground.
2. `approach`: takeoff latency < 1,160 ms from the object's start — before contact (CONVENTION:
   a takeoff after the object has arrived is not an escape; Card & Dickinson 2008 measure every
   takeoff before contact).
3. `pass_by`: takeoff < 0.5 — a near miss is not a collision (CONVENTION after Card & Dickinson
   2008 and von Reyn 2014: takeoff probability falls steeply off the collision course; a fly
   *may* jump at a 5-radius miss, so this is a convention, not a recording).
4. `static`: takeoff < 0.5 — a fly does not jump at a motionless object.

Measured on every condition: commands issued, thorax rise, closest approach of the object to the
eyes, and every readout's rate.

## Pre-registered predictions

- **Toy** (gain 1.0): its eye-driven detectors fire only at contact (docs/rfcs/34) — **2/4** (the
  nulls). The toy proves the loop runs, not that anything escapes.
- **FlyWire v783, reference LIF 0.45 (GF + 0.93 ms), 3 seeds.** Task 32: the eye loom never
  reaches the GF; live it is smaller still. No takeoff to the approach; none to the miss or the
  static object. **2/4**, checks 1–2 fail.
- **MaleCNS v1.0, reference LIF 0.65 (real TTMn).** Task 34's GF-free route fired TTMn at
  ~500 ms into the cached loom, while the disc was still small, from the 15 %-of-CNS spread the
  cached movie produced. Whether the live eye produces that spread is the open question: the
  live scene is half dark ground and the object is a few ommatidia until late. I predict a takeoff
  before contact on **some but not all seeds** (check 1 fails under the every-seed rule), the
  static object quiet, and the near miss — a fast dark object sweeping the eye — likely to fire
  the same spread route on at least one seed. **Central prediction 2/4**; 1/4 if the miss jumps.
- **Terminal-aware LIF** (both datasets): the eye routes are weaker still (M1b) — 2/4.
- **Rewired**: nothing reaches the command readout from the eye (tasks 33–35) — 2/4 on the nulls.

Nobody is predicted to pass. That is the point of putting the loop in the hard tier: the first
model whose optic lobe turns a real eye's late, small loom into a command before contact will
show it here, against the same body and the same physics as everyone else.

## What would make this task wrong

- **The eye–retina mapping** is a minimum-distance bijection between two 721-point lattices
  after whitening each axis, with the left eye mirrored (CONVENTION; nearest neighbour was tried
  first and was not a bijection, 563 of 721). A rotation error rotates the hexal
  lattice relative to flyvis's training orientation; the loom is radial and does not care, the
  near miss is directional and might.
- **Luminance** is the max of FlyGym's two photoreceptor channels in [0, 1]; the sky is 1.0 and
  the ground ~0.2. flyvis was trained on natural scenes; a two-tone world is not one.
- **Legs in view.** The eye renderer shows the fly's own front legs; during a jump they sweep
  the lower field. A real fly sees its legs too; the task does not pretend otherwise.
- **Cost.** ~45 s per condition on the toy (eye rendering 2 × 150 frames at 50 ms), ~2.5 min on
  MaleCNS; the task roughly doubles a suite run.

## Outcome (2026-09-21, 3 seeds, `rewired` control)

| | toy (gain 1.0, 1 seed) | MaleCNS v1.0, reference LIF 0.65 (real TTMn) | FlyWire v783, reference LIF 0.45 (GF + 0.93 ms) |
|---|---|---|---|
| approach → takeoff, latency from object start | yes, **1,186 ms** (26 ms *after* contact) | yes, 3/3, **1,100 ms** (1,111 / 1,151 / 1,039 — 10 to 120 ms before contact) | **no**, 3/3 (GF 0.0 Hz, LPLC2 0.0, 9 % of the brain active) |
| pass_by (10 mm miss) → takeoff | no | **yes, 3/3, 551 ms** | no (3 % active) |
| static → takeoff | no | no | no (1 %) |
| score · rewired · specificity | 3/4 | **3/4** · 2/4 · +0.25 | **2/4** · 2/4 · 0.00 |
| predicted | 2/4 | 2/4 (1/4 if the miss jumps) | 2/4 |

**MaleCNS: the loop closes and the fly jumps before contact — and also at the near miss.**
Both predictions about the reference on MaleCNS were wrong in the same direction: the live eye
drives the command on *every* seed, not some, and 10–120 ms before the object arrives. The route
is the one tasks 34–35 named: LPLC2 0.0 Hz, the GF 0.4 Hz, TTMn 4.1 Hz, 20 % of the CNS active —
the diffuse medulla-driven DN route to the GF-coupled interneurons, not the loom detectors. That
is also why the near miss jumps, on every seed and earlier (551 ms, while the object is sweeping
across the eye at 10 mm): the route answers "a dark thing moving on my eye", not "a dark thing
expanding at me". The motionless object, present throughout, does nothing (1 % of the CNS active,
TTMn 0). And the takeoff, 60 ms early, does not clear the object: the thorax rises 0.7 mm, the
object's closest approach to the eyes is 1.08 mm, inside its 2 mm radius. It is an escape command
in time and a failed escape in space — the body model's jump, not the brain's timing, is what
falls short there.

The shuffle: 2/4 on the nulls exactly as predicted; the specificity of +0.25 is the two checks
the real wiring makes and the shuffle does not (the approach takeoff and its timing).

The 169 older checks are bit-identical to the previous MaleCNS file.

**FlyWire: as predicted, 2/4.** With the GF standing in for the missing nerve cord, nothing
commands: the live loom never reaches the GF (task 32 live), LPLC2 and LC4 stay at 0 Hz, the
approach lights 9 % of the brain and the miss 3 %. The two nulls pass by silence; the shuffle
does the same, specificity 0.00. FlyWire's row is the reference submission through `flybench
evaluate` (verified); its 134 older checks are bit-identical.

**Reading both.** The only brain that closes the loop is the one with a nerve cord, and it
closes it through a route that does not discriminate approach from passage. The task's
purpose stands: a model whose optic lobe turns the eye's late, small loom into a command
before contact *and* holds still for a miss will be the first to score 4/4 here. The
terminal-aware rows have not been run on task 36 (M1b thinned the very route MaleCNS used;
the prediction stands at 2/4 for both) and show '–' until the next housekeeping rerun.
