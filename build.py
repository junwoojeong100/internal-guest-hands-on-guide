#!/usr/bin/env python3
"""Build the single-file guide.

Inlines every image referenced as {{IMG:name}} in the source template
(src/github-copilot-cli-codespaces.src.html) from assets/name.(jpg|png|webp)
as a data: URI, and writes github-copilot-cli-codespaces.html at the repo root.

Usage:  python3 build.py        (Python 3.8+, standard library only)
"""
import base64
import mimetypes
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src" / "github-copilot-cli-codespaces.src.html"
OUT = ROOT / "github-copilot-cli-codespaces.html"
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


def main() -> None:
    html = PLACEHOLDER.sub(lambda m: data_uri(m.group(1)), SRC.read_text(encoding="utf-8"))
    if "{{IMG" in html:
        sys.exit("unresolved {{IMG:...}} placeholder remains")
    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.name}: {len(html.encode('utf-8')) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
