# Running flybench on MaleCNS v1.0 (the Minecraft brain)

The viral "fly brain in Minecraft" and Beat Saber demos ran the Shiu 2024 LIF model on the
**male** central nervous system connectome (Janelia FlyEM, neuPrint dataset `male-cns:v1.0`,
176,422 neurons, 6.29 M edges with ≥5 synapses) at global gain 0.65. flybench was written
against FlyWire FAFB v783 (female, brain only). This page records how the two datasets' names
were reconciled so both can be scored on the same tasks.

```bash
flybench fetch-neuprint data-malecns          # anonymous, ~5 min, resumable
flybench build data-malecns --name malecns
flybench run -c malecns --config configs/malecns_minecraft.yaml --seeds 3 -o results/malecns-gain-0.65.json
```

## Name mapping

| population | FlyWire v783 | MaleCNS v1.0 | how the MaleCNS set was chosen |
|---|---|---|---|
| MN9 (proboscis motor) | `cell_type: CB0701` (2) | `cell_type: MN9` (2) | named directly |
| Giant Fiber | `cell_type: DNp01` (2) | `cell_type: GF` (2) | named directly |
| looming (LPLC2, LC4) | same names | same names | named directly |
| DA1 projection neurons | `DA1_(l\|v\|ad)PN` | same names | named directly |
| all descending neurons | `super_class: descending` | `super_class: descending_neuron` | regex `^descending` |
| **sugar GRNs** | `sub_class: sugar/water` (129) | labellar bristle `LB3a–d` (77) | connectivity, below |
| **bitter GRNs** | `sub_class: bitter` (65) | labellar bristle `LB1a–d` (38) | connectivity, below |

MaleCNS does not label gustatory neurons by taste modality; it groups labellar bristle GRNs
anatomically as `LB1a … LB4b`. It does, however, carry Shiu et al. 2022 (eLife, "Taste quality
and hunger interactions in a feeding sensorimotor circuit") names for the *second-order* taste
neurons in its `synonyms` field. Summing synapses from each labellar type onto those named cells:

| type | n | → sugar second-order (G2N-1, Clavicle, Zorro, Usnea, Phantom, Fudog) | → Scapula (bitter second-order) |
|---|---|---|---|
| LB1a | 11 | 0 | 92 |
| LB1b | 6 | 0 | 351 |
| LB1c | 16 | 23 | 1720 |
| LB1d | 5 | 0 | 68 |
| LB3a | 17 | 1586 | 0 |
| LB3b | 11 | 511 | 0 |
| LB3c | 23 | 2563 | 0 |
| LB3d | 26 | 1755 | 0 |

The split is clean: LB3 types are the sugar pathway, LB1 types the bitter pathway. LB2 and LB4
types make only weak contacts with either (some are likely water/mechanosensory) and are left
out of both stimuli. Pharyngeal and taste-peg GRNs are excluded on both datasets.

This is an inference from wiring, not a label the annotators gave, so it is stated here rather
than hidden in a selector. If Janelia publishes modality labels, the selectors should switch to
those and this table becomes a consistency check.

## Results: the reference model on the male CNS (3 seeds each)

| gain | core | sugar → MN9 | bitter → MN9 | looming: CNS active | after sugar ends | verdict |
|---|---|---|---|---|---|---|
| 0.45 | 0.57 | 0 Hz | 1.2 Hz (2/3 seeds pass) | 6.0% ✓ | quiet ✓ | vision works, taste never reaches the proboscis |
| 0.50 | 0.57 | 4.6 Hz (1/3 seeds) | 72 Hz | 9.4% ✓ | 2/3 seeds quiet | taste is a coin flip; bitter already triggers feeding |
| 0.55 | 0.50 | 0 Hz | 129 Hz | 10.3% | quiet | bitter feeds, sugar doesn't |
| **0.65** (Minecraft) | 0.57 | 175 Hz | 55 Hz | 11.9% | 14.7 Hz network, MN9 293 Hz, forever | everything fires; the brain cannot say no |

Looming → giant fiber passes at every gain (GF pinned near its 2.2 ms refractory ceiling, ~430 Hz);
a uniform flash is correctly ignored at every gain. Odour: 88–91% of all antennal-lobe projection
neurons respond to one odour at every gain tested. "Looming recruits the takeoff ensemble" fails
at every gain (22–39% of all descending neurons fire).

**There is no gain at which this model does both taste and vision on this dataset.** On FlyWire
v783 both fit inside one window at 0.45. Two things make the male taste pathway need more drive:
fewer labellar sugar GRNs (77 vs 129, and FlyWire's set includes water cells), and the
neurotransmitter predictions: 10 of the 77 male sugar GRNs are predicted glutamatergic and 19
"unclear". Real GRNs are cholinergic; under the Shiu sign convention glutamate is inhibitory, so
13% of the sugar input pushes MN9 the wrong way, and three of the largest sugar second-order
targets (Billiards, Quasimodo, Usnea) are predicted GABA here. The pathway is not weaker in the
fly; it is weaker in the prediction layer of this dataset.

Signed-path check (why we trust the LB1/LB3 labels): following synapses from each GRN set with
transmitter signs, the LB3 (sugar) set reaches MN9 with net excitation (+869 synapses at 3 hops,
+1,147 at 4) and the LB1 (bitter) set with net inhibition (−261 at 3 hops). The 55–129 Hz bitter
responses are the model failing at those gains, not the labels being swapped.

What this says about the demos: the brain people watched was running at a setting where sugar
extends the proboscis, but so does quinine, and an approaching shadow triggers feeding at 58 Hz,
and nothing ever switches off. It was a beautiful rendering of a network that had lost the ability
to inhibit. None of that is a criticism of the demo authors; it is what a five-constant model does
on a dataset it was never tuned for, and it is the reason a benchmark should exist.

## What differs and why it matters for scores

MaleCNS includes the ventral nerve cord, so "fraction of the brain active" counts ~37k extra
neurons that the female dataset does not have; the two datasets are compared on the same tasks
but are not the same animal, sex, or extent, and the stability thresholds were set on v783.
Treat cross-dataset rows as two experiments on the same instrument, not as a ranking.
