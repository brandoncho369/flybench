"""Reference list: every DOI in tasks/*.yaml citations plus the ones the text cites that no task does, formatted from
Crossref metadata (cached in out/crossref.json, so a rerun is offline). -> out/references.md, sorted by first author."""
import html
import json
import re
import urllib.request

import yaml

from common import FLYBENCH, OUT

DOI = re.compile(r"10\.\d{4,}/[^\s;)\"]+")
EXTRA = ["10.1038/s41586-024-07763-9",  # Shiu et al. 2024
         "10.1038/s41586-024-07558-y",  # Dorkenwald et al. 2024 (FlyWire)
         "10.1038/s41586-024-07939-3",  # Lappalainen et al. 2024 (flyvis)
         "10.1038/nature24626",         # Klapoetke et al. 2017
         "10.1162/089976603322385063",  # Benda & Herz 2003
         "10.1016/j.cell.2024.03.016",  # Eckstein et al. 2024 (transmitter prediction)
         "10.1038/s41586-024-07686-5",  # Schlegel et al. 2024
         "10.1038/s41586-024-07968-y",  # Lin et al. 2024
         "10.1038/s41592-021-01183-7",  # Buhmann et al. 2021 (synapse detection)
         "10.1038/s41586-024-07451-8",  # Cowley et al. 2024
         "10.1038/s41586-025-09029-4",  # Vaxenburg et al. 2025
         "10.1038/s41592-024-02497-y",  # Wang-Chen et al. 2024 (NeuroMechFly v2)
         "10.1016/j.neuron.2020.07.040",  # Schrimpf et al. 2020 (Brain-Score)
         "10.1038/339704a0",            # Hardie 1989 (photoreceptor histamine)
         "10.1038/s41586-024-07982-0",  # Pospisil et al. 2024
         "10.1126/science.1065103"]     # Maslov & Sneppen 2002 (degree-preserving rewiring)
# references without a Crossref DOI, written out by hand
MANUAL = ["Agarwal et al. (2021). Deep reinforcement learning at the edge of the statistical precipice. "
          "*Advances in Neural Information Processing Systems* 34. arXiv:2108.13264",
          "Janelia FlyEM (2025). MaleCNS v1.0 connectome (male brain and ventral nerve cord). neuPrint dataset "
          "`male-cns:v1.0`, neuprint.janelia.org"]

dois = {d.lower().rstrip(".,") for f in (FLYBENCH / "tasks").glob("*.yaml")
        for d in DOI.findall(str(yaml.safe_load(f.read_text(encoding="utf-8")).get("citation") or ""))} | set(EXTRA)
cache_f = OUT / "crossref.json"
cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
for d in sorted(dois - cache.keys()):
    req = urllib.request.Request(f"https://api.crossref.org/works/{d}", headers={"User-Agent": "flybench-paper (github.com/brandoncho369/flybench)"})
    cache[d] = json.load(urllib.request.urlopen(req, timeout=30))["message"]
cache_f.write_text(json.dumps(cache), encoding="utf-8")


def fmt(d, m):
    au = m.get("author") or [{"family": m.get("publisher", "?")}]
    names = [a.get("family") or a.get("name", "?") for a in au]
    who = names[0] if len(names) == 1 else f"{names[0]} & {names[1]}" if len(names) == 2 else f"{names[0]} et al."
    year = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
    journal = (m.get("short-container-title") or m.get("container-title") or [""])[0]
    loc = ":".join(x for x in (m.get("volume"), re.sub(r"^(\d+)-\d+$", r"\1", m.get("page") or m.get("article-number") or "")) if x)
    clean = lambda s: html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip().rstrip(".")
    return f"{who} ({year}). {clean(m['title'][0])}. *{clean(journal)}* {loc}. doi:{d}"


lines = sorted([fmt(d, cache[d]) for d in dois] + MANUAL, key=str.lower)
(OUT / "references.md").write_text("\n".join(f"- {x}" for x in lines) + "\n", encoding="utf-8")
print(len(lines), "references")
