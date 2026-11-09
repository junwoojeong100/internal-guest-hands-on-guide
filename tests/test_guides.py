"""Static checks for the published guide pages: local links, anchors, ids and Pages coverage."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted(path.name for path in ROOT.glob("*.html"))
EXTERNAL = ("http://", "https://", "mailto:", "data:", "javascript:")
SWITCH_ORDER = ["index.html", "github-copilot.html", "operator.html", "github-copilot-operator.html"]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: list[str] = []
        self.links: list[str] = []
        self.pre_labels: list[str | None] = []
        self.switch_links: list[tuple[str, bool]] = []
        self.scripts: list[str] = []
        self._in_switch = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "nav" and attributes.get("class") == "guide-switch":
            self._in_switch = True
        if tag in {"a", "link"} and attributes.get("href"):
            self.links.append(attributes["href"])
            if self._in_switch and tag == "a":
                self.switch_links.append((attributes["href"], attributes.get("aria-current") == "page"))
        for name in ("src", "poster"):
            if tag in {"img", "script", "source", "video"} and attributes.get(name):
                self.links.append(attributes[name])
        if tag == "script" and attributes.get("src"):
            self.scripts.append(attributes["src"])
        if tag == "pre":
            self.pre_labels.append(attributes.get("aria-label"))

    def handle_endtag(self, tag):
        if tag == "nav":
            self._in_switch = False


def parse(name: str) -> tuple[PageParser, str]:
    text = (ROOT / name).read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(text)
    return parser, text


def dynamic_ids(text: str) -> set[str]:
    """Ids that the page scripts create at load time (index.html builds its step sections)."""
    stages = {f"step-{stage}" for stage in re.findall(r'\{id:"([a-z-]+)",title:', text)}
    return stages | set(re.findall(r'\.id = "([\w-]+)"', text))


class GuidePageTests(unittest.TestCase):
    def test_all_four_guides_exist(self):
        self.assertEqual(sorted(SWITCH_ORDER), PAGES)

    def test_ids_are_unique_and_pre_blocks_have_copy_labels(self):
        for name in PAGES:
            parser, _ = parse(name)
            duplicates = {value for value in parser.ids if parser.ids.count(value) > 1}
            self.assertFalse(duplicates, f"{name}: duplicate ids {sorted(duplicates)}")
            self.assertTrue(all(parser.pre_labels), f"{name}: every <pre> needs an aria-label for its copy button")

    def test_local_links_and_anchors_resolve(self):
        known = {name: set(parse(name)[0].ids) | dynamic_ids(parse(name)[1]) for name in PAGES}
        problems = []
        for name in PAGES:
            for link in parse(name)[0].links:
                if link.startswith(EXTERNAL):
                    continue
                parts = urlsplit(link)
                target = name if not parts.path else parts.path
                if not (ROOT / unquote(target)).is_file():
                    problems.append(f"{name}: missing file {link}")
                elif parts.fragment and target in known and unquote(parts.fragment) not in known[target]:
                    problems.append(f"{name}: missing anchor {link}")
        self.assertEqual([], problems)

    def test_each_page_has_the_same_guide_switch_and_shared_scripts(self):
        for name in PAGES:
            parser, _ = parse(name)
            self.assertEqual(SWITCH_ORDER, [href for href, _ in parser.switch_links], name)
            self.assertEqual([name], [href for href, current in parser.switch_links if current], name)
            for script in ("assets/theme.js", "assets/navigation.js", "assets/copy.js"):
                self.assertIn(script, parser.scripts, f"{name} must load {script}")

    def test_pages_workflow_publishes_every_guide(self):
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        copy_line = next(line for line in workflow.splitlines() if line.strip().startswith("cp index.html"))
        for name in PAGES:
            self.assertIn(f"test -s {name}", workflow)
            self.assertIn(name, copy_line)


if __name__ == "__main__":
    unittest.main()
