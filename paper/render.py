"""Fill {{file.path.to.value|format}} placeholders in DRAFT.md from figures/out/<file>.numbers.json -> DRAFT.rendered.md.
Fails, listing every placeholder it cannot resolve, so no number in the text is typed by hand.

    {{fig2_graph_builds.mean_graded.flywire783_ntfix@0.7|.3f}}   ->  0.731
    {{facts.n_tasks}}                                              ->  37
Keys containing dots are matched greedily against the JSON (e.g. "flywire783@0.7")."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures" / "out"
PH = re.compile(r"\{\{([^}|]+)(?:\|([^}]+))?\}\}")


def lookup(obj, parts):
    if not parts:
        return obj
    for n in range(len(parts), 0, -1):  # longest key first: keys may contain dots
        key = ".".join(parts[:n])
        if isinstance(obj, dict) and key in obj:
            return lookup(obj[key], parts[n:])
        if isinstance(obj, list) and n == 1 and key.isdigit() and int(key) < len(obj):
            return lookup(obj[int(key)], parts[1:])
    raise KeyError(".".join(parts))


def main() -> int:
    sources = {p.name[: -len(".numbers.json")]: json.loads(p.read_text(encoding="utf-8")) for p in OUT.glob("*.numbers.json")}
    text = (HERE / "DRAFT.md").read_text(encoding="utf-8")
    missing = []

    def sub(m):
        path, fmt = m.group(1).strip(), m.group(2)
        src, *rest = path.split(".")
        try:
            v = lookup(sources[src], rest)
        except KeyError:
            v = None
        if v is None:
            missing.append(path)
            return m.group(0)
        if fmt == "len":
            return str(len(v))
        return format(v, fmt) if fmt else str(v)

    out = PH.sub(sub, text)
    if missing:
        print("unresolved:\n  " + "\n  ".join(sorted(set(missing))))
        return 1
    (HERE / "DRAFT.rendered.md").write_text(out, encoding="utf-8")
    print(f"rendered {len(PH.findall(text))} numbers -> DRAFT.rendered.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
