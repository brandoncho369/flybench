"""Repo-level numbers for the text: task counts, LIF constants, pinned builds, version. -> out/facts.numbers.json"""
import json
import sys
import tomllib

import yaml

from common import FLYBENCH, OUT, task_meta

CORE = ("stability", "sugar_to_proboscis", "bitter_suppression", "looming_to_giant_fiber", "taste_specificity")
meta = task_meta()
pins = json.loads((FLYBENCH / "flybench" / "manifests.json").read_text(encoding="utf-8"))
facts = {
    "version": tomllib.loads((FLYBENCH / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"],
    "zenodo_version_doi": "10.5281/zenodo.23655868",
    "n_tasks": len(meta), "n_core": sum(t in CORE for t in meta), "n_hard": sum(t not in CORE for t in meta),
    "n_circuits": len({m["circuit"] for m in meta.values()}),
    "lif": yaml.safe_load((FLYBENCH / "configs" / "shiu2024.yaml").read_text(encoding="utf-8")),
    "pins": {k: {"sha256_short": v.get("sha256", "")[:8], "n": v.get("n"), "n_edges": v.get("n_edges")} for k, v in pins.items()},
}
sys.path.insert(0, str(FLYBENCH))
from flybench.toy import build_toy_connectome  # noqa: E402  (the toy is built in code, so its manifest has no n)

toy = build_toy_connectome()
facts["pins"]["toy"].update(n=toy.n, n_edges=toy.n_edges)
(OUT / "facts.numbers.json").write_text(json.dumps(facts, indent=2), encoding="utf-8")
print(json.dumps({k: facts[k] for k in ("version", "n_tasks", "n_core", "n_hard", "n_circuits")}))
