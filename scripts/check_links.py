#!/usr/bin/env python3
"""Check that external links on the site still resolve.

Split out from validate_site.py because this one touches the network: DOIs,
journals and university repositories go down or rate-limit, and that should
never block a merge. The workflow runs it with continue-on-error.

Run locally with:  python3 scripts/check_links.py
"""

from __future__ import annotations

import concurrent.futures
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = sorted(ROOT.glob("*.html"))

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
TIMEOUT = 25

# Hosts that reliably reject automated requests. Their links are still worth
# having; we just cannot verify them from CI.
SKIP_HOSTS = (
    "scholar.google.com",     # blocks non-browser traffic
    "drive.google.com",       # requires a session for previews
    "linkedin.com",
)


def collect() -> dict[str, list[str]]:
    urls: dict[str, list[str]] = {}
    for page in PAGES:
        s = page.read_text(encoding="utf-8")
        # Ignore commented-out markup — those links are not live.
        s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
        for m in re.finditer(r'(?:href|src)="(https?://[^"]+)"', s):
            urls.setdefault(m.group(1), []).append(page.name)
    return urls


def check(url: str) -> tuple[str, int | str]:
    if any(h in url for h in SKIP_HOSTS):
        return url, "skipped"

    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return url, r.status
    except urllib.error.HTTPError as e:
        # Plenty of servers reject HEAD but serve GET.
        if e.code in (403, 405, 501):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    return url, r.status
            except Exception as e2:  # noqa: BLE001
                return url, f"{type(e2).__name__}: {e2}"
        return url, e.code
    except Exception as e:  # noqa: BLE001
        return url, f"{type(e).__name__}: {e}"


def main() -> int:
    urls = collect()
    print(f"Checking {len(urls)} external link(s) across {len(PAGES)} pages\n")

    bad: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for url, status in pool.map(check, urls):
            where = ", ".join(sorted(set(urls[url])))
            if status == "skipped":
                print(f"  skip  {url}")
            elif isinstance(status, int) and 200 <= status < 400:
                print(f"  ok    {status}  {url}")
            else:
                print(f"  FAIL  {status}  {url}  ({where})")
                bad.append(f"{status}  {url}  ({where})")

    if bad:
        print(f"\n{len(bad)} external link(s) did not resolve:", file=sys.stderr)
        for b in bad:
            print(f"  {b}", file=sys.stderr)
        return 1

    print("\nAll external links resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
