# danielmartinezfelip.github.io

Personal academic website — served by GitHub Pages from `main` at
<https://danielmartinezfelip.github.io>.

Plain HTML, CSS and JavaScript. No build step, no framework, no package
manager: what is in the repository is what is served.

## Layout

| Path | Purpose |
|---|---|
| `index.html` | Home / about |
| `research.html` | Publications, under review, work in progress, thesis |
| `conferences.html` | Talks timeline + map |
| `teaching.html` | Teaching experience |
| `curriculum_vitae.html` | CV (embedded PDF) |
| `404.html` | Not-found page |
| `styles.css` | All shared styling, including dark mode and print |
| `site.js` | All shared behaviour (see below) |
| `fonts/` | Self-hosted Inter (variable, latin + latin-ext) |
| `vendor/leaflet/` | Self-hosted Leaflet 1.9.4 for the conference map |
| `scripts/` | Validation scripts run by CI |
| `og-card.jpg` | 1200×630 social preview card |

### Shared code lives in `site.js`

Theme toggle, the document modal (CV and thesis summary), abstract toggles,
BibTeX cite buttons, the scroll-to-top button, the mobile menu, and the
footer date are all defined once in `site.js` and apply to every page that
loads it. Don't copy them back into individual pages.

The footer's "last updated" text comes from a single `SITE_UPDATED` constant
at the top of `site.js`. The text in each page's footer is only a fallback
for visitors with JavaScript disabled — if you change one, change both, or
CI will flag the mismatch.

The home page's job-market-paper card is populated from `research.html` at
runtime, so the paper's title, authors and status only need editing in one
place.

## Running locally

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000>. Opening the files directly with `file://`
mostly works, but the home page's job-market card will not populate, because
it fetches `research.html`.

## Checks

```bash
python3 scripts/validate_site.py   # structure, links, metadata — stdlib only
python3 scripts/check_links.py     # external links — needs network
```

`validate_site.py` runs on every pull request and must pass. It checks HTML
tag balance and duplicate ids, that internal links and in-page anchors
resolve, canonical URLs, JSON-LD parses, the sitemap matches the real pages,
that no CDN dependency has crept back in, that the footer fallback date
agrees with `site.js`, and that the declared `og:image` dimensions match the
actual image file.

`check_links.py` runs too, but is advisory only — journals, DOI resolvers and
university repositories go down or block CI runners, and that should not
block a merge.

## Adding a publication

Edit `research.html` only. Each entry is a `.paper-entry` block; copy an
existing one. The `Cite` button reads its BibTeX from the button's `data-bib`
attribute. Adding the `badge-jmp` badge marks an entry as the job market
paper, which is what the home page card looks for.

## Custom domain

The site currently uses the default `danielmartinezfelip.github.io`. A domain
you own is worth having for an academic site — it survives changing
institutions, and papers citing your URL keep working if you ever move off
GitHub Pages.

To switch, once you have registered a domain:

1. At your DNS provider, create four `A` records for the apex domain pointing
   at GitHub Pages: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`,
   `185.199.111.153`. Add a `CNAME` record for `www` pointing at
   `danielmartinezfelip.github.io`.
2. In the repository, go to **Settings → Pages → Custom domain**, enter the
   domain and save. GitHub commits a `CNAME` file for you.
3. Wait for the DNS check to pass, then tick **Enforce HTTPS**.
4. Update the absolute URLs in the repo to the new domain: `og:url`,
   `og:image`, `twitter:image`, `rel="canonical"`, `sitemap.xml`,
   `robots.txt`, the `SITE` constant in `scripts/validate_site.py`, and the
   JSON-LD `url` fields. `scripts/validate_site.py` will fail until these
   agree, which is the point.

Do not add a `CNAME` file before the DNS records resolve — GitHub Pages will
start serving the site at a domain that does not work yet, and
`danielmartinezfelip.github.io` will redirect to it.
