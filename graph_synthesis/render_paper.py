"""Render the illustrated manuscript locally; disallow remote or out-of-tree assets."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse
from .visualize import ROOT, check_outputs, sha256

CSS = '''
@page { size: A4; margin: 19mm 18mm 19mm;
  @top-right { content: "Jev / graph-synthesis assessment"; font: 8pt sans-serif; }
  @bottom-center { content: counter(page); font: 9pt sans-serif; }
}
body { font-family: "DejaVu Serif", serif; font-size: 10.5pt; line-height: 1.45; }
h1,h2,h3 { font-family: "DejaVu Sans", sans-serif; line-height: 1.22; break-after: avoid; }
h1 { font-size: 23pt; margin: 0 0 12pt; }
h2 { font-size: 15pt; margin-top: 22pt; }
h3 { font-size: 11.5pt; margin-top: 17pt; }
p { margin: 7pt 0; orphans: 3; widows: 3; }
code,pre { font-family: "DejaVu Sans Mono", monospace; font-size: 8.2pt; overflow-wrap: anywhere; }
pre { white-space: pre-wrap; }
a { text-decoration: none; overflow-wrap: anywhere; }
table { break-inside: avoid; width: 100%; border-collapse: collapse; font: 8pt/1.3 "DejaVu Sans", sans-serif; margin: 12pt 0; }
thead { display: table-header-group; }
th,td { padding: 5pt 4pt; text-align: left; border-bottom: .4pt solid; vertical-align: top; overflow-wrap: anywhere; }
tr { break-inside: avoid; }
figure { margin: 16pt 0; break-inside: avoid; }
figure img { width: 100%; max-height: 103mm; object-fit: contain; }
figcaption { font: 8.7pt/1.35 "DejaVu Sans", sans-serif; margin-top: 6pt; }
'''


def render_paper(root: Path, output: Path) -> dict:
    from markdown_it import MarkdownIt
    import markdown_it
    import weasyprint
    from weasyprint import HTML, default_url_fetcher
    root = root.resolve()
    check_outputs(root, root/"graph_synthesis/figures")
    source = root/"graph_synthesis/paper.md"
    text = source.read_text(encoding="utf-8")
    images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text)
    if len(images) != 15:
        raise ValueError("The illustrated paper must include all 15 documented figures")
    for name in images:
        path = (source.parent/name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Missing or unsafe manuscript image: " + name)
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(text)
    body = re.sub(r'<p>(<img [^>]+>)</p>\s*<p>(<strong>Figure [\s\S]*?)</p>', r'<figure>\1<figcaption>\2</figcaption></figure>', body)
    html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>From Typed Decisions to Repairable Evidence Graphs</title><meta name="author" content="Timothy Wayne Gregg"><style>'+CSS+'</style></head><body>'+body+'</body></html>'
    def local_assets(url, **kwargs):
        parsed = urlparse(url)
        if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
            raise ValueError("Remote asset access is disabled")
        path = Path(unquote(parsed.path)).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Out-of-tree asset access is disabled")
        return default_url_fetcher(url, **kwargs)
    output.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(source.parent)+"/", url_fetcher=local_assets).write_pdf(output)
    report = {"manuscript_sha256": sha256(source), "figure_manifest_sha256": sha256(root/"graph_synthesis/figures/MANIFEST.json"),
              "renderer_sha256": sha256(Path(__file__)), "markdown_it_version": markdown_it.__version__,
              "weasyprint_version": weasyprint.__version__, "figures": len(images), "pdf_sha256": sha256(output),
              "note": "Reproducible content and chart data; PDF/font bytes may vary by platform. No remote asset fetches are permitted."}
    output.with_suffix(".build.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render_paper(args.repository, args.output), indent=2))


if __name__ == "__main__":
    main()
