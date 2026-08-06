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


def request(url: str, method: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status


def check(url: str) -> tuple[str, str, str]:
    """Return (url, verdict, detail) where verdict is ok / blocked / broken / skipped.

    Only 'broken' fails the run. Publishers and social sites routinely refuse
    automated requests from CI ranges; that is not a broken link, and treating
    it as one would train everyone to ignore this job.
    """
    if any(h in url for h in SKIP_HOSTS):
        return url, "skipped", ""

    try:
        status = request(url, "HEAD")
        return url, "ok", str(status)
    except urllib.error.HTTPError as e:
        # Retry with GET before believing the failure. Plenty of servers reject
        # HEAD outright — including with 404, which is why 404 is retried here
        # rather than reported straight away.
        if e.code in (403, 404, 405, 429, 501):
            try:
                status = request(url, "GET")
                return url, "ok", str(status)
            except urllib.error.HTTPError as e2:
                if e2.code in (401, 403, 429):
                    return url, "blocked", f"HTTP {e2.code}"
                return url, "broken", f"HTTP {e2.code}"
            except Exception as e2:  # noqa: BLE001
                return url, "blocked", f"{type(e2).__name__}: {e2}"
        if e.code in (401, 429):
            return url, "blocked", f"HTTP {e.code}"
        return url, "broken", f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        # DNS/TLS/timeout: could be the network, could be the runner. Not proof
        # the link is dead.
        return url, "blocked", f"{type(e).__name__}: {e}"


def main() -> int:
    urls = collect()
    print(f"Checking {len(urls)} external link(s) across {len(PAGES)} pages\n")

    broken: list[str] = []
    blocked: list[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = sorted(pool.map(check, urls), key=lambda r: (r[1], r[0]))

    for url, verdict, detail in results:
        where = ", ".join(sorted(set(urls[url])))
        if verdict == "skipped":
            print(f"  skip     {url}")
        elif verdict == "ok":
            print(f"  ok       {detail}  {url}")
        elif verdict == "blocked":
            print(f"  blocked  {detail}  {url}")
            blocked.append(f"{detail}  {url}")
        else:
            print(f"  BROKEN   {detail}  {url}  ({where})")
            broken.append(f"{detail}  {url}  ({where})")

    if blocked:
        print(f"\n{len(blocked)} link(s) refused automated requests "
              f"(not treated as broken):")
        for b in blocked:
            print(f"  {b}")

    if broken:
        print(f"\n{len(broken)} link(s) appear genuinely broken:", file=sys.stderr)
        for b in broken:
            print(f"  {b}", file=sys.stderr)
        return 1

    print("\nNo broken external links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
