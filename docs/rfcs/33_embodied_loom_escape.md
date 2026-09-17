# RFC: task 33 — the first embodied task: a loom makes the body jump, a flash and rest do not

Status: pre-registered 2026-09-17, before any real-brain run. Roadmap item 51 (Phase 7a), the
first task of the embodied track. **No development run on a real brain preceded this RFC**; the
body transducer was tuned on its own (a standing NeuroMechFly and a hand-timed command) and never
with a brain attached.

## The behaviour

A looming stimulus with r/v = 40 ms evokes one giant-fiber spike and a takeoff: the GF drives the
tergotrochanteral motor neuron (TTMn) through a giant mixed synapse (Tanouye & Wyman 1980; Allen
et al. 2006), the TTM extends the middle legs and the fly leaves the substrate within a few
milliseconds of the spike (Trimarchi & Schneiderman 1995; Card & Dickinson 2008 for the takeoff
sequence; von Reyn et al. 2014 for the GF spike near collision). A full-field brightening is not
a loom and does not fire the GF (von Reyn 2014; task 11); a fly at rest does not jump.

## What is new: a body

Every task so far reads spikes. This one hands them to a physics body — NeuroMechFly in FlyGym
2.1 (Lobato-Rios et al. 2022; Wang-Chen et al. 2024), MuJoCo, 0.1 ms steps — and scores what the
body *did*. The body is a **declared, fixed transducer** (`flybench/embodied/flygym_body.py`):

- **command** = a spike of TTMn where the dataset has a nerve cord (MaleCNS, the toy); where it
  has none (FlyWire) the GF stands in, plus the measured 0.93 ms GF → TTM delay (Augustin et al.
  2019, the constant of task 19). The task's YAML says which and the result notes which was used.
- **jump program** = +1.0 rad on both middle legs' trochanter–femur and femur–tibia pitch over
  5 ms, held 20 ms, released over 50 ms; one program per command, commands during a program are
  ignored (CONVENTION: the actuators are force-limited; this program lifts the thorax ~0.7 mm and
  every foot leaves the ground ~6–11 ms after the command; the real fly's legs extend in ~5–10 ms
  and it is airborne within ~10 ms of the GF spike — Card & Dickinson 2008).
- **takeoff** = all six ground-contact sensors read zero within 30 ms of a command. A physics
  event, not a threshold on a rate.
- **latency** = stimulus onset → takeoff, ms.

Feed-forward only. Nothing from the body returns to the brain; the loop is not closed and the
RFC does not claim it is. What the task measures is *when the brain commanded and whether that
was enough to leave the ground*, judged on the body.

## Conditions

`loom` — the task-4 convention, LPLC2 + LC4 at 150 Hz for 200–500 ms (MODELED: the optic lobe
assumed to have computed "loom"); `loom_eye` — a rendered loom through the flyvis front end
(task 32); `flash_eye` — a rendered flash through flyvis; `baseline` — nothing. Duration 1300 ms.

## Checks

1. `loom`: takeoff ≥ 1 (the body left the ground).
2. `loom`: takeoff latency < 300 ms from loom onset (CONVENTION: the loom convention starts at
   200 ms and runs 300 ms; a takeoff after the drive ended is not a response to it. The real fly
   takes off ~5–10 ms after the GF spike, which comes near collision).
3. `baseline`: takeoff < 0.5 (a fly at rest does not jump).
4. `flash_eye`: takeoff < 0.5 (the task-11 null, through the eye and the body). **Measured on
   the loom_eye condition too, but not scored there** — task 32 established that this front end
   does not reach the GF with a loom, so `loom_eye → takeoff` would be a second score for the
   same failure; it is reported.

Every condition also reports `n_commands` and `thorax_rise_mm`.

## Pre-registered predictions

- **FlyWire v783, LIF 0.45, 3 seeds.** The GF fires at ~430 Hz for the whole loom drive
  (task 4/13). Its first spike comes within ~10 ms of the drive onset; the body takes off
  ~11 ms later. Check 1 passes, check 2 passes with latency ~20–25 ms. Baseline: the network is
  silent at rest (task 1), no command, check 3 passes. Flash through the eye: task 32 measured
  GF 37 Hz to the flash → the body **jumps to the flash** → check 4 **fails**. Loom through the
  eye: GF 0 Hz → no takeoff (reported, unscored). **3/4.**
- **MaleCNS v1.0, LIF 0.65.** TTMn is real here (task 15 passes GF → TTMn on MaleCNS). Loom:
  takeoff, latency similar. Baseline: task 1 passes on MaleCNS at 0.65 (silent at rest) → no
  jump. Flash through the eye: GF 5.8 Hz (task 32) — does TTMn follow? Task 19 says GF → TTMn
  conducts; at 5.8 Hz over a second the GF spikes ~6 times and TTMn should spike at least once →
  a jump → check 4 fails. **3/4.**
- **Adaptive LIF 0.45.** Same as the reference on the loom (adaptation does not stop the first
  spike); flash: fewer GF spikes but not zero → still a jump. 3/4.
- **Rewired control.** Task 4's loom fails on the shuffle (GF gets no loom input) → no takeoff
  → checks 1–2 fail; baseline stays silent → check 3 passes; flash through the eye on shuffled
  wiring lights a fifth of the brain at random — the GF probably fires → check 4 fails. **1/4**,
  specificity +0.50. `random` (Erdős–Rényi matched): the same 1/4 or 0/4 (a dense random brain
  is not silent at rest).

The interesting outcomes: a flash that does *not* jump on either brain (the GF's flash response
in task 32 was a network effect and might not survive the 0.93 ms stand-in / the TTMn threshold),
or a loom latency far longer than 25 ms (a GF that starts late).

## What would make this task wrong

- **The body does no work.** By design: a fixed program. A brain that fires the GF once at the
  right time and a brain that fires it at 430 Hz get the same jump. The task scores *timing and
  specificity*, not the escape's quality; it cannot distinguish a single-spike GF from a tonic one
  (task 13 does).
- **The GF stand-in on FlyWire** assumes GF → TTMn conducts one-for-one, which task 19 measured
  on MaleCNS. A dataset where it does not would be scored on the GF, not the muscle.
- **The takeoff criterion** is the body model's ground sensors; a different body (flybody) or a
  different jump program changes the ~11 ms and the 0.7 mm, not the pass/fail structure.
- **Toy:** GF → TTMn added to the toy (a strong chemical contact, MODELED); the toy's loom
  detectors fire the GF, the GF fires TTMn, the body jumps. The toy has no flyvis flash response
  on the GF (task 32's flash was measured, unscored) — so the toy is expected to pass 4/4, which
  proves the pipeline runs, not that the fly jumps.

## Outcome (2026-09-17, scored runs, 3 seeds, `rewired` control)

| | FlyWire v783, LIF 0.45 (GF stand-in + 0.93 ms) | MaleCNS v1.0, LIF 0.65 (real TTMn) |
|---|---|---|
| loom → takeoff / latency | **yes, 17.1 ms** (3/3 seeds, sd 0.17 ms); 4 commands | **yes, 23.1 ms** (3/3, sd 0.13 ms); TTMn 62 Hz, 4.7 commands |
| baseline → takeoff | no (0 commands) | no (0 commands) |
| flash through the eye → takeoff | **yes, 257 ms** after flash onset (3/3); GF 37 Hz, 2.7 commands | **yes, 264 ms** (3/3); GF 5.8 Hz, TTMn 0.7 Hz, 1 command |
| loom through the eye (unscored) | no takeoff, 0 commands (GF 0 Hz) | **yes, 499 ms** (3/3) — with the GF at 0 Hz: TTMn 3.3 Hz by a GF-independent path |
| score · rewired · specificity | 3/4 · 2/4 · +0.25 | 3/4 · 2/4 · +0.25 |

**Both brains: 3/4, as pre-registered, check by check.** The loom convention makes the body leave
the ground 17 ms after the drive starts (GF first spike ~6 ms, + 0.93 ms, + ~10 ms for the legs
to clear the ground); a fly at rest stays put; the loom through flyvis never commands; and the
flash through flyvis makes the body jump a quarter of a second after the lights come up. Task 32
measured the GF's flash response as a rate; task 33 shows what it *does*: the reference model,
given an eye and a body, jumps at a brightening and not at a loom.

One prediction was wrong: the rewired control scored 2/4, not 1/4 (specificity +0.25, not
+0.50). Baseline stays silent on the shuffle as predicted; the other check it passes is the
flash null — on shuffled wiring the flash through the eye does *not* fire the GF (a single-seed
control run with per-check control records: `[loom ✗, latency ✗, baseline ✓, flash ✓]`). So the
GF's flash response is a property of the real wiring, not of "a fifth of the brain lit at
random": the specific path from the flyvis-driven types to the GF exists on FlyWire and not on
its degree-matched shuffle. Result files now record which checks each control passes
(`controls.<name>.checks`), so this question is answered from the file in future (the MaleCNS
run predates the change; its 2/4 is presumed the same pair).

**MaleCNS adds a finding the RFC did not anticipate.** With the real TTMn as the command, the
loom through the eye — which task 32 showed never reaches the GF (0 Hz here too) — *does* make
the body jump, at 499 ms after loom onset (700 ms before the movie's collision), on all three
seeds: TTMn fires at 3.3 Hz with the GF silent. Task 32 measured that the flyvis loom lights
15 % of the male CNS; some of that reaches TTMn without the giant fiber — the long-latency,
non-GF escape pathway that Engel & Wu 1996 and Card & Dickinson 2008 describe is at least
wired. Unscored here by design (task 32 owns the eye-to-GF failure); it is the obvious next
task: *TTMn without GF* on MaleCNS, with the GF silenced, scored against the long-latency
takeoff's timing.
