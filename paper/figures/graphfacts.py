"""Graph-construction facts for the text (RFC D1): Codex download vs Shiu et al. 2024's Connectivity_783.parquet,
and the blank-transmitter neurons. -> out/graphfacts.numbers.json. Needs the Codex CSVs in flybench/data and the
Shiu parquet (github.com/philshiu/Drosophila_brain_model) at SHIU below."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import FLYBENCH, OUT

SHIU = Path.home() / ".cache" / "flybench" / "shiu783_src" / "Connectivity_783.parquet"
DATA = FLYBENCH / "data"

s = pd.read_parquet(SHIU, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity", "Excitatory"])
cx = pd.read_csv(DATA / "connections.csv.gz", usecols=["pre_root_id", "post_root_id", "syn_count", "nt_type"])
agg = cx.groupby(["pre_root_id", "post_root_id"], as_index=False)["syn_count"].sum()
m = agg.merge(s, left_on=["pre_root_id", "post_root_id"], right_on=["Presynaptic_ID", "Postsynaptic_ID"], how="outer", indicator=True)
both = m[m["_merge"] == "both"]
neurons = pd.read_csv(DATA / "neurons.csv.gz", usecols=["root_id", "nt_type"])
blank = set(neurons.root_id[neurons.nt_type.isna()])
votes = cx[cx.pre_root_id.isin(blank)].dropna(subset=["nt_type"])
maj = (votes.groupby(["pre_root_id", "nt_type"]).syn_count.sum().reset_index()
       .sort_values(["pre_root_id", "syn_count", "nt_type"]).drop_duplicates("pre_root_id", keep="last"))
cls = pd.read_csv(DATA / "classification.csv.gz", usecols=["root_id", "super_class", "class"])
bc = cls[cls.root_id.isin(blank)]

facts = {
    "shiu_edges": int(len(s)), "codex_pairs": int(len(agg)), "shared_pairs": int(len(both)),
    "codex_only_pairs": int((m["_merge"] == "left_only").sum()), "shiu_only_pairs": int((m["_merge"] == "right_only").sum()),
    "shiu_synapse_share_lt5": float(s.Connectivity[s.Connectivity < 5].sum() / s.Connectivity.sum()),
    "count_ratio_median": float((both.syn_count / both.Connectivity).median()),
    "blank_nt_neurons": len(blank),
    "blank_signed_inhibitory": int(maj.nt_type.isin(["GABA", "GLUT"]).sum()),
    "blank_by_super_class": {k: int(v) for k, v in bc.super_class.value_counts().head(4).items()},
    "blank_visual_sensory": int((bc["class"] == "visual").sum()),
    "blank_synapse_share": float(cx[cx.pre_root_id.isin(blank)].syn_count.sum() / cx.syn_count.sum()),
}
# sign agreement on shared pairs, read from the two pinned caches the model runs on (an outer join turns the
# 18-digit root ids into floats and silently loses lookups, so the signs are not re-derived from the CSVs)
import sys
sys.path.insert(0, str(FLYBENCH))
from flybench.connectome import load_connectome  # noqa: E402
a, b = load_connectome("flywire783").W.tocsr(), load_connectome("flywire783_shiu").W.tocsr()
pattern = a.copy(); pattern.data = np.ones_like(pattern.data)
bs = b.multiply(pattern).tocsr(); r, c = bs.nonzero()
facts["same_sign_share_shared"] = float((np.sign(np.asarray(a[r, c]).ravel()) == np.sign(np.asarray(bs[r, c]).ravel())).mean())
(OUT / "graphfacts.numbers.json").write_text(json.dumps(facts, indent=2), encoding="utf-8")
print(json.dumps(facts, indent=1))
