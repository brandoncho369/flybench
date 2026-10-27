# The preprint's source

"Which build of the connectome a whole-brain fly model runs on changes what it can do" (Cho 2026,
Zenodo, [doi:10.5281/zenodo.23678526](https://doi.org/10.5281/zenodo.23678526)). Every number in the text is a placeholder in `DRAFT.md` filled from a script's output, so
none is typed by hand.

```
cd paper/figures
python facts.py; python graphfacts.py; python photoreceptors.py     # repo facts, graph statistics
python fig1_overview.py; python fig1a_pipeline.py; python fig2_graph_builds.py; python fig3_gain_windows.py
python fig4_antennal_lobe.py; python fig5_valence.py; python fig6_vision.py
python stats.py; python table_s1.py; python bibliography.py      # paired CIs, Table S1, references
cd ..
python render.py      # DRAFT.md -> DRAFT.rendered.md; fails if any placeholder cannot be resolved
python build.py       # -> paper.html, paper.pdf (headless Chrome or Edge; needs `pip install markdown`)
```

Scripts read `results/*.json` and `results/sweeps/`; `fig2_graph_builds.py`, `graphfacts.py` and
`photoreceptors.py` also load the pinned connectome caches (build them first, see the main README).
`figures/out/` holds the outputs as archived, including each script's `*.numbers.json` and the
Crossref metadata cache (`crossref.json`), so `render.py` runs without rebuilding anything.
