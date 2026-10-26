"""Supplementary Table S1: the 37 tasks, from flybench/tasks/*.yaml. Columns: number, name, tier, circuit, what it
tests (the task title), whether it was pre-registered as an RFC before its first run (docs/rfcs/NN_*.md), and its
sources (the task's citation, DOIs left to the reference list). -> out/table_s1.md, out/table_s1.numbers.json"""
import json
import re

import yaml

from common import FLYBENCH, OUT

rfcs = {p.name[:2] for p in (FLYBENCH / "docs" / "rfcs").glob("[0-9][0-9]_*.md")}
rows = []
for f in sorted((FLYBENCH / "tasks").glob("*.yaml")):
    y = yaml.safe_load(f.read_text(encoding="utf-8"))
    cite = re.sub(r";?\s*doi:\s*10\.\d{4,}/[^\s;)]+", "", str(y.get("citation") or ""))
    cite = re.sub(r"\(\s*\)", "", re.sub(r"\s+", " ", cite))
    cite = re.sub(r"[,;]\s*([);])", r"\1", re.sub(r",\s*,", ",", cite)).strip(" ;,")
    rows.append({"n": int(f.name[:2]), "name": y["name"], "tier": y.get("tier", "core"), "circuit": y.get("circuit", ""),
                 "title": y.get("title", ""), "rfc": f.name[:2] in rfcs, "sources": cite})
lines = ["| # | task | tier | circuit | what it tests | RFC | sources |", "|---|---|---|---|---|---|---|"]
for r in rows:
    lines.append(f"| {r['n']} | `{r['name']}` | {r['tier']} | {r['circuit']} | {r['title']} | {'yes' if r['rfc'] else '–'} | {r['sources']} |")
(OUT / "table_s1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
(OUT / "table_s1.numbers.json").write_text(json.dumps({"n_tasks": len(rows), "n_rfc": sum(r["rfc"] for r in rows),
                                                       "n_before_rfcs": sum(not r["rfc"] for r in rows),
                                                       "first_rfc_task": min(r["n"] for r in rows if r["rfc"])}, indent=2),
                                           encoding="utf-8")
print(len(rows), "tasks;", sum(r["rfc"] for r in rows), "with an RFC")
