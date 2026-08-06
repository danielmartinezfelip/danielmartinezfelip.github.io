#!/usr/bin/env python3
"""Static checks for the site. No third-party dependencies — stdlib only.

Run locally with:  python3 scripts/validate_site.py

Each check exists because something actually broke, or would have gone
unnoticed. Notably `check_og_image` catches declared social-card dimensions
drifting from the real file, which is exactly how the og:image tags ended up
claiming 800x800 for a 616x426 image.
"""

from __future__ import annotations

import html.parser
import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://danielmartinezfelip.github.io"

# Pages that make up the public site. 404.html is deliberately excluded from
# the sitemap/canonical checks — it is noindex and not a crawlable URL.
PAGES = [
    "index.html",
    "research.html",
    "conferences.html",
    "teaching.html",
    "curriculum_vitae.html",
]
ALL_HTML = PAGES + ["404.html"]

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

errors: list[str] = []
notes: list[str] = []


def fail(check: str, msg: str) -> None:
    errors.append(f"[{check}] {msg}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# HTML structure
# --------------------------------------------------------------------------
class TagBalance(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, tuple[int, int]]] = []
        self.problems: list[str] = []
        self.ids: list[str] = []
        self.anchors: list[str] = []
        self.srcs: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            self.ids.append(d["id"])
        href = d.get("href")
        if href:
            self.anchors.append(href)
        for key in ("src",):
            if d.get(key):
                self.srcs.append(d[key])
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.problems.append(f"stray </{tag}> at line {self.getpos()[0]}")
            return
        if self.stack[-1][0] != tag:
            open_tag, pos = self.stack[-1]
            self.problems.append(
                f"</{tag}> at line {self.getpos()[0]} closes <{open_tag}> opened at line {pos[0]}"
            )
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    return
            return
        self.stack.pop()


def check_html_structure() -> None:
    for page in ALL_HTML:
        p = TagBalance()
        p.feed(read(page))
        for problem in p.problems:
            fail("html", f"{page}: {problem}")
        for tag, pos in p.stack:
            fail("html", f"{page}: <{tag}> opened at line {pos[0]} is never closed")

        dupes = {i for i in p.ids if p.ids.count(i) > 1}
        for d in sorted(dupes):
            fail("html", f'{page}: duplicate id="{d}"')


# --------------------------------------------------------------------------
# Links: internal targets and in-page anchors must resolve
# --------------------------------------------------------------------------
def check_internal_links() -> None:
    for page in ALL_HTML:
        p = TagBalance()
        p.feed(read(page))
        ids = set(p.ids)

        for href in p.anchors:
            if href.startswith(("http://", "https://", "mailto:", "tel:", "#!")):
                continue
            if href.startswith("#"):
                anchor = href[1:]
                if anchor and anchor not in ids:
                    fail("links", f"{page}: '{href}' points at no element on the page")
                continue
            target = (ROOT / href.lstrip("/")).resolve()
            if not target.exists():
                fail("links", f"{page}: href '{href}' does not exist on disk")

        for src in p.srcs:
            if src.startswith(("http://", "https://", "data:")):
                continue
            if not (ROOT / src.lstrip("/")).resolve().exists():
                fail("links", f"{page}: src '{src}' does not exist on disk")


# --------------------------------------------------------------------------
# Head metadata
# --------------------------------------------------------------------------
def check_canonical() -> None:
    for page in PAGES:
        s = read(page)
        m = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        if not m:
            fail("canonical", f"{page}: missing <link rel=\"canonical\">")
            continue
        expected = f"{SITE}/" if page == "index.html" else f"{SITE}/{page}"
        if m.group(1) != expected:
            fail("canonical", f"{page}: canonical is '{m.group(1)}', expected '{expected}'")

    if 'name="robots" content="noindex"' not in read("404.html"):
        fail("canonical", "404.html: should be noindex")


def jpeg_size(path: Path) -> tuple[int, int]:
    """Read JPEG dimensions from the SOF marker without an image library."""
    d = path.read_bytes()
    i = 2
    while i < len(d) - 9:
        if d[i] != 0xFF:
            i += 1
            continue
        marker = d[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            h, w = struct.unpack(">HH", d[i + 5:i + 9])
            return w, h
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        i += 2 + struct.unpack(">H", d[i + 2:i + 4])[0]
    raise ValueError(f"no SOF marker in {path}")


def check_og_image() -> None:
    """Declared og:image dimensions must match the real file.

    This is the check that would have caught the tags claiming 800x800 for
    an image that was actually 616x426.
    """
    for page in PAGES:
        s = read(page)
        url = re.search(r'<meta property="og:image" content="([^"]+)"', s)
        w = re.search(r'<meta property="og:image:width" content="(\d+)"', s)
        h = re.search(r'<meta property="og:image:height" content="(\d+)"', s)
        if not (url and w and h):
            fail("og", f"{page}: missing og:image, og:image:width or og:image:height")
            continue

        local = ROOT / url.group(1).replace(SITE + "/", "")
        if not local.exists():
            fail("og", f"{page}: og:image '{url.group(1)}' has no local file")
            continue

        actual_w, actual_h = jpeg_size(local)
        if (actual_w, actual_h) != (int(w.group(1)), int(h.group(1))):
            fail("og", f"{page}: og:image declares {w.group(1)}x{h.group(1)} "
                       f"but {local.name} is {actual_w}x{actual_h}")

        # summary_large_image wants a wide card; a near-square image gets
        # cropped badly or downgraded to a small card.
        if 'name="twitter:card" content="summary_large_image"' in s:
            ratio = actual_w / actual_h
            if not (1.7 <= ratio <= 2.1):
                fail("og", f"{page}: twitter:card is summary_large_image but "
                           f"{local.name} has ratio {ratio:.2f} (want ~1.91)")
            if actual_w < 1200:
                fail("og", f"{page}: {local.name} is {actual_w}px wide; "
                           f"summary_large_image wants >=1200px")


def check_structured_data() -> None:
    found = 0
    for page in ALL_HTML:
        for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', read(page), re.S
        ):
            try:
                json.loads(block)
                found += 1
            except json.JSONDecodeError as e:
                fail("json-ld", f"{page}: invalid JSON-LD — {e}")
    if found == 0:
        fail("json-ld", "no JSON-LD found anywhere on the site")
    notes.append(f"JSON-LD blocks parsed: {found}")


# --------------------------------------------------------------------------
# Sitemap / robots
# --------------------------------------------------------------------------
def check_sitemap() -> None:
    try:
        tree = ET.parse(ROOT / "sitemap.xml")
    except ET.ParseError as e:
        fail("sitemap", f"sitemap.xml is not valid XML — {e}")
        return

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    listed = {loc.text for loc in tree.getroot().findall(".//sm:loc", ns)}

    expected = {f"{SITE}/" if p == "index.html" else f"{SITE}/{p}" for p in PAGES}
    for missing in sorted(expected - listed):
        fail("sitemap", f"page not listed in sitemap.xml: {missing}")
    for extra in sorted(listed - expected):
        fail("sitemap", f"sitemap.xml lists a URL with no page: {extra}")

    robots = read("robots.txt")
    if f"Sitemap: {SITE}/sitemap.xml" not in robots:
        fail("robots", "robots.txt does not point at the sitemap")


# --------------------------------------------------------------------------
# Consistency
# --------------------------------------------------------------------------
def strip_comments(text: str, path: str) -> str:
    """Remove comments so prose mentioning a host isn't mistaken for a reference.

    Comments legitimately name the CDNs we migrated away from, explaining why
    the files are vendored — that documentation should not trip the check.
    """
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)          # CSS + JS block
    if path.endswith(".html"):
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)      # HTML
    if path.endswith(".js"):
        text = re.sub(r"(?m)^\s*//.*$", " ", text)               # JS line
    return text


def check_no_cdn_dependencies() -> None:
    """Fonts and Leaflet are vendored; a CDN reference means one crept back."""
    banned = ["cdnjs.cloudflare.com", "cdn.jsdelivr.net", "unpkg.com",
              "fonts.googleapis.com", "fonts.gstatic.com"]
    for path in ALL_HTML + ["styles.css", "site.js"]:
        s = strip_comments(read(path), path)
        for host in banned:
            if host in s:
                fail("vendoring", f"{path}: references {host} — should be self-hosted")


def check_footer_date_single_source() -> None:
    """The date is rendered from site.js; HTML holds only a no-JS fallback.
    They must agree, or JS-off visitors see a different date."""
    m = re.search(r"var SITE_UPDATED = '([^']+)'", read("site.js"))
    if not m:
        fail("footer", "site.js: SITE_UPDATED constant not found")
        return
    canonical = m.group(1)
    for page in ALL_HTML:
        for fallback in re.findall(r'<span class="footer-updated">Updated ([^<]+)</span>',
                                   read(page)):
            if fallback.strip() != canonical:
                fail("footer", f"{page}: fallback says '{fallback.strip()}' but "
                               f"site.js says '{canonical}'")


def check_accessibility_basics() -> None:
    for page in ALL_HTML:
        s = read(page)
        if 'class="skip-link"' not in s:
            fail("a11y", f"{page}: missing skip-to-content link")
        if 'id="main-content"' not in s:
            fail("a11y", f"{page}: missing id=\"main-content\" landmark")
        for img in re.findall(r"<img\s[^>]*>", s):
            if "alt=" not in img:
                fail("a11y", f"{page}: <img> without alt attribute: {img[:60]}")


# --------------------------------------------------------------------------
def main() -> int:
    for check in (
        check_html_structure,
        check_internal_links,
        check_canonical,
        check_og_image,
        check_structured_data,
        check_sitemap,
        check_no_cdn_dependencies,
        check_footer_date_single_source,
        check_accessibility_basics,
    ):
        check()

    for note in notes:
        print(f"  note: {note}")

    if errors:
        print(f"\n{len(errors)} problem(s) found:\n", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"\nAll checks passed ({len(ALL_HTML)} pages).")
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main())
