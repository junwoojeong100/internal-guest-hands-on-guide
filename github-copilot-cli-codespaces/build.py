#!/usr/bin/env python3
"""Build the single-file Codespaces + Copilot CLI + MCP guide.

Inlines every image referenced as {{IMG:name}} in the source template
(src/index.src.html) from assets/name.(jpg|png|webp) as a data: URI, and
writes index.html next to this script. Pages publishes that file as it is,
and tests/test_guides.py fails when it differs from a fresh build.

Usage:  python3 github-copilot-cli-codespaces/build.py   (standard library only)
"""
import base64
import mimetypes
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src" / "index.src.html"
OUT = ROOT / "index.html"
ASSETS = ROOT / "assets"
PLACEHOLDER = re.compile(r"\{\{IMG:([A-Za-z0-9_-]+)\}\}")


def data_uri(name: str) -> str:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = ASSETS / f"{name}{ext}"
        if path.exists():
            mime = mimetypes.guess_type(path.name)[0]
            payload = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{payload}"
    sys.exit(f"missing image asset: assets/{name}.(jpg|png|webp)")


def render() -> str:
    html = PLACEHOLDER.sub(lambda m: data_uri(m.group(1)), SRC.read_text(encoding="utf-8"))
    if "{{IMG" in html:
        sys.exit("unresolved {{IMG:...}} placeholder remains")
    return html


def main() -> None:
    html = render()
    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.name}: {len(html.encode('utf-8')) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
