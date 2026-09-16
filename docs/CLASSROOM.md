# Classroom bundle: three exercises on a connectome (ROADMAP item 58)

For a 90-minute open-Python slot (FlyWire Academy style). Everything runs on the toy connectome
with no download, or in the browser at [www.fly-bench.com](https://www.fly-bench.com); the
third exercise moves to the real brain if the room has the cache. Answers are at the bottom —
they are short, because the point of each exercise is the surprise, not the number.

Setup: `pip install git+https://github.com/brandoncho369/flybench` (or open
[`notebooks/01_toy.ipynb`](../notebooks/01_toy.ipynb) in Colab).

## Exercise 1 — Trace a reflex (20 min)

Open www.fly-bench.com, pick **FlyWire v783**, press **sugar GRNs** once, and watch the *what
fired* table for ten seconds.

1. Which cell types fire first, second, third? Write the chain down as `type → type → …` up to
   MN9 (the proboscis motor neuron). The table ranks by rate; the order of *appearance* is the
   pathway.
2. Press **bitter GRNs** while holding sugar (⏺). What happens to MN9? Which new types appear
   in the table, and what is their transmitter (hover the type)?
3. Now the question the benchmark asks: does the brain stop? Release everything and watch the
   *whole network* number for five seconds. Write down what it does. Then press **reset**.

In Python, the same experiment is six lines:

```python
from flybench import load_connectome, LIFSimulator, LIFParams, Stimulus
c = load_connectome("toy")                       # or "flywire783" if the cache is present
sim = LIFSimulator(c, LIFParams(gain=1.0))       # 0.45 on flywire783
res = sim.run(1500, [Stimulus(c.select("GRN_sugar"), rate_hz=100, t_start_ms=200, t_end_ms=700)])
mn9 = c.select("MN9")
print(res.rate_hz(mn9, 200, 700), res.rate_hz(mn9, 1000, 1500))   # during, after
```

## Exercise 2 — Break the model (30 min)

Every task in `tasks/` is a claim about wiring. The toy is hand-wired so the claims can pass;
your job is to find the edge each claim rests on.

1. Run the suite on the toy: `flybench run -c toy --seeds 2`. Which tasks fail even on the toy?
   Read their `basis:` lines in `tasks/` and say, in one sentence each, what the toy would need
   that a five-constant neuron does not have.
2. Cut the bitter pathway (the snippet is in the notebook, section 3) and rerun `bitter_suppression`.
   Now cut *only* the bitter local neurons' synapses onto MN9, leaving their synapses onto the
   taste interneurons. Does the task still pass? What does that tell you about where the
   suppression happens in the toy?
3. Turn the gain down until `sugar_to_proboscis` fails (`--gain 0.5`, `0.3`, …). Then turn it up
   until `stability` or `crosstalk` fails. Write down the window. On the real brain that window is
   0.40–0.45 and its edges are the two failure modes every whole-brain model has: nothing
   conducts, or everything does.

## Exercise 3 — Write a task (40 min)

Pick a reflex the toy has and no task scores yet, or invent one. Copy `tasks/02_sugar_to_proboscis.yaml`
to `tasks/99_mine.yaml` and change:

- the `readout` selector (run `flybench select -c toy '{cell_type: MN9}'` to see what a selector matches),
- the stimulus selector and rate,
- the checks — at least one positive check and one **null** check ("X must not fire"), each with a
  `basis:` that is a citation with a year or the word `convention` (the lint refuses anything else).

Then: `flybench lint tasks/99_mine.yaml`, `flybench run -c toy -t tasks/99_mine.yaml --controls rewired`.

1. Did your task pass on the toy? If not, is the task wrong or the toy? (Both are allowed answers;
   say which and why.)
2. What did the `rewired` control score? If it scored the same as the real wiring, your task is
   not measuring the connectome. What check would make it?
3. Write the three-line pre-registration the RFC template asks for: what you predict the real
   brain will do, before anyone runs it.

---

## Answer key

**1.** Sugar GRNs → taste interneurons (G2N-like on the toy; on FlyWire the second-order taste
cells the annotation calls `sugar/water` targets) → MN9 within ~10 ms. Bitter adds the GABAergic
bitter local neurons (`bitter_ln` on the toy) and MN9 drops to ~0 Hz. The network does *not*
stop on the real brain: ~8 % of it keeps firing at a constant rate until reset — the
`return_to_rest` failure, the clearest thing a better model must fix.

**2.** (1) On the toy the reference LIF fails `dose_response`, `adaptation`, `physiological_rates`,
`looming_dn_ensemble`, `gf_azimuth_invariance` and `pn_transfer_function`: all need graded
responses, memory or a rate ceiling below the refractory limit — dynamics, not wiring. (2) With
only bitter → MN9 cut the task still passes: the toy's suppression acts mostly at the taste
interneurons, upstream of MN9. (3) On the toy the window is wide (about 0.6–2); the point is that
it has two edges, and on the real brain they are 0.35 (taste dead) and 0.5 (bitter fails).

**3.** No fixed answer. A good task has a positive check and a null check, a `basis` on each,
passes on the toy, fails on `rewired`, and a prediction written before the real run. That is
exactly the rule every task in `tasks/` followed (`docs/rfcs/`), and a task that meets it is
worth a pull request.
