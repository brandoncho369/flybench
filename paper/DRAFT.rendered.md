# Which build of the connectome a whole-brain fly model runs on changes what it can do

Brandon Cho, independent researcher

## Abstract

Whole-brain spiking models of *Drosophila* are built from "the FlyWire connectome", but that is not
one graph: synapse tables are re-predicted, edges thresholded, and each neuron's transmitter, which
fixes the sign of everything it does, is inferred, and left blank where the inference is weak. We
built flybench, a benchmark of 37 tasks drawn from published fly experiments, scored
against shuffled-wiring controls, with predictions committed before the first run for every task and
model change after the first 15. We used it to compare three builds of the same
139,255 neurons under the widely used leaky integrate-and-fire (LIF) model of
Shiu et al. (2024). At the gain where Shiu et al.'s graph passes its core reflexes, the build changes
the mean task score by as much as adding spike-frequency adaptation to the neuron model does
(+0.098, 95 % CI +0.042 to
+0.164, against +0.092); at the
reference model's own gain the builds do not differ detectably. Signing the
19,658 neurons whose transmitter the public release leaves blank, with every
edge unchanged, scores about as high as Shiu et al.'s graph. It restores part of the antennal lobe's
channel identity, and at gains 0.5–0.65 it is the only change under which a model steers away from
CO₂ while still steering toward attractive odours. It also moves the working gain: on the signed
build no gain lets the LIF pass all five core feeding and escape reflexes, while an adaptive LIF
passes them from 0.46–0.53, against
0.43–0.49 on the reference build. One failure is shared by
every build: driven through a connectome-constrained model of the eye, the escape pathway responds to
a flash and not to a looming object. An independent analysis with a different signing rule reproduced
the graph statistics and the loss of bitter suppression. Benchmarks of connectome models should state
which graph they ran on.

## 1. Introduction

Whole-brain models of *Drosophila* built directly from the FlyWire connectome (Dorkenwald et al.
2024) now drive simulated feeding, grooming and escape, and the leaky integrate-and-fire (LIF) model
of Shiu et al. (2024) has become a common starting point: its constants are reused, its gain retuned,
and its output wired to virtual bodies. Connectome-constrained models of the fly now span scales:
point-neuron models of the central brain driven by sensory input (Shiu et al. 2024), analyses of how
far the wiring constrains the network's dynamics (Pospisil et al. 2024), models of the visual system
constrained by the connectome or by behaviour (Lappalainen et al. 2024; Cowley et al. 2024), and
physics models of the body that such networks can drive (Wang-Chen et al. 2024; Vaxenburg et al.
2025). Benchmarks that score models against many measurements at once are established for primate
vision (Schrimpf et al. 2020). Whole-brain fly models are usually evaluated on a few behaviours chosen
by their authors, rarely against a control that destroys the wiring, and often without saying exactly
which graph they ran on.

"The FlyWire connectome" is not one graph. Synapses are detected automatically from the electron
micrographs (Buhmann et al. 2021), neurons are proofread and typed (Dorkenwald et al. 2024; Schlegel
et al. 2024), and the transmitter of each neuron, which fixes the sign of everything it does, is
predicted from the images with a confidence that varies from cell to cell (Eckstein et al. 2024).
Downstream, model builders threshold edges and decide what to do with neurons whose prediction is
too weak to publish. The graph's large-scale statistics are well characterised (Lin et al. 2024);
how much these construction choices change a simulation's behaviour is not.

We built flybench, a benchmark of 37 tasks drawn from published fly experiments,
scored against shuffled-wiring controls (Section 2), and used it to ask that question. Three builds
of the same 139,255 FlyWire v783 neurons differ in their scores, at a gain where
all three can work, by about as much as adding spike-frequency adaptation does (Result 1); each has
its own working gain, and one has none (Result 2). Signing the neurons whose transmitter the public
release leaves blank restores part of the antennal lobe's channel identity (Result 3) and is the only
change that makes a model turn away from CO₂ (Result 4). One failure is shared by every build:
through a model of the fly's eye, the escape pathway responds to a flash and not to a looming object
(Result 5).

## 2. The benchmark

**Tasks.** Each of the 37 tasks is a stimulus, a readout population and one or more
checks taken from a published experiment: sugar on the labellum extends the proboscis (MN9 fires);
bitter suppresses it; a looming object drives the giant fibre; the DA1 projection neurons respond to
their own odour and not to others; an attractive odour on one antenna biases the ipsilateral steering
neuron DNa02. A few tasks check physiology or stability rather than a behaviour (the network is
silent without input; rates stay in a physiological range). Every threshold names its source, a
published experiment whose DOI was checked against Crossref for author and year, or is marked as a
convention. 5 tasks form the *core* tier, the feeding and escape reflexes the reference
model was tuned to pass; the other 32 are *hard*. The tasks span 12
circuits (Fig. 1; Table S1 lists every task and its sources).

**Pre-registration.** The first 15 tasks, including the five core reflexes,
were written before the proposal process existed and carry no pre-registered predictions. From task
16 on, every task, and every change to the scoring rules, the model or the
graph, starts as a written proposal (an RFC) with predictions for the reference model, an adaptive
LIF, the male connectome and the shuffled control, committed to the public repository before the
first run on real wiring. Outcomes are recorded next to the predictions, including the wrong ones
(Table 1); the experiments in this paper are covered by RFC D1 (the graph builds) and RFC 37 (odour
valence).

**Controls.** Each task can be scored on three destroyed versions of the same graph: degree-preserving
rewiring (each neuron keeps its out-degree, weights and sign; targets are shuffled; Maslov & Sneppen
2002), an Erdős–Rényi graph matched in size and weight distribution, and a sign permutation. A task
that also passes on shuffled wiring is flagged non-diagnostic; a row's *specificity* is the mean task
score on real wiring minus the best control. Every row in this paper carries the rewired control.

**Scoring.** A threshold check has a margin *m*, the log₁₀ ratio of the measured value to the
threshold, signed so that *m* > 0 passes, and a graded score 1/(1 + 10^(−2*m*)): 0.5 on the threshold,
0.91 at 3.2× on the passing side. A check that carries the recorded mean and spread of its
measurement scores 1/(1 + exp(2(|*z*| − 2))) and passes when |*z*| < 2. A task's graded score is the
mean over its checks, averaged over seeds. Two gates prevent vacuous passes: a comparison between
conditions fails if every compared readout is at its refractory ceiling (RFC S1) or below 2 Hz (RFC
S2). A check passes only if the seed mean and every seed pass. This paper summarises a row by the
plain mean of task graded scores over the tasks every compared row ran; flybench's leaderboard ranks
by the interquartile mean (IQM) over tasks (Agarwal et al. 2021), and we report both where they
disagree.

**The toy.** A 3,872-neuron synthetic network is hand-wired so that every task can
pass. It proves a task is passable and its checks computable; it says nothing about the fly.

![](figures/out/fig1a_pipeline.png)
![](figures/out/fig1b_overview.png)

**Figure 1. The benchmark.** **A,** How one task is scored, with task 02 (sugar → proboscis) as the
example. **B,** Graded score of every task on six rows: the reference model (LIF, Codex ≥5 build, gain
0.45), the adaptive LIF on the same build, Shiu et al.'s constants at gain 1.0 on the Codex build,
the LIF on Shiu et al.'s graph at 0.7, the LIF on the signed build at 0.65, and the male connectome
(MaleCNS v1.0) at 0.65; three seeds each. Tasks are grouped by circuit, core tier first. "–": the task
cannot run on that row. Tasks that read the nerve cord run only on the male connectome, which has
one; the lateralised olfactory tasks run only on FlyWire, because the male connectome's olfactory
receptor neurons carry no soma side.

## 3. Results

### Result 1: three builds of the same neurons

The public FlyWire release (Codex v783) lists synapses per neuron pair and neuropil, keeping pairs
with at least five synapses (3,732,460 pairs). Shiu et al. (2024) distributed their
own graph of the same neurons, `Connectivity_783.parquet`, with no threshold
(15,091,983 edges; 37% of its synapses sit in pairs
of fewer than five) and from an earlier synapse table: on the 3,667,935 pairs the two
share, Codex counts a median 1.33× more synapses, and the sign agrees on
96.2%. The third difference is the one this paper turns on: Codex
leaves the transmitter blank for 19,658 neurons whose prediction is
low-confidence, mostly optic-lobe and sensory cells (6,262 of them
photoreceptors and other visual sensory neurons), and a build that reads a blank as excitatory, as
flybench's reference did, makes all of them excitatory. Signing each by the majority transmitter of
its own predicted synapses makes 5,493 of them inhibitory.

The three builds therefore carry about the same excitation and different inhibition (Fig. 2A:
E/I 1.87 for the reference build,
1.59 with the blanks signed,
1.48 for Shiu's graph). We compare them with the
same LIF at two gains: 0.45, the reference build's working gain, and 0.7, where Shiu's graph passes
its core reflexes. At 0.7 the mean graded score over the 29 tasks
every row ran is 0.625 on the reference build,
0.724 with the blanks signed and
0.710 on Shiu's graph (Fig. 2B). Paired over tasks,
signing the blanks adds +0.098 (95 % CI
+0.042 to +0.164;
17 tasks better, 3 worse) and Shiu's
graph adds +0.085 (+0.032 to
+0.149). For scale, adding spike-frequency adaptation to the reference
model at its own gain adds +0.092
(+0.020 to +0.171). The signed
build and Shiu's graph cannot be told apart (+0.013,
-0.056 to +0.091); their order depends
on the summary, since the IQM puts Shiu's graph ahead (-0.019).

At 0.45 the builds do not differ detectably (signed +0.015,
-0.100 to +0.128; Shiu's graph
-0.045, -0.154 to
+0.050): at the reference build's own gain, Shiu's graph and the signed
build are under-driven (Result 2). The effect of the build is therefore conditional on the gain, which
is itself a property of the build. Where it appears, it is not uniform (Fig. 2C): it is largest in
olfaction and in returning to rest after a stimulus, and three tasks get worse: dose response,
halting and bitter suppression. The blank neurons carry only
7.4% of the graph's synapses, so the effect is not a matter of how many
synapses changed sign but of where they are.

An independent analysis (Daniel Culotta, independent researcher, Italy; analyses run by AI
assistants under his direction; unpublished, personal communication, 2026) built Shiu's graph from
the same files and obtained the same edge counts and sign agreement. Signing the blanks by FlyWire's
top per-neuron prediction instead (8,564 neurons inhibitory), he also found the reference LIF loses
bitter suppression at every gain, and that the adaptive LIF passes all five core reflexes from gain
0.45 to 0.55. He notes three caveats: that window rests on three grid points with three seeds each
and no confidence intervals; about half of the score gained off the core comes from olfactory tasks,
where the newly signed neurons are low-confidence antennal-lobe local neurons; and the adaptive model
was tested after the reference model was seen to fail. Result 2 repeats the test on our signing rule,
with a finer grid and the predictions written first.

![](figures/out/fig2_graph_builds.png)

**Figure 2. Three builds of the same FlyWire v783 neurons.** **A,** Edges, and synapses summed by the
sign of the presynaptic neuron, per build. **B,** Mean graded score of the LIF on each build at gains
0.45 and 0.7, over the 29 tasks every row ran, three seeds each.
Bars: 95 % CI of each row's mean (bootstrap over tasks and seeds); differences between rows are
paired over tasks and their CIs are given in the text. Dashed line: the adaptive LIF on the reference
build at 0.45. **C,** Per-task change at gain 0.7, signed build minus reference build.

### Result 2: the working gain belongs to the graph

A whole-brain LIF has one free parameter that matters, the gain that scales every synapse, and
flybench fixes it per model as the *core window*: the gains at which the five core reflexes (rest,
sugar → proboscis, bitter suppression, loom → giant fibre, taste specificity) all pass on every seed.
We swept gain from 0.40 to 0.70 in steps of 0.01 on two builds with both neuron models, five seeds per
point (124 runs), with the predictions committed first (RFC D1).

With the blank transmitters signed, the LIF has no window
(0 of 31 gains
pass; Fig. 3). Below 0.63 the proboscis motor neuron MN9 does not respond to sugar on every seed; from
0.63 it does, but bitter no longer suppresses it. The two taste reflexes want opposite gains, and on
this build no gain gives both. A coarser sweep (steps of 0.05) had already found no window, against
our prediction of one at 0.55–0.60 (Table 1); the fine sweep's prediction, written after it, was that
none would appear at 0.01 resolution either. Adding spike-frequency adaptation opens a window of
8 points,
0.46–0.53 (predicted: at least 0.05 wide within
0.45–0.60), close to the 0.45–0.55 Daniel Culotta found with a different signing rule. Above it,
bitter suppression fails again.

On the reference build the LIF's window is 0.42–0.45
(4 points, predicted ~0.42–0.47): flybench's reference gain of
0.45 sits on its upper edge, and one step above it bitter suppression fails. The adaptive LIF passes
from 0.43–0.49, 7
points, more than twice the width we predicted (at most 0.03): we had read a single passing point on
the coarse grid as a narrow window. Signing the blanks does not widen the adaptive window
(8 points against
7); it shifts it up by about 0.03 and removes the LIF's.
Every row fails the same way at its edges: below a window, sugar does not reliably drive MN9; just
above, bitter no longer suppresses it. On the reference build, higher still, the whole brain ignites
and the sugar and loom checks fail too; on the signed build, nothing but bitter suppression fails from
there up to 0.70.

The working gain is therefore not a property of the neuron model alone. It moves with the transmitter
assignment of neurons no core task reads, and a gain tuned on one build carries no guarantee on
another. The core tier was defined by what the reference model passes, so these windows measure each
build against the reference's own reflexes; they compare builds, they do not rank them.

![](figures/out/fig3_gain_windows.png)

**Figure 3. The core window per build and neuron model.** Each cell is one gain (0.40–0.70, steps of
0.01) run on the five core tasks with five seeds. Filled: all five core reflexes pass on every seed.
Grey: at least one fails, lettered S (sugar → proboscis), B (bitter suppression), L (loom → giant
fibre), T (taste specificity) or R (rest). Right: the longest run of passing gains.

### Result 3: the antennal lobe's channels

DA1 projection neurons in the fly respond to their own odour, cVA, and little to others (lifetime
sparseness 0.90; Schlief & Wilson 2007). On the reference build at its working gain they fire at
434 Hz to their own glomerulus and at
400 Hz to each of seven others: lifetime sparseness
0.001 (Fig. 4). We had recorded this as "the antennal lobe
carries no channel identity". With the blank transmitters signed, the response to other glomeruli
falls to 80 Hz while the own-channel response stays at
413 Hz (sparseness
0.50; 0.32
at gain 0.65). Neither adaptation nor Shiu's graph does this: the adaptive LIF on the reference build
reaches 0.066, and Shiu's graph at 0.7
0.000. Part of the earlier finding was therefore a property
of the build, not of the model; the rest stands, since
0.50 is still far from 0.90. The signed build has no gain
at which every core reflex passes (Result 2), so this is a statement about the antennal lobe on that
build, not about a model that passes the rest of the benchmark.

![](figures/out/fig4_antennal_lobe.png)

**Figure 4. DA1 projection neurons and their own channel (task 18).** DA1 PN rate when the receptor
neurons of one glomerulus are driven at 100 Hz, on the reference build and the signed build at gain
0.45. Bars: mean of three seeds; dots: each seed. DA1's own ligand is cVA. Legend: lifetime sparseness
across the eight conditions, against 0.90 measured in the fly (Schlief & Wilson 2007).

### Result 4: odour valence

Task 37 drives the receptor neurons of one glomerulus on the left antenna and reads the left and
right DNa02. In the fly, DM1, DM2 and VA2 are attractive and V (CO₂) and DA2 (geosmin) aversive.
On the reference build every channel drives the stimulated side harder, including CO₂
(327 Hz left against
33 Hz right): the model would turn toward everything it
smells (Fig. 5). Shiu's graph does the same. With the blank transmitters signed, from gain 0.5 to 0.7
CO₂ on the left antenna drives the right DNa02 instead, on every seed (at 0.65,
0.7 against
14 Hz), and at 0.5, 0.6 and 0.65 every attractive
channel still biases the left: the only separation of an aversive from an attractive channel in any
row. It is not robust across gain: at 0.45 the signed build turns toward CO₂, and at 0.55 and 0.7 an
attractive channel fails (RFC 37). The rates are modest, the asymmetry of the attractive channels varies between seeds, and
the signed build fails bitter suppression at every one of these gains. We had predicted the
separation would not happen. Geosmin, carried by few receptor neurons, reaches DNa02 on no build.

![](figures/out/fig5_valence.png)

**Figure 5. Odour valence (task 37).** The receptor neurons of one glomerulus on the left antenna are
driven at 100 Hz; the asymmetry (L − R)/(L + R) of the left and right DNa02 rates is +1 for a turn
toward the stimulated side and −1 for a turn away. Shaded: attractive channels (should be > 0);
unshaded: aversive (should be < 0). The reference build and Shiu's graph at their working gains; the
signed build, which has no gain passing every core reflex, at 0.65, the best of its gains on this
task. Large dots: from seed-mean rates; small dots: each seed. Hollow: both DNa02 below 2 Hz (no
response).

### Result 5: vision through a model of the eye

Task 32 renders a looming disc and a full-field flash through the flyvis model of the fly's optic
lobe (Lappalainen et al. 2024) and drives the connectome's own visual neurons column by column. On
every build and on the male connectome, the flash drives the giant-fibre readout (reference build
37 Hz) and the loom drives nothing at the working gains, not
even the loom detectors LPLC2 and LC4 (Fig. 6); only Shiu et al.'s constants at gain 1.0 give the loom
a response (4 Hz), still below the flash
(12 Hz). This failure does not depend on the build, and the account
recorded in RFC 32 suggests why. The loom reaches the driven T5 cells as a sparse late edge: even in
the last frame only 10–15 % of columns exceed 20 Hz, about 1 Hz averaged over the field, which is
roughly 0.07 mV onto an LPLC2 through its ~110 T5 synapses. The flash is a synchronous transient on
every column at once. With these inputs, a point neuron that sums its synapses has no way to prefer
the first over the second, whatever the signs. In the fly, LPLC2's loom selectivity comes from the
layer-specific radial arrangement of its T4/T5 inputs and from inhibition of inward motion through
lobula-plate interneurons (Klapoetke et al. 2017), both of which depend on where on the dendrite each
input lands, which a point neuron pooling every synapse into one compartment discards. An alternative
we have not tested is the interface itself: flyvis outputs are converted to Poisson rates on the
connectome's cells, and a different mapping could change the loom's drive. The reflex tasks that drive
LPLC2 and LC4 themselves at 150 Hz were doing all the work of loom detection. The account was first
drawn from development runs before the RFC's outcome was recorded, so it is an explanation, not a
pre-registered prediction.

![](figures/out/fig6_vision.png)

**Figure 6. Through a model of the eye, a flash drives the escape readout and a loom does not (task
32).** A looming disc and a full-field flash are rendered through the flyvis optic-lobe model
(Lappalainen et al. 2024), whose outputs drive the connectome's own visual neurons column by column.
Bars: giant-fibre readout rate in the task window, mean of three seeds, for each build, Shiu et al.'s
constants at gain 1.0 and the male connectome. The loom gives 0 Hz on every seed of every row except
Shiu et al.'s constants; per-seed flash rates are not stored.

## 4. What this benchmark cannot tell you

**A pass is not a mechanism.** A task passes when a readout crosses a threshold taken from an
experiment. The model can cross it for a reason the fly does not have; several RFCs record a pass
"for the wrong reason" (Table 1). A failure is more informative than a pass, and specificity against
shuffled wiring is the minimum evidence that a pass depends on the connectome at all.

**Readouts are inferred.** Many tasks read a cell type as a stand-in for a behaviour: MN9 for
proboscis extension, the giant fibre for takeoff, the left/right DNa02 ratio for a turn. Task 37's
turn-away from CO₂ is a DNa02 asymmetry, not a turn; the CO₂ avoidance that flies show also runs
through the lateral horn and the mushroom body, which this readout does not test.

**Few seeds, threshold checks.** A check passes only if it passes on every one of three seeds (five
in the gain sweep). Near a threshold, outcomes are decided seed by seed, and a small change to a
stimulus can flip seeds in either direction (task 06 in flybench 1.0.1). The graded score is a
monotone transform of the margin to a threshold, not a likelihood; a mean over tasks weights every
task equally whatever its difficulty, and its value depends on the summary (mean or IQM).

**Not every task is pre-registered.** The first 15 tasks, the five core
reflexes among them, predate the proposal process, and the core tier was chosen as the reflexes the
reference model passes. Many thresholds are conventions, marked as such in the task files.

**The toy is not biology.** The 3,872-neuron toy is wired by hand so that every task
can pass; it shows a task is passable and computable, nothing about the fly.

**Datasets.** The male connectome lacks soma sides for the olfactory receptor neurons, so the
lateralised olfactory tasks run on FlyWire only. FlyWire's transmitter predictions have no histamine
class (Eckstein et al. 2024): of the 11,151 photoreceptors, which are
histaminergic and inhibitory in the fly (Hardie 1989), most are excitatory in every build
(9,896 in the reference build,
9,119 with the blanks signed, 8,391 of
10,319 with outputs in Shiu's graph). No current task drives them (task 32
enters the connectome downstream, at T4/T5 and the transmedullary cells), but any task that does will
inherit the wrong sign.

**The reference build is kept, not fixed.** flybench 1.0 keeps the build that reads a blank
transmitter as excitatory as its reference, because the signed build has no gain at which all five
core reflexes pass (Result 2). Both builds are pinned and every result file names its graph; the
choice is documented, not hidden, and a later version can change it with a new reference row.

## 5. Predictions we got wrong

Of 27 pre-registered RFCs, about 85 of roughly 285 individual predictions (each scored check per
dataset, each predicted score, control score or named magnitude; counted by hand from the RFC outcome
sections) were wrong. Misses cluster in two assumptions: that a given gain makes the whole brain
ignite, and that the direct wiring between a stimulus and a readout decides the outcome. Table 1
lists the most informative. Every row is quoted from the outcome section of the named RFC, or from
`docs/FINDINGS.md`, in the repository.

**Table 1.** Selected wrong predictions. FW, FlyWire v783 reference build; MC, MaleCNS v1.0.

| RFC | predicted | measured | row | what it taught |
|---|---|---|---|---|
| 18 DA1 sparseness | sparseness 0.2–0.5 | 0.0009 | FW 0.45 | one glomerulus drove every PN; partly the blank-sign default (Result 3) |
| 19 GF → muscle | GF → TTMn 1.8–2.5 ms; legs before wings | 11.8 ms; wings 1.2 ms first | MC 0.65 | the missing gap junction is about one spike being enough, not about delay |
| 21 LC → DN matrix | LC16 → MDN excites (the surest positive) | 0 spikes | FW 0.45 | no direct or two-hop path exists; a functional result had been read as a synapse |
| 21 LC → DN matrix | 9/16, specificity −0.13 | 14/16, specificity +0.44 | MC 0.65 | a high gain is not "everything reaches everything" |
| 23 size principle | 0.95 of the pool recruited; shuffle ties | 0.47; shuffle 0.81 (specificity −0.33) | MC 0.65 | inhibition onto small motor neurons is size-structured; the shuffle destroys it |
| 24 optic flow | wrong-side DNp15 < 2 Hz | 51 Hz | FW 0.45 | one H2 cell lights 8.6 % of the brain |
| 25 grooming vs backward | 3/4 | 0/4 | FW 0.45 | network state (DSOG1 inhibition) beat a 4:1 two-hop wiring ratio |
| 28 DNa02 vs DNa01 | one DN ignites the CNS | 0.0 % active | MC 0.65 | a lone descending neuron on a silent cord moves nothing (led to the 2 Hz floor gate) |
| 29 EPG ring | bump in cue window, 3/7 | 1/7; MC ring 0 Hz in the dark | FW 0.45, MC 0.65 | one transmitter label (ExR6) produced opposite failures on the two datasets |
| 30 egg laying | oviEN → oviDN ≈ 0–2 Hz | 14.3 Hz | FW 0.45 | steady-state synapse arithmetic misses local recruitment |
| 35 GF-free route | silencing every DN abolishes TTMn | 3.17 spikes/neuron | MC 0.65 | point neurons fire ascending neurons backwards from axo-axonic input |
| M1 terminal synapses | no other task changes | 3 tasks improve (high salt: MN9 183 → 0 Hz) | MC 0.65 | the same artefact explained an unrelated taste failure |
| 37 odour valence | adaptive LIF 3/5 | 0/5 | adaptive 0.45 | adaptation made the DNa02 pair winner-take-all, decided by seed |
| D1 + 37 | signed build 3/5 ("signs fix inhibition, not valence") | 4/5; CO₂ turns away | signed 0.5–0.65 | the only aversive/attractive split on the board was hidden by a default (Result 4) |
| D1 graph | Shiu's graph adds ≤ +0.03 at gain 0.7 | +0.07 | Shiu 0.7 | construction matters as much as the neuron model (Result 1) |
| D1 sweep | signed build window 0.55–0.60 | no window | signed LIF | correct signs make the proboscis reflex switch-like (Result 2) |
| D1 fine sweep | adaptive window ≤ 0.03 wide | 0.43–0.49 | adaptive, Codex | one passing point on a coarse grid is not a narrow window |
| task 06 (FINDINGS) | adaptive LIF keeps the reflex at the measured 65 Hz | 0/3 seeds (26 → 2 Hz) | adaptive 0.45 | at the rate a real sugar receptor fires, the adaptive model's reflex does not conduct |

## Methods

**Model.** Every neuron is the same current-based LIF with Shiu et al.'s constants: resting and
reset potential -52.0 mV, threshold -45.0 mV, membrane time constant
20.0 ms, synaptic time constant 5.0 ms, refractory period
2.2 ms, synaptic delay 1.8 ms, 0.275 mV per synapse
scaled by a global gain, integration step 0.1 ms. The adaptive variant adds a
spike-triggered adaptation current (b = 2 mV, τ = 200 ms; Benda & Herz 2003).

**Stimuli and readouts.** As in Shiu et al. (2024), stimulated neurons are forced to spike as
independent Poisson processes at the task's rate (subject to refractoriness), from the task's start
to its end time; a ramp stimulus changes the rate linearly. Neurons are selected by FlyWire
annotations (cell type, class, side). A readout is the mean rate of its population in the task's
analysis window. Conditions run 0.5–2 s of simulated time (1 s or less for most tasks). Task 32's stimuli are the
flyvis model's per-column outputs, converted to Poisson rates on the matching connectome cells.

**Graphs.** All builds are pinned by a SHA-256 fingerprint over neuron ids, the sparse weight
matrix and annotations; a run refuses an unpinned graph. Reference build: the FlyWire Codex v783
download (codex.flywire.ai: filtered connections, transmitter predictions, annotations), synapses
summed across neuropils, pairs ≥ 5 kept, sign from the presynaptic neuron's transmitter (ACh,
dopamine, serotonin, octopamine excitatory; GABA, glutamate inhibitory; blank excitatory)
(`3002ef5f…`). Signed build: identical, except that a blank neuron takes the
synapse-weighted majority transmitter of its own rows in the Codex connection table
(`27dc0261…`). Shiu's graph: `Connectivity_783.parquet` from Shiu et al.'s
repository (github.com/philshiu/Drosophila_brain_model), with their signs, on the same neuron index,
annotations and positions (`fd8ac1e5…`). Male connectome: MaleCNS v1.0
from neuPrint (Janelia FlyEM 2025), same rules as the reference build.

**Controls.** The rewired control shuffles each neuron's targets while keeping its out-degree,
weights and signs (Maslov & Sneppen 2002), with a fixed seed; it is run with the same seeds and
stimuli as the real graph.

**Runs.** Three seeds per condition (seeds 0, 1, 2) with the rewired control, from flybench
1.0.1 (Zenodo, doi:10.5281/zenodo.23655868). Each (task, wiring) unit is an independent
seeded simulation; parallel runs are bit-identical to serial ones. The gain sweep of Result 2 ran the
five core tasks only, five seeds per point, gains 0.40–0.70 in steps of 0.01; its result files and the
script that reads the windows (`scripts/core_window.py`) are in the repository
(`results/sweeps/d1_core_fine/`). Version 1.0.1 adds the sweep, the three-seed Codex row at gain 0.7
and task 06 rerun at the sugar-receptor rate its cited figure shows (65 Hz, not the 80 Hz of 1.0.0).
Each result file records the code version, parameters and graph fingerprint it ran with.

**Statistics.** Rows are compared over the tasks both ran. A paired difference is the mean over tasks
of the difference in task graded score; its 95 % CI comes from a hierarchical bootstrap (tasks
resampled with replacement, then each row's seeds resampled within each task; 10,000 draws). The
same procedure gives the CI of the IQM difference. A task counts as better or worse when its score
moves by more than 0.01. The script (`paper/figures/stats.py` in the repository) reads the archived
result files.

**Compute.** Runs used a laptop (Intel Core i7-13700HX, 32 GB RAM) with three worker processes of
about 2.2 GB each. A row of the benchmark took between 1 and 33 CPU-hours; each result file records
its own cost.

**Availability.** Code, tasks, RFCs, every result file, and the scripts that make this paper's
figures, statistics and numbers (`paper/`): github.com/brandoncho369/flybench,
archived as doi:10.5281/zenodo.23655868; interactive explorer and leaderboard: www.fly-bench.com.

## Acknowledgements

Daniel Culotta reported that the benchmark's "Shiu 2024" row did not run on Shiu's graph, and
independently replicated the graph comparison and the sign result.

## Funding

This work received no external funding.

## Use of AI tools

The benchmark's code, the task files, the figure scripts and drafts of this text were written with
Claude (Anthropic), an AI assistant, working under the author's direction, including the
pre-registered predictions, which were committed to the repository before each run. The author
chose what to test and what to report and is responsible for the content; every number in the text
is filled in by script from the result files. Daniel Culotta's analysis (Result 1) was likewise run
with AI assistants under his direction.

## Competing interests

None.

## References
