"""Build the preprint PDF: render.py (numbers from the result files) -> DRAFT.rendered.md + references -> paper.html
-> paper.pdf, printed by headless Chrome or Edge. Rerun the figure scripts first if a result file changed."""
import re
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
CSS = """
@page { size: A4; margin: 20mm 18mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; line-height: 1.45; color: #0b0b0b; background: #fff; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0 0 4pt; }
h1 + p { color: #52514e; margin-top: 0; }
h2 { font-size: 12.5pt; margin: 18pt 0 6pt; }
h3 { font-size: 10.5pt; margin: 14pt 0 4pt; }
h2, h3 { break-after: avoid; }
p { margin: 0 0 7pt; text-align: justify; hyphens: auto; }
img { display: block; max-width: 100%; max-height: 190mm; width: auto; margin: 10pt auto 4pt; break-inside: avoid; }
p:has(> img) { break-inside: avoid; break-after: avoid; }
table { border-collapse: collapse; font-size: 8pt; margin: 6pt 0 10pt; }
th, td { border-bottom: 1px solid #e1e0d9; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { border-bottom: 1px solid #898781; }
tr { break-inside: avoid; }
code { font-size: 8.5pt; }
table.s1 { font-size: 7pt; width: 100%; }
table.s1 td:nth-child(7) { width: 38%; }
h2#s1 { break-before: page; }
ul.refs { padding-left: 0; list-style: none; font-size: 8.5pt; }
ul.refs li { margin-bottom: 3pt; padding-left: 14pt; text-indent: -14pt; }
"""


def main() -> int:
    if subprocess.run([sys.executable, str(HERE / "render.py")]).returncode:
        return 1
    text = (HERE / "DRAFT.rendered.md").read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->\n?", "", text, flags=re.S)  # notes to self stay out of the PDF
    refs = (HERE / "figures" / "out" / "references.md").read_text(encoding="utf-8")
    text += ("\nThe list includes every source a task threshold cites (Table S1), formatted from Crossref metadata "
             "where a DOI exists.\n\n" + refs)
    table = (HERE / "figures" / "out" / "table_s1.md").read_text(encoding="utf-8")
    text += (f"\n## Supplementary Table S1\n\n**Table S1.** The {table.count(chr(10)) - 2} tasks. Tier: core (the reflexes "
             "the reference model was tuned to pass) or hard. RFC: pre-registered with predictions before the first run "
             "on real wiring (`docs/rfcs/` in the repository). Sources: the task's citation; conditions, checks and "
             "thresholds are in `tasks/*.yaml`.\n\n" + table)
    body = markdown.markdown(text, extensions=["tables"])
    body = re.sub(r"(<h2>References</h2>.*?)<ul>", r"\1<ul class=\"refs\">", body, count=1, flags=re.S)
    body = body.replace("<h2>Supplementary Table S1</h2>", "<h2 id=\"s1\">Supplementary Table S1</h2>")
    body = re.sub(r"(<h2 id=\"s1\">Supplementary Table S1</h2>.*?)<table>", r"\1<table class=\"s1\">", body, count=1, flags=re.S)
    html_f = HERE / "paper.html"
    html_f.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>flybench preprint</title>"
                      f"<style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
    browser = next((b for b in BROWSERS if Path(b).exists()), None)
    if browser is None:
        print("no Chrome or Edge found; open paper.html and print to PDF")
        return 1
    pdf = HERE / "paper.pdf"
    subprocess.run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={pdf}", html_f.as_uri()], check=True, capture_output=True)
    print(f"wrote {pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
