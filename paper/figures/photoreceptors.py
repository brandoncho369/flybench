"""Photoreceptors (R1-6, R7, R8) in Codex v783: how many, what transmitter Codex predicts, and how each build signs them.
In the fly they release histamine onto inhibitory (HisCl1) receptors. -> out/photoreceptors.numbers.json"""
import json
from pathlib import Path

import pandas as pd

from common import FLYBENCH, OUT

DATA = FLYBENCH / "data"
SHIU = Path.home() / ".cache" / "flybench" / "shiu783_src" / "Connectivity_783.parquet"
ct = pd.read_csv(DATA / "consolidated_cell_types.csv.gz")
nt = pd.read_csv(DATA / "neurons.csv.gz", usecols=["root_id", "nt_type"])
cls = pd.read_csv(DATA / "classification.csv.gz", usecols=["root_id", "class", "sub_class"])
ctcol = "primary_type" if "primary_type" in ct.columns else ct.columns[1]
pr = ct[ct[ctcol].astype(str).str.fullmatch(r"R(1-6|7[a-z]*|8[a-z]*)")].merge(nt, on="root_id", how="left")

cx = pd.read_csv(DATA / "connections.csv.gz", usecols=["pre_root_id", "syn_count", "nt_type"])
cx = cx[cx.pre_root_id.isin(set(pr.root_id))].dropna(subset=["nt_type"])
maj = (cx.groupby(["pre_root_id", "nt_type"]).syn_count.sum().reset_index()
       .sort_values(["pre_root_id", "syn_count", "nt_type"]).drop_duplicates("pre_root_id", keep="last"))
INH = {"GABA", "GLUT"}
blank = pr.nt_type.isna()
signed = pr.merge(maj.rename(columns={"pre_root_id": "root_id", "nt_type": "maj"}), on="root_id", how="left")
facts = {
    "n_photoreceptors": int(len(pr)),
    "by_type": {k: int(v) for k, v in pr[ctcol].value_counts().items()},
    "codex_nt": {str(k): int(v) for k, v in pr.nt_type.fillna("blank").value_counts().items()},
    "excitatory_reference": int((~pr.nt_type.isin(INH)).sum()),
    "inhibitory_after_signing": int(((signed.nt_type.isin(INH)) | (blank & signed.maj.isin(INH))).sum()),
    "class": {str(k): int(v) for k, v in pr.merge(cls, on="root_id", how="left")["class"].fillna("none").value_counts().items()},
}
s = pd.read_parquet(SHIU, columns=["Presynaptic_ID", "Connectivity", "Excitatory"])
s = s[s.Presynaptic_ID.isin(set(pr.root_id))]
shiu_inh = s.assign(w=s.Connectivity * (2 * s.Excitatory - 1)).groupby("Presynaptic_ID").w.sum()
facts["excitatory_after_signing"] = facts["n_photoreceptors"] - facts["inhibitory_after_signing"]
facts["shiu_with_outputs"] = int(len(shiu_inh))
facts["shiu_inhibitory"] = int((shiu_inh < 0).sum())
facts["shiu_excitatory"] = int((shiu_inh > 0).sum())
(OUT / "photoreceptors.numbers.json").write_text(json.dumps(facts, indent=2), encoding="utf-8")
print(json.dumps(facts, indent=1))
