"""Render the current full manuscript to HTML and PDF using local assets only."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname


def render(output):
    from markdown_it import MarkdownIt
    from weasyprint import HTML, default_url_fetcher
    from .render_paper import CSS
    root = Path(__file__).resolve().parents[1]
    source = root / "manuscript/paper-current.md"
    markdown = re.sub(r"<!-- (?:FOLLOWUP|ADAPTIVE|RISK_CONTROL)_RESEARCH_(?:START|END) -->", "", source.read_text(encoding="utf-8"))
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(markdown)
    body = re.sub(r"<p>(<img [^>]+>)</p>", r"<figure>\1</figure>", body)
    text = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Jev: fresh execution and graph synthesis</title><style>' + CSS + '</style></head><body>' + body + '</body></html>'
    def local(url, **kwargs):
        parsed = urlparse(url)
        if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
            raise ValueError("Only local assets allowed")
        path = Path(url2pathname(parsed.path)).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Asset outside repository")
        return default_url_fetcher(url, **kwargs)
    output.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=text, base_url=source.parent.as_uri() + "/", url_fetcher=local).write_pdf(output)
    # HTML stays beside its Markdown source so the relative asset links remain portable.
    source.with_suffix(".html").write_text(text, encoding="utf-8")
    output.with_suffix(".build.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "pdf_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "note": "Local-only assets; PDF bytes may vary with renderer and fonts."}, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    render(parser.parse_args().output)
