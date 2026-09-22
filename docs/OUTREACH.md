# Outreach drafts

Posts for Brandon to send; nothing here is sent automatically. Each is written for its venue's
norms; numbers are from `docs/FINDINGS.md` on 2026-09-21 (v0.2.0, DOI 10.5281/zenodo.22886374).

## Show HN

**Title** (80 chars max):
`Show HN: flybench – does a simulated fly brain still do what a real fly does?`

**Text:**

Last year the full wiring diagram of a fruit fly brain came out (FlyWire, 140k neurons), and
people dropped it into a leaky integrate-and-fire model and wired it to Minecraft and Doom. Every
one of those demos had to pick a synaptic weight and a global gain, and nobody checked whether
the simulated fly still did fly things.

flybench is that check: 36 tasks, each a published behaviour (sugar on the tongue extends the
proboscis, bitter cancels it, a looming shadow fires the giant fiber, a fly returns to rest…)
with a citation, a threshold with a stated basis, and a prediction written down before the first
run. Every row runs on shuffled wiring too, so "passes on any brain" is visible.

Things it found: the demos' gain of 1.0 has a fifth of the brain firing at 29 Hz — a seizure,
not a reflex; the working gain is 0.45. Put a real optic-lobe model (flyvis) in front of the
connectome and the giant fiber fires at a *flash* and not at a loom, the opposite of the fly.
Put a physics body (NeuroMechFly) behind it and it jumps at the flash. A whole-CNS point-neuron
model lets ascending neurons fire *backwards* from their brain-side synapses; keeping those off
the soma — no free parameters — makes the mushroom body sparse on both brains. And with the loop
closed through the body's own eyes, the male brain jumps before an approaching ball hits it, and
also at one that misses.

Everything is a YAML task, a JSON result and an RFC. Submissions are pull requests; CI runs them
on the real connectome. The browser version at fly-bench.com runs the same model live.

https://github.com/brandoncho369/flybench

## FlyWire community / connectomics Slack or forum

Subject: a behavioural benchmark for whole-connectome LIF models (FlyWire v783 + MaleCNS v1.0)

I've been building a benchmark for the "drop the connectome into a LIF" models that followed the
FlyWire release: 36 published behaviours as tasks (taste, escape, olfaction, grooming, steering,
egg laying, the compass…), each with cited thresholds and a pre-registered RFC, shuffled-wiring
controls, and now a flyvis front end and a NeuroMechFly body. Two datasets: FlyWire v783 and
MaleCNS v1.0 (with its nerve cord).

Two findings I'd value the community's read on:
1. Through flyvis, the LIF's giant fiber responds to a full-field flash and not to a loom (RFC 32),
   and on MaleCNS the loom reaches TTMn without the GF, through nine DN types converging on GFC2
   (RFC 35). Are those DN types (DNge048, DNa02, DNbe007, DNge006, DNg45…) known to anyone as
   loom-responsive?
2. A point-neuron model sums axo-axonic inputs into the soma, which lets ascending neurons fire
   backwards from their brain-side terminals. Treating those synapses as presynaptic modulation
   (neuPrint ROI counts, no free parameters) changes a lot (RFC M1/M1b). If anyone has a
   per-synapse axon/dendrite split for either dataset, that would sharpen it considerably.

Every threshold cites its source; if one is wrong, a citation fixes it in one line.
https://github.com/brandoncho369/flybench · DOI 10.5281/zenodo.22886374

## Authors of the behaviours (one email template)

Subject: your [paper] is a task in a connectome-simulation benchmark — is the threshold right?

Dear Dr [Name],

I maintain flybench, a benchmark that scores whole-connectome simulations of Drosophila against
published behaviour. Your [paper, year] is the basis of task [N], "[title]": [one sentence on
what the task checks and the threshold used]. The pre-registered prediction and the outcome on
FlyWire v783 and MaleCNS v1.0 are here: [RFC link].

I'd be grateful for two minutes of your time on one question: is [the threshold / the readout]
a fair reading of your result? If not, a corrected number with the figure it comes from is all
the task needs, and you would be credited as the task's author in the repository and its
citation file.

Thank you,
Brandon Cho

## Awesome lists (pull requests)

- awesome-neuroscience / awesome-computational-neuroscience: under "Benchmarks" or "Connectomics":
  `- [flybench](https://github.com/brandoncho369/flybench) — behavioural benchmark for
  whole-connectome simulations of Drosophila (FlyWire, MaleCNS): 36 cited tasks, shuffled-wiring
  controls, an optic-lobe front end and an embodied track.`
- FlyWire's "community tools" page: the same line plus fly-bench.com.

## Bluesky / X (one post, thread optional)

Put the whole fruit-fly connectome in a spiking model and ask it to do fly things. It extends
its proboscis to sugar (good), fires its escape neuron at a flash instead of a loom (bad), and
runs its ascending neurons backwards (a point-neuron artefact, now fixed with zero parameters).
36 cited tasks, every prediction written before the run. github.com/brandoncho369/flybench

## Where stars come from, honestly

Stars follow visibility, and visibility follows a post that makes one concrete claim a reader
can check. The claim here is "the demos' fly brain has a seizure at gain 1.0" or "the simulated
giant fiber fires at a flash, not a loom" — pick one per post. Post the HN version on a weekday
morning US time; answer every comment with a number and a file path. One post per venue; do
not cross-post the same text.
